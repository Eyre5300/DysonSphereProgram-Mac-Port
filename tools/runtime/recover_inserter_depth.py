"""Restore the owned inserter shader's SOFTPARTICLES_ON depth-sampling programs."""
from pathlib import Path
import json,re

def adapt_recovery(source):
 edits=[("out=root/'preflight-project/Assets/RecoveredGraphics'","out=root/'preflight-project/Assets/RecoveredInserterDepth'"),
        (" name=item['name']\n if len(sys.argv)"," name=item['name']\n if name!='VF Shaders/Forward/Inserter Arrow':continue\n if len(sys.argv)"),
        ("k.startswith('_ENABLE_') or k=='_DISABLE_MIP'","k.startswith('_ENABLE_') or k=='_DISABLE_MIP' or k=='SOFTPARTICLES_ON'"),
        ("root/'recovered-graphics-manifest.json'","root/'inserter-depth-variants-manifest.json'")]
 # Reject changed recovery layouts before running any export or overwriting shaders.
 for old,new in edits:
  if source.count(old)!=1:raise ValueError('Unsupported owned shader recovery layout: '+old.split('\n')[0])
 for old,new in edits:source=source.replace(old,new,1)
 return source

def restore():
 r=Path('work/dsp-runtime');source=adapt_recovery((r/'recover_graphics.py').read_text())
 exec(compile(source,'recover_owned_inserter_depth','exec'),{})
 manifest=json.loads((r/'inserter-depth-variants-manifest.json').read_text())
 if manifest['failures'] or len(manifest['shaders'])!=1:raise ValueError('Owned inserter depth recovery failed')
 pending=[]
 for row in manifest['shaders']:
  if len(row['programs'])!=8:raise ValueError('Unexpected owned inserter vertex/fragment selection count')
  text=(r/'preflight-project'/row['path']).read_text()
  if '#pragma multi_compile __ SOFTPARTICLES_ON' not in text or '_CameraDepthTexture.Sample' not in text:raise ValueError('Original depth branch missing')
  for name in set(re.findall(r'Buffer<uint4> (\w+);',text)):
   text=text.replace(name+'.Load(','PortRead'+name+'(')
   text=text.replace('Buffer<uint4> '+name+';',f'Buffer<uint4> {name};\nuint _PortWords{name};\nuint4 PortRead{name}(uint i){{return i<_PortWords{name}?{name}.Load(i):uint4(0,0,0,0);}}')
  if 'asfloat(' in text:text=text.replace('#pragma target 5.0','#pragma target 5.0\n#pragma skip_optimizations metal')
  for relative in row['original_paths']:pending.append((r/'port-project'/relative,text))
 for path,text in pending:path.write_text(text)
 print('Restored owned inserter screen-depth vertex/fragment branches; original state/materials unchanged')

if __name__=='__main__':restore()
