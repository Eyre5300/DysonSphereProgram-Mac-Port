from pathlib import Path
r=Path(__file__).resolve().parent/'port-project/Assets/Scripts/Assembly-CSharp'
for name,camera,image,rt in [('UIStarmap','screenCamera','screenImage','starmapRT'),('UIMilkyWay','screenCamera','screenImage','milkyWayRT'),('DysonMapCamera','editorCamera','dysonEditor.screenImage','screenRT'),('MechaEditorCamera','editorCamera','mechaEditor.screenImage','screenRT')]:
 p=r/(name+'.cs');s=p.read_text()
 if 'PortUIRenderTargets' in s:continue
 start=s.index('protected override void _OnCreate()');end=s.index('\n\t}',start)
 chunk=s[start:end];assert 'CheckOrCreateRTex();' in chunk;chunk=chunk.replace('CheckOrCreateRTex();',f'if (!PortUIRenderTargets.Enabled) CheckOrCreateRTex();\n\t\telse {camera}.enabled = false;');s=s[:start]+chunk+s[end:]
 k='protected override void _OnOpen()\n\t{';assert k in s;s=s.replace(k,k+'\n\t\tif (PortUIRenderTargets.Enabled) CheckOrCreateRTex();')
 start=s.index('protected override void _OnClose()');end=s.index('\n\t}',start);s=s[:end]+'\n\t\tif (PortUIRenderTargets.Enabled) ReleaseRTex();'+s[end:]
 k=rt+'.antiAliasing = 4;';assert k in s;s=s.replace(k,k+f'\n\t\t\tPortUIRenderTargets.Prepare({rt}, "{name}.{rt}");')
 start=s.index('void ReleaseRTex()');brace=s.index('{',start);code=f'\n\t\tif (PortUIRenderTargets.Enabled) {{ {camera}.enabled = false; {camera}.targetTexture = null; if ({image} != null) {image}.texture = null; }}'
 if name=='UIStarmap':
  s=s.replace('gizmoRT.antiAliasing = 4;','gizmoRT.antiAliasing = 4;\n\t\t\tPortUIRenderTargets.Prepare(gizmoRT, "UIStarmap.gizmoRT");')
  start=s.index('void ReleaseRTex()');brace=s.index('{',start)
  code+='\n\t\tif (PortUIRenderTargets.Enabled) { gizmoCamera.enabled = false; gizmoCamera.targetTexture = null; if (gizmoImage != null) gizmoImage.texture = null; }'
 s=s[:brace+1]+code+s[brace+1:];p.write_text(s)
 print(name)
