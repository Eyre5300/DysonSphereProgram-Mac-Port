using System;
using System.Collections;
using System.Collections.Generic;
using System.IO;
using UnityEngine;

// An explicitly armed local smoke test. Normal launches install no test object.
public sealed class PortConverterSmoke : MonoBehaviour {
 [Serializable] sealed class Result {
  public string phase,saveName,unity,graphics;
  public bool saved,reloaded,uiTargetsVerified,startupNativeFullscreenVerified;
  public int startupWidth,startupHeight;
  public long beforeSaveTick,afterReloadTick;
  public int width,height;
  public List<string> errors=new List<string>();
 }
 static string Folder=>Application.persistentDataPath;
 readonly Result result=new Result();
 [RuntimeInitializeOnLoadMethod(RuntimeInitializeLoadType.BeforeSceneLoad)]
 static void Install(){
  string flag=Path.Combine(Folder,"port-converter-smoke.flag");
  if(!File.Exists(flag))return;
  File.Delete(flag);AudioListener.volume=0;AudioListener.pause=true;
  var go=new GameObject("Explicit local converter smoke test");DontDestroyOnLoad(go);go.AddComponent<PortConverterSmoke>();
 }
 void Awake(){Application.logMessageReceived+=Log;}
 void OnDestroy(){Application.logMessageReceived-=Log;}
 void LateUpdate(){AudioListener.volume=0;AudioListener.pause=true;}
 void Log(string message,string stack,LogType type){
  if(type!=LogType.Error&&type!=LogType.Exception&&type!=LogType.Assert)return;
  string text=message+"\n"+stack;if(result.errors.Count<20&&!result.errors.Contains(text))result.errors.Add(text);
 }
 void Write(string phase){
  result.phase=phase;result.unity=Application.unityVersion;result.graphics=SystemInfo.graphicsDeviceName;result.width=Screen.width;result.height=Screen.height;
  File.WriteAllText(Path.Combine(Folder,"converter-smoke-result.json"),JsonUtility.ToJson(result,true));
 }
 static void CheckTarget(RenderTexture target,Camera camera,string name){
  if(target==null||!target.IsCreated()||camera==null||!camera.enabled||camera.targetTexture!=target)
   throw new Exception("UI render target inactive: "+name);
  if(target.format!=RenderTextureFormat.ARGBHalf||target.antiAliasing!=4||target.depth<24||target.bindTextureMS)
   throw new Exception("Original UI render descriptor changed: "+name);
  bool memoryless=(target.memorylessMode&RenderTextureMemoryless.MSAA)!=0;
  if(memoryless!=PortMemorylessUI.Enabled)throw new Exception("Unexpected UI MSAA storage: "+name);
 }
 IEnumerator CheckUIPages(string label){
  var ui=UIRoot.instance.uiGame;
  ui.OpenStarmapWithCurrentLocation();yield return new WaitForSecondsRealtime(2);
  CheckTarget(ui.starmap.starmapRT,ui.starmap.screenCamera,"starmap");
  CheckTarget(ui.starmap.gizmoRT,ui.starmap.gizmoCamera,"starmap gizmo");
  if(ui.starmap.starmapRT.width!=Screen.width||ui.starmap.starmapRT.height!=Screen.height)
   throw new Exception("Starmap resolution mismatch");
  ui.ShutStarmap();ui.OpenDysonEditor();yield return new WaitForSecondsRealtime(2);
  var dyson=FindObjectOfType<DysonMapCamera>();
  if(dyson==null)throw new Exception("Dyson camera missing");
  CheckTarget(dyson.screenRT,dyson.editorCamera,"Dyson editor");
  ui.dysonEditor._Close();UIRoot.instance.OpenMechaEditor();yield return new WaitForSecondsRealtime(2);
  var mecha=FindObjectOfType<MechaEditorCamera>();
  if(mecha==null)throw new Exception("Mecha camera missing");
  CheckTarget(mecha.screenRT,mecha.editorCamera,"Mecha editor");
  yield return new WaitForEndOfFrame();var image=ScreenCapture.CaptureScreenshotAsTexture();
  try{File.WriteAllBytes(Path.Combine(Folder,"converter-smoke-ui-"+label+".png"),image.EncodeToPNG());}finally{Destroy(image);}
  yield return null;UIRoot.instance.CloseMechaEditor();
 }
 IEnumerator CheckUIResize(){
  int width=Screen.width,height=Screen.height;var mode=Screen.fullScreenMode;var savedOption=DSPGame.globalOption;
  try{
   yield return CheckUIPages("initial");
   var windowed=savedOption;windowed.resolution.width=2266;windowed.resolution.height=1488;
   windowed.resolution.refreshRateRatio=GameResolutions.DoubleToRefreshRate(60);windowed.displayMode=EOptionDisplayMode.Windowed;
   DSPGame.globalOption=windowed;DSPGame.globalOption.Apply();yield return new WaitForSecondsRealtime(3);
   if(Application.platform==RuntimePlatform.IPhonePlayer){
    var native=PortDisplayPresets.StartupResolution;
    if(Screen.width!=native.width||Screen.height!=native.height||Screen.fullScreenMode!=FullScreenMode.FullScreenWindow)
     throw new Exception("iOS settings did not retain the native fullscreen surface");
   }else if(Screen.width!=2266||Screen.height!=1488||Screen.fullScreenMode!=FullScreenMode.Windowed)
    throw new Exception("Original user windowed option did not apply after startup");
   yield return CheckUIPages("resized");
  }finally{DSPGame.globalOption=savedOption;DSPGame.globalOption.Apply();}
  yield return new WaitForSecondsRealtime(3);yield return CheckUIPages("restored");
 }
 static bool Ready()=>GameMain.isRunning&&!DSPGame.IsMenuDemo&&GameMain.data!=null&&GameMain.data.guideComplete&&GameMain.mainPlayer!=null&&GameMain.localPlanet!=null&&GameMain.localPlanet.factoryLoaded;
 IEnumerator Start(){
  var stack=new Stack<IEnumerator>();stack.Push(Run());bool failed=false;
  while(stack.Count>0){var run=stack.Peek();object next=null;bool more=false;Exception failure=null;
   try{more=run.MoveNext();if(more)next=run.Current;}catch(Exception e){failure=e;}
   if(failure!=null){result.errors.Add(failure.ToString());failed=true;break;}
   if(!more){(stack.Pop() as IDisposable)?.Dispose();continue;}
   if(next is IEnumerator nested){stack.Push(nested);continue;}yield return next;
  }
  while(stack.Count>0)(stack.Pop() as IDisposable)?.Dispose();
  Write(!failed&&result.saved&&result.reloaded&&result.uiTargetsVerified&&result.errors.Count==0?"passed":"failed");
  yield return null;DSPGame.ExitProgram();
 }
 IEnumerator Run(){
  Write("preloading");float deadline=Time.realtimeSinceStartup+300;
  while(!VFPreload.done&&Time.realtimeSinceStartup<deadline){
   var loader=FindObjectOfType<VFPreload>();if(loader!=null&&loader.languageSelectGroup.gameObject.activeSelf)loader.SelectLanguageZHCN();
   yield return new WaitForSecondsRealtime(1);
  }
  if(!VFPreload.done)throw new Exception("Preload timed out");
  yield return new WaitForSecondsRealtime(2);
  if(Application.platform==RuntimePlatform.OSXPlayer||Application.platform==RuntimePlatform.IPhonePlayer){
   var native=PortDisplayPresets.StartupResolution;
   if(!PortDisplayPresets.StartupConfigured||Screen.width!=native.width||Screen.height!=native.height||Screen.fullScreenMode!=FullScreenMode.FullScreenWindow)
    throw new Exception("Startup did not use the detected native fullscreen surface");
   if(DSPGame.globalOption.resolution.width!=native.width||DSPGame.globalOption.resolution.height!=native.height||DSPGame.globalOption.displayMode!=EOptionDisplayMode.BorderlessFullScreenWithCursorConfined)
    throw new Exception("Startup UI options do not match native fullscreen");
   result.startupNativeFullscreenVerified=true;result.startupWidth=native.width;result.startupHeight=native.height;
  }
  var desc=new GameDesc();desc.SetForNewGame(UniverseGen.algoVersion,20261010,64,1,1);DSPGame.StartGameSkipPrologue(desc);Write("new_game");
  yield return null;deadline=Time.realtimeSinceStartup+240;
  while((!Ready()||GameMain.gameTick<120)&&Time.realtimeSinceStartup<deadline)yield return new WaitForSecondsRealtime(1);
  if(!Ready()||GameMain.gameTick<120)throw new Exception("New game failed to advance");
  Write("checking_ui_targets");yield return CheckUIResize();result.uiTargetsVerified=true;
  yield return new WaitForEndOfFrame();var image=ScreenCapture.CaptureScreenshotAsTexture();
  try{File.WriteAllBytes(Path.Combine(Folder,"converter-smoke-newgame.png"),image.EncodeToPNG());}finally{Destroy(image);}
  // Saving renders a thumbnail. Leave end-of-frame rendering before it re-enters Camera.Render.
  Write("screenshot_captured");yield return null;
  Debug.Log("PORT_SMOKE_SAVE_BEGIN");
  result.saveName="PortConverterSmoke-"+DateTime.UtcNow.ToString("yyyyMMdd-HHmmss")+"-"+Guid.NewGuid().ToString("N").Substring(0,6);
  result.beforeSaveTick=GameMain.gameTick;result.saved=GameSave.SaveCurrentGame(result.saveName);
  if(!result.saved)throw new Exception("Local smoke save failed");
  Write("saved");Debug.Log("PORT_SMOKE_SAVE_DONE");yield return null;
  DSPGame.StartGame(result.saveName);Write("reloading");yield return null;deadline=Time.realtimeSinceStartup+240;
  while(!Ready()&&Time.realtimeSinceStartup<deadline)yield return new WaitForSecondsRealtime(1);
  if(!Ready()||GameMain.data.gameDesc.galaxySeed!=20261010)throw new Exception("Reload did not restore the test world");
  yield return new WaitForSecondsRealtime(3);Write("checking_reloaded_ui");yield return CheckUIPages("reloaded");result.afterReloadTick=GameMain.gameTick;result.reloaded=result.afterReloadTick>result.beforeSaveTick;
 }
}
