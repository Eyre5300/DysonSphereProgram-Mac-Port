"""Give ordinary built inserter arrows an owned-shader derivative with depth testing."""
import argparse
from pathlib import Path
ORIGINAL='VF Shaders/Forward/Inserter Arrow'
REPLACEMENT='DSPPort/Inserter Arrow Occluded'
def apply(project, shader_only=False):
 project=Path(project);source=project/'Assets/Resources/shaders/vff inserterarrow.shader'
 text=source.read_text()
 if text.count('Shader "'+ORIGINAL+'"')!=1 or text.count('ZTest Off')!=1 or text.count('ZWrite Off')!=1:
  raise ValueError('Unsupported owned inserter arrow shader layout')
 derived=text.replace('Shader "'+ORIGINAL+'"','Shader "'+REPLACEMENT+'"',1).replace('ZTest Off','ZTest LEqual',1)
 path=project/'Assets/Scripts/Assembly-CSharp/InserterRenderer.cs';original=path.read_text();patched=original
 anchor='base.Init(_manager, _modelId, _objectDesc, _argBuffer, _argOffset, replaceMat);'
 call='PortInserterOcclusion.Configure(this);'
 if not shader_only:
  if original.count(anchor)!=2 or original.count(call)>1:raise ValueError('Unsupported inserter Init layout')
  offset=original.index(anchor)+len(anchor)
  # Only GPUInstancingManager ordinary-world overload, never the blueprint overload.
  prefix=original[:original.index(anchor)]
  if 'Init(GPUInstancingManager' not in prefix or 'Init(BPGPUInstancingManager' in prefix:raise ValueError('Unexpected inserter overload ordering')
  if call in original:
   if original.index(call)!=offset+len('\n\t\t'):raise ValueError('Mixed inserter occlusion patch')
  else:patched=original[:offset]+'\n\t\t'+call+original[offset:]
 target=project/'Assets/Resources/PortInserterArrowOccluded.shader'
 if target.exists() and target.read_text()!=derived:raise ValueError('Existing shader derivative does not match owned input')
 target.write_text(derived)
 if patched!=original:path.write_text(patched)
if __name__=='__main__':
 parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--project',type=Path,required=True);parser.add_argument('--shader-only',action='store_true');args=parser.parse_args();apply(args.project,args.shader_only)
