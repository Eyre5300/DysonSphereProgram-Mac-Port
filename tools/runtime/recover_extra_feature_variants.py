"""Restore omitted UI clipping and explicit effect toggles from original DXBC.
Keep untouched the manually lowered geometry/tessellation and all Post FX.
"""
from pathlib import Path
import json,re
r=Path('work/dsp-runtime')
selected={'UI/Unlit/Detail','UI/TranslucentImage','UI/TranslucentImage3D','UI Ex/Praseable Text','VF Shaders/Procedure Particle/General Bomb Explosion','VF Shaders/Procedure Particle/Local Explosion','VF Shaders/Forward Spacecraft/Enemy Tri-planar Connection','VF Shaders/Renderable Instancing/DF Ground Tower Plasma','VF Shaders/Renderable Instancing/DF Space Tower Plasma'}
s=(r/'recover_graphics.py').read_text()
s=s.replace("out=root/'preflight-project/Assets/RecoveredGraphics'","out=root/'preflight-project/Assets/RecoveredExtraVariants'")
s=s.replace(" name=item['name']\n if len(sys.argv)"," name=item['name']\n if name not in "+repr(selected)+":continue\n if len(sys.argv)")
s=s.replace("k.startswith('_ENABLE_') or k=='_DISABLE_MIP'","k.startswith('_') or k.startswith('UNITY_UI_')")
s=s.replace("root/'recovered-graphics-manifest.json'","root/'extra-feature-variants-manifest.json'")
exec(compile(s,'recover_graphics_extra','exec'),{})
manifest=json.loads((r/'extra-feature-variants-manifest.json').read_text());assert not manifest['failures']
for record in manifest['shaders']:
 text=(r/'preflight-project'/record['path']).read_text()
 # Reapply the established bounds-checked Metal buffer adapter locally.
 for name in set(re.findall(r'Buffer<uint4> (\w+);',text)):
  text=text.replace(name+'.Load(','PortRead'+name+'(')
  text=text.replace('Buffer<uint4> '+name+';',f'Buffer<uint4> {name};\nuint _PortWords{name};\nuint4 PortRead{name}(uint i){{return i<_PortWords{name}?{name}.Load(i):uint4(0,0,0,0);}}')
 if 'asfloat('in text:text=text.replace('#pragma target 5.0','#pragma target 5.0\n#pragma skip_optimizations metal')
 for path in record['original_paths']:(r/'port-project'/path).write_text(text)
print('Installed',len(manifest['shaders']),'shader families with original explicit feature variants')
