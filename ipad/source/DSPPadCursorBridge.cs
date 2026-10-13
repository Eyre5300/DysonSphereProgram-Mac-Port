using System;using System.Runtime.InteropServices;using UnityEngine;
// Called with the exact result of original UICursor cursor/window/Tab rules.
public static class DSPPadCursorBridge {
 [DllImport("@rpath/UnityFramework.framework/UnityFramework")]static extern void DSPAOTSetPointerLock(int requested);
 [DllImport("@rpath/UnityFramework.framework/UnityFramework")]static extern int DSPAOTPointerLockStatus();
 static bool unavailable;public static bool Requested{get;private set;}
 // The platform that grants pointer capture is authoritative. A request alone
 // must not enable free look when iPadOS refuses capture or loses focus.
 public static bool ResolveLocked(bool requested,bool focused,int status,bool legacy){
  if(!requested||!focused)return false;
  return status<0?legacy:(status&15)==15;
 }
 public static bool Locked=>ResolveLocked(Requested,Application.isFocused,NativeStatus,Cursor.lockState==CursorLockMode.Locked);
 public static int NativeStatus {get{if(unavailable)return -1;try{return DSPAOTPointerLockStatus();}catch(DllNotFoundException){unavailable=true;}catch(EntryPointNotFoundException){unavailable=true;}return -1;}}
 public static void SetRequested(bool wanted){Requested=wanted&&Application.isFocused;if(unavailable)return;try{DSPAOTSetPointerLock(Requested?1:0);}catch(DllNotFoundException){unavailable=true;}catch(EntryPointNotFoundException){unavailable=true;}}
}
