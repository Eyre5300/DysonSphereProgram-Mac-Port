#if DSP_EMU_IPAD
using System;
using System.IO;
using System.Collections.Generic;
using UnityEngine;
using UnityEngine.EventSystems;
using UnityEngine.UI;

// Diagnostic-only. Never injects, consumes, resets, rebinds, or chooses inputs.
// Call AfterUpdate/AfterFixed after the original VFInput samplers. No Runtime
// initializer is needed (incremental emu builds keep an older initializer table).
public static class DSPPadManagedInputTrace {
 const int Capacity=2048,EventCapacity=128;
 [Serializable] public struct Sample {
  public int frame,phase,sequence,reason,width,height;
  public float time,deltaTime;
  public int nativeButtons,legacyButtons,legacyDown,legacyUp,wrappedButtons,wrappedDown,wrappedUp,virtualWorldButton;
  public Vector2 nativeDelta,legacyAxes,wrappedAxes,gameAxes,moveAxes,touchMove,touchLook;
  public float legacyWheel,wrappedWheel,gameWheel,inScrollWheel;
  public Vector3 legacyPosition,wrappedPosition;
  public int keysHeld,keysDown,keysUp,modifier,modifierDown,flags,cursorLock;
  public bool cursorVisible;
  public bool cursorRequested,cursorEffective,warpCommand,warping;public int nativeCursorStatus;
  public float warpState,sailDistance,sailDistanceWanted,sailWeight;public Quaternion sailRotation;
  public Vector4 controllerInput;
  public Vector3 playerPosition,requestedVelocity,rigidVelocity;
  public bool grounded;public float groundDistance;
  public long gameTick;
  public bool jumpHeld,jumpDown,jumpUp,jumpOnDown,alive,disableController;
  public float jumpAxisValue,jumpCoolTime,flyUpChance,jumpedTime;
  public int jumpAxisBits,jumpOverrideBits,jumpCode,jumpModifier,takeOffCode,takeOffModifier,pullUpCode,pullUpModifier,viewMode,movementState,movementStateInFrame;
  public string forwardCollider;
  public int touchCount,touchPhases,touchTypes,finger0,finger1;
  public Vector2 touchPosition0,touchPosition1,touchDelta0,touchDelta1;
  public float middleValue,overrideValue;
  public int middleBits,overrideBits,overrideCode,overrideModifier;
  public bool rotatePressing,rotateDown,rotateUp;
  public int physicalModifiers,wrappedKeysHeld,buildRotateCode,buildRotateModifier,buildCounterCode,buildCounterModifier;
  public bool buildRotateDown,buildCounterDown;
  public ulong capsSequence;
  public string selected,firstHit,firstHitModule,inputModule,inputOverride,hButton;
  public bool hEnabled,hInteractable,hPanelActive;
 }
 struct Entry {public Sample sample;public GameObject selected,firstHit;public BaseRaycaster hitModule;public BaseInputModule inputModule;public Button hButton;}
 [Serializable] public struct UIEvent {public int frame,kind,pointerId,button;public float time;public Vector2 position,delta;public bool eligible,dragging,enabled,interactable;}
 [Serializable] public sealed class Snapshot {public int schema=2,totalSamples,totalEvents,overwrittenSamples,overwrittenEvents;public string legend;public Sample[] samples;public UIEvent[] uiEvents;}
 static readonly Entry[] ring=new Entry[Capacity];static readonly UIEvent[] events=new UIEvent[EventCapacity];
 static readonly List<RaycastResult> hits=new List<RaycastResult>(128);
 static readonly KeyCode[] keys={KeyCode.W,KeyCode.A,KeyCode.S,KeyCode.D,KeyCode.LeftShift,KeyCode.RightShift,KeyCode.LeftControl,KeyCode.RightControl,KeyCode.LeftAlt,KeyCode.RightAlt,KeyCode.C,KeyCode.Escape,KeyCode.Tab,KeyCode.H,KeyCode.CapsLock,KeyCode.Space,KeyCode.R,KeyCode.LeftArrow,KeyCode.RightArrow,KeyCode.LeftCommand,KeyCode.RightCommand};
 static int total,totalEvents,lastHeld,lastButtons,lastFlags,lastTouches;static float lastSample=-1,lastRaycast=-1;
 static EventSystem pointerSystem;static PointerEventData pointer;static GameObject lastHit;static BaseRaycaster lastHitModule;
 static float detailedUntil;
 public static void DetailedFor(float seconds){if(Enabled)detailedUntil=Mathf.Max(detailedUntil,Time.realtimeSinceStartup+Mathf.Clamp(seconds,0,10));}
 static DSPPadManagedInputTraceDriver driver;static Button boundHButton;
 public static bool Enabled=>DSPPadDiagnosticLaunch.TelemetryAllowed;
 public static string OutputPath=>Path.Combine(Application.persistentDataPath,"dsp-managed-input-trace.json");
 public static void EnsureInstalled(){
  if(driver!=null)return;
  var go=new GameObject("DSP diagnostic input trace");UnityEngine.Object.DontDestroyOnLoad(go);driver=go.AddComponent<DSPPadManagedInputTraceDriver>();
 }
 public static void AfterUpdate(){Capture(0);}
 public static void AfterFixed(){Capture(1);}
 public static void AfterLate(){Capture(2);}
 public static void AfterControllerInput(){if(Enabled&&Time.realtimeSinceStartup<detailedUntil)Capture(3);}
 static int ButtonMask(int mode,bool wrapped){int value=0;for(int b=0;b<3;b++){bool held=wrapped?(mode==0?DSPPadInput.GetMouseButton(b):mode==1?DSPPadInput.GetMouseButtonDown(b):DSPPadInput.GetMouseButtonUp(b)):(mode==0?Input.GetMouseButton(b):mode==1?Input.GetMouseButtonDown(b):Input.GetMouseButtonUp(b));if(held)value|=1<<b;}return value;}
 static string DescribeCollision(Collider collider){
  string text=collider.name+":"+collider.GetType().Name+":layer="+collider.gameObject.layer+":bounds="+collider.bounds;
  var physics=GameMain.localPlanet!=null?GameMain.localPlanet.physics:null;ColliderData data;
  if(physics!=null&&physics.GetColliderData(collider,out data))text+=":object="+data.objType+"/"+data.objId+":usage="+data.usage+":originalPosition="+data.pos+":originalExtents="+data.ext;
  return text;
 }
 static int AxisBits(VFInput.InputAxis a,int i){if(a==null||i<0||i>=a.length)return 0;return(a.press[i]?1:0)|(a.lastPress[i]?2:0)|(a.down[i]?4:0)|(a.up[i]?8:0)|(a.useCounter[i]<<4);}
 static float AxisValue(VFInput.InputAxis a,int i)=>a!=null&&i>=0&&i<a.length?a.value[i]:0;
 static void Capture(int phase){
  if(!Enabled)return;EnsureInstalled();
  Sample s=default;s.frame=Time.frameCount;s.phase=phase;s.time=Time.realtimeSinceStartup;s.deltaTime=Time.unscaledDeltaTime;s.width=Screen.width;s.height=Screen.height;
  s.nativeButtons=DSPPadInput.ButtonMask;s.nativeDelta=DSPPadInput.RawDelta;
  s.virtualWorldButton=DSPPadInput.ActiveWorldButton;
  s.legacyButtons=ButtonMask(0,false);s.legacyDown=ButtonMask(1,false);s.legacyUp=ButtonMask(2,false);
  s.wrappedButtons=ButtonMask(0,true);s.wrappedDown=ButtonMask(1,true);s.wrappedUp=ButtonMask(2,true);
  s.legacyAxes=new Vector2(Input.GetAxis("Mouse X"),Input.GetAxis("Mouse Y"));s.legacyWheel=Input.GetAxis("Mouse Wheel");
  s.wrappedAxes=new Vector2(DSPPadInput.GetAxis("Mouse X"),DSPPadInput.GetAxis("Mouse Y"));s.wrappedWheel=DSPPadInput.GetAxis("Mouse Wheel");
  s.gameAxes=VFInput.mouseMoveAxis;s.moveAxes=VFInput.moveAxis;s.gameWheel=VFInput.mouseWheel;s.inScrollWheel=VFInput.inScrollMouseWheel;
  s.legacyPosition=Input.mousePosition;s.wrappedPosition=DSPPadInput.mousePosition;
  for(int i=0;i<keys.Length;i++){int bit=1<<i;if(Input.GetKey(keys[i]))s.keysHeld|=bit;if(Input.GetKeyDown(keys[i]))s.keysDown|=bit;if(Input.GetKeyUp(keys[i]))s.keysUp|=bit;}
  s.physicalModifiers=DSPPadInput.PhysicalModifierMask;for(int i=0;i<keys.Length;i++)if(DSPPadInput.GetKey(keys[i]))s.wrappedKeysHeld|=1<<i;
  if(VFInput.override_keys!=null&&VFInput.override_keys.Length>57){s.buildRotateCode=VFInput.override_keys[55].keyCode;s.buildRotateModifier=VFInput.override_keys[55].modifier;s.buildCounterCode=VFInput.override_keys[57].keyCode;s.buildCounterModifier=VFInput.override_keys[57].modifier;s.buildRotateDown=VFInput._rotate.onDown;s.buildCounterDown=VFInput._counterRotate.onDown;}
  s.modifier=CombineKey.currModifier;s.modifierDown=CombineKey.currModifierDown;
  s.flags=(Application.isFocused?1:0)|(DSPPadInput.PhysicalMouse?2:0)|(DSPPadInput.NativeMouseTransport?4:0)|(DSPSmartTouchFrame.KeyboardAndMouse?8:0)|(VFInput.inScreen?16:0)|(VFInput.inputing?32:0)|(VFInput.onGUI?64:0)|(VFInput.onGUIOperate?128:0)|(VFInput.inFullscreenGUI?256:0)|(VFInput.inCombatScreenGUI?512:0)|(VFInput.inScreenshotMode?1024:0)|(VFInput.inScrollView?2048:0)|(GameMain.isPaused?4096:0)|(DSPGame.IsMenuDemo?8192:0)|(GameMain.isRunning?16384:0)|(DSPSmartTouchFrame.Enabled?32768:0)|(DSPSmartTouchFrame.LookHeld?65536:0)|(VFInput.noModifier?131072:0)|(UIBlockZone.blocked?262144:0);
  s.cursorLock=(int)Cursor.lockState;s.cursorVisible=Cursor.visible;s.cursorRequested=DSPPadCursorBridge.Requested;s.nativeCursorStatus=DSPPadCursorBridge.NativeStatus;s.cursorEffective=UICursor.locked;s.touchMove=DSPSmartTouchFrame.Move;s.touchLook=DSPSmartTouchFrame.Look;
  if(GameMain.mainPlayer!=null){s.warpState=GameMain.mainPlayer.warpState;s.warpCommand=GameMain.mainPlayer.warpCommand;s.warping=GameMain.mainPlayer.warping;}
  if(GameCamera.instance!=null&&GameCamera.instance.sailPoser!=null){var sail=GameCamera.instance.sailPoser;s.sailDistance=sail.distCoef;s.sailDistanceWanted=sail.distCoefWanted;s.sailWeight=sail.weight;s.sailRotation=sail.targetURot;}
  s.touchCount=Input.touchCount;s.finger0=s.finger1=-1;
  for(int i=0;i<s.touchCount;i++){var t=Input.GetTouch(i);s.touchPhases|=1<<(int)t.phase;s.touchTypes|=1<<(int)t.type;if(i==0){s.finger0=t.fingerId;s.touchPosition0=t.position;s.touchDelta0=t.deltaPosition;}else if(i==1){s.finger1=t.fingerId;s.touchPosition1=t.position;s.touchDelta1=t.deltaPosition;}}
  s.jumpHeld=DSPPadInput.GetKey(KeyCode.Space);s.jumpDown=DSPPadInput.GetKeyDown(KeyCode.Space);s.jumpUp=DSPPadInput.GetKeyUp(KeyCode.Space);
  s.jumpAxisValue=AxisValue(VFInput.axis_button,28);s.jumpAxisBits=AxisBits(VFInput.axis_button,28);s.jumpOverrideBits=AxisBits(VFInput.axis_combine_key,8);
  if(VFInput.override_keys!=null&&VFInput.override_keys.Length>10){s.jumpOnDown=VFInput._jump.onDown;s.jumpCode=VFInput.override_keys[8].keyCode;s.jumpModifier=VFInput.override_keys[8].modifier;s.takeOffCode=VFInput.override_keys[9].keyCode;s.takeOffModifier=VFInput.override_keys[9].modifier;s.pullUpCode=VFInput.override_keys[10].keyCode;s.pullUpModifier=VFInput.override_keys[10].modifier;}
  s.gameTick=GameMain.gameTick;s.viewMode=(int)UIGame.viewMode;s.disableController=GameMain.data!=null&&GameMain.data.disableController;
  s.middleValue=AxisValue(VFInput.axis_button,2);s.middleBits=AxisBits(VFInput.axis_button,2);s.overrideValue=AxisValue(VFInput.axis_combine_key,48);s.overrideBits=AxisBits(VFInput.axis_combine_key,48);
  if(VFInput.override_keys!=null&&VFInput.override_keys.Length>48){s.overrideCode=VFInput.override_keys[48].keyCode;s.overrideModifier=VFInput.override_keys[48].modifier;}
  if(VFInput.axis_button!=null){var r=VFInput._cameraRTSRotateButton;s.rotatePressing=r.pressing;s.rotateDown=r.onDown;s.rotateUp=r.onUp;}
  s.capsSequence=PortMacInput.NativeSequence;
  var player=GameMain.mainPlayer;
  if(player!=null&&player.controller!=null){var pc=player.controller;s.playerPosition=player.position;s.controllerInput=pc.input0;s.requestedVelocity=pc.velocity;s.rigidVelocity=pc.rigid?pc.rigid.velocity:Vector3.zero;s.grounded=pc.actionWalk.isGrounded;s.groundDistance=pc.actionWalk.groundDist;s.alive=player.isAlive;s.jumpCoolTime=pc.actionWalk.jumpCoolTime;s.flyUpChance=pc.actionWalk.flyUpChance;s.jumpedTime=pc.actionWalk.jumpedTime;s.movementState=(int)player.movementState;s.movementStateInFrame=(int)pc.movementStateInFrame;
   if(pc.input0.sqrMagnitude>.1f){var normal=player.position.normalized;var intended=pc.actionWalk.moveVelocity+pc.actionWalk.rtsVelocity;var direction=Vector3.ProjectOnPlane(intended,normal).normalized;RaycastHit hit;
    if(direction.sqrMagnitude>.01f&&Physics.SphereCast(player.position+normal*.5f,.35f,direction,out hit,2f,15873,QueryTriggerInteraction.Ignore))s.forwardCollider=DescribeCollision(hit.collider)+":distance="+hit.distance;
    foreach(var overlap in Physics.OverlapSphere(player.position+normal*.5f,.35f,15873,QueryTriggerInteraction.Ignore))if(overlap.transform!=pc.transform&&!overlap.transform.IsChildOf(pc.transform))s.forwardCollider+=";overlap="+DescribeCollision(overlap);
   }
  }
  int buttons=s.nativeButtons|(s.legacyButtons<<3)|(s.wrappedButtons<<6);
  bool edge=s.legacyDown!=0||s.legacyUp!=0||s.wrappedDown!=0||s.wrappedUp!=0||s.keysDown!=0||s.keysUp!=0;
  bool changed=s.keysHeld!=lastHeld||buttons!=lastButtons||s.flags!=lastFlags||s.touchCount!=lastTouches;
  bool wheel=s.legacyWheel!=0||s.wrappedWheel!=0;
  bool activity=s.nativeDelta.sqrMagnitude>0||s.legacyAxes.sqrMagnitude>0||s.touchCount>0||s.keysHeld!=0||s.wrappedKeysHeld!=0||buttons!=0;
  bool detailed=s.time<detailedUntil;
  s.reason=(edge?1:0)|(changed?2:0)|(wheel?4:0)|(activity?8:0)|(detailed?16:0);
  if(!detailed&&!edge&&!changed&&!wheel&&s.time-lastSample<(activity?.05f:.25f))return;
  lastSample=s.time;lastHeld=s.keysHeld;lastButtons=buttons;lastFlags=s.flags;lastTouches=s.touchCount;
  var es=EventSystem.current;GameObject selected=es!=null?es.currentSelectedGameObject:null;
  if(es!=null&&(edge||changed||wheel||s.time-lastRaycast>=.05f)){
   if(pointer==null||pointerSystem!=es){pointerSystem=es;pointer=new PointerEventData(es);}pointer.Reset();pointer.position=s.wrappedPosition;hits.Clear();es.RaycastAll(pointer,hits);lastHit=null;lastHitModule=null;
   for(int i=0;i<hits.Count;i++){if(hits[i].module is GraphicRaycaster){lastHit=hits[i].gameObject;lastHitModule=hits[i].module;break;}}lastRaycast=s.time;
  }else if(es==null){lastHit=null;lastHitModule=null;}
  Button h=null;var root=UIRoot.instance;if(root!=null&&root.uiGame!=null&&root.uiGame.gameMenu!=null){var menu=root.uiGame.gameMenu;h=menu.button1;s.hPanelActive=menu.detailFuncGroup!=null&&menu.detailFuncGroup.gameObject.activeInHierarchy;}
  if(h!=null){s.hEnabled=h.isActiveAndEnabled;s.hInteractable=h.interactable;if(boundHButton!=h){if(h.GetComponent<DSPPadHButtonTrace>()==null)h.gameObject.AddComponent<DSPPadHButtonTrace>();boundHButton=h;}}
  s.sequence=total+1;ring[total%Capacity]=new Entry{sample=s,selected=selected,firstHit=lastHit,hitModule=lastHitModule,inputModule=es!=null?es.currentInputModule:null,hButton=h};total++;
 }
 public static void RecordUI(int kind,PointerEventData e,Button b){if(!Enabled||e==null)return;events[totalEvents%EventCapacity]=new UIEvent{frame=Time.frameCount,time=Time.realtimeSinceStartup,kind=kind,pointerId=e.pointerId,button=(int)e.button,position=e.position,delta=e.delta,eligible=e.eligibleForClick,dragging=e.dragging,enabled=b!=null&&b.isActiveAndEnabled,interactable=b!=null&&b.interactable};totalEvents++;}
 static string PathOf(GameObject go){if(go==null)return "";string path=go.name;var t=go.transform;while(t.parent!=null){t=t.parent;path=t.name+"/"+path;}return path;}
 public static string Dump(){
  int n=Math.Min(total,Capacity),m=Math.Min(totalEvents,EventCapacity);var output=new Snapshot{totalSamples=total,totalEvents=totalEvents,overwrittenSamples=Math.Max(0,total-Capacity),overwrittenEvents=Math.Max(0,totalEvents-EventCapacity),samples=new Sample[n],uiEvents=new UIEvent[m],legend="phase 0=after VFInput.Update 1=after Fixed 2=Late 3=after original PlayerController.GetInput; reason edge1 change2 wheel4 activity8 detailed16; keys W A S D LShift RShift LCtrl RCtrl LAlt RAlt C Esc Tab H Caps Space R LeftArrow RightArrow LCommand RCommand; flags focus1 physical2 native4 pair8 inScreen16 inputing32 onGUI64 onGUIOperate128 fullscreen256 combat512 screenshot1024 scroll2048 paused4096 menu8192 running16384 touchEnabled32768 lookHeld65536 noModifier131072 UIBlock262144; axis bits press1 lastPress2 down4 up8 useCounter<<4; touchPhases 1<<TouchPhase; UI kinds enter0 exit1 down2 up3 click4"};
  for(int i=0;i<n;i++){var e=ring[(total-n+i)%Capacity];var s=e.sample;s.selected=PathOf(e.selected);s.firstHit=PathOf(e.firstHit);s.firstHitModule=e.hitModule!=null?e.hitModule.GetType().Name:"";s.inputModule=e.inputModule!=null?e.inputModule.GetType().Name:"";s.inputOverride=e.inputModule!=null&&e.inputModule.inputOverride!=null?e.inputModule.inputOverride.GetType().Name:"";s.hButton=e.hButton!=null?PathOf(e.hButton.gameObject):"";output.samples[i]=s;}for(int i=0;i<m;i++)output.uiEvents[i]=events[(totalEvents-m+i)%EventCapacity];
  return JsonUtility.ToJson(output,true);
 }
 public static void Flush(){if(!Enabled||total==0)return;try{File.WriteAllText(OutputPath,Dump());}catch(Exception ex){Debug.LogWarning("Input trace write failed: "+ex.GetType().Name);}}
}
public sealed class DSPPadManagedInputTraceDriver:MonoBehaviour {
 float nextWrite;void LateUpdate(){DSPPadManagedInputTrace.AfterLate();if(Time.realtimeSinceStartup>=nextWrite){nextWrite=Time.realtimeSinceStartup+10f;DSPPadManagedInputTrace.Flush();}}
 void OnApplicationPause(bool paused){if(paused)DSPPadManagedInputTrace.Flush();}void OnApplicationQuit(){DSPPadManagedInputTrace.Flush();}
}
public sealed class DSPPadHButtonTrace:MonoBehaviour,IPointerEnterHandler,IPointerExitHandler,IPointerDownHandler,IPointerUpHandler,IPointerClickHandler {
 Button button;void Awake(){button=GetComponent<Button>();}
 public void OnPointerEnter(PointerEventData e){DSPPadManagedInputTrace.RecordUI(0,e,button);}public void OnPointerExit(PointerEventData e){DSPPadManagedInputTrace.RecordUI(1,e,button);}public void OnPointerDown(PointerEventData e){DSPPadManagedInputTrace.RecordUI(2,e,button);}public void OnPointerUp(PointerEventData e){DSPPadManagedInputTrace.RecordUI(3,e,button);}public void OnPointerClick(PointerEventData e){DSPPadManagedInputTrace.RecordUI(4,e,button);}
}
#endif
