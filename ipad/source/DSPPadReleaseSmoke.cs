using System;using System.IO;using System.Reflection;using System.Collections;using System.Collections.Generic;using UnityEngine;
// Opt-in package smoke only. No key injection, frame cap or graphics changes.
public static class DSPPadReleaseSmoke {
 [Serializable]public sealed class Report {public string batchIdentifier=DSPPadDiagnosticLaunch.BatchIdentifier,buildVersion=DSPPadDiagnosticLaunch.BuildVersion,phase;public bool completed,restored;public long startTick,endTick;public int width,height;public List<string> checks=new List<string>(),errors=new List<string>();}
 static Report report;static FieldInfo saveField;static string oldPath;static GameOption oldOption;static bool captured;
 public static bool Passed=>report!=null&&report.completed&&report.restored&&report.errors.Count==0;
 static void Write(){File.WriteAllText(Path.Combine(Application.persistentDataPath,"release-smoke.json"),JsonUtility.ToJson(report,true));}
 static bool Ready()=>GameMain.isRunning&&!GameMain.isLoading&&!DSPGame.IsMenuDemo&&GameMain.localPlanet!=null&&GameMain.localPlanet.factoryLoaded&&GameMain.mainPlayer!=null;
 static void Check(string name,bool ok){if(!ok)throw new Exception(name);report.checks.Add(name);Write();}
 static IEnumerator WaitWorld(){float end=Time.realtimeSinceStartup+240;yield return null;while((!Ready()||GameMain.gameTick<120)&&Time.realtimeSinceStartup<end)yield return null;Check("entered gameplay world",Ready()&&GameMain.gameTick>=120);}
 static IEnumerator Sequence(){
  oldOption=DSPGame.globalOption;captured=true;saveField=typeof(GameConfig).GetField("gameSavePath",BindingFlags.Static|BindingFlags.NonPublic);if(saveField==null)throw new Exception("Save isolation unavailable");oldPath=(string)saveField.GetValue(null);
  string folder=Path.Combine(Application.persistentDataPath,"release-smoke-"+DSPPadDiagnosticLaunch.BatchIdentifier);Directory.CreateDirectory(folder);saveField.SetValue(null,folder+Path.DirectorySeparatorChar);var option=oldOption;option.autoSaveTime=0;DSPGame.globalOption=option;
  report.width=Screen.width;report.height=Screen.height;report.phase="loading";Write();var desc=new GameDesc();desc.SetForNewGame(UniverseGen.algoVersion,20261011,64,1,1);DSPGame.StartGameSkipPrologue(desc);yield return WaitWorld();
  report.startTick=GameMain.gameTick;int frame=Time.frameCount;yield return new WaitForSecondsRealtime(8);report.endTick=GameMain.gameTick;Check("simulation advances",report.endTick>report.startTick+60);Check("render frames advance",Time.frameCount>frame+30);Check("resolution retained",Screen.width==report.width&&Screen.height==report.height);Check("factory veins present",GameMain.mainPlayer.factory!=null&&GameMain.mainPlayer.factory.veinCursor>1);
  report.phase="save-reload";Write();long saved=GameMain.gameTick;Check("isolated save succeeds",GameSave.SaveCurrentGame("release-smoke"));DSPGame.StartGame("release-smoke");yield return WaitWorld();Check("isolated save reloads",GameMain.gameTick>=saved);
  yield return new WaitForEndOfFrame();var shot=ScreenCapture.CaptureScreenshotAsTexture();try{File.WriteAllBytes(Path.Combine(Application.persistentDataPath,"release-smoke.png"),shot.EncodeToPNG());}finally{UnityEngine.Object.Destroy(shot);}report.completed=true;
 }
 public static IEnumerator Run(){
  if(!DSPPadDiagnosticLaunch.ReleaseSmokeRequested)yield break;report=new Report();var stack=new Stack<IEnumerator>();stack.Push(Sequence());
  try{while(stack.Count>0){bool more=false;object next=null;Exception error=null;try{more=stack.Peek().MoveNext();if(more)next=stack.Peek().Current;}catch(Exception e){error=e;}if(error!=null){report.errors.Add(error.ToString());break;}if(!more){(stack.Pop() as IDisposable)?.Dispose();continue;}if(next is IEnumerator){stack.Push((IEnumerator)next);continue;}yield return next;}}
  finally{while(stack.Count>0)(stack.Pop() as IDisposable)?.Dispose();if(GameMain.isRunning)DSPGame.EndGame();if(saveField!=null&&oldPath!=null)saveField.SetValue(null,oldPath);if(captured)DSPGame.globalOption=oldOption;report.restored=captured&&saveField!=null&&(string)saveField.GetValue(null)==oldPath;report.phase=Passed?"passed":"failed";Write();}
 }
}
