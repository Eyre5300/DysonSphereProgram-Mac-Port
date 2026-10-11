#!/usr/bin/env python3
"""Apply authored Mac platform corrections to a private exported project.
No recovered game source is included; original method bodies remain in local input.
Run after apply_portability.py and apply_platform_startup.py, before buffer binding.
"""
from pathlib import Path
import argparse

def replace_once(text, old, new):
    if text.count(old)!=1:raise ValueError('Expected one unmodified patch anchor: '+repr(old[:100]))
    return text.replace(old,new,1)
def wrap_method(text, signature, body, condition='UNITY_STANDALONE_OSX || UNITY_IOS || UNITY_EDITOR_OSX'):
    start=text.index(signature);begin=text.index('{',start);depth=1;end=begin+1
    while depth:
        depth+=(text[end]=='{')-(text[end]=='}');end+=1
    return text[:begin+1]+'\n#if '+condition+'\n'+body+'\n#else\n'+text[begin+1:end-1]+'\n#endif\n'+text[end-1:]
def apply(project):
    root=project/'Assets/Scripts/Assembly-CSharp'
    def edit(name,fn):
        p=root/name;p.write_text(fn(p.read_text()))
    edit('GameConfig.cs',lambda s:wrap_method(s,'public static void InitOverrideDocumentFolder()',
        'overrideDocumentFolder = UnityEngine.Application.persistentDataPath + "/LocalPortData/";\nreturn;'))
    edit('CpuTopology.cs',lambda s:wrap_method(s,'public static CpuTopology DetectCpuTopology()',
        '''int count = Math.Max(1, Environment.ProcessorCount);
var portable = new CpuTopology { maxProcessorCount = count, physicalCores = new CpuPhysicalCore[count] };
for (int i=0;i<count;i++) portable.physicalCores[i] = new CpuPhysicalCore { index=i, logicalProcessors=new[]{i} };
return portable;'''))
    edit('UIMechaLoadGroup.cs',lambda s:replace_once(s,'string path = "Icarus/Mecha/";',
        'string path = Path.Combine(Application.streamingAssetsPath, "Icarus", "Mecha");'))
    edit('PrefabDesc.cs',lambda s:s.replace('= "Verta/";','= UnityEngine.Application.streamingAssetsPath + "/Verta/";'))
    edit('DSPGame.cs',lambda s:wrap_method(s,'public static void ShutApplicationImmediate()',
        'PortMacShutdown.Request();','UNITY_STANDALONE_OSX && !UNITY_EDITOR'))
    edit('SectorModel.cs',lambda s:replace_once(s,'private void OnCameraPostRender(Camera cam)\n\t{',
        '''private void OnCameraPostRender(Camera cam)
	{
        if (!GameMain.isRunning || GameMain.mainPlayer?.controller?.actionBuild == null ||
            GameCamera.instance == null || GameCamera.instance.hdScreenshot == null || combatStatRenderer == null) return;'''))
    def shell(s):
        begin=s.index('\t\tmesh.vertices = verts;');end=s.index('\n\t\tmesh.bounds = ',begin)
        return s[:begin]+'\t\tPortShellMesh.Populate(mesh, verts, uvs, uv2s, array, indices);'+s[end:]
    edit('DysonShell.cs',shell)
    def clamp(s):
        s=replace_once(s,'private bool moving;','private bool moving;\n private bool portClampPending;\n private int portScreenWidth,portScreenHeight;')
        s=replace_once(s,'private void OnEnable()\n\t{','private void OnEnable()\n\t{\n portClampPending=true;')
        method='''
#if UNITY_IOS || UNITY_STANDALONE_OSX
 private void LateUpdate() {
  if (!portClampPending && Screen.width==portScreenWidth && Screen.height==portScreenHeight) return;
  if (dragTrans==null || refTrans==null || UIRoot.instance==null) return;
  var parent=dragTrans.parent as RectTransform; if(parent==null)return;
  Canvas.ForceUpdateCanvases();var corners=new Vector3[4];refTrans.GetWorldCorners(corners);
  var canvas=refTrans.GetComponentInParent<Canvas>();
  Camera camera=canvas!=null&&canvas.renderMode!=RenderMode.ScreenSpaceOverlay?canvas.worldCamera:null;
  Vector2 min=new Vector2(float.MaxValue,float.MaxValue),max=new Vector2(float.MinValue,float.MinValue);
  foreach(var corner in corners){var point=RectTransformUtility.WorldToScreenPoint(camera,corner);min=Vector2.Min(min,point);max=Vector2.Max(max,point);}
  Vector2 shift=Vector2.zero;
  if(min.x<0)shift.x=-min.x;else if(max.x>Screen.width)shift.x=Screen.width-max.x;
  if(max.y>Screen.height)shift.y=Screen.height-max.y;else if(min.y<0)shift.y=-min.y;
  Vector2 from,to;
  if(RectTransformUtility.ScreenPointToLocalPointInRectangle(parent,min,camera,out from)&&RectTransformUtility.ScreenPointToLocalPointInRectangle(parent,min+shift,camera,out to))dragTrans.anchoredPosition+=to-from;
  portClampPending=false;portScreenWidth=Screen.width;portScreenHeight=Screen.height;
 }
#endif
'''
        return replace_once(s,'\tprivate void OnDisable()',method+'\n\tprivate void OnDisable()')
    edit('UIWindowDrag.cs',clamp)
if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--project',type=Path,required=True);apply(p.parse_args().project)
