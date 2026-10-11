from pathlib import Path
import json,re,hashlib
root=Path('work/dsp-runtime')
ns={}
exec((root/'recover_graphics.py').read_text().split('records=[];failures=[]')[0],ns)
include=root/'port-project/Assets/PortRecoveredVariants';include.mkdir(exist_ok=True)
records=[]
for item in json.loads((root/'graphics-metadata/index.json').read_text()):
 name=item['name']
 if not name.startswith('Hidden/Post FX/'):continue
 meta=json.loads(Path(item['path']).read_text());form=meta['m_ParsedForm']
 header=ns['shaderpaths'][name][0][1];output=[header];programs=set()
 for ss in form['m_SubShaders']:
  output.append('SubShader {')
  if ss['m_Tags']['tags']:output.append('Tags { '+' '.join(json.dumps(k)+'='+json.dumps(v)for k,v in ss['m_Tags']['tags'])+' }')
  output.append('LOD '+str(ss['m_LOD']))
  for pa in ss['m_Passes']:
   if pa['m_Type']==1:output.append('UsePass '+json.dumps(pa['m_UseName']));continue
   assert pa['m_Type']==0
   stages=[];keywords=set()
   for stage,macro in [('progVertex','SHADER_STAGE_VERTEX'),('progFragment','SHADER_STAGE_FRAGMENT')]:
    prog=pa[stage];choices=[(s,p)for g,ps in zip(prog['m_PlayerSubPrograms'],prog['m_ParameterBlobIndices'])for s,p in zip(g,ps)]
    choices=[(s,p)for s,p in choices if not any('STEREO'in form['m_KeywordNames'][i]for i in s['m_KeywordIndices'])]
    variants=[];relevant=set()
    for sub,pi in choices:
     flags=frozenset(form['m_KeywordNames'][i] for i in sub['m_KeywordIndices']);relevant.update(flags)
     code,sha=ns['rebuild_stage'](meta,pa,stage,sub,Path(item['path']).stem+'-'+str(pi)+'.bin')
     key=hashlib.sha256(code.encode()).hexdigest();inc=include/(key+'.hlsl')
     if not inc.exists():inc.write_text(code)
     variants.append((flags,key));programs.add(key)
    keywords.update(relevant)
    body=[]
    if len({v[1]for v in variants})==1:body=['#include "Assets/PortRecoveredVariants/'+variants[0][1]+'.hlsl"']
    else:
     unique={f:k for f,k in variants}
     for vi,(flags,key)in enumerate(sorted(unique.items(),key=lambda v:(-len(v[0]),sorted(v[0])))):
      condition=' && '.join((''if k in flags else '!')+'defined('+k+')'for k in sorted(relevant))or'1'
      body+=['#if '+condition if vi==0 else '#elif '+condition,'#include "Assets/PortRecoveredVariants/'+key+'.hlsl"']
     body+=['#else','#error Unsupported original Post FX keyword combination','#endif']
    stages.append('#if defined('+macro+')\n'+'\n'.join(body)+'\n#endif')
   groups=[['DEPTH_OF_FIELD','DEPTH_OF_FIELD_COC_VIEW'],['BLOOM','BLOOM_LENS_DIRT'],['COLOR_GRADING','COLOR_GRADING_LOG_VIEW'],['VIGNETTE_CLASSIC','VIGNETTE_MASKED'],['TONEMAPPING_NEUTRAL','TONEMAPPING_FILMIC'],['FOG_LINEAR','FOG_EXP','FOG_EXP2']]
   pragmas=[];remaining=set(keywords)
   for group in groups:
    used=[k for k in group if k in remaining]
    if used:pragmas.append('#pragma multi_compile __ '+' '.join(used));remaining-=set(used)
   pragmas+=['#pragma multi_compile __ '+k for k in sorted(remaining)]
   output+=['Pass {',ns['state'](pa),'HLSLPROGRAM','#pragma target 5.0','#pragma skip_optimizations metal','#pragma vertex RecoveredVert','#pragma fragment RecoveredFrag',*pragmas,*stages,'ENDHLSL','}']
  output.append('}')
 output.append('Fallback Off\n}')
 paths=[]
 for p,_ in ns['shaderpaths'][name]:
  rel=p.relative_to(root/'recovered-project/ExportedProject');target=root/'port-project'/rel;target.write_text('\n'.join(output));paths.append(str(rel))
 records.append(dict(name=name,paths=paths,programs=len(programs)))
 print(name,len(programs),flush=True)
(root/'postfx-variants-manifest.json').write_text(json.dumps(records,indent=2))
