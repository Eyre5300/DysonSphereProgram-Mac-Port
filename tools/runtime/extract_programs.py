import os
"""Read-only inventory of all game D3D11 programs; omit engine builtins."""
from pathlib import Path
from collections import Counter
import json, struct, hashlib
import UnityPy, lz4.block

ROOT = Path(os.environ['DSP_GAME_INPUT'])/'DSPGAME_Data'
OUT = Path('work/dsp-shader-probe/batch')
(OUT/'programs').mkdir(parents=True, exist_ok=True)
records = {}; objects = []; errors = []

def blocks(blob):
    pos = 0
    while True:
        i = blob.find(b'DXBC', pos)
        if i < 0: return
        pos = i + 4
        if i + 32 > len(blob): continue
        size, count = struct.unpack_from('<II', blob, i+24)
        if not (0 < count < 100 and 32+count*4 <= size <= len(blob)-i): continue
        data = blob[i:i+size]; stage = None; tags = []
        for off in struct.unpack_from('<'+'I'*count, data, 32):
            if off+8 > len(data): break
            tag = data[off:off+4].decode('ascii'); tags.append(tag)
            if tag in ('SHDR','SHEX'):
                stage = struct.unpack_from('<I',data,off+8)[0] >> 16
        if stage is not None: yield data, stage, tags
        pos = i+size

def register(blob, ref):
    found=[]
    for code, stage, tags in blocks(blob):
        sha = hashlib.sha256(code).hexdigest()
        if sha not in records:
            (OUT/'programs'/f'{sha}.dxbc').write_bytes(code)
            records[sha] = dict(sha256=sha, bytes=len(code), stage=stage, chunks=tags, references=[])
        if ref not in records[sha]['references']: records[sha]['references'].append(ref)
        found.append(sha)
    return found

for filename in ['globalgamemanagers.assets','resources.assets','sharedassets0.assets']:
    env = UnityPy.load(str(ROOT/filename))
    count=0
    for obj in env.objects:
        if obj.type.name not in ('Shader','ComputeShader'): continue
        rec = dict(file=filename, path_id=obj.path_id, type=obj.type.name, programs=[])
        try:
            d=obj.parse_as_object()
            rec['name'] = d.m_ParsedForm.m_Name if obj.type.name=='Shader' else d.m_Name
            if obj.type.name=='Shader':
                rec['platforms']=d.platforms
                for platform, offsets, clens, dlens in zip(d.platforms,d.offsets,d.compressedLengths,d.decompressedLengths):
                    if platform != 4: continue
                    for segment,(offset,clen,dlen) in enumerate(zip(offsets,clens,dlens)):
                        raw=lz4.block.decompress(bytes(d.compressedBlob)[offset:offset+clen],uncompressed_size=dlen)
                        rec['programs'] += register(raw,dict(file=filename,path_id=obj.path_id,name=rec['name'],segment=segment))
            else:
                for vi,variant in enumerate(d.variants):
                    for kernel in variant.kernels:
                        codes=getattr(kernel,'uniqueVariants',None) or [v for _,v in (getattr(kernel,'variantMap',None) or [])]
                        if not codes and hasattr(kernel,'code'): codes=[kernel]
                        for ki,program in enumerate(codes):
                            rec['programs'] += register(bytes(program.code),dict(file=filename,path_id=obj.path_id,name=d.m_Name,kernel=str(kernel.name),variant=vi,kernel_variant=ki,thread_group=program.threadGroupSize))
            rec['programs']=sorted(set(rec['programs']))
            objects.append(rec); count+=1
        except Exception as e:
            errors.append(dict(file=filename,path_id=obj.path_id,error=repr(e)))
    print(filename, count, 'objects;',len(records),'unique programs',flush=True)
report=dict(objects=objects,programs=list(records.values()),errors=errors)
(OUT/'inventory.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
print(json.dumps(dict(objects=len(objects),unique_programs=len(records),stages=dict(Counter(p['stage'] for p in records.values())),errors=errors)),flush=True)
