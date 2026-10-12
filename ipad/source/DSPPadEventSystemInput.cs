using System.Collections.Generic;
using UnityEngine;
using UnityEngine.EventSystems;
// Feed the original legacy UGUI module from the SAME canonical mouse snapshot
// as VFInput. Original event dispatch, navigation, IME, drag/click rules and
// direct/stylus Touch structs remain owned by Unity's existing input module.
[DisallowMultipleComponent]
public sealed class DSPPadEventSystemInput:BaseInput {
 BaseInput originalInput;
 public BaseInput OriginalInput=>originalInput;
 readonly List<Touch> directTouches=new List<Touch>(4);
 int touchFrame=-1,mouseFrame=-1;
 bool previousPresent,uiPresent;
 public static int BindingCount {get;private set;}
 public static string LastBindingFailure {get;private set;}
 public int IgnoredIndirectTouches {get;private set;}
 // Called from the existing production DSPPadInput.Poll path after its frame
 // guard. No added RuntimeInitialize manifest is needed for direct DLL builds.
 public static void EnsureInstalled(){
#if DSP_EMU_IPAD
  var system=EventSystem.current;if(!system)return;
  var module=system.currentInputModule as StandaloneInputModule;
  if(!module)module=system.GetComponent<StandaloneInputModule>();
  if(!module)return;
  if(module.inputOverride is DSPPadEventSystemInput)return;
  if(module.inputOverride){LastBindingFailure="Existing input override: "+module.inputOverride.GetType().FullName;return;}
  // Keep the original component/default object intact. Its non-mouse virtual
  // defaults are stateless Unity Input forwarding; a foreign custom override
  // is deliberately not replaced. Preserve its touch source as well.
  var original=module.input;
  var input=system.GetComponent<DSPPadEventSystemInput>();
  if(!input)input=system.gameObject.AddComponent<DSPPadEventSystemInput>();
  input.originalInput=original==input?null:original;module.inputOverride=input;BindingCount++;LastBindingFailure="";
#endif
 }
 void MouseSnapshot(){
  DSPPadInput.Poll();
  if(mouseFrame==Time.frameCount)return;mouseFrame=Time.frameCount;
  bool present=!(DSPPadInputMode.UseTouch||DSPPadDocuments.Busy)&&(DSPPadInput.NativeMouseTransport?DSPPadInput.PhysicalMouse:(originalInput?originalInput.mousePresent:base.mousePresent));
  // Allow the original module one disappearance frame to consume canonical Up
  // edges and end its pointer press/drag. Keyboard presence never enables it.
  uiPresent=present||previousPresent;previousPresent=present;
 }
 public override bool mousePresent {get{MouseSnapshot();return uiPresent;}}
 public override Vector2 mousePosition {get{MouseSnapshot();return DSPPadInput.mousePosition;}}
 public override Vector2 mouseScrollDelta {get{MouseSnapshot();return DSPPadInput.mouseScrollDelta;}}
 // mouseScrollDeltaPerTick inherits the actual shipped BaseInput constant 1.
 public override bool GetMouseButton(int button){MouseSnapshot();return DSPPadInput.UIGetMouseButton(button,0);}
 public override bool GetMouseButtonDown(int button){MouseSnapshot();return DSPPadInput.UIGetMouseButton(button,1);}
 public override bool GetMouseButtonUp(int button){MouseSnapshot();return DSPPadInput.UIGetMouseButton(button,2);}
 void TouchSnapshot(){
  if(touchFrame==Time.frameCount)return;touchFrame=Time.frameCount;directTouches.Clear();IgnoredIndirectTouches=0;
  int count=originalInput?originalInput.touchCount:base.touchCount;
  for(int i=0;i<count;i++){
   var touch=originalInput?originalInput.GetTouch(i):base.GetTouch(i);
   // Shipped StandaloneInputModule already discards Indirect entries, but its
   // count>0 return suppresses ProcessMouseEvent even if ALL were discarded.
   // Filter only those duplicates before its count/loop; other fields/IDs and
   // original direct/stylus event processing are unchanged.
   if(touch.type==TouchType.Indirect){IgnoredIndirectTouches++;continue;}
   directTouches.Add(touch);
  }
 }
 public override int touchCount {get{TouchSnapshot();return directTouches.Count;}}
 public override Touch GetTouch(int index){TouchSnapshot();return directTouches[index];}
 // GetAxisRaw, GetButtonDown, touchSupported, compositionString and all IME
 // members intentionally inherit BaseInput: no remapping of keyboard rules.
}
