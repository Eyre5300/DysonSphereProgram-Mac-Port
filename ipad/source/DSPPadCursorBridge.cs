using System;using System.Runtime.InteropServices;using UnityEngine;
// Called with the exact result of original UICursor cursor/window/Tab rules.
public static class DSPPadCursorBridge {
 [DllImport("@rpath/UnityFramework.framework/UnityFramework")]static extern void DSPAOTSetPointerLock(int requested);
 [DllImport("@rpath/UnityFramework.framework/UnityFramework")]static extern int DSPAOTPointerLockStatus();
 static bool unavailable;public static bool Requested{get;private set;}
 public static int NativeStatus {get{if(unavailable)return -1;try{return DSPAOTPointerLockStatus();}catch(DllNotFoundException){unavailable=true;}catch(EntryPointNotFoundException){unavailable=true;}return -1;}}
 public static void SetRequested(bool wanted){Requested=wanted&&Application.isFocused;if(unavailable)return;try{DSPAOTSetPointerLock(Requested?1:0);}catch(DllNotFoundException){unavailable=true;}catch(EntryPointNotFoundException){unavailable=true;}}
}
