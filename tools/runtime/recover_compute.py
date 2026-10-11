"""Recover compute HLSL and restore Unity property names from exported metadata.

Input is the user's local purchased game. Generated files stay local.
Each kernel is compiled separately with its original constant-buffer variant.
"""
from pathlib import Path
import hashlib, json, re, struct, subprocess

root = Path(__file__).resolve().parent
workspace = root.parents[1]
programs = workspace / 'work/dsp-shader-probe/batch/programs'
cross = workspace / 'work/SPIRV-Cross/spirv-cross'
output = root / 'preflight-project/Assets/Resources/RecoveredCompute'
output.mkdir(parents=True, exist_ok=True)
cache = root / 'recovered-hlsl'
cache.mkdir(exist_ok=True)
manifest = []

from restore_append import restore_append_buffers

def cb_source(cb, array_name):
    declarations = []
    slots = {}
    array_cases = []
    types = {0:'float', 1:'int', 2:'uint', 5:'uint'}
    for p in cb['params']:
        assert p['rowCount'] == 1
        typ = types[p['type']]
        n = p['colCount']; name = p['name']; offset = p['offset']
        assert re.fullmatch(r'[A-Za-z_]\w*', name)
        hlsl_type = typ + (str(n) if n > 1 else '')
        array = p['arraySize']; suffix = f'[{array}]' if array else ''
        component = 'xyzw'[(offset % 16)//4]
        declarations.append(f'    {hlsl_type} {name}{suffix} : packoffset(c{offset//16}.{component});')
        if array:
            assert n == 4 and offset % 16 == 0 and typ == 'float'
            array_cases.append(f'    if (index >= {offset//16}u && index < {offset//16+array}u) return {name}[index - {offset//16}u];')
        else:
            for lane in range(n):
                expr = name + ('.'+'xyzw'[lane] if n>1 else '')
                if typ != 'float': expr = 'asfloat('+expr+')'
                index = (offset + lane*4)//16
                slot = slots.setdefault(index, ['0.0f']*4)
                slot[((offset + lane*4)%16)//4] = expr
    function = 'Read_' + array_name
    lines = ['cbuffer RecoveredGlobals : register(b0)', '{', *declarations, '};',
             f'float4 {function}(uint index)', '{', *array_cases]
    for index, components in sorted(slots.items()):
        lines.append(f'    if (index == {index}u) return float4('+', '.join(components)+');')
    lines += ['    return 0.0f.xxxx;', '}']
    return '\n'.join(lines), function

for obj in json.loads((root/'compute-metadata.json').read_text()):
    data = obj['data']; assert len(data['variants']) == 1
    platform = data['variants'][0]; blocks=[]; pragma=[]; kernels=[]
    for number, kernel in enumerate(platform['kernels']):
        assert len(kernel['uniqueVariants']) == 1
        variant = kernel['uniqueVariants'][0]
        binary = bytes.fromhex(variant['code']); sha = hashlib.sha256(binary).hexdigest()
        spv = programs/(sha+'.spv'); assert spv.exists(), sha
        hlsl = cache/(sha+'.hlsl')
        if not hlsl.exists():
            subprocess.run([str(cross), str(spv), '--hlsl', '--shader-model', '50', '--output', str(hlsl)], check=True)
        text = hlsl.read_text()
        matches = list(re.finditer(r'cbuffer\s+\w+\s*:\s*register\(b\d+\)\s*\{\s*float4\s+(\w+)\[(\d+)\]\s*:\s*packoffset\(c0\);\s*\};', text))
        assert len(matches) == len(variant['cbs']) <= 1
        if matches:
            indices = bytes.fromhex(variant['cbVariantIndices'])
            cb_index = struct.unpack('<I', indices)[0]
            cb = platform['constantBuffers'][cb_index]
            m = matches[0]; name = m[1]
            rebuilt, function = cb_source(cb,name)
            text = text[:m.start()]+rebuilt+text[m.end():]
            text = re.sub(r'\b'+re.escape(name)+r'\[([^\[\]]+)\]',lambda m:function+'('+m[1]+')',text)
            assert not re.search(r'\b'+re.escape(name)+r'\[', text)
        # Remove register suffixes before renaming identifiers; never rename
        # register tokens as if they were variable identifiers.
        text = re.sub(r'\s*:\s*register\([uts]\d+\)', '', text)
        names={}
        for group, prefix in [('inBuffers','t'),('outBuffers','u'),('textures','t')]:
            for item in variant[group]:
                names[prefix+str(item['bindPoint'])] = item['name']
                if group == 'textures' and item['samplerBindPoint'] >= 0:
                    names['s'+str(item['samplerBindPoint'])] = 'sampler'+item['name']
        if names:
            text=re.sub(r'\b(?:'+ '|'.join(map(re.escape,names)) +r')\b',lambda m:names[m[0]],text)
        for old, new in names.items():
            # Explicit registers retain original DirectX binding indices;
            # Unity resolves properties by their recovered names on Metal.
            text=re.sub(r'(?m)^(\w+(?:<[^>]+>)?\s+'+re.escape(new)+r')\s*;',lambda m:m[1]+' : register('+old+');',text)
        text=restore_append_buffers(text,names)
        assert not variant['builtinSamplers'], 'Builtin sampler mapping not implemented'
        text=re.sub(r'\bvoid main\(', 'void '+kernel['name']+'(', text)
        pragma.append(f'#pragma kernel {kernel["name"]} RECOVERED_KERNEL_{number}')
        blocks.append(f'#if defined(RECOVERED_KERNEL_{number})\n{text}\n#endif')
        size=list(struct.unpack('<III',bytes.fromhex(variant['threadGroupSize'])))
        kernels.append({'name':kernel['name'],'dxbc_sha256':sha,'threads':size})
    path=output/(data['m_Name']+'.compute')
    generated = '// Locally recovered game compute shader; original Unity bindings preserved.\n'+'\n'.join(pragma)+'\n#pragma target 5.0\n'+'\n'.join(blocks)
    if data['m_Name'] in {'DFSLancerCulling','DFSHumpbackCulling','DFSFortressCulling','DFGRaiderCulling','DFGRangerCulling','DFGGuardianCulling','DFGTruckCulling','DFSAntCulling'}:
        from typed_register_probe import transform
        generated = transform(generated)
    path.write_text(generated)
    manifest.append({'name':data['m_Name'],'path':str(path.relative_to(root/'preflight-project')),'original_asset':obj['path'],'kernels':kernels})
    print(data['m_Name'],len(kernels),'kernels',flush=True)
(root/'recovered-compute-manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
print('Generated',len(manifest),'compute assets;',sum(len(x['kernels']) for x in manifest),'kernels.')
