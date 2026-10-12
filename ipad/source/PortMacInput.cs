using UnityEngine;
#if UNITY_STANDALONE_OSX && !UNITY_EDITOR
using System.Runtime.InteropServices;
#endif
// Caps Lock is a toggle modifier on macOS; legacy held-key polling can miss it.
public static class PortMacInput {
#if UNITY_STANDALONE_OSX && !UNITY_EDITOR
 #if DSP_EMU_IPAD
 const string NativeLibrary="@rpath/UnityFramework.framework/UnityFramework";
 #else
 const string NativeLibrary="DSPPortInput";
 #endif
 [DllImport(NativeLibrary)] static extern ulong DSPPortCapsSequence();
 [DllImport(NativeLibrary)] static extern int DSPPortCapsAvailable();
 static bool initialized, unavailable, wasFocused, pending, deviceAvailable;
 static ulong sequence;
 static float receivedAt;
 public static ulong NativeSequence => sequence;
 public static void Poll(){
  if(unavailable)return;
  ulong current;
  try{current=DSPPortCapsSequence();deviceAvailable=DSPPortCapsAvailable()!=0;}catch(System.DllNotFoundException){unavailable=true;return;}catch(System.EntryPointNotFoundException){unavailable=true;return;}
  bool focused=Application.isFocused;
  bool eligible=focused&&!VFInput.inputing&&!VFInput.inFullscreenGUI&&VFInput.noModifier&&VFInput.override_keys[24].IsNull()&&GameMain.mainPlayer!=null&&GameMain.mainPlayer.sailing&&!DSPGame.IsMenuDemo;
  if(!eligible)pending=false;
  if(initialized&&wasFocused&&eligible&&current!=sequence){pending=true;receivedAt=Time.realtimeSinceStartup;}
  sequence=current;initialized=true;wasFocused=focused;
 }
 public static bool DefaultWarp(bool legacy){
  if(unavailable||!initialized||!deviceAvailable)return legacy;
  bool result=pending&&Application.isFocused&&!VFInput.inputing&&!VFInput.inFullscreenGUI&&Time.realtimeSinceStartup-receivedAt<0.25f;
  pending=false;return result;
 }
#else
 public static ulong NativeSequence => 0;
 public static void Poll(){}
 public static bool DefaultWarp(bool legacy)=>legacy;
#endif
}
