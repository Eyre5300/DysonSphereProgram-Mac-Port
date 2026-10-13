using System;
using System.Collections;
using System.Collections.Generic;
using System.IO;
using System.Reflection;
using System.Security.Cryptography;
using UnityEngine;
// Explicitly requested diagnostic batch only; never changes receiver operation.
public static class DSPRayReceiverRegression {
 [Serializable] public sealed class Report {
  public string build,batch,phase,fixtureSHA256;
  public bool completed,sourceUnchanged,savePathRestored;
  public int receivers,lensReceivers,poweredLensReceivers,target;
  public uint gpuState;public float gpuPower,gpuWorkingLength;public string gpuReadError;
  public List<string> errors=new List<string>();
  public string scope="CPU/GPU animation state and rendered views; capture completion is not visual parity acceptance.";
 }
 static Report report;static string folder,fixture,oldSave;static FieldInfo saveField;
 static GameOption oldOption;static bool optionsSaved;
 public static bool Passed=>report!=null&&report.completed&&report.sourceUnchanged&&report.savePathRestored&&report.errors.Count==0;
 static string Hash(string path){using(var h=SHA256.Create())using(var f=File.OpenRead(path))return BitConverter.ToString(h.ComputeHash(f)).Replace("-","").ToLowerInvariant();}
 static void Write(string phase){report.phase=phase;File.WriteAllText(Path.Combine(folder,"report.json"),JsonUtility.ToJson(report,true));}
 static bool Ready()=>GameMain.isRunning&&!GameMain.isLoading&&!DSPGame.IsMenuDemo&&GameMain.localPlanet!=null&&GameMain.localPlanet.factoryLoaded;
 static IEnumerator Shot(string label){
  yield return new WaitForSecondsRealtime(2);yield return new WaitForEndOfFrame();
  DSPRayReceiverAudit.Capture(folder,label);
  var image=ScreenCapture.CaptureScreenshotAsTexture();try{File.WriteAllBytes(Path.Combine(folder,label+".png"),image.EncodeToPNG());}finally{UnityEngine.Object.Destroy(image);}
  Write(label);
 }
 static IEnumerator Body(){
  fixture=Path.Combine(Application.persistentDataPath,"ray-receiver-fixture.dsv");report.fixtureSHA256=Hash(fixture);
  oldOption=DSPGame.globalOption;optionsSaved=true;var option=oldOption;option.autoSaveTime=0;option.audioVolume=0;DSPGame.globalOption=option;option.Apply();
  saveField=typeof(GameConfig).GetField("gameSavePath",BindingFlags.Static|BindingFlags.NonPublic);if(saveField==null)throw new Exception("Save isolation unavailable");
  oldSave=(string)saveField.GetValue(null);string isolated=Path.Combine(folder,"save");Directory.CreateDirectory(isolated);saveField.SetValue(null,isolated+Path.DirectorySeparatorChar);
  File.Copy(fixture,Path.Combine(isolated,"ReceiverFixture.dsv"),true);Write("loading");DSPGame.StartGame("ReceiverFixture");yield return null;
  float until=Time.realtimeSinceStartup+240;while(!Ready()&&Time.realtimeSinceStartup<until)yield return null;if(!Ready())throw new Exception("Receiver fixture did not load");
  GameMain.Resume();yield return new WaitForSecondsRealtime(5);yield return Shot("original-view");
  var f=GameMain.localPlanet.factory;var ps=f.powerSystem;float best=float.MaxValue;
  for(int i=1;i<ps.genCursor;i++){
   var g=ps.genPool[i];if(g.id!=i||!g.gamma)continue;report.receivers++;bool lens=g.catalystPoint>0||g.catalystCount>0;if(lens)report.lensReceivers++;if(lens&&g.capacityCurrentTick>0)report.poweredLensReceivers++;
   if(g.entityId<=0||g.entityId>=f.entityPool.Length)continue;float distance=(f.entityPool[g.entityId].pos-GameMain.mainPlayer.position).sqrMagnitude;
   // Prefer a working lens receiver, keeping unsupported/no-lens cases visible in the report.
   float score=distance+(lens&&g.capacityCurrentTick>0?0:1000000);if(score<best){best=score;report.target=g.entityId;}
  }
  if(report.target==0)throw new Exception("No receiver on fixture's current planet");
  try{var data=new AnimData[1];GameMain.localPlanet.factoryModel.entityAnimBuffer.GetData(data,0,report.target,1);report.gpuState=data[0].state;report.gpuPower=data[0].power;report.gpuWorkingLength=data[0].working_length;}catch(Exception e){report.gpuReadError=e.ToString();}
  var camera=GameCamera.main;var controller=GameCamera.instance;bool enabled=controller.enabled;var position=camera.transform.position;var rotation=camera.transform.rotation;
  Vector3 target=f.entityPool[report.target].pos,up=target.normalized,tangent=Vector3.Cross(up,Vector3.up).normalized;if(tangent.sqrMagnitude<.1f)tangent=Vector3.Cross(up,Vector3.right).normalized;
  try{
   controller.enabled=false;
   for(int view=0;view<3;view++){
    Vector3 side=Quaternion.AngleAxis(view*120,up)*tangent;
    camera.transform.position=target+up*24+side*80;camera.transform.rotation=Quaternion.LookRotation(target+up*12-camera.transform.position,up);
    yield return Shot("receiver-view-"+view);
   }
   string path=Path.Combine(Application.persistentDataPath,"ray-probes.bundle");
   if(DSPPadDiagnosticLaunch.RayReceiverProbesRequested){
    if(!File.Exists(path))throw new Exception("Explicit receiver probe bundle missing");
    var bundle=AssetBundle.LoadFromFile(path);if(!bundle)throw new Exception("Receiver probe bundle unavailable");
    var materials=new Dictionary<Material,Shader>();foreach(var m in Resources.FindObjectsOfTypeAll<Material>())if(m.shader&&m.shader.name=="VF Shaders/Forward/Unlit Additive Ray Receiver Gravity")materials.Add(m,m.shader);
    if(materials.Count==0)throw new Exception("Receiver materials missing");
    try{
     foreach(var shader in bundle.LoadAllAssets<Shader>()){
      if(!shader.isSupported)throw new Exception("Unsupported receiver probe "+shader.name);
      foreach(var m in materials.Keys)m.shader=shader;
      yield return Shot("probe-"+shader.name.Substring(shader.name.LastIndexOf('/')+1));
     }
    }finally{foreach(var m in materials.Keys)if(m)m.shader=materials[m];bundle.Unload(true);}
    yield return Shot("probe-restored");
   }
  }finally{camera.transform.position=position;camera.transform.rotation=rotation;controller.enabled=enabled;}
 }
 public static IEnumerator Run(){
  if(!DSPPadDiagnosticLaunch.RayReceiverAuditRequested)yield break;
  report=new Report{build=DSPPadDiagnosticLaunch.BuildVersion,batch=DSPPadDiagnosticLaunch.BatchIdentifier};folder=Path.Combine(Application.persistentDataPath,"ray-receiver-"+report.build);Directory.CreateDirectory(folder);Write("starting");
  var stack=new Stack<IEnumerator>();stack.Push(Body());
  while(stack.Count>0){bool more;object next=null;try{more=stack.Peek().MoveNext();if(more)next=stack.Peek().Current;}catch(Exception e){report.errors.Add(e.ToString());break;}if(!more){(stack.Pop() as IDisposable)?.Dispose();continue;}if(next is IEnumerator){stack.Push((IEnumerator)next);continue;}yield return next;}
  while(stack.Count>0)(stack.Pop() as IDisposable)?.Dispose();
  try{if(GameMain.isRunning)DSPGame.EndGame();if(saveField!=null&&oldSave!=null){saveField.SetValue(null,oldSave);report.savePathRestored=(string)saveField.GetValue(null)==oldSave;}if(optionsSaved){DSPGame.globalOption=oldOption;oldOption.Apply();}if(File.Exists(fixture))report.sourceUnchanged=Hash(fixture)==report.fixtureSHA256;}
  catch(Exception e){report.errors.Add("Cleanup: "+e);}
  report.completed=true;Write("finished");
 }
}
