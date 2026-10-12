using System;
using UnityEngine;
using System.Runtime.InteropServices;
// Physical-device transport only; original VFInput / CombineKey still decide
// binding, modifiers, fixed-tick edges and camera sensitivity.
public static class DSPPadInput {
 [DllImport("@rpath/UnityFramework.framework/UnityFramework")]
 static extern int DSPAOTPollPointer(out float dx,out float dy,out float wheel,out float normalizedX,out float normalizedY);
#if DSP_EMU_IPAD
 public static int PhysicalModifierMask=>DSPPadKeyboard.PhysicalModifiers;
#endif

 static int buttons,previous,frame=-1,packetDown,packetUp;static bool unavailable,nativeTransport;
 static int rawButtons,rawDown,rawUp;
 static readonly DSPPadKeyQueue[] mouseKeys={new DSPPadKeyQueue(),new DSPPadKeyQueue(),new DSPPadKeyQueue(),new DSPPadKeyQueue(),new DSPPadKeyQueue(),new DSPPadKeyQueue(),new DSPPadKeyQueue()};
 static Vector2 delta;static float wheel;static Vector3 position;static bool positionReady;
 static bool escapeQueued,escapeHeld,escapeFixedSampled;
 static int escapeDownFrame=-1,escapeUpFrame=-1;static float escapeStarted;
 // 1=queued, 2=down awaiting fixed sample, 3=up awaiting fixed sample.
 static int tapState,tapButton,tapCanceledButton,tapDownFrame=-1,tapUpFrame=-1;static Vector3 tapPosition;
 static float tapStarted;static bool tapDownSampled,tapUpSampled,tapCancelBarrier;
 public static bool VirtualPointerActive=>tapState>=2||DSPTouchControls.PointerActive;
 public static int ActiveWorldButton=>tapState==0?-1:tapButton;
 public static int WorldTapPresses {get;private set;}
 public static int WorldTapFixedDownSamples {get;private set;}
 public static int WorldTapFixedUpSamples {get;private set;}
 public static int WorldTapCanceled {get;private set;}
 static bool TapContextAllowed=>Application.isFocused&&!DSPSmartTouchFrame.KeyboardAndMouse&&GameMain.isRunning&&!DSPGame.IsMenuDemo&&!GameMain.isPaused&&!VFInput.inFullscreenGUI&&!VFInput.inputing&&!VFInput.inScreenshotMode;
 public static bool QueueWorldTap(Vector2 point,int button=0){
  DSPSmartTouchFrame.CheckPeripherals();
  if(button<0||button>1||!TapContextAllowed||tapState!=0||tapCancelBarrier||escapeHeld||escapeQueued||buttons!=0||DSPSmartTouchFrame.UIBlocks(point))return false;
  tapState=1;tapButton=button;tapPosition=new Vector3(point.x,point.y,0);tapStarted=Time.realtimeSinceStartup;tapDownSampled=tapUpSampled=false;WorldTapPresses++;return true;
 }
 static void ClearPrimaryEdges(VFInput.InputAxis axis,int index){
  if(axis==null||index<0||index>=axis.press.Length)return;
  axis.press[index]=axis.lastPress[index]=axis.down[index]=axis.up[index]=false;axis.value[index]=0;axis.eventFrame[index]=0;
 }
 public static void CancelWorldTap(){
  if(tapState==0)return;
  bool started=tapState>=2;tapState=0;tapDownFrame=tapUpFrame=-1;tapDownSampled=tapUpSampled=false;WorldTapCanceled++;
  // A cancellation is not an intentional mouse release: BuildTool_Click
  // confirms onUp. Discard only our owned button state and let the original
  // no-press path cancel its stage, before accepting that physical button again.
  if(started){
   tapCancelBarrier=true;tapCanceledButton=tapButton;ClearPrimaryEdges(VFInput.axis_button,tapButton);
   if(VFInput.override_keys!=null)for(int i=0;i<VFInput.override_keys.Length;i++)if(VFInput.override_keys[i].keyCode==(int)KeyCode.Mouse0+tapButton)ClearPrimaryEdges(VFInput.axis_combine_key,i);
  }
 }
 static void UpdateWorldTap(){
  if(tapState==0)return;
  if(!TapContextAllowed||buttons!=0||Time.realtimeSinceStartup-tapStarted>DSPPadTapGesture.MaximumSampleSeconds){CancelWorldTap();return;}
  if(tapState==1){
   if(DSPSmartTouchFrame.UIBlocks(new Vector2(tapPosition.x,tapPosition.y))){CancelWorldTap();return;}
   tapState=2;tapDownFrame=Time.frameCount;
  }else if(tapState==2&&tapDownSampled){tapState=3;tapUpFrame=Time.frameCount;}
  else if(tapState==3&&tapUpSampled){tapState=0;tapDownFrame=tapUpFrame=-1;}
 }
 public static bool PhysicalMouse {get;private set;}
 public static bool NativeMouseTransport=>nativeTransport;
 public static int ButtonMask=>buttons;
 public static int NativeDownMask=>packetDown;
 public static int NativeUpMask=>packetUp;
 public static bool NativePositionValid {get;private set;}
 public static bool UIKitPointerSource {get;private set;}
 public static bool DiagnosticPointerSource {get;private set;}
 public static Vector2 mouseScrollDelta=>nativeTransport?new Vector2(0,PhysicalMouse?wheel:0):UnityEngine.Input.mouseScrollDelta;
 public static bool anyKey {get{Poll();return UnityEngine.Input.anyKey||buttons!=0||escapeHeld
#if DSP_EMU_IPAD
  ||DSPPadKeyboard.AnyHeld
#endif
  ;}}
 public static bool anyKeyDown {get{Poll();return UnityEngine.Input.anyKeyDown||rawDown!=0||escapeDownFrame==Time.frameCount
#if DSP_EMU_IPAD
  ||DSPPadKeyboard.AnyDown
#endif
  ;}}
 public static Vector2 RawDelta=>delta;
 public static int MouseFrames {get;private set;}
 public static int VirtualEscapePresses {get;private set;}
 public static int VirtualEscapeFixedSamples {get;private set;}
 // A tap is one normal key press. Keep it held until VFInput's original fixed
 // sampler has observed it; do not close any game window here.
 public static void QueueEscape(){
  if(!Application.isFocused||escapeHeld||escapeQueued)return;
  escapeQueued=true;VirtualEscapePresses++;DSPSmartTouchFrame.Reset();
 }
 public static void UpdateInputPublished(){DSPTouchControls.Published();
#if DSP_EMU_IPAD
  DSPPadKeyboard.UpdatePublished();
#endif
  for(int b=0;b<7;b++)mouseKeys[b].Published();
 }
 public static void FixedInputSampled(){DSPTouchControls.Sampled();
#if DSP_EMU_IPAD
  DSPPadKeyboard.FixedSampled();
#endif
  for(int b=0;b<7;b++)mouseKeys[b].Sampled();
  if(VFInput.axis_button!=null){
   if(tapCancelBarrier&&!VFInput.axis_button.press[tapCanceledButton])tapCancelBarrier=false;
   if(tapState==2&&VFInput.axis_button.press[tapButton]&&!tapDownSampled){tapDownSampled=true;WorldTapFixedDownSamples++;}
   if(tapState==3&&!VFInput.axis_button.press[tapButton]&&!tapUpSampled){tapUpSampled=true;WorldTapFixedUpSamples++;}
  }
  if(escapeHeld&&VFInput.axis_button!=null&&VFInput.axis_button.press[5]){
   escapeFixedSampled=true;VirtualEscapeFixedSamples++;
  }
 }
 public static void CancelVirtualKeys(){CancelWorldTap();escapeQueued=false;escapeHeld=false;escapeFixedSampled=false;escapeDownFrame=escapeUpFrame=-1;}
#if DSP_EMU_IPAD
 [RuntimeInitializeOnLoadMethod(RuntimeInitializeLoadType.BeforeSceneLoad)]
 static void Install(){UnityEngine.Input.simulateMouseWithTouches=false;CancelVirtualKeys();}
#endif
 public static void Poll(){
  if(frame==Time.frameCount)return;frame=Time.frameCount;previous=buttons;delta=Vector2.zero;wheel=0;
#if DSP_EMU_IPAD
  DSPPadKeyboard.Poll();
  DSPPadPerformanceHUD.EnsureInstalled();
  DSPPadEscapeButton.EnsureInstalled();
  DSPPadStarmapTouch.EnsureInstalled();
  DSPPadEventSystemInput.EnsureInstalled();
#endif
  DSPSmartTouchFrame.CheckPeripherals();
  bool old=PhysicalMouse,wasDiagnosticPointer=DiagnosticPointerSource;int state=0;float nx=0,ny=0;
  if(!unavailable)try{float x,y;state=DSPAOTPollPointer(out x,out y,out wheel,out nx,out ny);delta=new Vector2(x,y);nativeTransport=true;}catch(DllNotFoundException){unavailable=true;}catch(EntryPointNotFoundException){unavailable=true;}
  PhysicalMouse=(state&128)!=0;NativePositionValid=(state&256)!=0;UIKitPointerSource=(state&512)!=0;DiagnosticPointerSource=(state&(1<<24))!=0;
  if(wasDiagnosticPointer&&!DiagnosticPointerSource&&!NativePositionValid){positionReady=false;position=Vector3.zero;}
  int held=PhysicalMouse?state&127:0;packetDown=PhysicalMouse?(state>>10)&127:0;packetUp=(state>>17)&127;
  // UIKit can deliver an entire click between two rendered frames. Keep its
  // press until the original fixed input sampler has observed it, then publish
  // its release. This transports the physical edge; bindings remain original.
  rawDown=packetDown|(held&~rawButtons);rawUp=packetUp|(rawButtons&~held);rawButtons=held;buttons=0;
  for(int b=0;b<7;b++){
   int bit=1<<b;mouseKeys[b].Poll((held&bit)!=0,(packetDown&bit)!=0?1:0,0,PhysicalMouse&&Application.isFocused,Time.realtimeSinceStartup);
   if(mouseKeys[b].Held&&PhysicalMouse)buttons|=bit;
  }
  packetUp&=~buttons;
  if(!Application.isFocused){delta=Vector2.zero;wheel=0;buttons=packetDown=packetUp=0;CancelVirtualKeys();}
  if(!old&&PhysicalMouse)previous=buttons&~packetDown;
  if(delta.sqrMagnitude>0)MouseFrames++;
  // Physical UIKit coordinates are independent of finger-generated Unity
  // cursor coordinates. Use the same canonical point for world and original UI.
  if(NativePositionValid&&PhysicalMouse){position=new Vector3(nx*Screen.width,ny*Screen.height,0);positionReady=true;}
  else if(!nativeTransport&&(!positionReady||UnityEngine.Input.touchCount==0)){position=UnityEngine.Input.mousePosition;positionReady=true;}
  DSPPadDocuments.Ensure();
  DSPPadInputMode.Poll(delta,wheel,rawDown!=0,rawButtons!=0,DiagnosticPointerSource);
  DSPSmartTouchFrame.CheckPeripherals();
  DSPTouchControls.Poll();
  UpdateWorldTap();
  if(escapeHeld&&Time.realtimeSinceStartup-escapeStarted>2f)CancelVirtualKeys();
  if(escapeHeld&&escapeFixedSampled){escapeHeld=false;escapeFixedSampled=false;escapeUpFrame=frame;}
  if(escapeQueued&&!escapeHeld&&escapeUpFrame!=frame){escapeQueued=false;escapeHeld=true;escapeFixedSampled=false;escapeDownFrame=frame;escapeStarted=Time.realtimeSinceStartup;}
 }
 public static Vector3 mousePosition {get{Poll();return tapState>=2?tapPosition:DSPTouchControls.PointerActive?DSPTouchControls.Pointer:(nativeTransport?position:UnityEngine.Input.mousePosition);}}
 static bool MouseKey(KeyCode key,out int index){index=(int)key-(int)KeyCode.Mouse0;return index>=0&&index<7;}
 public static bool GetKey(KeyCode key){
  Poll();
  if(DSPPadDocuments.Busy)return false;
  bool touchKey;if(DSPTouchControls.Read(key,0,out touchKey))return touchKey;
  if(key==KeyCode.Escape&&escapeHeld)return true;
#if DSP_EMU_IPAD
  bool keyValue;if(DSPPadKeyboard.Read(key,0,out keyValue))return keyValue;
#endif
  int b;bool mouse=MouseKey(key,out b);if(mouse){if(tapCancelBarrier&&b==tapCanceledButton)return false;if(tapState==2&&b==tapButton)return true;}
  if(mouse&&DSPPadInputMode.UseTouch)return false;
  if(mouse&&nativeTransport)return PhysicalMouse&&(buttons&(1<<b))!=0;
  return UnityEngine.Input.GetKey(key);
 }
 public static bool GetKeyDown(KeyCode key){
  Poll();
  if(DSPPadDocuments.Busy)return false;
  bool touchKey;if(DSPTouchControls.Read(key,1,out touchKey))return touchKey;
  if(key==KeyCode.Escape&&escapeDownFrame==Time.frameCount)return true;
#if DSP_EMU_IPAD
  bool keyValue;if(DSPPadKeyboard.Read(key,1,out keyValue))return keyValue;
#endif
  int b;bool mouse=MouseKey(key,out b);if(mouse){if(tapCancelBarrier&&b==tapCanceledButton)return false;if(b==tapButton&&tapDownFrame==Time.frameCount)return true;}
  if(mouse&&DSPPadInputMode.UseTouch)return false;
  if(mouse&&nativeTransport)return PhysicalMouse&&(((packetDown&(1<<b))!=0)||((buttons&(1<<b))!=0&&(previous&(1<<b))==0));
  return UnityEngine.Input.GetKeyDown(key);
 }
 public static bool GetKeyUp(KeyCode key){
  Poll();
  if(DSPPadDocuments.Busy)return false;
  bool touchKey;if(DSPTouchControls.Read(key,2,out touchKey))return touchKey;
  if(key==KeyCode.Escape&&escapeUpFrame==Time.frameCount)return true;
#if DSP_EMU_IPAD
  bool keyValue;if(DSPPadKeyboard.Read(key,2,out keyValue))return keyValue;
#endif
  int b;bool mouse=MouseKey(key,out b);if(mouse){if(tapCancelBarrier&&b==tapCanceledButton)return false;if(b==tapButton&&tapUpFrame==Time.frameCount)return true;}
  if(mouse&&nativeTransport)return ((packetUp&(1<<b))!=0)||((buttons&(1<<b))==0&&(previous&(1<<b))!=0);
  return UnityEngine.Input.GetKeyUp(key);
 }
 public static bool UIGetMouseButton(int button,int mode){Poll();if(button<0||button>=7)return false;if(!nativeTransport)return mode==0?UnityEngine.Input.GetMouseButton(button):mode==1?UnityEngine.Input.GetMouseButtonDown(button):UnityEngine.Input.GetMouseButtonUp(button);int mask=mode==0?rawButtons:mode==1?rawDown:rawUp;return Application.isFocused&&(mask&(1<<button))!=0;}
 public static bool GetMouseButton(int button)=>button>=0&&button<7?GetKey(KeyCode.Mouse0+button):UnityEngine.Input.GetMouseButton(button);
 public static bool GetMouseButtonDown(int button)=>button>=0&&button<7?GetKeyDown(KeyCode.Mouse0+button):UnityEngine.Input.GetMouseButtonDown(button);
 public static bool GetMouseButtonUp(int button)=>button>=0&&button<7?GetKeyUp(KeyCode.Mouse0+button):UnityEngine.Input.GetMouseButtonUp(button);
 public static float GetAxis(string name){
  Poll();
  if(DSPTouchControls.Enabled&&name=="Mouse Wheel"&&DSPTouchControls.Zoom!=0)return DSPTouchControls.Zoom*.1f;
  if(DSPPadDocuments.Busy||DSPPadInputMode.UseTouch)return 0;
  if(nativeTransport){if(name=="Mouse X")return PhysicalMouse?delta.x*.1f:0;if(name=="Mouse Y")return PhysicalMouse?delta.y*.1f:0;if(name=="Mouse Wheel")return PhysicalMouse?wheel*.1f:0;}
  return UnityEngine.Input.GetAxis(name);
 }
 public static void ResetInputAxes(){delta=Vector2.zero;wheel=0;previous=buttons=0;packetDown=packetUp=rawButtons=rawDown=rawUp=0;CancelVirtualKeys();for(int b=0;b<7;b++)mouseKeys[b].Clear();
#if DSP_EMU_IPAD
 DSPPadKeyboard.Reset();
#endif
 UnityEngine.Input.ResetInputAxes();}
}
