import os
from pathlib import Path
import json,UnityPy
root=Path(os.environ['DSP_GAME_INPUT'])/'DSPGAME_Data'
out=Path('work/dsp-runtime/shader-metadata');out.mkdir(exist_ok=True)
for filename in ['resources.assets','sharedassets0.assets','globalgamemanagers.assets']:
 env=UnityPy.load(str(root/filename))
 for obj in env.objects:
  if obj.type.name!='Shader':continue
  d=obj.parse_as_object(); name=d.m_ParsedForm.m_Name
  if 'Widget Alpha' in name or name=='VF Shaders/Forward/Planet Surface' or 'Text Alpha' in name:
   data=obj.read_typetree(); data.pop('compressedBlob',None)
   (out/(str(obj.path_id)+'-'+filename+'.json')).write_text(json.dumps(data,indent=2))
   print(name,obj.path_id,filename,flush=True)
