using System;using System.IO;using System.Collections;using System.Collections.Generic;using System.Reflection;using UnityEngine;
// Explicitly selected batch: saved render modes and original space-flight input.
// Never uses the user's save directory or changes original flight rules.
public static class DSPPadFlightAudit {
 [System.Runtime.InteropServices.DllImport("@rpath/UnityFramework.framework/UnityFramework")]static extern int DSPAOTVerifyMouseCallbacks();
 [Serializable] sealed class Report {public string batchIdentifier=DSPPadDiagnosticLaunch.BatchIdentifier,buildVersion=DSPPadDiagnosticLaunch.BuildVersion,phase;public bool completed,savePathRestored;public List<string> checks=new List<string>();public List<string> errors=new List<string>();}
 static Report report;static FieldInfo saveField;static string oldSavePath;static GameOption oldOption;static bool optionsCaptured;
 public static bool Passed=>report!=null&&report.completed&&report.savePathRestored&&report.errors.Count==0&&DSPPadKeyboardRegression.Passed;
 static void Write(){File.WriteAllText(Path.Combine(Application.persistentDataPath,"flight-audit.json"),JsonUtility.ToJson(report,true));}
 static void Check(bool value,string detail){report.checks.Add((value?"PASS ":"FAIL ")+detail);Write();if(!value)throw new Exception(detail);}
 static IEnumerator Modes(){
  var ui=UIRoot.instance.optionWindow;ui._Open();yield return new WaitForSecondsRealtime(.3f);
  foreach(int width in new[]{1600,1376}){
   var modes=GameResolutions.GetResolutions(DSPGame.globalOption.displayMode);int index=modes.FindIndex(m=>m.width==width&&m.height==width*3/4);
   Check(index>=0,"original options list contains "+width+"x"+width*3/4);
   ui.resolutionComp.itemIndex=index;yield return new WaitForSecondsRealtime(2);
   Check(Screen.width==width&&Screen.height==width*3/4,"original preview applies "+width+"x"+width*3/4);
   ui.ConfirmResolutionChange();yield return new WaitForSecondsRealtime(.3f);
   Check(DSPGame.globalOption.resolution.width==width,"original resolution confirmation stores "+width);
  }
  ui._Close();
 }
 static IEnumerator Sequence(){
  oldOption=DSPGame.globalOption;optionsCaptured=true;report.phase="display-modes";Write();yield return Modes();
  saveField=typeof(GameConfig).GetField("gameSavePath",BindingFlags.Static|BindingFlags.NonPublic);Check(saveField!=null,"save path isolation available");oldSavePath=(string)saveField.GetValue(null);
  var folder=Path.Combine(Application.persistentDataPath,"flight-audit-"+DSPPadDiagnosticLaunch.BatchIdentifier);Directory.CreateDirectory(folder);saveField.SetValue(null,folder+Path.DirectorySeparatorChar);
  var opt=DSPGame.globalOption;opt.autoSaveTime=0;DSPGame.globalOption=opt;
  var desc=new GameDesc();desc.SetForNewGame(UniverseGen.algoVersion,20261011,64,1,1);DSPGame.StartGameSkipPrologue(desc);
  report.phase="isolated-world-loading";Write();yield return null;float end=Time.realtimeSinceStartup+240;
  while((!GameMain.isRunning||GameMain.isLoading||DSPGame.IsMenuDemo||GameMain.localPlanet==null||!GameMain.localPlanet.factoryLoaded||GameMain.gameTick<120)&&Time.realtimeSinceStartup<end)yield return null;
  Check(GameMain.isRunning&&!DSPGame.IsMenuDemo&&GameMain.localPlanet!=null&&GameMain.localPlanet.factoryLoaded&&GameMain.gameTick>=120,"isolated world entered");
  yield return new WaitForSecondsRealtime(3);int callbacks=DSPAOTVerifyMouseCallbacks();Check(callbacks==31,"native move/scroll/button callbacks installed and zero-delta callback delivery works: "+callbacks);report.phase="flight-input";Write();yield return DSPPadKeyboardRegression.RunFlightOnly();
  Check(DSPPadKeyboardRegression.Passed,"flight transport assertions complete");
  DSPGame.EndGame();yield return new WaitForSecondsRealtime(2);
 }
 public static IEnumerator Run(){
  if(!DSPPadDiagnosticLaunch.FlightAuditRequested)yield break;report=new Report();var stack=new Stack<IEnumerator>();stack.Push(Sequence());
  try{while(stack.Count>0){bool more=false;object next=null;Exception error=null;try{more=stack.Peek().MoveNext();if(more)next=stack.Peek().Current;}catch(Exception e){error=e;}
   if(error!=null){report.errors.Add(error.ToString());break;}if(!more){(stack.Pop() as IDisposable)?.Dispose();continue;}if(next is IEnumerator){stack.Push((IEnumerator)next);continue;}yield return next;
  }report.completed=stack.Count==0;}
  finally{
   while(stack.Count>0)(stack.Pop() as IDisposable)?.Dispose();
   if(GameMain.isRunning)DSPGame.EndGame();
   if(saveField!=null&&oldSavePath!=null){saveField.SetValue(null,oldSavePath);report.savePathRestored=(string)saveField.GetValue(null)==oldSavePath;}
   // Keep the explicitly requested 1376 mode; restore all other user preferences.
   if(optionsCaptured){var saved=DSPGame.globalOption;oldOption.resolution=saved.resolution;oldOption.displayMode=saved.displayMode;DSPGame.globalOption=oldOption;oldOption.SaveGlobal();}
   report.phase=Passed?"passed":"failed";Write();
  }
 }
}
