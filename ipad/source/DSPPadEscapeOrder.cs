using UnityEngine;
// Thin scheduling adapter; Windows UIGame/BuildTool/GameMain retain every
// close/cancel/pause decision and consume through the original UseEscape.
public static class DSPPadEscapeOrder {
 static readonly DSPPadEscapeSequence sequence=new DSPPadEscapeSequence();
 static GameMain owner;static DSPPadEscapeLifecycle lifecycle;
 public static bool WaitingForPauseMenu {get;private set;}
 public static bool ResettingPauseMenu {get;private set;}
 static bool Valid=>Application.isFocused&&!DSPPadDocuments.Busy&&!VFInput.inputing&&GameMain.isRunning&&!DSPGame.IsMenuDemo&&!GameMain.inOtherScene&&GameMain.mainPlayer!=null&&!GameMain.mainPlayer.respawning;
 public static void AfterUpdate(){
  if(!lifecycle){var go=new GameObject("iPad Escape lifecycle");Object.DontDestroyOnLoad(go);lifecycle=go.AddComponent<DSPPadEscapeLifecycle>();}
  if(owner!=GameMain.instance||!Valid){sequence.Clear();WaitingForPauseMenu=false;}owner=GameMain.instance;
  if(!GameMain.isPaused)WaitingForPauseMenu=false;
  if(Valid)sequence.Publish(VFInput.escape,Time.frameCount);
 }
 public static void AfterFixed(){sequence.Sample(VFInput.axis_button!=null&&VFInput.axis_button.press[5]);}
 public static void AfterLogic(){sequence.AfterLogic();}
 public static void Consumed(){sequence.Clear();}
 public static void FocusLost(){sequence.Clear();WaitingForPauseMenu=false;DSPPadKeyboard.ClearEscape();}
 public static void BeginPause(){WaitingForPauseMenu=true;}
 public static void ResetForPauseMenu(){
  ResettingPauseMenu=true;
  try{VFInput.ResetAllAxes();}finally{ResettingPauseMenu=false;WaitingForPauseMenu=false;}
 }
 public static bool PauseRequested=>Valid&&owner==GameMain.instance&&sequence.CanPause(Time.frameCount,GameMain.isPaused);
}
public sealed class DSPPadEscapeLifecycle:MonoBehaviour {
 void OnApplicationFocus(bool focused){if(!focused)DSPPadEscapeOrder.FocusLost();}
 void OnApplicationPause(bool paused){if(paused)DSPPadEscapeOrder.FocusLost();}
}
