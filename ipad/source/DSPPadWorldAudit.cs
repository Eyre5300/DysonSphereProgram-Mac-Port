using System;
using System.Collections;
using System.Collections.Generic;
using System.IO;
using System.Runtime.InteropServices;
using UnityEngine;
// Explicit diagnostic batch: inspect original data and GPU state without changing render policy.
public static class DSPPadWorldAudit {
 const string Native="@rpath/UnityFramework.framework/UnityFramework";
 [DllImport(Native)]static extern int DSPAOTQueueTestKey(int code,int pressed);
 [DllImport(Native)]static extern int DSPAOTQueueTestPointer(float x,float y,int buttons,float dx,float dy,float wheel);
 [Serializable]public class MaterialState {public string name,shader,keywords;public bool supported;public int passCount,instWords,idWords,animWords,vertaWords,vertexSize,vertexCount,frameCount;}
 [Serializable]public class Batch {public int lod,vertices,submeshes,capacity,instanceMismatch,expectedVertaWords;public uint[] args,ids;public List<MaterialState> materials=new List<MaterialState>();}
 [Serializable]public class Model {public int model,cursor,lodCount;public string type;public List<Batch> batches=new List<Batch>();}
 [Serializable]public class Vein {public int id,model,modelId,amount;public string type;public Vector3 position,screen;public AnimData animation;}
 [Serializable]public class Snapshot {public string label,viewMode;public bool renderVein,loaded,globe,star;public bool veinDistribution;public int visibleVeinIcons;public int veinCursor,liveVeins,visibleVeins,animCount,animMismatch;public float rtsDistance,planetDistance;public List<Model> models=new List<Model>();public List<Vein> veins=new List<Vein>();}
 [Serializable]public class Report {public string batchIdentifier=DSPPadDiagnosticLaunch.BatchIdentifier,buildVersion=DSPPadDiagnosticLaunch.BuildVersion;public bool completed,cameraRestored;public float[] cameraBefore,cameraAfter;public List<string> inputs=new List<string>(),errors=new List<string>();public List<Snapshot> snapshots=new List<Snapshot>();}
 static Report report;
 public static bool Passed=>report!=null&&report.completed&&report.errors.Count==0;
 static void Check(bool ok,string message){if(!ok)report.errors.Add(message);}
 static void Write(){File.WriteAllText(Path.Combine(Application.persistentDataPath,"world-audit.json"),JsonUtility.ToJson(report,true));}
 static void Pointer(int mask=0,float dx=0,float dy=0,float wheel=0){if(DSPAOTQueueTestPointer(.45f,.45f,mask,dx,dy,wheel)!=1)throw new Exception("Pointer rejected");}
 static IEnumerator Wait(float seconds){float until=Time.realtimeSinceStartup+seconds;do{Pointer();yield return null;}while(Time.realtimeSinceStartup<until);}
 static IEnumerator Key(KeyCode key){if(DSPAOTQueueTestKey(DSPPadKeyboard.HID(key),1)!=1||DSPAOTQueueTestKey(DSPPadKeyboard.HID(key),0)!=1)throw new Exception("Key rejected");yield return Wait(.4f);}
 static IEnumerator Wheels(int count){for(int i=0;i<count;i++){Pointer(wheel:-1);yield return null;yield return Wait(.06f);}}
 static MaterialState Material(Material m,bool animated){return new MaterialState{name=m.name,shader=m.shader.name,keywords=string.Join(" ",m.shaderKeywords),supported=m.shader.isSupported,passCount=m.passCount,instWords=m.GetInt("_PortWords_InstBuffer"),idWords=m.GetInt("_PortWords_IdBuffer"),animWords=m.GetInt("_PortWords_AnimBuffer"),vertaWords=animated?m.GetInt("_PortWords_VertaBuffer"):0,vertexSize=animated?m.GetInt("_VertexSize"):0,vertexCount=animated?m.GetInt("_VertexCount"):0,frameCount=animated?m.GetInt("_FrameCount"):0};}
 static void SnapshotNow(string label){
  var planet=GameMain.localPlanet;var f=planet.factory;var fm=planet.factoryModel;var mgr=fm.gpuiManager;var c=GameCamera.instance;
  var s=new Snapshot{label=label,viewMode=UIGame.viewMode.ToString(),renderVein=mgr.renderVein,loaded=planet.factoryLoaded,globe=UIRoot.instance.uiGame.globemap.active,star=UIRoot.instance.uiGame.starmap.active,veinCursor=f.veinCursor,rtsDistance=c.rtsPoser.distCoefWanted,planetDistance=c.planetPoser.distWanted};
  s.veinDistribution=UIRoot.instance.uiGame.dfVeinOnFinal;foreach(var tip in UIRoot.instance.uiGame.veinDetail.allTips)if(tip!=null&&tip.active&&tip.veinIcon!=null&&tip.veinIcon.sprite!=null&&tip.veinIcon.gameObject.activeInHierarchy)s.visibleVeinIcons++;
  if(label=="globe")Check(s.veinDistribution&&s.visibleVeinIcons>0,"Enabled globe vein icons missing");
  var anim=fm.veinAnimBuffer;if(anim!=null){s.animCount=anim.count;var data=new AnimData[anim.count];anim.GetData(data);for(int i=0;i<Math.Min(data.Length,f.veinAnimPool.Length);i++)if(!data[i].Equals(f.veinAnimPool[i]))s.animMismatch++;}
  for(int i=1;i<f.veinCursor;i++){var v=f.veinPool[i];if(v.id!=i||v.amount<=0)continue;s.liveVeins++;Vector3 screen=Camera.main.WorldToScreenPoint(v.pos);bool visible=screen.z>0&&screen.x>0&&screen.y>0&&screen.x<Screen.width&&screen.y<Screen.height;if(visible)s.visibleVeins++;if(s.veins.Count<15||visible&&s.veins.Count<100)s.veins.Add(new Vein{id=i,model=v.modelIndex,modelId=v.modelId,amount=v.amount,type=v.type.ToString(),position=v.pos,screen=screen,animation=f.veinAnimPool[i]});}
  for(int i=0;i<mgr.objectRenderers.Length;i++){
   var renderer=mgr.objectRenderers[i];if(renderer==null||renderer.instCursor<=1)continue;
   var model=new Model{model=i,cursor=renderer.instCursor,type=mgr.objectTypes[i].ToString(),lodCount=renderer.objectDesc.lodCount};
   foreach(var b in renderer.lodBatches??new BatchRenderer[0]){
    var info=new Batch{expectedVertaWords=b.vertaBuffer==null||b.vertaBuffer.cbuffer==null?0:b.vertaBuffer.cbuffer.count*(b.vertaBuffer.cbuffer.stride/4),lod=b.lod,vertices=b.mesh.vertexCount,submeshes=b.subCount,capacity=b.instBuffer.count,args=new uint[5*b.subCount]};b.argBuffer.GetData(info.args,0,b.argOffset,info.args.Length);
    uint count=0;for(int j=1;j<info.args.Length;j+=5)count=Math.Max(count,info.args[j]);info.ids=new uint[Math.Min((int)count,64)];if(info.ids.Length>0)b.idBuffer.GetData(info.ids,0,0,info.ids.Length);
    var data=new GPUOBJECT[b.instBuffer.count];b.instBuffer.GetData(data);for(int j=0;j<Math.Min(renderer.instCursor,data.Length);j++)if(!data[j].Equals(renderer.instPool[j]))info.instanceMismatch++;
    foreach(var mat in b.materials)if(mat){var m=Material(mat,info.expectedVertaWords>0);info.materials.Add(m);Check(m.supported,label+" unsupported shader "+m.shader);Check(m.vertaWords==info.expectedVertaWords,label+" Verta length mismatch model="+i+" lod="+b.lod);}
    Check(info.instanceMismatch==0,label+" instance upload mismatch model="+i);model.batches.Add(info);
   }s.models.Add(model);
  }Check(s.liveVeins>0&&s.renderVein,label+" no active vein rendering");Check(s.animMismatch==0,label+" vein animation upload mismatch");report.snapshots.Add(s);Write();
 }
 static float[] CameraState(){var c=GameCamera.instance;return new[]{c.rtsPoser.yawWanted,c.rtsPoser.pitchCoefWanted,c.rtsPoser.distCoefWanted,c.buildPoser.yawWanted,c.buildPoser.pitchCoefWanted,c.buildPoser.distCoefWanted};}
 static void RestoreCamera(){var c=GameCamera.instance;var a=report.cameraBefore;c.rtsPoser.yawWanted=a[0];c.rtsPoser.pitchCoefWanted=a[1];c.rtsPoser.distCoefWanted=a[2];c.buildPoser.yawWanted=a[3];c.buildPoser.pitchCoefWanted=a[4];c.buildPoser.distCoefWanted=a[5];c.rtsPoser.ToWanted();c.buildPoser.ToWanted();report.cameraAfter=CameraState();report.cameraRestored=true;for(int i=0;i<a.Length;i++)report.cameraRestored&=Mathf.Abs(a[i]-report.cameraAfter[i])<.0001f;Check(report.cameraRestored,"Camera fixture restore failed");Write();}
 static IEnumerator Body(){
  // Snapshot both camera modes before exercising original globe/starmap transitions.
  // Returning from globe intentionally changes them in Windows; restore only the
  // diagnostic fixture so later flight tests start from their independent baseline.
  report.cameraBefore=CameraState();
  yield return Wait(2);yield return new WaitForEndOfFrame();SnapshotNow("normal");yield return DSPPadRenderDiagnostics.Capture("31-veins-normal");yield return Wheels(35);yield return Wait(.3f);report.inputs.Add("Normal zoom limit: "+UIGame.viewMode+" distance="+GameCamera.instance.rtsPoser.distCoefWanted);Write();
  yield return Key(KeyCode.M);yield return Wait(3);bool oldVeinDisplay=UIRoot.instance.uiGame.dfVeinOn;if(!oldVeinDisplay)UIRoot.instance.uiGame.ToggleVeinDistributionDetail();yield return Wait(1);yield return new WaitForEndOfFrame();SnapshotNow("globe");yield return DSPPadRenderDiagnostics.Capture("31-veins-globe");if(!oldVeinDisplay)UIRoot.instance.uiGame.ToggleVeinDistributionDetail();
  var poser=GameCamera.instance.planetPoser;Quaternion before=poser.rotationWanted;
  for(int i=0;i<15;i++){Pointer(1,4,1);yield return null;}yield return Wait(.4f);report.inputs.Add("Globe left drag angle="+Quaternion.Angle(before,poser.rotationWanted));Check(Quaternion.Angle(before,poser.rotationWanted)<.1f,"Left drag unexpectedly rotates globe");before=poser.rotationWanted;
  for(int i=0;i<15;i++){Pointer(4,4,1);yield return null;}yield return Wait(.4f);report.inputs.Add("Globe middle drag angle="+Quaternion.Angle(before,poser.rotationWanted));Check(Quaternion.Angle(before,poser.rotationWanted)>1,"Middle drag failed to rotate globe");Write();
  yield return Wheels(60);yield return Wait(.4f);yield return Wheels(30);yield return Wait(2);report.inputs.Add("Globe zoom transition: "+UIGame.viewMode+" star="+UIRoot.instance.uiGame.starmap.active);Check(UIRoot.instance.uiGame.starmap.active,"Globe zoom failed to enter starmap");Write();
  yield return Key(KeyCode.Escape);yield return Wait(2);if(UIRoot.instance.uiGame.globemap.active){yield return Key(KeyCode.M);yield return Wait(1);}
  RestoreCamera();yield return Wait(1);
 }
 public static IEnumerator Run(){if(!DSPPadDiagnosticLaunch.AutomaticActionsAllowed)return Empty();return Guard();}
 static IEnumerator Empty(){yield break;}
 static IEnumerator Guard(){report=new Report();Write();var stack=new Stack<IEnumerator>();stack.Push(Body());while(stack.Count>0){bool more=false;object value=null;Exception error=null;try{more=stack.Peek().MoveNext();if(more)value=stack.Peek().Current;}catch(Exception e){error=e;}if(error!=null){report.errors.Add(error.ToString());break;}if(!more){stack.Pop();continue;}if(value is IEnumerator){stack.Push((IEnumerator)value);continue;}yield return value;}// Leave diagnostic transports available for the following keyboard/mouse phases.
 Pointer();DSPPadInput.ResetInputAxes();report.completed=true;Write();}
}
