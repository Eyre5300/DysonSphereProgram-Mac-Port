using System;using System.Collections;using System.Collections.Generic;using System.IO;using System.Reflection;using UnityEngine;
// Private opt-in diagnostics. Isolated generated worlds; never rewrite a user save.
public sealed class DSPPadFunctionalBatch:MonoBehaviour {
 [Serializable] sealed class StageResult {public string name,status,scope,error;public float seconds;}
 [Serializable] sealed class Report {public string phase;public bool completed;public List<StageResult> stages=new List<StageResult>();public List<string> errors=new List<string>();}
 [Serializable] sealed class Phase {public string phase;}
 Report report=new Report();string folder,savePath;FieldInfo pathField;GameOption options;bool haveOptions,finished;
 public static IEnumerator RunBatch(){if(!DSPPadDiagnosticLaunch.AutomaticActionsAllowed)yield break;var go=new GameObject("Private iPad functional batch");DontDestroyOnLoad(go);var b=go.AddComponent<DSPPadFunctionalBatch>();b.folder=Path.Combine(Application.persistentDataPath,"functional-batch-"+DSPPadDiagnosticLaunch.BuildVersion);Directory.CreateDirectory(b.folder);while(!b.finished)yield return null;Destroy(go);}
 void LateUpdate(){AudioListener.volume=0;AudioListener.pause=true;PortBlueprintAudit.PinPreview();}
 void Log(string text,string stack,LogType type){if(type==LogType.Error||type==LogType.Exception||type==LogType.Assert){if(report.errors.Count<100)report.errors.Add(text+"\n"+stack);}}
 void Write(string phase){report.phase=phase;File.WriteAllText(Path.Combine(folder,"report.json"),JsonUtility.ToJson(report,true));Debug.Log("IPAD_FUNCTIONAL "+phase);}
 static void Check(bool value,string why){if(!value)throw new Exception(why);}
 static bool Ready(){return GameMain.isRunning&&!DSPGame.IsMenuDemo&&GameMain.data!=null&&GameMain.mainPlayer!=null&&GameMain.localPlanet!=null&&GameMain.localPlanet.factoryLoaded;}
 IEnumerator Guard(IEnumerator run,string name,string scope,Func<bool> passed=null){
  var result=new StageResult{name=name,scope=scope,status="running"};report.stages.Add(result);Write(name);int errors=report.errors.Count;float start=Time.realtimeSinceStartup;var stack=new Stack<IEnumerator>();stack.Push(run);
  while(stack.Count>0){bool more=false;object next=null;try{more=stack.Peek().MoveNext();if(more)next=stack.Peek().Current;}catch(Exception e){result.error=e.ToString();}
   if(result.error!=null)break;if(!more){(stack.Pop() as IDisposable)?.Dispose();continue;}if(next is IEnumerator){stack.Push((IEnumerator)next);continue;}yield return next;
  }
  while(stack.Count>0){try{(stack.Pop() as IDisposable)?.Dispose();}catch(Exception e){result.error=e.ToString();}}
  PortBlueprintAudit.Clear();if(result.error==null&&passed!=null){try{if(!passed())result.error="Stage completion assertion failed";}catch(Exception e){result.error=e.ToString();}}
  if(result.error==null&&report.errors.Count>errors)result.error="Runtime errors recorded during stage";result.status=result.error==null?"passed":"failed";result.seconds=Time.realtimeSinceStartup-start;Write(name+"_"+result.status);
 }
 IEnumerator Start(){Application.logMessageReceived+=Log;yield return Guard(Run(),"batch_driver","Isolated test setup and sequence; individual stage status is authoritative");
  PortBlueprintAudit.Clear();if(haveOptions){DSPGame.globalOption=options;DSPGame.globalOption.Apply();}if(pathField!=null&&savePath!=null)pathField.SetValue(null,savePath);Application.logMessageReceived-=Log;
  bool ok=report.errors.Count==0;foreach(var s in report.stages)ok&=s.status=="passed";report.completed=true;Write(ok?"passed":"completed_with_failures");finished=true;
 }
 IEnumerator NewWorld(){if(GameMain.isRunning){DSPGame.EndGame();yield return new WaitForSecondsRealtime(2);}var d=new GameDesc();d.SetForNewGame(UniverseGen.algoVersion,20261011,64,1,1);d.isPeaceMode=true;DSPGame.StartGameSkipPrologue(d);yield return null;float end=Time.realtimeSinceStartup+240;while((!Ready()||GameMain.gameTick<120)&&Time.realtimeSinceStartup<end)yield return new WaitForSecondsRealtime(1);Check(Ready()&&GameMain.gameTick>=120,"Independent world failed to start");yield return new WaitForSecondsRealtime(2);}
 IEnumerator Blueprints(){GameMain.history.blueprintLimit=1048576;yield return PortBlueprintAudit.Run(folder);yield return PortBlueprintAudit.BuildSample();Check(File.ReadAllText(Path.Combine(folder,"blueprint-audit.txt")).Contains("actualBlueprintConstructionPassed=True"),"Blueprint construction not completed; inspect fixture conditions");}
 IEnumerator Run(){
  options=DSPGame.globalOption;haveOptions=true;var opt=options;opt.autoSaveTime=0;opt.audioVolume=0;DSPGame.globalOption=opt;opt.Apply();pathField=typeof(GameConfig).GetField("gameSavePath",BindingFlags.Static|BindingFlags.NonPublic);Check(pathField!=null,"Save isolation unavailable");savePath=(string)pathField.GetValue(null);string isolated=Path.Combine(folder,"test-saves");Directory.CreateDirectory(isolated);pathField.SetValue(null,isolated+Path.DirectorySeparatorChar);
  yield return Guard(NewWorld(),"production_world","Independent peace world");
  yield return Guard(PortProductionChainAudit.SafeRun(),"production_chain","Fixture connections; actual mining, belts, sorting, smelting, assembly and save/reload",()=>PortProductionChainAudit.Passed);
  yield return Guard(PortScienceLogisticsAudit.SafeRun(),"science_logistics","Fixture stock/power; actual research unlock and drone delivery with conservation and reload",()=>PortScienceLogisticsAudit.Passed);
  yield return Guard(Blueprints(),"blueprints","Owned import/export/previews; supplied materials/capacity, original placement conditions and construction drones");
  yield return Guard(NewWorld(),"sphere_world","Independent sphere world");
  yield return Guard(PortSphereAudit.SafeRun(),"dyson_geometry_paint","Fixture completed structures; mesh, paint, power and reload",()=>JsonUtility.FromJson<Phase>(File.ReadAllText(Path.Combine(Application.persistentDataPath,"sphere-audit.json"))).phase=="passed");
  yield return Guard(NewWorld(),"launch_world","Independent launch world");
  yield return Guard(PortLaunchAudit.SafeRun(),"rockets_sails","Fixture supplies; original launch, travel, absorption, construction and reload",()=>PortLaunchAudit.Passed);
  yield return Guard(NewWorld(),"interstellar_world","Independent transport world");
  yield return Guard(PortInterstellarAudit.SafeRun(),"interstellar_transport","Original dispatch, warp, delivery, return and reload in flight; supplied ships/cargo/energy",()=>PortInterstellarAudit.Passed);
  if(GameMain.isRunning){DSPGame.EndGame();yield return new WaitForSecondsRealtime(2);}
  yield return Guard(PortCombatAudit.SafeRun(),"ground_combat","Natural generated enemies, supplied gauss/laser turrets and ammo; original firing, damage, kills, reload",()=>PortCombatAudit.Passed);
  yield return Guard(Panels(),"statistics_panels","Nine original statistics tabs and control/crafting/mecha/inventory windows; not physical UI hit test");
  yield return Guard(Stability(),"stability_save_reload","Five-minute continuous simulation and isolated save/reload; not a multi-hour test");
 }
 IEnumerator Capture(string label){yield return new WaitForEndOfFrame();var t=ScreenCapture.CaptureScreenshotAsTexture();try{File.WriteAllBytes(Path.Combine(folder,label+".png"),t.EncodeToPNG());}finally{Destroy(t);}yield return null;}
 IEnumerator Panels(){Check(Ready(),"World unavailable for UI batch");var ui=UIRoot.instance.uiGame;ui.OpenProductionWindow();for(int i=0;i<9;i++){ui.statWindow.OnTabButtonClick(i);yield return new WaitForSecondsRealtime(2);Check(ui.statWindow.active&&ui.statWindow.tabIndex==i,"Statistics tab "+i+" failed");yield return Capture("statistics-"+i);}ui.statWindow._Close();ui.OpenControlPanelWindow();yield return new WaitForSecondsRealtime(2);Check(ui.controlPanelWindow.active,"Control panel failed");yield return Capture("control-panel");ui.controlPanelWindow._Close();ui.OpenReplicatorWindow();yield return new WaitForSecondsRealtime(2);Check(ui.replicator.active,"Replicator failed");ui.replicator._Close();ui.OpenMechaWindow();yield return new WaitForSecondsRealtime(2);Check(ui.mechaWindow.active,"Mecha window failed");ui.mechaWindow._Close();ui.inventoryWindow._Open();yield return new WaitForSecondsRealtime(2);Check(ui.inventoryWindow.active,"Inventory failed");ui.inventoryWindow._Close();}
 IEnumerator Stability(){Check(Ready(),"World unavailable for stability");GameMain.Resume();GameMain.isFullscreenPaused=false;long tick=GameMain.gameTick;string p=Path.Combine(folder,"stability.txt");for(int i=0;i<30;i++){yield return new WaitForSecondsRealtime(10);Check(Ready(),"World stopped during stability");File.AppendAllText(p,"sample="+i+" tick="+GameMain.gameTick+" managedBytes="+GC.GetTotalMemory(false)+" focus="+Application.isFocused+"\n");}Check(GameMain.gameTick>tick+1000,"Simulation not advancing");long savedTick=GameMain.gameTick;Check(GameSave.SaveCurrentGame("iPad-Functional-Stability"),"Stability save failed");DSPGame.StartGame("iPad-Functional-Stability");yield return null;float end=Time.realtimeSinceStartup+180;while(!Ready()&&Time.realtimeSinceStartup<end)yield return new WaitForSecondsRealtime(1);Check(Ready()&&GameMain.gameTick>=savedTick,"Stability reload failed");yield return Capture("stability-reloaded");}
}
