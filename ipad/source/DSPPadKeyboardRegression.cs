using System;using System.IO;using System.Collections;using System.Collections.Generic;using System.Runtime.InteropServices;using UnityEngine;using UnityEngine.EventSystems;
// Opt-in transport test on the owned fixture. Gameplay handlers are never called
// directly for assertions; fixture stock/hand setup is explicitly programmatic.
public static class DSPPadKeyboardRegression {
 [DllImport("@rpath/UnityFramework.framework/UnityFramework")]static extern int DSPAOTQueueTestKey(int code,int pressed);
 [DllImport("@rpath/UnityFramework.framework/UnityFramework")]static extern void DSPAOTEndTestKeyboard();
 [DllImport("@rpath/UnityFramework.framework/UnityFramework")]static extern int DSPAOTQueueTestPointer(float x,float y,int buttons,float dx,float dy,float wheel);
 [Serializable]sealed class Result{public string source="PROGRAMMATIC native transport; physical keyboard unverified";public bool completed;public List<string> checks=new List<string>();}
 static Result result;static Vector2 point;
 static void Note(string name,bool pass,string evidence){result.checks.Add((pass?"PASS ":"FAIL ")+name+": "+evidence);Write();}
 static void Write(){File.WriteAllText(Path.Combine(Application.persistentDataPath,"dsp-keyboard-regression.json"),JsonUtility.ToJson(result,true));}
 static void Key(KeyCode key,bool down){if(DSPAOTQueueTestKey(DSPPadKeyboard.HID(key),down?1:0)!=1)throw new Exception("Native test key rejected: "+key);}
 static void Pointer(int mask){if(DSPAOTQueueTestPointer(point.x/Screen.width,point.y/Screen.height,mask,0,0,0)!=1)throw new Exception("Native pointer test rejected");}
 static IEnumerator Wait(float seconds){float end=Time.realtimeSinceStartup+seconds;do{Pointer(0);yield return null;}while(Time.realtimeSinceStartup<end);}
 static IEnumerator Tap(KeyCode key){Key(key,true);Key(key,false);yield return Wait(.3f);}
 static bool WorldPoint(){var hits=new List<RaycastResult>();for(int y=3;y<8;y++)for(int x=3;x<8;x++){point=new Vector2(Screen.width*x*.1f,Screen.height*y*.1f);hits.Clear();EventSystem.current.RaycastAll(new PointerEventData(EventSystem.current){position=point},hits);if(hits.Count==0)return true;}return false;}
 static IEnumerator Rotate(){
  var p=GameMain.mainPlayer;bool world=WorldPoint();Note("rotation world precondition",world,"uncovered original world point="+point);if(!world)yield break;
  int minerSlot=-1;for(int i=0;i<p.package.size;i++)if(p.package.grids[i].itemId==2301){minerSlot=i;break;}
  Note("miner inventory slot",minerSlot>=0,"slot="+minerSlot);if(minerSlot<0)yield break;
  p.SetHandItems(2301,1,minerSlot);yield return Wait(.6f);var click=p.controller.actionBuild.clickTool;
  bool active=p.inhandItemId==2301&&p.controller.actionBuild.activeTool==click;Note("original miner preview active",active,"hand="+p.inhandItemId);if(!active)yield break;
  float before=click.yaw;for(int i=0;i<3;i++){Key(KeyCode.R,true);Key(KeyCode.R,false);}yield return Wait(.8f);
  float change=Mathf.Repeat(click.yaw-before,360);Note("three R taps between render frames",Mathf.Abs(change-270)<.1f,"yaw="+before+" -> "+click.yaw+" expected +270");
  Key(KeyCode.R,true);yield return Wait(.2f);float held=click.yaw;yield return Wait(.35f);Note("plain R held preserves original no-repeat",Mathf.Abs(Mathf.DeltaAngle(held,click.yaw))<.1f,"yaw="+held+" -> "+click.yaw);Key(KeyCode.R,false);yield return Wait(.2f);
  before=click.yaw;Key(KeyCode.LeftShift,true);Key(KeyCode.R,true);yield return Wait(.2f);change=Mathf.Abs(Mathf.DeltaAngle(before,click.yaw));Note("Shift R original fine rotation",change>.1f,"yaw="+before+" -> "+click.yaw+" shift="+VFInput.shift);
  Key(KeyCode.LeftShift,false);yield return Wait(.15f);Note("Shift release during held R",!VFInput.shift&&DSPPadInput.GetKey(KeyCode.R),"shift="+VFInput.shift+" R="+DSPPadInput.GetKey(KeyCode.R));Key(KeyCode.R,false);yield return Wait(.2f);
  yield return Tap(KeyCode.Escape);Note("original Esc cancels preview",p.inhandItemId==0,"hand="+p.inhandItemId);
  if(p.controller.cmd.type==ECommand.Build){yield return Tap(KeyCode.Escape);Note("second original Esc leaves build mode",p.controller.cmd.type!=ECommand.Build,"command="+p.controller.cmd.type);}
 }
 static IEnumerator Fuel(KeyCode modifier){
  var p=GameMain.mainPlayer;var ui=UIRoot.instance.uiGame;if(!ui.mechaWindow.active)yield return Tap(KeyCode.C);if(!ui.inventoryWindow.active)ui.inventoryWindow._Open();yield return Wait(.4f);
  p.TryAddItemToPackage(1006,20,0,false);yield return Wait(.2f);var grid=ui.inventoryWindow.inventory;int index=-1;for(int i=0;i<p.package.size;i++)if(p.package.grids[i].itemId==1006){index=i;break;}
  bool ready=ui.mechaWindow.active&&index>=0&&LDB.items.Select(1006).HeatValue>0;Note(modifier+" fuel precondition",ready,"mecha="+ui.mechaWindow.active+" index="+index);if(!ready)yield break;
  var canvas=grid.GetComponentInParent<Canvas>();point=RectTransformUtility.WorldToScreenPoint(canvas.renderMode==RenderMode.ScreenSpaceOverlay?null:canvas.worldCamera,grid.contentRect.TransformPoint(new Vector3(index%grid.colCount*50+25,-index/grid.colCount*50-25,0)));
  int before=p.mecha.reactorStorage.GetItemCount(1006),inventory=p.package.GetItemCount(1006);Key(modifier,true);yield return Wait(.1f);Pointer(1);yield return null;Pointer(0);yield return Wait(.2f);Key(modifier,false);yield return Wait(.15f);
  int after=p.mecha.reactorStorage.GetItemCount(1006);Note(modifier+" native click to fuel",after>before&&p.package.GetItemCount(1006)<inventory,"fuel="+before+" -> "+after+" inventory="+inventory+" -> "+p.package.GetItemCount(1006)+" coordinate="+point);
  ui.mechaWindow._Close();ui.inventoryWindow._Close();yield return Wait(.2f);
 }
 [Serializable]sealed class WalkSample {public float time,energy;public string key,movement,obstacles;public Vector3 position,intended,actual;public Vector4 input;public bool grounded;}
 [Serializable]sealed class WalkReport {public string source="Long native-key route on initial test save; no teleport/collider edits";public List<WalkSample> samples=new List<WalkSample>();public List<string> checks=new List<string>();}
 static string Obstacles(Vector3 direction){
  var p=GameMain.mainPlayer;var up=p.position.normalized;var origin=p.position+up*.5f;string text="";
  var colliders=new List<Collider>(Physics.OverlapSphere(origin,.35f,15873,QueryTriggerInteraction.Ignore));
  foreach(var hit in Physics.SphereCastAll(origin,.35f,direction.normalized,2f,15873,QueryTriggerInteraction.Ignore))if(!colliders.Contains(hit.collider))colliders.Add(hit.collider);
  foreach(var c in colliders){if(c.transform==p.controller.transform||c.transform.IsChildOf(p.controller.transform))continue;
   text+=c.name+":"+c.GetType().Name+":bounds="+c.bounds;ColliderData cd;
   if(GameMain.localPlanet.physics.GetColliderData(c,out cd))text+=":object="+cd.objType+"/"+cd.objId+":original="+cd.pos+"/"+cd.ext;
   text+=";";
  }return text;
 }
 static IEnumerator Walking(){
  if(!WorldPoint())yield break;var p=GameMain.mainPlayer;var walk=new WalkReport();
  var route=new[]{KeyCode.A,KeyCode.W,KeyCode.D,KeyCode.S,KeyCode.A,KeyCode.W};
  for(int leg=0;leg<route.Length;leg++){
   var key=route[leg];float duration=leg==0?3f:15f;Vector3 before=p.position,last=before;float path=0,heldSince=Time.realtimeSinceStartup;int stopped=0;bool screenshot=false;Key(key,true);
   while(Time.realtimeSinceStartup-heldSince<duration){
    yield return Wait(.25f);var pc=p.controller;Vector3 intended=pc.actionWalk.moveVelocity+pc.actionWalk.rtsVelocity;
    float step=Vector3.Distance(last,p.position);path+=step;last=p.position;bool blocked=Time.realtimeSinceStartup-heldSince>1&&pc.input0.sqrMagnitude>.1f&&step<.05f;
    if(blocked)stopped++;
    walk.samples.Add(new WalkSample{time=Time.realtimeSinceStartup,key=key.ToString(),energy=(float)p.mecha.coreEnergy,movement=p.movementState.ToString(),position=p.position,intended=intended,actual=pc.rigid.velocity,input=pc.input0,grounded=pc.actionWalk.isGrounded,obstacles=Obstacles(intended)});
    if(blocked&&!screenshot){screenshot=true;yield return DSPPadRenderDiagnostics.Capture("23-walk-blocked-"+leg);}
   }
   Key(key,false);yield return Wait(.25f);string evidence="seconds="+duration+" path="+path+" net="+Vector3.Distance(before,p.position)+" stoppedQuarterSeconds="+stopped+" finalState="+p.movementState;
   walk.checks.Add(key+" "+evidence);Note(key+" long native-key route",path>1,evidence);
   File.WriteAllText(Path.Combine(Application.persistentDataPath,"dsp-long-walk-23.json"),JsonUtility.ToJson(walk,true));
   DSPPadManagedInputTrace.Flush();File.WriteAllText(Path.Combine(Application.persistentDataPath,"dsp-walk-input-23.json"),DSPPadManagedInputTrace.Dump());
  }
  Write();
 }

