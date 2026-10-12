using System;
using System.Collections.Generic;
using System.Runtime.InteropServices;
using UnityEngine;
using UnityEngine.EventSystems;
using UnityEngine.UI;
// Platform addon only. It does not alter the original game's keyboard bindings.
public static class DSPSmartTouchFrame {
 [DllImport("@rpath/UnityFramework.framework/UnityFramework")]
 static extern int DSPAOTHasKeyboardAndMouse();
 static readonly List<RaycastResult> hits=new List<RaycastResult>();
 static int left=-1,right=-1;static Vector2 origin,pendingLook;
 static readonly DSPPadTapGesture tap=new DSPPadTapGesture();
 static bool unavailable,wasEnabled;static int peripheralFrame=-1,width,height;
 public static bool KeyboardAndMouse {get;private set;}
 public static void CheckPeripherals(){
  if(DSPTouchControls.Enabled){KeyboardAndMouse=false;return;}
  if(peripheralFrame==Time.frameCount)return;peripheralFrame=Time.frameCount;
  if(!unavailable)try{KeyboardAndMouse=DSPAOTHasKeyboardAndMouse()!=0;}catch(DllNotFoundException){unavailable=true;}catch(EntryPointNotFoundException){unavailable=true;}
 }
 public static Vector2 Move {get;private set;}
 public static Vector2 Look {get;private set;}
 public static bool LookHeld=>DSPTouchControls.Enabled?DSPTouchControls.Looking:right!=-1;
 public static bool Enabled {get;private set;}
 public static int UIRejectedTouches {get;private set;}
 public static string LastUIBlocker {get;private set;}
 public static int TouchFrames {get;private set;}
 public static int LookFrames {get;private set;}
 public static float LookDistance {get;private set;}
 static string UIPath(Transform t){string s=t.name;while(t.parent!=null){t=t.parent;s=t.name+"/"+s;}return s;}
 public static string BlockerAt(Vector2 point) {
  if(EventSystem.current==null)return "";
  var p=new PointerEventData(EventSystem.current){position=point};hits.Clear();
  EventSystem.current.RaycastAll(p,hits);
  foreach(var hit in hits)if(hit.module is GraphicRaycaster)return UIPath(hit.gameObject.transform);
  return "";
 }
 public static bool UIBlocks(Vector2 point){if(DSPPadEscapeButton.Contains(point)){LastUIBlocker="iPad Esc";return true;}string b=BlockerAt(point);if(b.Length!=0)LastUIBlocker=b;return b.Length!=0;}
 public static void Reset(){DSPTouchControls.Reset();left=-1;right=-1;Move=Vector2.zero;Look=Vector2.zero;pendingLook=Vector2.zero;tap.Cancel();DSPPadInput.CancelWorldTap();}
 public static void Sample(bool gameplayAllowed) {
  if(DSPTouchControls.Enabled){DSPTouchControls.Poll();Enabled=DSPTouchControls.Allowed;Move=DSPTouchControls.Move;Look=DSPTouchControls.Look;return;}
  CheckPeripherals();
  if(width!=Screen.width||height!=Screen.height){Reset();width=Screen.width;height=Screen.height;}
  Enabled=gameplayAllowed&&!KeyboardAndMouse&&Application.isFocused;
  if(Enabled!=wasEnabled||!Enabled)Reset();wasEnabled=Enabled;
  Look=Vector2.zero;if(!Enabled)return;
  if(Input.touchCount>0)TouchFrames++;
  bool leftExists=false,rightExists=false;
  if(Input.touchCount!=1)tap.Cancel();
  float now=Time.realtimeSinceStartup,slop=DSPPadTapGesture.Slop(Screen.width);
  foreach(var t in Input.touches) {
   if(t.phase==TouchPhase.Began) {
    if(UIBlocks(t.position)){UIRejectedTouches++;continue;}
    if(Input.touchCount==1&&left==-1&&right==-1)tap.Begin(t.fingerId,t.position,now);
    if(t.position.x<Screen.width*.5f&&left==-1){left=t.fingerId;origin=t.position;}
    else if(t.position.x>=Screen.width*.5f&&right==-1){right=t.fingerId;pendingLook=Vector2.zero;}
   }
   if(t.fingerId!=left&&t.fingerId!=right)continue;
   bool blocked=UIBlocks(t.position);
   bool ended=t.phase==TouchPhase.Ended,cancel=ended||t.phase==TouchPhase.Canceled||blocked;
   tap.Observe(t.fingerId,t.position,now,slop);
   int click=ended&&!blocked&&Input.touchCount==1?tap.EndButton(t.fingerId,t.position,now,slop):-1;
   if(t.phase==TouchPhase.Canceled||blocked)tap.Cancel();
   if(t.fingerId==left){leftExists=true;
    if(cancel){left=-1;Move=Vector2.zero;}
    else{Vector2 d=t.position-origin;float radius=Mathf.Min(Screen.width*.12f,240),dead=radius*.1f;Move=d.magnitude<=dead?Vector2.zero:d.normalized*Mathf.Clamp01((d.magnitude-dead)/(radius-dead));}
   } else if(t.fingerId==right){rightExists=true;
    if(cancel){right=-1;pendingLook=Vector2.zero;}
    else{pendingLook+=t.deltaPosition*.1f;if(tap.Finger!=t.fingerId||!tap.Eligible){Look+=pendingLook;pendingLook=Vector2.zero;}}
   }
   if(click>=0)DSPPadInput.QueueWorldTap(t.position,click);
  }
  if(!leftExists){left=-1;Move=Vector2.zero;}if(!rightExists){right=-1;pendingLook=Vector2.zero;}
  if(Look.sqrMagnitude>0){LookFrames++;LookDistance+=Look.magnitude;}
 }
}
