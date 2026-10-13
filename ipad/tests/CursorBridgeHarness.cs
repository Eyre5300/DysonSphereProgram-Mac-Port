using System;
namespace UnityEngine {public enum CursorLockMode {None,Locked,Confined}public static class Cursor {public static CursorLockMode lockState;}public static class Application {public static bool isFocused;}}
class CursorBridgeHarness {
 static void Main(){
  for(int status=-1;status<32;status++)for(int request=0;request<2;request++)for(int focus=0;focus<2;focus++)for(int legacy=0;legacy<2;legacy++){
   bool expected=request==1&&focus==1&&(status<0?legacy==1:(status&15)==15);
   bool actual=DSPPadCursorBridge.ResolveLocked(request==1,focus==1,status,legacy==1);
   if(actual!=expected)throw new Exception("Capture readback mismatch");
  }
  if(DSPPadCursorBridge.ResolveLocked(true,true,11,true))throw new Exception("Requested/preferred is not granted");
  Console.WriteLine("264 cursor request/grant/focus/fallback cases passed");
 }
}
