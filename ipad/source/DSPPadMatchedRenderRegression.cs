using System;
using System.Collections;
using System.Collections.Generic;
using System.IO;
using System.Reflection;
using System.Security.Cryptography;
using UnityEngine;
using UnityEngine.PostProcessing;
using UnityEngine.UI;

// Private opt-in capture only. Called from a copy of the production bootstrap.
public sealed class DSPPadMatchedRenderRegression : MonoBehaviour {
 [Serializable] public sealed class Config { public string output; public string[] fixtures; public int width=2752,height=2064; }
 [Serializable] public sealed class Frame {
  public string label,fixture,fixtureSHA256,graphics,options,postProfile,cameraComponents,bloomExpectedFormat;
  public int width,height,planet,factories,shadows,shadowCascades,msaa; public long tick;
  public float yaw,pitch,zoom,fov,near,far; public Vector3 playerPosition,cameraPosition; public Quaternion cameraRotation;
  public Matrix4x4 projection; public bool paused,hdr,nativeCensusCaptured; public List<string> collisions=new List<string>(); public List<string> unsupportedShaders=new List<string>();
 }
 [Serializable] public sealed class TextAudit {public string path,text,font,fontNames,alignment,horizontalOverflow,verticalOverflow,clipParents;public int fontSize,fontStyle,minFontSize,maxFontSize,visibleCharacters,generatedCharacters,lineCount;public float preferredWidth,preferredHeight,pixelsPerUnit,canvasScale,referencePixels;public bool bestFit,dynamicFont,raycast;public Rect rect;public Vector3 scale;}
 [Serializable] public sealed class TextSnapshot {public string label;public int width,height;public List<TextAudit> texts=new List<TextAudit>();}
 static void CaptureText(string output,string label){
  var snapshot=new TextSnapshot{label=label,width=Screen.width,height=Screen.height};
  foreach(var t in UnityEngine.Object.FindObjectsOfType<Text>()){
   if(!t.isActiveAndEnabled||string.IsNullOrEmpty(t.text))continue;
   var canvas=t.canvas;var generator=t.cachedTextGenerator;var x=new TextAudit{path=DSPPadRenderDiagnostics.PathOf(t.transform),text=t.text,font=t.font?t.font.name:"null",fontNames=t.font?string.Join(";",t.font.fontNames):"",fontSize=t.fontSize,fontStyle=(int)t.fontStyle,alignment=t.alignment.ToString(),horizontalOverflow=t.horizontalOverflow.ToString(),verticalOverflow=t.verticalOverflow.ToString(),bestFit=t.resizeTextForBestFit,minFontSize=t.resizeTextMinSize,maxFontSize=t.resizeTextMaxSize,dynamicFont=t.font&&t.font.dynamic,raycast=t.raycastTarget,rect=t.rectTransform.rect,scale=t.rectTransform.lossyScale,preferredWidth=t.preferredWidth,preferredHeight=t.preferredHeight,pixelsPerUnit=t.pixelsPerUnit,canvasScale=canvas?canvas.scaleFactor:0,referencePixels=canvas?canvas.referencePixelsPerUnit:0,visibleCharacters=generator.characterCountVisible,generatedCharacters=generator.characterCount,lineCount=generator.lineCount};
   foreach(var mask in t.GetComponentsInParent<RectMask2D>())x.clipParents+=DSPPadRenderDiagnostics.PathOf(mask.transform)+":"+mask.rectTransform.rect+";";
   snapshot.texts.Add(x);
  }
  File.WriteAllText(Path.Combine(output,label+"-text-layout.json"),JsonUtility.ToJson(snapshot,true));
 }
 [Serializable] public sealed class Report {public string phase; public bool complete;public List<string> errors=new List<string>(); public List<string> frames=new List<string>();}
 bool finished; Config config; Report report=new Report(); GameOption savedOptions; bool haveOptions; string originalSavePath; FieldInfo savePathField; string fixtureHash,fixtureName;
 public static IEnumerator RunBatch(){
  if(!DSPPadDiagnosticLaunch.AutomaticActionsAllowed)yield break;
  var go=new GameObject("Private iPad matched render batch");DontDestroyOnLoad(go);var test=go.AddComponent<DSPPadMatchedRenderRegression>();
  test.config=new Config{width=Screen.width,height=Screen.height,output=Path.Combine(Application.persistentDataPath,"matched-render-"+DSPPadDiagnosticLaunch.BuildVersion),fixtures=new[]{Path.Combine(Application.persistentDataPath,"comparison-fixture-0.dsv"),Path.Combine(Application.persistentDataPath,"comparison-fixture-1.dsv")}};
  Directory.CreateDirectory(test.config.output);
  while(!test.finished)yield return null;
  Destroy(go);
 }
 void Awake(){Application.logMessageReceived+=Log;}
 void OnDestroy(){Application.logMessageReceived-=Log;}
 void LateUpdate(){AudioListener.volume=0;AudioListener.pause=true;}
 void Log(string message,string stack,LogType type){if(type==LogType.Error||type==LogType.Exception||type==LogType.Assert){if(report.errors.Count<50)report.errors.Add(message+"\n"+stack);}}
 void Write(string phase){report.phase=phase;File.WriteAllText(Path.Combine(config.output,"report.json"),JsonUtility.ToJson(report,true));}
 static void Check(bool ok,string message){if(!ok)throw new Exception(message);}
 static bool Ready(){return GameMain.isRunning&&!DSPGame.IsMenuDemo&&GameMain.data!=null&&GameMain.mainPlayer!=null&&GameMain.localPlanet!=null&&GameMain.localPlanet.factoryLoaded;}
 IEnumerator Start(){
  var stack=new Stack<IEnumerator>();stack.Push(Run());bool failed=false;
  while(stack.Count>0){var e=stack.Peek();bool more=false;object next=null;Exception error=null;try{more=e.MoveNext();if(more)next=e.Current;}catch(Exception ex){error=ex;}
   if(error!=null){report.errors.Add(error.ToString());failed=true;break;}if(!more){(stack.Pop() as IDisposable)?.Dispose();continue;}if(next is IEnumerator){stack.Push((IEnumerator)next);continue;}yield return next;
  }
  while(stack.Count>0)(stack.Pop() as IDisposable)?.Dispose();
  if(haveOptions){DSPGame.globalOption=savedOptions;DSPGame.globalOption.Apply();}
  if(savePathField!=null)savePathField.SetValue(null,originalSavePath);
  report.complete=!failed;Write(!failed&&report.errors.Count==0?"captured_ipad_comparison":"failed");yield return null;finished=true;
 }
 IEnumerator Run(){
  Write("preloading");float deadline=Time.realtimeSinceStartup+300;
  while(!VFPreload.done&&Time.realtimeSinceStartup<deadline){var loader=FindObjectOfType<VFPreload>();if(loader!=null&&loader.languageSelectGroup.gameObject.activeSelf)loader.SelectLanguageZHCN();yield return null;}
  Check(VFPreload.done,"Preload timed out");yield return new WaitForSecondsRealtime(2);
  savedOptions=DSPGame.globalOption;haveOptions=true;var option=savedOptions;var reference=JsonUtility.FromJson<GameOption>(File.ReadAllText(Path.Combine(Application.persistentDataPath,"comparison-options.json")));option.imfxMasterToggle=reference.imfxMasterToggle;option.bloomLevel=reference.bloomLevel;option.ssao=reference.ssao;option.msaa=reference.msaa;option.fxaa=reference.fxaa;option.shadowMode=reference.shadowMode;option.terrainShadow=reference.terrainShadow;option.dof=reference.dof;option.nephogram=reference.nephogram;option.cloud=reference.cloud;option.dithering=reference.dithering;option.resolution.width=config.width;option.resolution.height=config.height;option.resolution.refreshRateRatio=GameResolutions.DoubleToRefreshRate(60);option.displayMode=EOptionDisplayMode.Windowed;option.autoSaveTime=0;option.audioVolume=0;
  DSPGame.globalOption=option;option.Apply();yield return new WaitForSecondsRealtime(3);
  Check(Screen.width==config.width&&Screen.height==config.height,"Actual surface "+Screen.width+"x"+Screen.height+" differs from requested dimensions");
  File.WriteAllText(Path.Combine(config.output,"requested-options.json"),JsonUtility.ToJson(option,true));
  savePathField=typeof(GameConfig).GetField("gameSavePath",BindingFlags.Static|BindingFlags.NonPublic);Check(savePathField!=null,"Save isolation field unavailable");originalSavePath=(string)savePathField.GetValue(null);
  // User-requested larger saves visible in the original Load Game menu.
  // Only seed absent test copies; never replace a copy the user later played.
  for(int i=0;i<config.fixtures.Length;i++){
   string target=GameSave.SavePath(i==0?"iPad-Comparison-55MB":"iPad-Comparison-130MB");
   if(!File.Exists(target))File.Copy(config.fixtures[i],target);
  }
  string isolated=Path.Combine(config.output,"test-saves");Directory.CreateDirectory(isolated);savePathField.SetValue(null,isolated+Path.DirectorySeparatorChar);
  for(int i=0;i<config.fixtures.Length;i++){
   string fixture=config.fixtures[i];fixtureName=Path.GetFileName(fixture);using(var sha=SHA256.Create())using(var stream=File.OpenRead(fixture))fixtureHash=BitConverter.ToString(sha.ComputeHash(stream)).Replace("-","").ToLowerInvariant();
   string name="RenderCompare-"+i;File.Copy(fixture,GameSave.SavePath(name),true);Write("loading_"+i);DSPGame.StartGame(name);yield return null;deadline=Time.realtimeSinceStartup+300;
   while(!Ready()&&Time.realtimeSinceStartup<deadline)yield return null;Check(Ready(),"Fixture did not load onto a solid planet: "+fixtureName);
   yield return new WaitForSecondsRealtime(3);GameMain.Resume();GameMain.isFullscreenPaused=true;yield return null;
   var poser=GameCamera.instance.rtsPoser;Check(poser!=null,"Ground camera missing");
   float[] zooms={.05f,.5f,.95f,.75f};float[] pitches={.7f,.7f,.7f,.95f};float[] yaws={0,0,0,120};
   for(int view=0;view<zooms.Length;view++){poser.yawWanted=yaws[view];poser.distCoefWanted=zooms[view];poser.pitchCoefWanted=pitches[view];poser.ToWanted();yield return new WaitForSecondsRealtime(3);yield return Capture("fixture"+i+"-view"+view);yield return DSPPadRenderDiagnostics.Capture("23-matched-"+i+"-"+view);}
   // Same view, original effects retained; compare mobile Bloom with the desktop format.
   bool bloomFormat=DSPPadRenderFormats.DesktopBloomCandidate;
   try{DSPPadRenderFormats.DesktopBloomCandidate=true;yield return new WaitForSecondsRealtime(2);yield return DSPPadRenderDiagnostics.Capture("23-bloom-hdr-"+i);}
   finally{DSPPadRenderFormats.DesktopBloomCandidate=bloomFormat;}
   var ui=UIRoot.instance.uiGame;ui.OpenTechTree();yield return new WaitForSecondsRealtime(2);Check(ui.techTree.active&&!ui.escMenu.active,"Technology view not visible");yield return Capture("fixture"+i+"-technology");ui.ShutTechTree();
   ui.OpenStarmapWithCurrentLocation();yield return new WaitForSecondsRealtime(2);Check(ui.starmap.active&&!ui.escMenu.active,"Starmap view not visible");yield return Capture("fixture"+i+"-starmap");ui.ShutStarmap();
   GameMain.isFullscreenPaused=false;GameMain.Resume();yield return null;string roundtrip="RenderCompare-roundtrip-"+i;Check(GameSave.SaveCurrentGame(roundtrip),"Save roundtrip write failed");DSPGame.StartGame(roundtrip);yield return null;deadline=Time.realtimeSinceStartup+300;while(!Ready()&&Time.realtimeSinceStartup<deadline)yield return null;Check(Ready(),"Save roundtrip reload failed");
   DSPGame.EndGame();yield return new WaitForSecondsRealtime(2);
  }
 }
 IEnumerator Capture(string label){
  yield return new WaitForEndOfFrame();Check(!UIRoot.instance.uiGame.escMenu.active,"Pause menu obscures comparison view");Check(Screen.width==config.width&&Screen.height==config.height,"Surface dimensions changed during batch");var c=GameCamera.main;var p=GameMain.mainPlayer;var poser=GameCamera.instance.rtsPoser;
  var f=new Frame{label=label,fixture=fixtureName,fixtureSHA256=fixtureHash,graphics=SystemInfo.graphicsDeviceName,width=Screen.width,height=Screen.height,planet=p.planetId,factories=GameMain.data.factoryCount,tick=GameMain.gameTick,playerPosition=p.position,cameraPosition=c.transform.position,cameraRotation=c.transform.rotation,projection=c.projectionMatrix,yaw=poser.yawWanted,pitch=poser.pitchCoefWanted,zoom=poser.distCoefWanted,fov=c.fieldOfView,near=c.nearClipPlane,far=c.farClipPlane,paused=GameMain.isPaused,hdr=c.allowHDR,shadows=(int)QualitySettings.shadows,shadowCascades=QualitySettings.shadowCascades,msaa=QualitySettings.antiAliasing,options=JsonUtility.ToJson(DSPGame.globalOption),bloomExpectedFormat=(DSPPadRenderFormats.DesktopBloomCandidate?RenderTextureFormat.ARGBHalf:(Application.isMobilePlatform?RenderTextureFormat.Default:RenderTextureFormat.DefaultHDR)).ToString()};
  var post=c.GetComponent<PostProcessingBehaviour>();if(post&&post.profile)f.postProfile=JsonUtility.ToJson(post.profile);
  foreach(var b in c.GetComponents<Behaviour>())f.cameraComponents+=b.GetType().FullName+"="+b.enabled+";";
  var shaders=new HashSet<string>();foreach(var material in Resources.FindObjectsOfTypeAll<Material>())if(material.shader&&!material.shader.isSupported&&shaders.Add(material.shader.name))f.unsupportedShaders.Add(material.shader.name);
  Vector3 up=p.position.normalized;Vector3 forward=Vector3.ProjectOnPlane(c.transform.forward,up).normalized;
  for(int n=0;n<16;n++){var dir=Quaternion.AngleAxis(n*22.5f,up)*forward;foreach(var hit in Physics.SphereCastAll(p.position+up*.5f,.35f,dir,3f,15873,QueryTriggerInteraction.Ignore))f.collisions.Add("angle="+(n*22.5f)+" distance="+hit.distance+" name="+hit.collider.name+" type="+hit.collider.GetType().Name+" layer="+hit.collider.gameObject.layer+" bounds="+hit.collider.bounds);}
  var image=ScreenCapture.CaptureScreenshotAsTexture();try{Check(image.width==config.width&&image.height==config.height,"Captured image resolution mismatch");File.WriteAllBytes(Path.Combine(config.output,label+".png"),image.EncodeToPNG());}finally{Destroy(image);}
  if(label.Contains("technology")){CaptureText(config.output,label);DSPPadFontAudit.Capture(config.output,label);}
  DSPRayReceiverAudit.Capture(config.output,label);
  f.nativeCensusCaptured=DSPPadMemoryInventory.CaptureNative("23-matched-"+label);
  File.WriteAllText(Path.Combine(config.output,label+".json"),JsonUtility.ToJson(f,true));report.frames.Add(label);Write("capturing_"+label);yield return null;
 }
}
