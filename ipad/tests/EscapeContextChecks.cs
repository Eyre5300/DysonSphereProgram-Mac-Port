using System;
namespace UnityEngine {
 public class Object {public static implicit operator bool(Object obj)=>obj!=null;public static void DontDestroyOnLoad(Object obj){}}
 public class MonoBehaviour:Object {}
 public class GameObject:Object {public GameObject(string name){}public T AddComponent<T>() where T:new()=>new T();}
 public static class Application {public static bool isFocused=true;}
 public static class Time {public static int frameCount;}
}
static class DSPPadDocuments {public static bool Busy;}
static class DSPPadKeyboard {public static int clears;public static void ClearEscape(){clears++;}}
class Player {public bool respawning;}
class GameMain {public static GameMain instance=new GameMain();public static bool isRunning=true,isPaused,inOtherScene;public static Player mainPlayer=new Player();}
static class DSPGame {public static bool IsMenuDemo;}
class Axis {public bool[] press=new bool[6];}
static class VFInput {public static bool inputing,escape;public static Axis axis_button=new Axis();public static void ResetAllAxes(){if(!DSPPadEscapeOrder.ResettingPauseMenu)throw new Exception("reset scope");DSPPadEscapeOrder.Consumed();}}
class EscapeContextChecks {
 static void Check(bool value,string name){if(!value)throw new Exception(name);}
 static void Publish(){UnityEngine.Time.frameCount++;VFInput.escape=true;VFInput.axis_button.press[5]=true;DSPPadEscapeOrder.AfterUpdate();VFInput.escape=false;}
 static void Ready(){UnityEngine.Time.frameCount++;DSPPadEscapeOrder.AfterUpdate();DSPPadEscapeOrder.AfterFixed();DSPPadEscapeOrder.AfterLogic();}
 static void Main(){
  Publish();Ready();Check(DSPPadEscapeOrder.PauseRequested,"normal fallthrough");DSPPadEscapeOrder.Consumed();Check(!DSPPadEscapeOrder.PauseRequested,"consumed");
  Action<bool>[] gates={v=>GameMain.inOtherScene=v,v=>GameMain.mainPlayer.respawning=v,v=>VFInput.inputing=v,v=>DSPPadDocuments.Busy=v,v=>UnityEngine.Application.isFocused=!v,v=>GameMain.isRunning=!v,v=>DSPGame.IsMenuDemo=v};
  foreach(var gate in gates){Publish();gate(true);Ready();Check(!DSPPadEscapeOrder.PauseRequested,"blocked state cannot pause");gate(false);Ready();Check(!DSPPadEscapeOrder.PauseRequested,"return from blocked state has no stale Esc");}
  Publish();GameMain.instance=new GameMain();Ready();Check(!DSPPadEscapeOrder.PauseRequested,"world transition clears pending");
  Publish();DSPPadEscapeOrder.FocusLost();Ready();Check(!DSPPadEscapeOrder.PauseRequested&&DSPPadKeyboard.clears==1,"focus callback cancels without an intervening frame");
  GameMain.isPaused=true;Publish();UnityEngine.Time.frameCount++;Check(DSPPadEscapeOrder.PauseRequested,"resume without world ticks");
  DSPPadEscapeOrder.BeginPause();Check(DSPPadEscapeOrder.WaitingForPauseMenu,"next delivery waits until original pause menu reset");DSPPadEscapeOrder.ResetForPauseMenu();Check(!DSPPadEscapeOrder.WaitingForPauseMenu&&!DSPPadEscapeOrder.ResettingPauseMenu,"reset scope ends");
  Console.WriteLine("PASS Escape production wrapper: scene, respawn, text, documents, focus, menu, stop, consumed and paused contexts");
 }
}
