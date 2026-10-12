using System;using System.IO;using System.Collections;using System.Collections.Generic;using UnityEngine;using UnityEngine.Profiling;
// Private opt-in full-game test driver; silent batches, isolated diagnostic save.
public sealed class DSPPadBridgeDiagnostics:MonoBehaviour {
 [Serializable] sealed class Report {public string phase,unity,graphics,save,batchIdentifier,buildVersion;public long vertaFileBackedBytes;public int vertaLoads,vertaUploads,vertaMaterializations;public int width,height;public long tick,managedBytes,unityAllocatedBytes,unityReservedBytes;public bool autoTestCompleted,touchEnabled,autoTestRequested;public string launchArgumentError;public int uiRejectedTouches,touchFrames,lookFrames,mouseFrames,mouseButtons;public bool physicalMouse,nativePositionValid,uikitPointerSource,diagnosticPointerSource;public int nativeDownMask,nativeUpMask,uiInputBindings;public string uiInputBindingFailure;public float lookDistance,rtsYaw,rtsPitch;public string lastUIBlocker;public bool focused,paused,fullscreenUI,inputing;public List<string> checks=new List<string>();public bool escVisible;public int escPresses,escFixedSamples,worldTapPresses,worldTapFixedDownSamples,worldTapFixedUpSamples,worldTapCanceled;public bool keyboardAndMouse;public int starmapRefreshedTaps,starmapRejectedTaps;public string starmapLastRejection;public List<string> errors=new List<string>();}
 readonly Report r=new Report();float written;
 static string Folder=>Application.persistentDataPath;
 [RuntimeInitializeOnLoadMethod(RuntimeInitializeLoadType.BeforeSceneLoad)] static void Install(){Input.simulateMouseWithTouches=false;if(!DSPPadDiagnosticLaunch.TelemetryAllowed)return;var go=new GameObject("iPad bridge diagnostics");DontDestroyOnLoad(go);go.AddComponent<DSPPadBridgeDiagnostics>();}
 void Awake(){DSPPadMemoryPressureProbe.Install();if(DSPPadDiagnosticLaunch.AutomaticActionsAllowed){AudioListener.volume=0;AudioListener.pause=true;var stale=Path.Combine(Folder,"emu-command.txt");if(File.Exists(stale))File.Delete(stale);}r.autoTestRequested=DSPPadDiagnosticLaunch.AutomaticActionsAllowed;r.launchArgumentError=DSPPadDiagnosticLaunch.ArgumentError;Application.logMessageReceived+=Log;r.phase="boot";Write();}
 void OnDestroy(){Application.logMessageReceived-=Log;}
 void OnApplicationFocus(bool value){if(!value)DSPSmartTouchFrame.Reset();}
 void OnApplicationPause(bool value){if(value)DSPSmartTouchFrame.Reset();}
 void Log(string text,string stack,LogType type){if(type==LogType.Error||type==LogType.Exception||type==LogType.Assert){if(r.errors.Count<40&&!r.errors.Contains(text))r.errors.Add(text+"\n"+stack);busy=false;Write();}}
 void Write(){r.vertaFileBackedBytes=DSPPadVertaBacking.LiveBytes;r.vertaLoads=DSPPadVertaBacking.Loads;r.vertaUploads=DSPPadVertaBacking.Uploads;r.vertaMaterializations=DSPPadVertaBacking.Materializations;r.batchIdentifier=DSPPadDiagnosticLaunch.BatchIdentifier;r.buildVersion=DSPPadDiagnosticLaunch.BuildVersion;r.unity=Application.unityVersion;r.graphics=SystemInfo.graphicsDeviceName;r.width=Screen.width;r.height=Screen.height;r.tick=GameMain.gameTick;r.managedBytes=GC.GetTotalMemory(false);r.unityAllocatedBytes=Profiler.GetTotalAllocatedMemoryLong();r.unityReservedBytes=Profiler.GetTotalReservedMemoryLong();r.touchEnabled=DSPSmartTouchFrame.Enabled;r.uiRejectedTouches=DSPSmartTouchFrame.UIRejectedTouches;r.physicalMouse=DSPPadInput.PhysicalMouse;r.nativePositionValid=DSPPadInput.NativePositionValid;r.uikitPointerSource=DSPPadInput.UIKitPointerSource;r.diagnosticPointerSource=DSPPadInput.DiagnosticPointerSource;r.nativeDownMask=DSPPadInput.NativeDownMask;r.nativeUpMask=DSPPadInput.NativeUpMask;r.uiInputBindings=DSPPadEventSystemInput.BindingCount;r.uiInputBindingFailure=DSPPadEventSystemInput.LastBindingFailure;r.mouseFrames=DSPPadInput.MouseFrames;r.mouseButtons=DSPPadInput.ButtonMask;r.touchFrames=DSPSmartTouchFrame.TouchFrames;r.lookFrames=DSPSmartTouchFrame.LookFrames;r.lookDistance=DSPSmartTouchFrame.LookDistance;r.lastUIBlocker=DSPSmartTouchFrame.LastUIBlocker;r.escVisible=DSPPadEscapeButton.Visible;r.escPresses=DSPPadInput.VirtualEscapePresses;r.escFixedSamples=DSPPadInput.VirtualEscapeFixedSamples;r.worldTapPresses=DSPPadInput.WorldTapPresses;r.worldTapFixedDownSamples=DSPPadInput.WorldTapFixedDownSamples;r.worldTapFixedUpSamples=DSPPadInput.WorldTapFixedUpSamples;r.worldTapCanceled=DSPPadInput.WorldTapCanceled;r.keyboardAndMouse=DSPSmartTouchFrame.KeyboardAndMouse;r.starmapRefreshedTaps=DSPPadStarmapTouch.RefreshedTaps;r.starmapRejectedTaps=DSPPadStarmapTouch.RejectedTaps;r.starmapLastRejection=DSPPadStarmapTouch.LastRejection;r.focused=Application.isFocused;r.paused=GameMain.isPaused;r.fullscreenUI=VFInput.inFullscreenGUI;r.inputing=VFInput.inputing;if(GameCamera.instance&&GameCamera.instance.rtsPoser){r.rtsYaw=GameCamera.instance.rtsPoser.yaw;r.rtsPitch=GameCamera.instance.rtsPoser.pitch;}File.WriteAllText(Path.Combine(Folder,"emu-full-game-report.json"),JsonUtility.ToJson(r,true));}
 bool busy;string waitingCommand;float commandStableSince;
 void Update(){DSPPadMemoryPressureProbe.Poll();DSPPadMemoryInventory.Poll();if(DSPPadDiagnosticLaunch.AutomaticActionsAllowed){AudioListener.volume=0;AudioListener.pause=true;}if(DSPPadDiagnosticLaunch.AutomaticActionsAllowed&&!busy&&File.Exists(Path.Combine(Folder,"emu-command.txt"))){string command=File.ReadAllText(Path.Combine(Folder,"emu-command.txt")).Trim();if(command!=waitingCommand){waitingCommand=command;commandStableSince=Time.realtimeSinceStartup;}else if(Time.realtimeSinceStartup-commandStableSince>1){File.Delete(Path.Combine(Folder,"emu-command.txt"));waitingCommand=null;Stage("command_"+command);StartCoroutine(Command(command));}}if(Time.realtimeSinceStartup-written>3){written=Time.realtimeSinceStartup;Write();}}
 void Stage(string name){r.phase=name;Write();DSPPadMemoryInventory.Stage(name);}
 IEnumerator Capture(string file){yield return new WaitForEndOfFrame();var t=ScreenCapture.CaptureScreenshotAsTexture();try{File.WriteAllBytes(Path.Combine(Folder,file),t.EncodeToPNG());}finally{Destroy(t);}yield return null;}
  IEnumerator Command(string command){if(!DSPPadDiagnosticLaunch.AutomaticActionsAllowed)yield break;busy=true;try{if(command=="audit")DSPPadRenderDiagnostics.AuditNow();else if(command=="render_ab")yield return DSPPadRenderDiagnostics.RenderAB();else if(command=="capture")yield return DSPPadRenderDiagnostics.Capture("manual");else if(command=="end_game"){if(GameMain.isRunning)DSPGame.EndGame();Stage("ended_normally");}else if(command=="exit")DSPGame.ExitProgram();}finally{busy=false;Write();}}
 IEnumerator EscPulse(string label){yield return new WaitForSecondsRealtime(.4f);bool clicked=DSPPadEscapeButton.ClickForDiagnostics();r.checks.Add(label+"_escape_button_hit="+clicked+" blocker="+DSPPadEscapeButton.LastBlockingUI+" layer="+DSPPadEscapeButton.CurrentLayer);yield return new WaitForSecondsRealtime(.8f);Write();}
 // This probes the real original world-raycast/order pipeline, not a physical
 // finger gesture. Do not count it as human touch/Universal Control proof.
 IEnumerator WorldMineProbe(){
  var p=GameMain.mainPlayer;var f=p!=null?p.factory:null;var c=Camera.main;
  if(p==null||f==null||!c||DSPSmartTouchFrame.KeyboardAndMouse){r.checks.Add("world_mine_probe_skipped=unavailable_or_keyboard_mouse");yield break;}
  int id=0;Vector2 point=Vector2.zero;float best=float.MaxValue;
  for(int i=1;i<f.veinCursor;i++){
   var v=f.veinPool[i];if(v.id!=i||v.amount<=0)continue;var screen=c.WorldToScreenPoint(v.pos);
   float distance=(v.pos-p.position).sqrMagnitude;
   if(screen.z<=0||screen.x<Screen.width*.12f||screen.x>Screen.width*.88f||screen.y<Screen.height*.22f||screen.y>Screen.height*.78f||distance>=best||DSPSmartTouchFrame.UIBlocks(screen))continue;
   id=i;point=screen;best=distance;
  }
  if(id==0){r.checks.Add("world_mine_probe_skipped=no_visible_vein");yield break;}
  int before=f.veinPool[id].amount;bool queued=DSPPadInput.QueueWorldTap(point,1);r.checks.Add("world_right_tap_queued="+queued+" vein="+id);
  if(queued){
   yield return new WaitForSecondsRealtime(1);
   var order=p.currentOrder;r.checks.Add("original_mine_order="+(order!=null&&order.type==EOrderType.Mine&&order.objType==EObjectType.Vein&&order.objId==id));
   yield return new WaitForSecondsRealtime(8);
   r.checks.Add("vein_mined="+(f.veinPool[id].amount<before)+" original_amount="+before+" current="+f.veinPool[id].amount);
   yield return DSPPadRenderDiagnostics.Capture("12-original-mine-input");
  }
  Write();
 }
 IEnumerator Start(){
  if(!DSPPadDiagnosticLaunch.AutomaticActionsAllowed){Stage("normal_launch");yield break;}
  busy=true;
  if(DSPPadDiagnosticLaunch.BCProbeRequested){Stage("bc_probe_waiting");yield break;}
  float limit=Time.realtimeSinceStartup+300;while(!VFPreload.done&&Time.realtimeSinceStartup<limit){var p=FindObjectOfType<VFPreload>();if(p!=null&&p.languageSelectGroup.gameObject.activeSelf)p.SelectLanguageZHCN();yield return new WaitForSecondsRealtime(1);}
  if(!VFPreload.done){Stage("preload_timeout");busy=false;DSPGame.ExitProgram();yield break;}
  Stage("main_menu");yield return new WaitForSecondsRealtime(3);yield return Capture("emu-full-game-menu.png");
  string flag=Path.Combine(Folder,"emu-full-game-first-test-completed.flag");if(File.Exists(flag)){r.save=File.ReadAllText(flag).Trim();DSPGame.StartGame(r.save);}else {
  var desc=new GameDesc();desc.SetForNewGame(UniverseGen.algoVersion,20261011,64,1,1);DSPGame.StartGameSkipPrologue(desc);}
  Stage("new_game_loading");
  limit=Time.realtimeSinceStartup+240;while(!(GameMain.isRunning&&!DSPGame.IsMenuDemo&&GameMain.data!=null&&GameMain.data.guideComplete&&GameMain.localPlanet!=null&&GameMain.localPlanet.factoryLoaded&&GameMain.gameTick>120)&&Time.realtimeSinceStartup<limit)yield return new WaitForSecondsRealtime(1);
  if(!GameMain.isRunning||GameMain.localPlanet==null||!GameMain.localPlanet.factoryLoaded||GameMain.gameTick<=120){Stage("new_game_timeout");busy=false;DSPGame.ExitProgram();yield break;}
  Stage("new_game_running");yield return Capture("emu-full-game-newgame.png");
  if(DSPPadDiagnosticLaunch.WorldAuditRequested){Stage("world_audit");yield return DSPPadWorldAudit.Run();if(!DSPPadWorldAudit.Passed)r.errors.Add("World rendering/input audit failed");}
  if(DSPTouchControls.Enabled||DSPPadDiagnosticLaunch.InputFilesRequested||DSPPadDiagnosticLaunch.WorldAuditRequested){
   Stage("input_files_regression");yield return DSPPadIntegrationRegression.Run();if(!DSPPadIntegrationRegression.Passed)r.errors.Add("Input/files integration failed");
   if(DSPTouchControls.Enabled){DSPPadInputMode.SetPreference(DSPPadInputMode.Choice.Touch);yield return new WaitForSecondsRealtime(.5f);Stage("touch_combined_regression");yield return DSPTouchRegression.Run();if(!DSPTouchRegression.Passed)r.errors.Add("Touch combined regression failed");DSPPadInputMode.SetPreference(DSPPadInputMode.Choice.Keyboard);yield return new WaitForSecondsRealtime(.5f);}
   DSPPadBatchFixture.Prepare();Stage("keyboard_regression_batch");yield return DSPPadKeyboardRegression.Run();Stage("mouse_regression_batch");yield return DSPPadMouseRegression.Run();
   if(DSPTouchControls.Enabled)DSPPadInputMode.SetPreference(DSPPadInputMode.Choice.Automatic);
   r.autoTestCompleted=true;busy=false;Stage("batch_finished_normal_exit");DSPGame.ExitProgram();yield break;
  }

  Stage("render_regression");yield return DSPPadRenderDiagnostics.RegressionViews();
  Stage("shadow_regression");yield return DSPPadShadowRegression.Run();
  var ui=UIRoot.instance.uiGame;
  Stage("interface_batch");ui.inventoryWindow._Open();yield return new WaitForSecondsRealtime(1);yield return DSPPadRenderDiagnostics.Capture("12-inventory");yield return EscPulse("inventory");r.checks.Add("inventory_closed_by_escape="+!ui.inventoryWindow.active);if(ui.inventoryWindow.active)ui.inventoryWindow._Close();
  ui.OpenStarmapWithCurrentLocation();yield return new WaitForSecondsRealtime(1);yield return DSPPadRenderDiagnostics.Capture("12-starmap");yield return EscPulse("starmap");r.checks.Add("starmap_closed_by_escape="+!ui.starmap.active);if(ui.starmap.active)ui.ShutStarmap();
  ui.OpenDysonEditor();yield return new WaitForSecondsRealtime(1);yield return DSPPadRenderDiagnostics.Capture("12-dyson");yield return EscPulse("dyson");r.checks.Add("dyson_closed_by_escape="+!ui.dysonEditor.active);if(ui.dysonEditor.active)ui.dysonEditor._Close();
  UIRoot.instance.OpenMechaEditor();yield return new WaitForSecondsRealtime(1);yield return DSPPadRenderDiagnostics.Capture("12-mecha");yield return EscPulse("mecha");r.checks.Add("mecha_closed_by_escape="+!UIRoot.instance.uiMechaEditor.active);if(UIRoot.instance.uiMechaEditor.active)UIRoot.instance.CloseMechaEditor();
  ui.OpenTechTree();yield return new WaitForSecondsRealtime(1);yield return DSPPadRenderDiagnostics.Capture("12-technology");yield return EscPulse("technology");r.checks.Add("technology_closed_by_escape="+!ui.techTree.active);if(ui.techTree.active)ui.ShutTechTree();
  ui.OpenBlueprintBrowser();yield return new WaitForSecondsRealtime(1);yield return DSPPadRenderDiagnostics.Capture("12-blueprint-browser");yield return EscPulse("blueprint-browser");r.checks.Add("blueprint_browser_closed_by_escape="+!ui.blueprintBrowser.active);if(ui.blueprintBrowser.active)ui.ShutBlueprintBrowser();
  ui.OpenReplicatorWindow();yield return new WaitForSecondsRealtime(1);yield return DSPPadRenderDiagnostics.Capture("12-replicator");yield return EscPulse("replicator");r.checks.Add("replicator_closed_by_escape="+!ui.replicator.active);if(ui.replicator.active)ui.replicator._Close();
  yield return EscPulse("pause");r.checks.Add("paused_by_escape="+GameMain.isPaused);yield return DSPPadRenderDiagnostics.Capture("12-pause");
  yield return EscPulse("resume");r.checks.Add("resumed_by_escape="+!GameMain.isPaused);if(GameMain.isPaused)GameMain.Resume();
  Write();
  // Pure-touch expansion is deferred by the user; this batch exercises keyboard/mouse.
  Stage("keyboard_regression_batch");DSPPadBatchFixture.Prepare();yield return new WaitForSecondsRealtime(1);yield return DSPPadKeyboardRegression.Run();
  Stage("mouse_regression_batch");yield return DSPPadMouseRegression.Run();
  Stage("save_reload_batch");yield return DSPPadBatchFixture.Roundtrip();
  string handoffSave=DSPPadBatchFixture.HandoffSave??r.save;Stage("matched_large_save_render_batch");yield return DSPPadMatchedRenderRegression.RunBatch();
  if(DSPPadDiagnosticLaunch.HumanHandoffRequested&&!string.IsNullOrEmpty(handoffSave)){DSPGame.StartGame(handoffSave);yield return new WaitForSecondsRealtime(5);}
  Stage("functional_batch_20");yield return DSPPadFunctionalBatch.RunBatch();
  r.autoTestCompleted=true;busy=false;
  if(DSPPadDiagnosticLaunch.HumanHandoffRequested){Stage("ready_for_human_test_no_auto_exit");yield break;}
  Stage("batch_finished_normal_exit");DSPGame.ExitProgram();
 // One bounded physical-input retest, then the original game exit lifecycle.
 }
}
