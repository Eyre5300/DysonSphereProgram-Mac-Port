using System;using System.IO;using System.Collections;using System.Collections.Generic;using System.Reflection;using System.Runtime.InteropServices;using UnityEngine;using UnityEngine.EventSystems;
// Opt-in high-refresh batch. Fixtures may open windows or supply inventory;
// every close/cancel/pause assertion uses native Escape packets and game code.
public static class DSPPadEscapeAudit {
 [DllImport("@rpath/UnityFramework.framework/UnityFramework")]static extern int DSPAOTQueueTestKey(int code,int pressed);
 [DllImport("@rpath/UnityFramework.framework/UnityFramework")]static extern void DSPAOTEndTestKeyboard();
 [DllImport("@rpath/UnityFramework.framework/UnityFramework")]static extern int DSPAOTQueueTestPointer(float x,float y,int buttons,float dx,float dy,float wheel);
 [DllImport("@rpath/UnityFramework.framework/UnityFramework")]static extern void DSPAOTEndTestPointer();
 [Serializable]sealed class Check {public string name,evidence;public bool passed;}
 [Serializable]sealed class Transition {public int frame,state;public long tick;}
 [Serializable]sealed class Report {
  public string batchIdentifier=DSPPadDiagnosticLaunch.BatchIdentifier,buildVersion=DSPPadDiagnosticLaunch.BuildVersion,phase;
  public bool completed,savePathRestored,optionsUnchanged;public float measuredFPS;public int framesWithoutLogic;
  public List<Check> checks=new List<Check>();public List<string> errors=new List<string>();public List<Transition> rapidTransitions=new List<Transition>();
 }
 static Report report;static FieldInfo saveField;static string oldSavePath;static GameOption oldOption;static bool captured;static Vector2 point;static long lastTick=-1;static bool recording;
 public static bool Passed=>report!=null&&report.completed&&report.savePathRestored&&report.optionsUnchanged&&report.errors.Count==0;
 static void Write(){File.WriteAllText(Path.Combine(Application.persistentDataPath,"escape-audit.json"),JsonUtility.ToJson(report,true));}
 static void Assert(string name,bool value,string evidence=""){report.checks.Add(new Check{name=name,passed=value,evidence=evidence});Write();if(!value)throw new Exception(name+": "+evidence);}
 static void Key(KeyCode key,bool down){if(DSPAOTQueueTestKey(DSPPadKeyboard.HID(key),down?1:0)!=1)throw new Exception("Rejected key");}
 static void Esc(){Key(KeyCode.Escape,true);Key(KeyCode.Escape,false);}
 static int State(){var ui=UIRoot.instance.uiGame;var p=GameMain.mainPlayer;return(ui.inventoryWindow.active?1:0)|(ui.mechaWindow.active?2:0)|(ui.itemPicker.active?4:0)|(p.inhandItemId!=0?8:0)|(p.controller.cmd.type==ECommand.Build?16:0)|(GameMain.isPaused?32:0);}
 static void Record(){
  if(GameMain.isRunning&&!GameMain.isPaused&&!DSPGame.IsMenuDemo){long tick=GameMain.gameTick;if(tick==lastTick)report.framesWithoutLogic++;lastTick=tick;}
  if(recording){int state=State();var list=report.rapidTransitions;if(list.Count==0||list[list.Count-1].state!=state)list.Add(new Transition{frame=Time.frameCount,tick=GameMain.gameTick,state=state});}
 }
 static IEnumerator Wait(float seconds){float end=Time.realtimeSinceStartup+seconds;do{if(DSPAOTQueueTestPointer(point.x/Screen.width,point.y/Screen.height,0,0,0,0)!=1)throw new Exception("Rejected pointer");yield return null;Record();}while(Time.realtimeSinceStartup<end);}
 static IEnumerator Tap(KeyCode key){Key(key,true);Key(key,false);yield return Wait(.25f);}
 static void WorldPoint(){var hits=new List<RaycastResult>();for(int y=3;y<8;y++)for(int x=3;x<8;x++){point=new Vector2(Screen.width*x*.1f,Screen.height*y*.1f);hits.Clear();EventSystem.current.RaycastAll(new PointerEventData(EventSystem.current){position=point},hits);if(hits.Count==0)return;}throw new Exception("No uncovered world point");}
 static IEnumerator Preview(int item){
  var p=GameMain.mainPlayer;p.TryAddItemToPackage(item,5,0,false);int slot=-1;for(int i=0;i<p.package.size;i++)if(p.package.grids[i].itemId==item){slot=i;break;}
  WorldPoint();p.SetHandItems(item,1,slot);yield return Wait(.3f);
  Assert("preview ready "+item,p.inhandItemId==item&&p.controller.cmd.type==ECommand.Build&&p.controller.actionBuild.activeTool!=null,"state="+State());
 }
 static IEnumerator CancelBuild(string label){
  var p=GameMain.mainPlayer;WorldPoint();yield return Wait(.1f);yield return Tap(KeyCode.Escape);
  Assert(label+" cancels hand before pause",p.inhandItemId==0&&!GameMain.isPaused,"state="+State());
  yield return Tap(KeyCode.Escape);Assert(label+" leaves build before pause",p.controller.cmd.type!=ECommand.Build&&!GameMain.isPaused,"state="+State());
 }
 static IEnumerator Sequence(){
  oldOption=DSPGame.globalOption;captured=true;saveField=typeof(GameConfig).GetField("gameSavePath",BindingFlags.Static|BindingFlags.NonPublic);
  if(saveField==null)throw new Exception("Missing save isolation");oldSavePath=(string)saveField.GetValue(null);
  string folder=Path.Combine(Application.persistentDataPath,"escape-audit-"+DSPPadDiagnosticLaunch.BatchIdentifier);Directory.CreateDirectory(folder);saveField.SetValue(null,folder+Path.DirectorySeparatorChar);
  var option=oldOption;option.autoSaveTime=0;DSPGame.globalOption=option;
  var desc=new GameDesc();desc.SetForNewGame(UniverseGen.algoVersion,20261011,64,1,1);DSPGame.StartGameSkipPrologue(desc);report.phase="isolated-world-loading";Write();yield return null;
  float end=Time.realtimeSinceStartup+240;while((!GameMain.isRunning||GameMain.isLoading||DSPGame.IsMenuDemo||GameMain.localPlanet==null||!GameMain.localPlanet.factoryLoaded||GameMain.gameTick<120)&&Time.realtimeSinceStartup<end)yield return null;
  Assert("isolated world entered",GameMain.isRunning&&!DSPGame.IsMenuDemo&&GameMain.localPlanet!=null&&GameMain.localPlanet.factoryLoaded&&GameMain.gameTick>=120);
  point=new Vector2(Screen.width*.5f,Screen.height*.5f);DSPPadBatchFixture.Prepare();yield return Wait(3);
  var ui=UIRoot.instance.uiGame;var p=GameMain.mainPlayer;ui.researchResultTip.FadeOut();if(GameMain.data.guideRunning)GameMain.data.EndStandardModeGuide(false);yield return Wait(1);WorldPoint();
  float started=Time.realtimeSinceStartup;int frames=Time.frameCount;yield return Wait(3);report.measuredFPS=(Time.frameCount-frames)/(Time.realtimeSinceStartup-started);
  Assert("high refresh without frame cap",report.measuredFPS>90,"FPS="+report.measuredFPS+" target="+Application.targetFrameRate+" vsync="+QualitySettings.vSyncCount);
  report.phase="escape-regression";Write();
  foreach(int item in new[]{2301,2001,2011}){yield return Preview(item);yield return CancelBuild("tool "+item);}
  // Repeated presses at shifting render/fixed phases, not a single lucky run.
  for(int i=0;i<12;i++){yield return Preview(2301);for(int f=0;f<i%5;f++)yield return null;yield return CancelBuild("phase "+i);}
  yield return Preview(2301);yield return Tap(KeyCode.C);Assert("C opens original window pair",ui.mechaWindow.active&&ui.inventoryWindow.active);
  UIItemPicker.Popup(Vector2.zero,null);yield return Wait(.2f);Assert("picker fixture active",ui.itemPicker.active);
  yield return Tap(KeyCode.Escape);Assert("picker closes before inventory",!ui.itemPicker.active&&ui.inventoryWindow.active&&ui.mechaWindow.active&&p.inhandItemId==2301&&!GameMain.isPaused);
  yield return Tap(KeyCode.Escape);Assert("inventory closes before mecha",!ui.inventoryWindow.active&&ui.mechaWindow.active&&p.inhandItemId==2301&&!GameMain.isPaused);
  yield return Tap(KeyCode.Escape);Assert("mecha closes before build",!ui.mechaWindow.active&&p.inhandItemId==2301&&!GameMain.isPaused);
  yield return CancelBuild("nested windows");
  // Six complete taps arrive between two renders. Keep all intermediate states.
  yield return Preview(2301);yield return Tap(KeyCode.C);WorldPoint();yield return Wait(.1f);recording=true;Record();
  for(int i=0;i<6;i++)Esc();yield return Wait(1);recording=false;
  int[] expected={27,26,24,16,0,32,0};bool exact=report.rapidTransitions.Count==expected.Length;for(int i=0;exact&&i<expected.Length;i++)exact=report.rapidTransitions[i].state==expected[i];
  Assert("six rapid taps preserve every original layer",exact,string.Join(",",report.rapidTransitions.ConvertAll(t=>t.state.ToString()).ToArray()));
  yield return Preview(2301);Key(KeyCode.Escape,true);yield return Wait(.9f);Assert("held Esc cancels once",p.inhandItemId==0&&p.controller.cmd.type==ECommand.Build&&!GameMain.isPaused);Key(KeyCode.Escape,false);yield return Wait(.25f);
  yield return Tap(KeyCode.Escape);Assert("release then press leaves build",p.controller.cmd.type!=ECommand.Build&&!GameMain.isPaused);
  yield return Tap(KeyCode.Escape);Assert("unconsumed Esc opens pause",GameMain.isPaused);
  UIRoot.instance.optionWindow._Open();yield return Wait(.3f);yield return Tap(KeyCode.Escape);Assert("options close before pause resumes",!UIRoot.instance.optionWindow.active&&GameMain.isPaused);
  yield return Tap(KeyCode.Escape);Assert("Esc resumes suspended simulation",!GameMain.isPaused);
  Key(KeyCode.Escape,true);yield return Wait(.9f);Assert("held Esc does not resume newly opened pause",GameMain.isPaused);Key(KeyCode.Escape,false);yield return Wait(.25f);
  yield return Tap(KeyCode.Escape);Assert("fresh Esc resumes after long hold",!GameMain.isPaused);
  ui.OpenTechTree();yield return Wait(.4f);Assert("technology fixture active",ui.techTree.active);yield return Tap(KeyCode.Escape);Assert("technology closes without pause",!ui.techTree.active&&!GameMain.isPaused);
  ui.OpenStarmapWithCurrentLocation();yield return Wait(.4f);Assert("starmap fixture active",ui.starmap.active);yield return Tap(KeyCode.Escape);Assert("starmap closes without pause",!ui.starmap.active&&!GameMain.isPaused);
  ui.OpenBlueprintBrowser();yield return Wait(.4f);Assert("blueprint fixture active",ui.blueprintBrowser.active);yield return Tap(KeyCode.Escape);Assert("blueprint closes without pause",!ui.blueprintBrowser.active&&!GameMain.isPaused);
  yield return Wait(.5f);Assert("no delayed Esc remains",!GameMain.isPaused&&!DSPPadEscapeOrder.PauseRequested);
  Assert("render frames without simulation covered",report.framesWithoutLogic>100,"frames="+report.framesWithoutLogic);
  DSPPadManagedInputTrace.Flush();File.WriteAllText(Path.Combine(Application.persistentDataPath,"escape-input-trace.json"),DSPPadManagedInputTrace.Dump());
 }
 public static IEnumerator Run(){
  if(!DSPPadDiagnosticLaunch.EscapeAuditRequested)yield break;report=new Report();var stack=new Stack<IEnumerator>();stack.Push(Sequence());
  try{while(stack.Count>0){bool more=false;object next=null;Exception error=null;try{more=stack.Peek().MoveNext();if(more)next=stack.Peek().Current;}catch(Exception e){error=e;}
   if(error!=null){report.errors.Add(error.ToString());break;}if(!more){(stack.Pop() as IDisposable)?.Dispose();continue;}if(next is IEnumerator){stack.Push((IEnumerator)next);continue;}yield return next;
  }report.completed=stack.Count==0;}
  finally{
   while(stack.Count>0)(stack.Pop() as IDisposable)?.Dispose();DSPAOTEndTestKeyboard();DSPAOTEndTestPointer();DSPPadInput.ResetInputAxes();
   if(GameMain.isRunning)DSPGame.EndGame();
   if(saveField!=null&&oldSavePath!=null){saveField.SetValue(null,oldSavePath);report.savePathRestored=(string)saveField.GetValue(null)==oldSavePath;}
   if(captured){DSPGame.globalOption=oldOption;report.optionsUnchanged=true;}
   report.phase=Passed?"passed":"failed";Write();
  }
 }
}
