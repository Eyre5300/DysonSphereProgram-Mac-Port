"""Stage recovered original lighting variants without modifying the shipping project.

Preserve the already repaired shader wrapper, render state, properties and fallback.
Only ordinary vertex/fragment passes are eligible; custom geometry/tessellation
requires its own recovery path. Run GPU reception checks before integration.
"""
from pathlib import Path
import json,re,hashlib,sys
r=Path('work/dsp-runtime');ns={}
exec((r/'recover_graphics.py').read_text().split('records=[];failures=[]')[0],ns)
dest=r/'lighting-variants-staged';dest.mkdir(exist_ok=True)
includes=dest/'PortLightingVariants';includes.mkdir(exist_ok=True)
selected=set(sys.argv[1:]) or {'VF Shaders/Forward/PBR Standard DFGround Tower1'}
if '--all' in selected:selected=set(json.loads((r/'shadow-variant-candidates.json').read_text()))
records=[];skipped=[]
for item in json.loads((r/'graphics-metadata/index.json').read_text()):
 name=item['name']
 if name not in selected:continue
 meta=json.loads(Path(item['path']).read_text());form=meta['m_ParsedForm'];blocks=[];programs=set();keywords_seen=set()
 if any(pa[s]['m_PlayerSubPrograms'] for ss in form['m_SubShaders'] for pa in ss['m_Passes'] for s in ['progGeometry','progHull','progDomain']):
  skipped.append({'name':name,'reason':'Custom geometry/tessellation; retain existing specialized recovery'});continue
 if name not in ns['shaderpaths']:
  skipped.append({'name':name,'reason':'No original shader path'});continue
 for ss in form['m_SubShaders']:
  for pa in ss['m_Passes']:
   if pa['m_Type']!=0:continue
   assert not any(pa[s]['m_PlayerSubPrograms'] for s in ['progGeometry','progHull','progDomain']),name
   stages=[];pass_keywords=set();pass_flags=[]
   for stage,macro in [('progVertex','SHADER_STAGE_VERTEX'),('progFragment','SHADER_STAGE_FRAGMENT')]:
    prog=pa[stage];choices=[(s,p) for g,ps in zip(prog['m_PlayerSubPrograms'],prog['m_ParameterBlobIndices']) for s,p in zip(g,ps)]
    choices=[(s,p) for s,p in choices if not any('STEREO' in form['m_KeywordNames'][i] for i in s['m_KeywordIndices'])]
    variants={};relevant=set()
    for sub,pi in choices:
     flags=frozenset(form['m_KeywordNames'][i] for i in sub['m_KeywordIndices']);relevant.update(flags);pass_flags.append(flags)
     code,sha=ns['rebuild_stage'](meta,pa,stage,sub,Path(item['path']).stem+'-'+str(pi)+'.bin')
     for buffer in set(re.findall(r'Buffer<uint4> (\w+);',code)):
      code=code.replace(buffer+'.Load(','PortRead'+buffer+'(')
      code=code.replace('Buffer<uint4> '+buffer+';',f'Buffer<uint4> {buffer};\nuint _PortWords{buffer};\nuint4 PortRead{buffer}(uint i){{return i<_PortWords{buffer}?{buffer}.Load(i):uint4(0,0,0,0);}}')
     key=hashlib.sha256(code.encode()).hexdigest();(includes/(key+'.hlsl')).write_text(code);variants[flags]=key;programs.add(key)
    pass_keywords.update(relevant);body=[]
    # Original compiled combinations take precedence; stage-irrelevant keywords
    # do not participate. More general originals cover uncompiled engine mixes.
    ordered=sorted(variants.items(),key=lambda x:(-len(x[0]),sorted(x[0])))
    for vi,(flags,key) in enumerate(ordered):
     condition=' && '.join('defined('+k+')' for k in sorted(flags)) or '1'
     body+=['#if '+condition if vi==0 else '#elif '+condition,'#include "Assets/PortLightingVariants/'+key+'.hlsl"']
    fallback=min(variants,key=len)
    body+=['#else','#include "Assets/PortLightingVariants/'+variants[fallback]+'.hlsl"','#endif']
    stages.append('#if defined('+macro+')\n'+'\n'.join(body)+'\n#endif')
   pragmas=[];remaining=set(pass_keywords)
   for group in [{'DIRECTIONAL','POINT','SPOT','POINT_COOKIE','DIRECTIONAL_COOKIE'},{'SHADOWS_DEPTH','SHADOWS_CUBE'},{'FOG_LINEAR','FOG_EXP','FOG_EXP2'}]:
    used=remaining&group
    if used:
     optional=any(not(flags&used) for flags in pass_flags)
     pragmas.append('#pragma multi_compile '+('__ ' if optional else '')+' '.join(sorted(used)));remaining-=used
   pragmas+=['#pragma multi_compile __ '+k for k in sorted(remaining)]
   keywords_seen.update(pass_keywords)
   blocks.append('\n'.join(['HLSLPROGRAM','#pragma target 5.0','#pragma skip_optimizations metal','#pragma vertex RecoveredVert','#pragma fragment RecoveredFrag',*pragmas,*stages,'ENDHLSL']))
 paths=[]
 for original,_ in ns['shaderpaths'][name]:
  rel=original.relative_to(r/'recovered-project/ExportedProject');current=(r/'port-project'/rel).read_text()
  assert len(re.findall('HLSLPROGRAM',current))==len(blocks),(name,'pass count changed')
  it=iter(blocks);text=re.sub(r'HLSLPROGRAM.*?ENDHLSL',lambda m:next(it),current,flags=re.S)
  target=dest/rel;target.parent.mkdir(parents=True,exist_ok=True);target.write_text(text);paths.append(str(rel))
 records.append({'name':name,'paths':paths,'programs':len(programs),'keywords':sorted(keywords_seen)})
 print(name,len(programs),'programs staged',flush=True)
(dest/'manifest.json').write_text(json.dumps(records,indent=2)+'\n')
(dest/'skipped.json').write_text(json.dumps(skipped,indent=2)+'\n')