 static void FlightTrace(string suffix){DSPPadManagedInputTrace.Flush();File.WriteAllText(Path.Combine(Application.persistentDataPath,"flight-23-"+suffix+".json"),DSPPadManagedInputTrace.Dump());}
 static string FlightPrecondition(){var p=GameMain.mainPlayer;var w=p.controller.actionWalk;return "grounded="+w.isGrounded+" groundDistance="+w.groundDist+" jumpCoolTime="+w.jumpCoolTime+" flyUpChance="+w.flyUpChance+" inputing="+VFInput.inputing+" fullscreen="+VFInput.inFullscreenGUI+" disabled="+GameMain.data.disableController+" alive="+p.isAlive+" viewMode="+UIGame.viewMode+" jump="+VFInput.override_keys[8].keyCode+"/"+VFInput.override_keys[8].modifier+" takeOff="+VFInput.override_keys[9].keyCode+"/"+VFInput.override_keys[9].modifier+" pullUp="+VFInput.override_keys[10].keyCode+"/"+VFInput.override_keys[10].modifier;}
 static IEnumerator FlightCursor(){
  var player=GameMain.mainPlayer;string save="DSPemu-FlightFixture23-"+DateTime.UtcNow.ToString("yyyyMMdd-HHmmss");
  if(!GameSave.SaveCurrentGame(save)){Note("flight fixture snapshot",false,"Save failed; no fixture changes performed");yield break;}
  // Fixture prerequisites only. Transition, physics, camera and cursor remain original.
  bool hadGuide=GameMain.data.guideRunning;int oldThruster=player.mecha.thrusterLevel;
  if(hadGuide)GameMain.data.EndStandardModeGuide(false);
  player.mecha.thrusterLevel=Math.Max(2,oldThruster);player.mecha.coreEnergy=player.mecha.coreEnergyCap;
  Note("flight fixture",true,"Snapshot saved; thruster prerequisite supplied "+oldThruster+" -> "+player.mecha.thrusterLevel+"; guideRunning="+hadGuide+"; no position/movement-state/camera assignments");
  if(player.controller.cmd.type==ECommand.Build){yield return Tap(KeyCode.Escape);yield return Tap(KeyCode.Escape);}
  var ui=UIRoot.instance.uiGame;bool world=WorldPoint();Note("flight world input precondition",world&&!VFInput.inFullscreenGUI,"point="+point+" fullscreen="+VFInput.inFullscreenGUI+" command="+player.controller.cmd.type);
  bool sawFly=false,sawSail=false,space=false;
  try {
   // Windows PlayerMove_Walk: a second jump edge within 0.8 s switches to Fly.
   DSPPadManagedInputTrace.DetailedFor(3f);yield return Wait(.1f);FlightTrace("before-space");
   result.checks.Add("EVIDENCE quick Space precondition: "+FlightPrecondition());Write();
   yield return Tap(KeyCode.Space);FlightTrace("after-space1");yield return Tap(KeyCode.Space);FlightTrace("after-space2");yield return Wait(.2f);
   sawFly=player.movementState==EMovementState.Fly;
   Note("original double Space enters flight",sawFly,"movement="+player.movementState+" thruster="+player.mecha.thrusterLevel);
   FlightTrace("quick-final");
   if(!sawFly){
    // A separate held-key diagnostic, never a replacement verdict for quick edges.
    float settle=Time.realtimeSinceStartup+5f;while(Time.realtimeSinceStartup<settle&&(!player.controller.actionWalk.isGrounded||player.controller.actionWalk.jumpCoolTime>0||player.controller.actionWalk.flyUpChance>0))yield return Wait(.1f);
    bool ready=player.movementState==EMovementState.Walk&&player.controller.actionWalk.isGrounded&&player.controller.actionWalk.jumpCoolTime==0&&player.controller.actionWalk.flyUpChance==0;
    result.checks.Add("EVIDENCE held Space precondition: "+FlightPrecondition());Write();
    if(ready){DSPPadManagedInputTrace.DetailedFor(3f);FlightTrace("held-before");Key(KeyCode.Space,true);yield return Wait(.12f);Key(KeyCode.Space,false);yield return Wait(.12f);FlightTrace("held-after1");Key(KeyCode.Space,true);yield return Wait(.12f);Key(KeyCode.Space,false);yield return Wait(.2f);FlightTrace("held-after2");sawFly=player.movementState==EMovementState.Fly;Note("separate held double Space enters flight",sawFly,"movement="+player.movementState+"; quick-edge verdict above remains unchanged");}
    else{result.checks.Add("UNVERIFIED held Space: ground precondition unavailable");Write();}
   }
   if(sawFly){
    // Windows PlayerMove_Fly: Space raises target altitude, W supplies >12.5 horizontal speed;
    // at actual altitude >49 and thruster >=2 the original controller switches to Sail.
    Key(KeyCode.W,true);Key(KeyCode.Space,true);float end=Time.realtimeSinceStartup+90;
    while(Time.realtimeSinceStartup<end){yield return Wait(.25f);sawSail|=player.sailing;if(player.sailing&&GameMain.localPlanet==null){space=true;break;}}
   }
  } finally {Key(KeyCode.Space,false);Key(KeyCode.W,false);}
  yield return Wait(.5f);
  Note("space fixture active",space&&player.sailing&&GameMain.localPlanet==null,"sawFly="+sawFly+" sawSail="+sawSail+" movement="+player.movementState+" planet="+player.planetId);
  if(space&&player.sailing&&GameMain.localPlanet==null){
   Note("sailing original cursor request",Cursor.lockState==CursorLockMode.Locked&&DSPPadCursorBridge.Requested&&(DSPPadCursorBridge.NativeStatus&3)==3,"managed="+Cursor.lockState+" UIKitStatus="+DSPPadCursorBridge.NativeStatus);
   yield return DSPPadRenderDiagnostics.Capture("23-space-cursor");
   yield return Tap(KeyCode.Tab);yield return Wait(.5f);Note("Tab releases sailing pointer",ui.disableLockCursor&&!DSPPadCursorBridge.Requested&&(DSPPadCursorBridge.NativeStatus&7)==0,"disabled="+ui.disableLockCursor+" status="+DSPPadCursorBridge.NativeStatus);
   yield return Tap(KeyCode.Tab);yield return Wait(.5f);Note("Tab restores sailing pointer",!ui.disableLockCursor&&DSPPadCursorBridge.Requested&&(DSPPadCursorBridge.NativeStatus&3)==3,"status="+DSPPadCursorBridge.NativeStatus);
   yield return Tap(KeyCode.C);yield return Wait(.5f);Note("C opens mecha plus inventory and releases sailing pointer",ui.mechaWindow.active&&ui.inventoryWindow.active&&ui.isCursorNeeded&&!DSPPadCursorBridge.Requested&&(DSPPadCursorBridge.NativeStatus&7)==0,"mecha="+ui.mechaWindow.active+" inventory="+ui.inventoryWindow.active+" needed="+ui.isCursorNeeded+" status="+DSPPadCursorBridge.NativeStatus);
   yield return Tap(KeyCode.Escape);yield return Wait(.5f);Note("first Esc closes inventory only and keeps sailing pointer released",!ui.inventoryWindow.active&&ui.mechaWindow.active&&ui.isCursorNeeded&&!DSPPadCursorBridge.Requested&&(DSPPadCursorBridge.NativeStatus&7)==0,"mecha="+ui.mechaWindow.active+" inventory="+ui.inventoryWindow.active+" needed="+ui.isCursorNeeded+" status="+DSPPadCursorBridge.NativeStatus);
   yield return Tap(KeyCode.Escape);yield return Wait(.5f);Note("second Esc closes mecha and restores sailing pointer",!ui.inventoryWindow.active&&!ui.mechaWindow.active&&!ui.isCursorNeeded&&DSPPadCursorBridge.Requested&&(DSPPadCursorBridge.NativeStatus&3)==3,"needed="+ui.isCursorNeeded+" status="+DSPPadCursorBridge.NativeStatus);
  }else{result.checks.Add("UNVERIFIED sailing cursor/Tab/C/Esc: natural flight fixture did not reach space; no downstream cursor verdict");Write();}
  result.checks.Add("LIMIT physical unlimited relative movement: no synthetic packet proves a connected mouse; native status bits requested1/preferred2/granted4/foreground8/GCMouse16="+DSPPadCursorBridge.NativeStatus);Write();
  DSPGame.StartGame(save);yield return null;float deadline=Time.realtimeSinceStartup+180;while((!GameMain.isRunning||GameMain.isLoading||GameMain.localPlanet==null||!GameMain.localPlanet.factoryLoaded)&&Time.realtimeSinceStartup<deadline)yield return Wait(1);
  yield return Wait(2);Note("flight fixture restored to ground",GameMain.localPlanet!=null&&!GameMain.mainPlayer.sailing&&!DSPPadCursorBridge.Requested,"status="+DSPPadCursorBridge.NativeStatus);
 }
 static IEnumerator Sequence(){yield return Wait(.2f);yield return Rotate();yield return Fuel(KeyCode.LeftControl);yield return Fuel(KeyCode.RightControl);Key(KeyCode.LeftCommand,true);yield return Wait(.1f);Note("Command remains independent from Windows Ctrl",!VFInput.control,"control="+VFInput.control);Key(KeyCode.LeftCommand,false);yield return Wait(.1f);yield return Walking();yield return FlightCursor();}
 public static IEnumerator Run(){
  if(!DSPPadDiagnosticLaunch.NativePointerTestAllowed)yield break;result=new Result();point=new Vector2(Screen.width*.5f,Screen.height*.5f);var stack=new Stack<IEnumerator>();stack.Push(Sequence());
  try{while(stack.Count>0){bool more=false;object next=null;Exception error=null;try{more=stack.Peek().MoveNext();if(more)next=stack.Peek().Current;}catch(Exception e){error=e;}if(error!=null){Note("diagnostic exception",false,error.ToString());break;}if(!more){(stack.Pop() as IDisposable)?.Dispose();continue;}if(next is IEnumerator){stack.Push((IEnumerator)next);continue;}yield return next;}result.completed=stack.Count==0;}
  finally{DSPAOTEndTestKeyboard();Pointer(0);DSPPadInput.ResetInputAxes();while(stack.Count>0)(stack.Pop() as IDisposable)?.Dispose();Write();}
 }
}
