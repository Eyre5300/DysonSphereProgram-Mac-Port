using System;using System.IO;using System.Reflection;using System.Collections;using System.Collections.Generic;using System.Security.Cryptography;using UnityEngine;using UnityEngine.PostProcessing;
// Explicit diagnostics only. Uses a separately supplied copy; all writes are
// redirected into a batch-owned directory before loading it. No user save edits.
public static class DSPPadSceneAudit {
 [Serializable] public class Sample {
  public string label;public int width,height,frames;public long ticks;public double seconds,stopwatchSeconds,actualFPS,actualUPS,hudFPS,hudUPS,controllerFPS,controllerUPS,fixRatio,cpuTotalMs,cpuCompleteMs;
  public int targetFrameRate,vSync,msaa;public bool paused;public float fixedDeltaTime;public double[] cpuMilliseconds;public double cpuFrameMs,gpuFrameMs;public int validFrameTimings;public float medianMs,p95Ms;
 }
 [Serializable] public class View {public string label;public int planet,enemyId;public long tick;public Vector3 player,enemy,camera;public string option;public float sunDot;public Quaternion cameraRotation;public string terrain;}
 [Serializable] public class Report {public string phase;public string batchIdentifier=DSPPadDiagnosticLaunch.BatchIdentifier,buildVersion=DSPPadDiagnosticLaunch.BuildVersion,fixtureSHA256;public bool completed,sourceUnchanged,savePathRestored;public List<string> errors=new List<string>();public List<Sample> samples=new List<Sample>();public List<View> views=new List<View>();public string scope="Focused terrain compiler/normal diagnostics only; screenshots excluded from timings; original materials/camera restored. Paused render timings are not simulation performance acceptance.";}
 static Report report;static string folder;static FieldInfo saveField;static string oldSavePath,fixture;static GameOption oldOption;static bool optionsSaved;
 public static bool Passed=>report!=null&&report.completed&&report.sourceUnchanged&&report.savePathRestored&&report.errors.Count==0;
 static void Write(){File.WriteAllText(Path.Combine(Application.persistentDataPath,"scene-audit.json"),JsonUtility.ToJson(report,true));}
 static string Hash(string p){using(var s=SHA256.Create())using(var f=File.OpenRead(p))return BitConverter.ToString(s.ComputeHash(f)).Replace("-","").ToLowerInvariant();}
 static void Check(bool value,string message){if(!value)throw new Exception(message);}
 static bool Ready()=>GameMain.isRunning&&!GameMain.isLoading&&!DSPGame.IsMenuDemo&&GameMain.localPlanet!=null&&GameMain.localPlanet.factoryLoaded;
 static IEnumerator Measure(string label,float duration=10){
  report.phase=label;Write();
  yield return new WaitForSecondsRealtime(3);
  var samples=new List<float>();var frameTimings=new FrameTiming[1];double begin=Time.realtimeSinceStartupAsDouble,last=begin;long ticks=GameMain.gameTick;int frame=Time.frameCount;var watch=System.Diagnostics.Stopwatch.StartNew();
  var s=new Sample{label=label,width=Screen.width,height=Screen.height,msaa=QualitySettings.antiAliasing,paused=GameMain.isFullscreenPaused||GameMain.isPaused};
  do {FrameTimingManager.CaptureFrameTimings();yield return null;double now=Time.realtimeSinceStartupAsDouble;samples.Add((float)((now-last)*1000));last=now;
   if(FrameTimingManager.GetLatestTimings(1,frameTimings)>0&&frameTimings[0].gpuFrameTime>0){s.validFrameTimings++;s.cpuFrameMs+=frameTimings[0].cpuFrameTime;s.gpuFrameMs+=frameTimings[0].gpuFrameTime;}
  }while(Time.realtimeSinceStartupAsDouble-begin<duration);
  s.seconds=Time.realtimeSinceStartupAsDouble-begin;s.stopwatchSeconds=watch.Elapsed.TotalSeconds;s.frames=Time.frameCount-frame;s.ticks=GameMain.gameTick-ticks;s.actualFPS=s.frames/s.seconds;s.actualUPS=s.ticks/s.seconds;
  var hud=UIRoot.instance.GetComponentInChildren<UIFpsStat>(true);s.hudFPS=hud?hud.fps:0;s.hudUPS=hud?hud.ups:0;s.controllerFPS=FPSController.currentFPS;s.controllerUPS=FPSController.currentUPS;s.fixRatio=FPSController.GetFixRatio();s.fixedDeltaTime=Time.fixedDeltaTime;s.targetFrameRate=Application.targetFrameRate;s.vSync=QualitySettings.vSyncCount;
  s.cpuTotalMs=PerformanceMonitor.totalTimeCostsAve*1000;s.cpuCompleteMs=PerformanceMonitor.totalTimeCostsAveComplete*1000;
  if(PerformanceMonitor.timeCostsAve!=null){s.cpuMilliseconds=(double[])PerformanceMonitor.timeCostsAve.Clone();for(int i=0;i<s.cpuMilliseconds.Length;i++)s.cpuMilliseconds[i]*=1000;}
  samples.Sort();s.medianMs=samples[samples.Count/2];s.p95Ms=samples[Math.Min(samples.Count-1,(int)(samples.Count*.95))];if(s.validFrameTimings>0){s.cpuFrameMs/=s.validFrameTimings;s.gpuFrameMs/=s.validFrameTimings;}
  report.samples.Add(s);Write();
 }
 static IEnumerator ViewShot(string label,int enemyId){
  yield return new WaitForSecondsRealtime(2);var p=GameMain.mainPlayer;var e=enemyId>0?(Vector3)p.factory.enemyPool[enemyId].pos:Vector3.zero;
  var star=GameMain.universeSimulator.LocalStarSimulator();var light=star?star.sunLight:null;
  report.views.Add(new View{label=label,planet=p.planetId,enemyId=enemyId,tick=GameMain.gameTick,player=p.position,enemy=e,camera=Camera.main.transform.position,cameraRotation=Camera.main.transform.rotation,terrain=TerrainInfo(),option=JsonUtility.ToJson(DSPGame.globalOption),sunDot=light?Vector3.Dot(p.position.normalized,-light.transform.forward):0});
  yield return DSPPadRenderDiagnostics.Capture(label);Write();
 }
 static string TerrainInfo(){
  var m=GameMain.localPlanet.terrainMaterial;if(!m)return "missing";
  string text=m.name+" shader="+m.shader.name+" keywords="+string.Join(",",m.shaderKeywords);
  foreach(var key in new[]{"_SunDir","_Rotation","_AmbientColor0","_AmbientColor1","_AmbientColor2"})if(m.HasProperty(key))text+=";"+key+"="+m.GetVector(key).ToString("F5");
  foreach(var key in new[]{"_BioTex0A","_BioTex0N","_BioTex1A","_BioTex1N","_BioTex2A","_BioTex2N"}){var t=m.GetTexture(key);if(t)text+=";"+key+"="+t.name+"/"+t.graphicsFormat+"/"+t.width+"x"+t.height;}
  return text;
 }
 static IEnumerator SurfaceProbe(string prefix,bool performance){
  var materials=new List<Material>();foreach(var m in Resources.FindObjectsOfTypeAll<Material>())if(m.shader&&m.shader.name=="VF Shaders/Forward/Planet Surface")materials.Add(m);
  Check(materials.Count>0,"No original terrain materials found");var original=materials[0].shader;var candidate=Resources.Load<Shader>("PortSceneAudit/TerrainTyped");Check(candidate&&candidate.isSupported,"Typed terrain diagnostic unavailable");
  bool wasPaused=GameMain.isFullscreenPaused;GameMain.isFullscreenPaused=true;
  try{
   yield return ViewShot(prefix+"-original",0);if(performance)yield return Measure(prefix+"-original");
   foreach(var m in materials)m.shader=candidate;
   yield return ViewShot(prefix+"-typed",0);if(performance)yield return Measure(prefix+"-typed");
  }finally{foreach(var m in materials)if(m)m.shader=original;}
  yield return ViewShot(prefix+"-restored",0);if(performance)yield return Measure(prefix+"-restored");GameMain.isFullscreenPaused=wasPaused;
  // A flat DXT5nm normal sample isolates texture channel/normal interpretation.
  // This diagnostic texture is never saved or used during ordinary play.
  wasPaused=GameMain.isFullscreenPaused;GameMain.isFullscreenPaused=true;
  var flat=new Texture2D(1,1,TextureFormat.RGBA32,false,true);flat.SetPixel(0,0,new Color(.5f,.5f,1,.5f));flat.Apply();
  var saved=new List<Texture[]>();string[] keys={"_BioTex0N","_BioTex1N","_BioTex2N"};
  try{foreach(var m in materials){var textures=new Texture[3];for(int i=0;i<3;i++){textures[i]=m.GetTexture(keys[i]);m.SetTexture(keys[i],flat);}saved.Add(textures);}yield return ViewShot(prefix+"-flat-normal",0);}
  finally{for(int n=0;n<saved.Count;n++)for(int i=0;i<3;i++)materials[n].SetTexture(keys[i],saved[n][i]);UnityEngine.Object.Destroy(flat);GameMain.isFullscreenPaused=wasPaused;}
 }
 static IEnumerator InitialGlobe(){
  GameMain.isFullscreenPaused=true;var ui=UIRoot.instance.uiGame;ui.OpenGlobemap();yield return new WaitForSecondsRealtime(3);
  try{yield return SurfaceProbe("scene-initial-globe",false);}
  finally{ui.ShutGlobemap();GameMain.isFullscreenPaused=false;}
  yield return new WaitForSecondsRealtime(2);
 }
 [Serializable] class ShaderProbe {public string original,resource;}
 [Serializable] class ShaderProbes {public ShaderProbe[] items;}
 static IEnumerator LivePerformance(){
  report.scope="Live post-processing compiler and resolution/MSAA candidates; full scene features remain enabled. Temporary shader and display changes restored. No universal 60 FPS claim.";
  GameMain.Resume();GameMain.isFullscreenPaused=false;DSPPadRenderDiagnostics.AuditNow();
  yield return new WaitForSecondsRealtime(15);
  yield return Measure("perf-native-original",25);yield return ViewShot("perf-native-original",0);
  var manifest=Resources.Load<TextAsset>("PortSceneAudit/PostFxManifest");Check(manifest,"Post-processing probe manifest missing");
  var shaders=new Dictionary<string,Shader>();foreach(var item in JsonUtility.FromJson<ShaderProbes>(manifest.text).items){var candidate=Resources.Load<Shader>(item.resource);Check(candidate&&candidate.isSupported,"Unsupported compiler candidate "+item.resource);shaders[item.original]=candidate;}
  var originals=new Dictionary<Material,Shader>();var keywords=new Dictionary<Material,string[]>();
  foreach(var m in Resources.FindObjectsOfTypeAll<Material>())if(m.shader&&shaders.ContainsKey(m.shader.name)){originals[m]=m.shader;keywords[m]=m.shaderKeywords;}
  Check(originals.Count>=4,"Active post-processing materials missing");
  try{foreach(var pair in originals){pair.Key.shader=shaders[pair.Value.name];pair.Key.shaderKeywords=keywords[pair.Key];}yield return Measure("perf-native-typed-postfx",25);yield return ViewShot("perf-native-typed-postfx",0);}
  finally{foreach(var pair in originals)if(pair.Key){pair.Key.shader=pair.Value;pair.Key.shaderKeywords=keywords[pair.Key];}}
  yield return Measure("perf-native-restored",20);yield return ViewShot("perf-native-restored",0);
  int width=Screen.width,height=Screen.height,msaa=QualitySettings.antiAliasing;var mode=Screen.fullScreenMode;
  int bestWidth=0,bestHeight=0,bestMSAA=0;
  try{
   foreach(int candidateWidth in new[]{1920,1600,1376}){
    int candidateHeight=Mathf.RoundToInt((float)candidateWidth*height/width);Screen.SetResolution(candidateWidth,candidateHeight,FullScreenMode.FullScreenWindow);
    foreach(int aa in new[]{4,2}){QualitySettings.antiAliasing=aa;yield return Measure("perf-full-effects-"+candidateWidth+"-msaa"+aa,15);var sample=report.samples[report.samples.Count-1];Check(sample.width==candidateWidth&&sample.height==candidateHeight,"Requested render size did not apply");if(bestWidth==0&&sample.actualFPS>=58.5){bestWidth=candidateWidth;bestHeight=candidateHeight;bestMSAA=aa;}}
   }
   if(bestWidth>0){Screen.SetResolution(bestWidth,bestHeight,FullScreenMode.FullScreenWindow);QualitySettings.antiAliasing=bestMSAA;yield return Measure("perf-60fps-candidate-sustained",120);yield return ViewShot("perf-60fps-candidate",0);}
  }finally{QualitySettings.antiAliasing=msaa;Screen.SetResolution(width,height,mode);}
  yield return Measure("perf-original-restored",20);
  Check(!GameMain.isFullscreenPaused&&!GameMain.isPaused,"Simulation unexpectedly paused");
  foreach(var sample in report.samples)Check(sample.ticks>0&&!sample.paused,"Paused sample cannot count as live performance: "+sample.label);
 }
 static IEnumerator Body(){
  if(!DSPPadDiagnosticLaunch.PerformanceAuditRequested)yield return InitialGlobe();
  fixture=Path.Combine(Application.persistentDataPath,"scene-audit-fixture.dsv");Check(File.Exists(fixture),"Supply an owned scene-audit-fixture.dsv copy first");report.fixtureSHA256=Hash(fixture);
  folder=Path.Combine(Application.persistentDataPath,"scene-audit-"+DSPPadDiagnosticLaunch.BatchIdentifier);Directory.CreateDirectory(folder);
  oldOption=DSPGame.globalOption;optionsSaved=true;var opt=oldOption;opt.autoSaveTime=0;opt.audioVolume=0;DSPGame.globalOption=opt;
  saveField=typeof(GameConfig).GetField("gameSavePath",BindingFlags.Static|BindingFlags.NonPublic);Check(saveField!=null,"Save isolation field missing");oldSavePath=(string)saveField.GetValue(null);
  if(GameMain.isRunning){DSPGame.EndGame();yield return new WaitForSecondsRealtime(2);}
  saveField.SetValue(null,folder+Path.DirectorySeparatorChar);File.Copy(fixture,Path.Combine(folder,"SceneFixture.dsv"),false);
  DSPGame.StartGame("SceneFixture");yield return null;float limit=Time.realtimeSinceStartup+240;while(!Ready()&&Time.realtimeSinceStartup<limit)yield return null;Check(Ready(),"Fixture failed to load");GameMain.Resume();yield return new WaitForSecondsRealtime(6);
  DSPPadRenderDiagnostics.AuditNow();
  if(DSPPadDiagnosticLaunch.PerformanceAuditRequested){yield return LivePerformance();DSPGame.EndGame();yield return new WaitForSecondsRealtime(2);report.sourceUnchanged=Hash(fixture)==report.fixtureSHA256;yield break;}
  yield return SurfaceProbe("scene-fixture-ground",true);
  var factory=GameMain.mainPlayer.factory;var bases=factory.enemySystem.bases;int count=0;
  for(int i=1;i<bases.cursor&&count<1;i++){
   var b=bases.buffer[i];if(b==null||b.id!=i||b.enemyId<=0)continue;int eid=b.enemyId;Vector3 pos=factory.enemyPool[eid].pos;
   // A paused player does not update its camera target. Use a diagnostic camera
   // outside the terrain, without teleporting the player into a factory model.
   var camera=Camera.main;var gameCamera=GameCamera.instance;bool enabled=gameCamera.enabled;Vector3 oldPosition=camera.transform.position;Quaternion oldRotation=camera.transform.rotation;
   GameMain.isFullscreenPaused=true;Vector3 up=pos.normalized,tangent=Vector3.Cross(up,Vector3.up).normalized;if(tangent.sqrMagnitude<.1f)tangent=Vector3.Cross(up,Vector3.right).normalized;
   try{
    gameCamera.enabled=false;camera.transform.position=up*(GameMain.localPlanet.realRadius+65)+tangent*45;camera.transform.rotation=Quaternion.LookRotation(pos-camera.transform.position,up);
    Check(camera.transform.position.magnitude>GameMain.localPlanet.realRadius+30,"Diagnostic camera is below terrain");Check(Vector3.Dot(camera.transform.forward,(pos-camera.transform.position).normalized)>.95f,"Diagnostic camera does not face base");
    yield return ViewShot("scene-fixture-base",eid);yield return SurfaceProbe("scene-fixture-base-terrain",false);
   }finally{camera.transform.position=oldPosition;camera.transform.rotation=oldRotation;gameCamera.enabled=enabled;GameMain.isFullscreenPaused=false;}
   count++;
  }
  Check(count>0,"No dark-fog base found on fixture's current planet");
  GameMain.isFullscreenPaused=false;DSPGame.EndGame();yield return new WaitForSecondsRealtime(2);report.sourceUnchanged=Hash(fixture)==report.fixtureSHA256;
 }
 public static IEnumerator Run(){
  if(!DSPPadDiagnosticLaunch.SceneAuditRequested&&!DSPPadDiagnosticLaunch.PerformanceAuditRequested)yield break;report=new Report();Write();
  var stack=new Stack<IEnumerator>();stack.Push(Body());
  while(stack.Count>0){bool more;object value=null;try{more=stack.Peek().MoveNext();if(more)value=stack.Peek().Current;}catch(Exception e){report.errors.Add(e.ToString());break;}if(!more){(stack.Pop() as IDisposable)?.Dispose();continue;}if(value is IEnumerator){stack.Push((IEnumerator)value);continue;}yield return value;}
  while(stack.Count>0)(stack.Pop() as IDisposable)?.Dispose();
  try{GameMain.isFullscreenPaused=false;if(GameMain.isRunning)DSPGame.EndGame();if(saveField!=null&&oldSavePath!=null){saveField.SetValue(null,oldSavePath);report.savePathRestored=(string)saveField.GetValue(null)==oldSavePath;}if(optionsSaved){DSPGame.globalOption=oldOption;oldOption.Apply();}if(File.Exists(fixture))report.sourceUnchanged=Hash(fixture)==report.fixtureSHA256;}
  catch(Exception e){report.errors.Add("Cleanup: "+e);}
  report.completed=true;Write();
 }
}
