using System;using System.Runtime.InteropServices;using UnityEngine;
// Input ownership changes only on activity, never on peripheral connection.
public static class DSPPadInputMode {
 public enum Choice {Automatic,Keyboard,Touch}
 [DllImport("@rpath/UnityFramework.framework/UnityFramework")]static extern uint DSPAOTKeyboardActivity();
 static bool initialized;static uint keyboardSerial;static int frame=-1,releaseAfter=-1;static Vector2 motion;static float motionAt;static bool pendingTouch=true;
 public static Choice Preference {get;private set;}public static bool TouchActive {get;private set;}=true;
 public static bool UseTouch=>DSPTouchControls.Enabled&&TouchActive;
 public static string Label=>Preference==Choice.Automatic?"输入：自动"+(UseTouch?"·触控":"·键鼠"):Preference==Choice.Touch?"输入：触控":"输入：键鼠";
 public static void SetPreference(Choice value){Preference=value;PlayerPrefs.SetInt("DSP.InputMode",(int)value);PlayerPrefs.Save();if(value!=Choice.Automatic)Request(value==Choice.Touch);}
 public static void Cycle(){SetPreference((Choice)(((int)Preference+1)%3));}
 static void Request(bool touch){pendingTouch=touch;}
 static void Apply(){if(TouchActive==pendingTouch)return;TouchActive=pendingTouch;DSPTouchControls.Reset();DSPTouchControls.RefreshVisibility();}
 public static void Observe(bool keyDown,Vector2 delta,float wheel,bool mouseDown,bool pointerHeld,bool fingerBegan,bool fingerHeld,bool touchTransaction){
  if(!DSPTouchControls.Enabled||DSPPadDocuments.Busy||!Application.isFocused)return;
  if(Preference==Choice.Automatic){
   if(Time.realtimeSinceStartup-motionAt>.2f)motion=Vector2.zero;
   if(delta.sqrMagnitude>0){motion+=delta;motionAt=Time.realtimeSinceStartup;}
   if(keyDown||mouseDown||Mathf.Abs(wheel)>.001f||motion.sqrMagnitude>=9){Request(false);motion=Vector2.zero;}
   if(fingerBegan)Request(true);
  }else Request(Preference==Choice.Touch);
  // Keep the original release in its original input mode before handing over.
  if((TouchActive&&(fingerHeld||touchTransaction))||(!TouchActive&&pointerHeld))releaseAfter=Time.frameCount+1;
  if(Time.frameCount>releaseAfter)Apply();
 }
 public static void Poll(Vector2 delta,float wheel,bool mouseDown,bool pointerHeld,bool diagnosticPointer){
  if(!DSPTouchControls.Enabled||frame==Time.frameCount)return;frame=Time.frameCount;
  uint serial=DSPAOTKeyboardActivity();if(!initialized){initialized=true;keyboardSerial=serial;Preference=(Choice)Mathf.Clamp(PlayerPrefs.GetInt("DSP.InputMode",0),0,2);}
  bool key=serial!=keyboardSerial;keyboardSerial=serial;bool began=false,held=false;
  foreach(var t in Input.touches)if(t.type!=TouchType.Indirect){began|=t.phase==TouchPhase.Began;held|=t.phase!=TouchPhase.Ended&&t.phase!=TouchPhase.Canceled;}
  Observe(key,diagnosticPointer?Vector2.zero:delta,diagnosticPointer?0:wheel,!diagnosticPointer&&mouseDown,pointerHeld,began,held,DSPPadInput.ActiveWorldButton>=0);
 }
}
