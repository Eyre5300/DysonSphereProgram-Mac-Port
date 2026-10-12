using System;
using System.Collections;
using System.Collections.Generic;
using System.IO;
using System.Runtime.InteropServices;
using UnityEngine;
using UnityEngine.EventSystems;
using UnityEngine.UI;

// Authored port diagnostic. Queues native packets, then lets the normal Unity
// UI and original Windows game updates process them. Never a physical-input proof.
public static class DSPPadMouseRegression {
 [DllImport("@rpath/UnityFramework.framework/UnityFramework")]
 static extern int DSPAOTQueueTestPointer(float nx,float ny,int buttons,float dx,float dy,float wheel);
 [DllImport("@rpath/UnityFramework.framework/UnityFramework")]
 static extern int DSPAOTClearTestPointer();

 [Serializable] public sealed class Check {
  public string name,status,evidence;
  public string source="native-programmatic; NOT physical keyboard/mouse";
 }
 [Serializable] public sealed class Report {
  public string source="native-programmatic; NOT physical keyboard/mouse";
  public string scope="Own isolated diagnostic world only; no placement by this helper; original sandbox APIs provide explicitly labeled fixture stock outside this helper";
  public bool explicitBatch,explicitPointerTest,completed,nativeAccepted,normalRelease,clearAccepted;
  public int acceptedPackets,rejectedPackets,coordinateSamples;
  public float elapsedSeconds,maximumCanonicalCoordinateErrorPixels;
  public string nativeError;
  public List<Check> checks=new List<Check>();
 }
 static Report report;
 static readonly List<RaycastResult> hits=new List<RaycastResult>(32);
 static Vector2 currentPoint;
 static float deadline,started;
 static bool unavailable,ran;
 static string folder;
 static bool HasPointerTestFlag()=>DSPPadDiagnosticLaunch.NativePointerTestAllowed;

 static void Add(string name,string status,string evidence){
  report.checks.Add(new Check{name=name,status=status,evidence=evidence});
  Write();
 }
 static void Write(){
  if(report==null)return;
  report.elapsedSeconds=Time.realtimeSinceStartup-started;
  try{File.WriteAllText(Path.Combine(folder,"dsp-native-mouse-regression.json"),JsonUtility.ToJson(report,true));}
  catch(Exception e){Debug.LogWarning("DSP native mouse report: "+e.GetType().Name);}
 }
 static bool Send(Vector2 point,int mask,Vector2 motion,float scroll){
  currentPoint=point;
  if(unavailable||Time.realtimeSinceStartup>deadline)return false;
  try{
   int result=DSPAOTQueueTestPointer(Mathf.Clamp01(point.x/Screen.width),Mathf.Clamp01(point.y/Screen.height),mask,motion.x,motion.y,scroll);
   if(result==1){report.acceptedPackets++;report.nativeAccepted=true;return true;}
   report.rejectedPackets++;unavailable=true;report.nativeError="Native batch/foreground gate rejected the packet";
  }catch(Exception e){unavailable=true;report.nativeError=e.GetType().FullName+": "+e.Message;}
  return false;
 }
 static IEnumerator Hold(Vector2 point,int mask,float seconds){
  float end=Time.realtimeSinceStartup+seconds;
  do{if(!Send(point,mask,Vector2.zero,0))yield break;yield return null;}while(Time.realtimeSinceStartup<end);
  Vector3 actual=DSPPadInput.mousePosition;
  report.coordinateSamples++;
  report.maximumCanonicalCoordinateErrorPixels=Mathf.Max(report.maximumCanonicalCoordinateErrorPixels,Vector2.Distance(point,new Vector2(actual.x,actual.y)));
 }
 static IEnumerator Move(Vector2 from,Vector2 to,int mask,float seconds){
  float begin=Time.realtimeSinceStartup;
  Vector2 last=from;
  do{
   float t=Mathf.Clamp01((Time.realtimeSinceStartup-begin)/seconds);
   Vector2 next=Vector2.Lerp(from,to,t);
   if(!Send(next,mask,next-last,0))yield break;
   last=next;yield return null;
  }while(Time.realtimeSinceStartup-begin<seconds);
  Send(to,mask,to-last,0);yield return null;
 }
 static IEnumerator Wheel(Vector2 point,float wheel){
  if(!Send(point,0,Vector2.zero,wheel))yield break;
  yield return null;
  yield return Hold(point,0,.35f);
 }
 static IEnumerator Click(Vector2 point){
  yield return Hold(point,0,.25f);
  yield return Hold(point,1,.22f);
  yield return Hold(point,0,.25f);
 }
 static IEnumerator Escape(){
  yield return Hold(currentPoint,0,.22f);
  DSPPadInput.QueueEscape();
  yield return Hold(currentPoint,0,.5f);
 }
 static Graphic FirstGraphic(Vector2 point){
  var system=EventSystem.current;
  if(system==null)return null;
  var data=new PointerEventData(system){position=point};
  hits.Clear();system.RaycastAll(data,hits);
  for(int i=0;i<hits.Count;i++){
   var graphic=hits[i].gameObject.GetComponent<Graphic>();
   if(graphic!=null)return graphic;
  }
  return null;
 }
 static string HitName(Vector2 point){
  Graphic hit=FirstGraphic(point);
  if(hit==null)return "world/no Graphic hit";
  string name=hit.name;Transform parent=hit.transform.parent;
  for(int i=0;parent!=null&&i<4;i++,parent=parent.parent)name=parent.name+"/"+name;
  return name;
 }
 static bool PointForButton(Button button,out Vector2 point){
  point=Vector2.zero;
  if(button==null||!button.gameObject.activeInHierarchy||!button.IsInteractable())return false;
  var rect=button.transform as RectTransform;
  if(rect==null)return false;
  Canvas canvas=button.GetComponentInParent<Canvas>();
  Camera camera=canvas!=null&&canvas.renderMode!=RenderMode.ScreenSpaceOverlay?canvas.worldCamera:null;
  point=RectTransformUtility.WorldToScreenPoint(camera,rect.TransformPoint(rect.rect.center));
  if(point.x<2||point.y<2||point.x>Screen.width-2||point.y>Screen.height-2)return false;
  Graphic first=FirstGraphic(point);
  return first!=null&&(first.transform==button.transform||first.transform.IsChildOf(button.transform));
 }
 static bool FindPoint(Graphic exact,bool world,out Vector2 point){
  // This is a diagnostic search, not a gameplay UI exception. Exact first-hit
  // checks prevent clicks crossing a foreground menu or technology node.
  int[] order={5,4,6,3,7,2,8};
  for(int yi=0;yi<order.Length;yi++)for(int xi=0;xi<order.Length;xi++){
   Vector2 candidate=new Vector2(Screen.width*order[xi]*.1f,Screen.height*order[yi]*.1f);
   Graphic first=FirstGraphic(candidate);
   if(world?first==null:first==exact){point=candidate;return true;}
  }
  point=Vector2.zero;return false;
 }
 static Vector2 Offset(Vector2 point,float nx,float ny){
  return new Vector2(Mathf.Clamp(point.x+Screen.width*nx,Screen.width*.1f,Screen.width*.9f),Mathf.Clamp(point.y+Screen.height*ny,Screen.height*.1f,Screen.height*.9f));
 }
 static IEnumerator HIcon(UIGame ui){
  Vector2 point;
  Button button=ui.gameMenu==null?null:ui.gameMenu.button1;
  if(!PointForButton(button,out point)){Add("H menu icon","SKIPPED","Original H button is inactive, noninteractable, offscreen, or covered by a foreground Graphic");yield break;}
  if(Cursor.lockState==CursorLockMode.Locked){Add("H menu icon","SKIPPED","Original locked-cursor UGUI rule prevents pointer selection; no cursor rule bypass");yield break;}
  bool before=ui.gameMenu.detailFuncGroup.gameObject.activeSelf;
  int hand=GameMain.mainPlayer.inhandItemId;
  string first=HitName(point);
  yield return Click(point);
  bool after=ui.gameMenu.detailFuncGroup.gameObject.activeSelf;
  Add("H menu icon",after!=before?"PASS":"FAIL","First hit="+first+"; active="+before+" -> "+after+"; canonical coordinates delivered through native packet and BaseInput, no On_H_Switch call");
  Add("H foreground priority",GameMain.mainPlayer.inhandItemId==hand?"PASS":"FAIL","Validated first Graphic belongs to original H Button; hand item="+hand+" -> "+GameMain.mainPlayer.inhandItemId);
  if(after!=before){
   yield return DSPPadRenderDiagnostics.Capture("16-h-open");
   var menu=ui.gameMenu;int index=0;
   foreach(var ring in new[]{menu.button0,menu.button1,menu.button2,menu.button3,menu.button4,menu.button5,menu.buttonS}){
    Vector2 ringPoint;bool reachableRing=PointForButton(ring,out ringPoint);
    Add("H open ring hit "+index++,reachableRing?"PASS":"FAIL","center="+ringPoint+" first="+HitName(ringPoint));
   }
   Vector2 actual;
   bool reachable=PointForButton(button,out actual);
   Add("H reopened target geometry",reachable?"PASS":"FAIL","Original point="+point+" current center="+actual+"; old hit="+HitName(point)+"; new hit="+HitName(actual));
   if(reachable){yield return Click(actual);Add("H menu return",ui.gameMenu.detailFuncGroup.gameObject.activeSelf==before?"PASS":"FAIL","Second native UI click at current original Button center");}
  }
  int fastPassed=0;
  for(int i=0;i<4;i++){
   if(!PointForButton(button,out point))break;
   bool state=ui.gameMenu.detailFuncGroup.gameObject.activeSelf;
   Send(point,1,Vector2.zero,0);Send(point,0,Vector2.zero,0);
   yield return Hold(point,0,.12f);
   if(ui.gameMenu.detailFuncGroup.gameObject.activeSelf!=state)fastPassed++;
  }
  Add("H four short clicks",fastPassed==4?"PASS":"FAIL","Each down/up delivered between render samples; observed toggles="+fastPassed+"/4");
 }
 static IEnumerator Technology(UIGame ui){
  ui.OpenTechTree();yield return Hold(currentPoint,0,.6f);
  var tech=ui.techTree;
  var background=tech.transform.Find("BG");
  Graphic blank=background==null?null:background.GetComponent<Graphic>();
  Vector2 point;
  if(!tech.active||blank==null||!FindPoint(blank,false,out point)){
   Add("Tech blank pan and wheel","SKIPPED","No exact original TechTree/BG first-hit content point; foreground nodes/menus are not bypassed");
   if(tech.active)yield return Escape();yield break;
  }
  yield return Hold(point,0,.35f);
  RectTransform graph=tech.page==0?tech.graphGroup0:tech.graphGroup1;
  Vector2 before=graph.anchoredPosition;
  RTSPoser rts=GameCamera.instance==null?null:GameCamera.instance.rtsPoser;
  float yawBefore=rts==null?0:rts.yawWanted;
  float distanceBefore=rts==null?0:rts.distCoefWanted;
  bool fullBefore=VFInput.inFullscreenGUI;
  Vector2 end=Offset(point,.08f,.06f);
  // Drag begins ONLY on exact blank content. Hold repeats every rendered frame
  // to let the original fixed sampler and UpdateDrag observe the same gesture.
  yield return Hold(point,1,.25f);
  yield return Move(point,end,1,.4f);
  yield return Hold(end,1,.22f);
  yield return Hold(end,0,.3f);
  Vector2 after=graph.anchoredPosition;
  Add("Tech content pan",Vector2.Distance(before,after)>1?"PASS":"FAIL","Original graph anchoredPosition="+before+" -> "+after+"; mouseOp="+tech.mouseOpInTechTree+"; original hover-latch/UpdateDrag only");
  float scaleBefore=graph.localScale.x;
  yield return Wheel(end,-1);
  yield return Hold(end,0,.35f);
  float scaleOut=graph.localScale.x;
  // Original selected-node logic can consume the first zoom-out. A second
  // separately released wheel pulse observes the same original rule.
  if(Mathf.Abs(scaleOut-scaleBefore)<.01f){yield return Wheel(end,-1);yield return Hold(end,0,.35f);scaleOut=graph.localScale.x;}
  yield return Wheel(end,1);yield return Hold(end,0,.35f);
  float scaleBack=graph.localScale.x;
  Add("Tech wheel zoom",Mathf.Abs(scaleOut-scaleBefore)>.02f&&Mathf.Abs(scaleBack-scaleOut)>.02f?"PASS":"FAIL","Original scale="+scaleBefore+" -> "+scaleOut+" -> "+scaleBack+"; raw native wheel -1/neutral/+1, original .08 threshold and .16 s cooldown");
  if(rts!=null){
   bool protectedCamera=fullBefore&&VFInput.inFullscreenGUI&&Mathf.Abs(Mathf.DeltaAngle(yawBefore,rts.yawWanted))<.02f&&Mathf.Abs(distanceBefore-rts.distCoefWanted)<.0005f;
   Add("Fullscreen UI world-camera negative control",protectedCamera?"PASS":"FAIL","Fullscreen="+fullBefore+"/"+VFInput.inFullscreenGUI+"; world yaw="+yawBefore+" -> "+rts.yawWanted+"; world distCoef="+distanceBefore+" -> "+rts.distCoefWanted);
  }else Add("Fullscreen UI world-camera negative control","SKIPPED","RTS poser unavailable");
  yield return Escape();
  Add("Tech original Esc",!tech.active?"PASS":"FAIL","Original Escape key transport closes technology; no ShutTechTree callback");
 }
 static IEnumerator WorldCamera(){
  RTSPoser rts=GameCamera.instance==null?null:GameCamera.instance.rtsPoser;
  Vector2 point;
  if(rts==null||GameMain.mainPlayer.sailing||VFInput.inFullscreenGUI||GameMain.isPaused||!FindPoint(null,true,out point)){
   Add("World middle rotation and wheel","SKIPPED","Requires original ground RTS world, resumed, no fullscreen UI, and first-raycast-free point");yield break;
  }
  yield return Hold(point,0,.3f);
  float before=rts.yawWanted;
  Vector2 end=Offset(point,.05f,0);
  if(FirstGraphic(end)!=null){end=Offset(point,-.05f,0);}
  if(FirstGraphic(end)!=null){Add("World middle rotation","SKIPPED","No clear end point; foreground menus retain priority");yield break;}
  yield return Move(point,end,0,.3f);yield return Hold(end,0,.22f);
  Add("World no-rotate-button negative control",Mathf.Abs(Mathf.DeltaAngle(before,rts.yawWanted))<.02f?"PASS":"FAIL","Native motion with mask0 retains original yawWanted="+before+" -> "+rts.yawWanted+"; touch LookHeld="+DSPSmartTouchFrame.LookHeld);
  yield return Move(end,point,0,.3f);yield return Hold(point,0,.22f);
  before=rts.yawWanted;
  yield return Hold(point,4,.25f);
  yield return Move(point,end,4,.4f);
  yield return Hold(end,4,.25f);
  yield return Hold(end,0,.3f);
  float after=rts.yawWanted;
  Add("World middle rotation",Mathf.Abs(Mathf.DeltaAngle(before,after))>.2f?"PASS":"FAIL","Original RTS yawWanted="+before+" -> "+after+"; mask4 and canonical native dx; no camera method call or assignment");
  yield return Hold(end,4,.22f);yield return Move(end,point,4,.4f);yield return Hold(point,0,.3f);
  float distanceBefore=rts.distCoefWanted;
  yield return Wheel(point,1);float zoomIn=rts.distCoefWanted;
  yield return Wheel(point,-1);float zoomOut=rts.distCoefWanted;
  Add("World wheel zoom",Mathf.Abs(zoomIn-distanceBefore)>.0002f&&Mathf.Abs(zoomOut-zoomIn)>.0002f?"PASS":"FAIL","Original distCoefWanted="+distanceBefore+" -> "+zoomIn+" -> "+zoomOut+"; no distance assignment; endpoint clamps remain original");
 }
 static IEnumerator Construction(UIGame ui){
  Player player=GameMain.mainPlayer;
  PlanetFactory factory=GameMain.localPlanet==null?null:GameMain.localPlanet.factory;
  if(factory==null||player==null||player.sailing||player.inhandItemId!=0||!VFInput.readyToBuild||!ui.buildMenu.active||VFInput.inFullscreenGUI||GameMain.isPaused){
   Add("Construction preview","SKIPPED","Requires original empty hand, ground, loaded factory, readyToBuild, visible original build menu; state is not forced");yield break;
  }
  ItemProto chosen=null;int category=0,child=0;
  foreach(ItemProto item in LDB.items.dataArray){
   if(item==null||!item.CanBuild||!item.IsEntity||item.BuildMode!=1||item.prefabDesc==null||!GameMain.history.ItemUnlocked(item.ID)||player.package.GetItemCount(item.ID)<=0)continue;
   int cat=item.BuildIndex/100,idx=item.BuildIndex%100;
   if(cat<=0||cat>=ui.buildMenu.categoryButtons.Length||idx<=0||idx>=ui.buildMenu.childButtons.Length||cat>=9)continue;
   chosen=item;category=cat;child=idx;break;
  }
  if(chosen==null){Add("Construction preview","SKIPPED","No unlocked ordinary building already in actual inventory; no stock/tech injection");yield break;}
  Vector2 point;
  if(ui.buildMenu.currentCategory!=category){
   if(!PointForButton(ui.buildMenu.categoryButtons[category].button,out point)){Add("Construction menu","SKIPPED","Chosen original category button is not topmost/interactable");yield break;}
   yield return Click(point);
  }
  // Original childCanvas fades from -0.5 to >0.8 at4/s before interactable.
  // Respect that original animation; do not report an immediate click failure.
  yield return Hold(currentPoint,0,.4f);
  if(ui.buildMenu.currentCategory!=category||!PointForButton(ui.buildMenu.childButtons[child].button,out point)){Add("Construction menu","SKIPPED","Original child did not become visible/topmost; callbacks are not invoked");yield break;}
  int inventory=player.package.GetItemCount(chosen.ID),entities=factory.entityCursor,prebuilds=factory.prebuildCursor;
  yield return Click(point);
  bool selected=player.inhandItemId==chosen.ID;
  Add("Construction original menu selection",selected?"PASS":"FAIL","Item="+chosen.ID+"; actual hand="+player.inhandItemId+"; genuine category/child UI click, inventory count="+inventory);
  if(selected){
   Vector2 world;
   if(FindPoint(null,true,out world)){
    yield return Hold(world,0,.5f);
    BuildTool_Click click=player.controller.actionBuild.clickTool;
    Vector3 snappedA=click.castGroundPosSnapped;
    int countA=click.buildPreviews==null?0:click.buildPreviews.Count;
    Vector3 previewA=countA>0?click.buildPreviews[0].lpos:Vector3.zero;
    Vector2 second=Offset(world,.08f,.06f);
    if(FirstGraphic(second)==null){
     yield return Move(world,second,0,.25f);yield return Hold(second,0,.6f);
     int countB=click.buildPreviews==null?0:click.buildPreviews.Count;
     Vector3 previewB=countB>0?click.buildPreviews[0].lpos:Vector3.zero;
     bool moved=click.active&&click.castGround&&countA>0&&countB>0&&Vector3.Distance(snappedA,click.castGroundPosSnapped)>.05f&&Vector3.Distance(previewA,previewB)>.05f;
     Add("Construction world canonical position",moved?"PASS":"FAIL","Screen="+world+" -> "+second+"; ground="+snappedA+" -> "+click.castGroundPosSnapped+"; preview="+previewA+" -> "+previewB+"; counts="+countA+"/"+countB+"; condition="+(countB>0?click.buildPreviews[0].condition.ToString():"none")+"; world mask0 only, no placement");
    }else Add("Construction world canonical position","SKIPPED","Second world point is covered by original UI; no bypass");
   }else Add("Construction world canonical position","SKIPPED","No uncovered world point");
   yield return Escape();
   Add("Construction original Esc cancellation",player.inhandItemId==0?"PASS":"FAIL","Original hand after Esc="+player.inhandItemId+"; no SetHandItems cancellation call");
  }
  bool unchanged=player.package.GetItemCount(chosen.ID)==inventory&&factory.entityCursor==entities&&factory.prebuildCursor==prebuilds;
  Add("Construction no-placement negative control",unchanged?"PASS":"FAIL","Item="+inventory+" -> "+player.package.GetItemCount(chosen.ID)+"; entityCursor="+entities+" -> "+factory.entityCursor+"; prebuildCursor="+prebuilds+" -> "+factory.prebuildCursor+"; no save performed");
 }
 static IEnumerator Sequence(){
  UIGame ui=UIRoot.instance.uiGame;
  yield return Hold(currentPoint,0,.3f);
  if(unavailable)yield break;
  yield return HIcon(ui);
  if(unavailable)yield break;
  yield return Technology(ui);
  if(unavailable)yield break;
  yield return WorldCamera();
  if(unavailable)yield break;
  yield return Construction(ui);
  yield return Hold(currentPoint,0,.35f);
  report.normalRelease=DSPPadInput.ButtonMask==0;
  Add("Native canonical coordinates",report.maximumCanonicalCoordinateErrorPixels<=2?"PASS":"FAIL","Settled samples="+report.coordinateSamples+"; maximum requested/DSP position error="+report.maximumCanonicalCoordinateErrorPixels+" px; valid="+DSPPadInput.NativePositionValid+"; diagnosticSource="+DSPPadInput.DiagnosticPointerSource);
  Add("Keyboard physical coverage","UNVERIFIED","Programmatic pointer packets do not prove UC/USB/Bluetooth/physical buttons, WASD-followed rotation, modifiers, wheel detents, or handoff continuity. Actual physical transport remains unverified; autonomous validation records this limit.");
 }
 public static IEnumerator Run(){
  // The caller must invoke this only in its own isolated diagnostic world.
  // No persistent command or normal launch can enable native injection.
  if(ran||!DSPPadDiagnosticLaunch.AutomaticActionsAllowed||!HasPointerTestFlag())yield break;
  ran=true;started=Time.realtimeSinceStartup;deadline=started+45;
  folder=Application.persistentDataPath;report=new Report{explicitBatch=true,explicitPointerTest=true};
  currentPoint=new Vector2(Screen.width*.5f,Screen.height*.5f);
  if(!GameMain.isRunning||DSPGame.IsMenuDemo||GameMain.mainPlayer==null||UIRoot.instance==null||UIRoot.instance.uiGame==null){Add("World preflight","SKIPPED","Isolated playable diagnostic world unavailable");Write();yield break;}
  var stack=new Stack<IEnumerator>();stack.Push(Sequence());
  try{
   while(stack.Count>0&&!unavailable&&Time.realtimeSinceStartup<deadline){
    object next=null;bool advance=false;Exception error=null;
    try{advance=stack.Peek().MoveNext();if(advance)next=stack.Peek().Current;}
    catch(Exception e){error=e;}
    if(error!=null){Add("Diagnostic exception","FAIL",error.GetType().FullName+": "+error.Message);break;}
    if(!advance){var done=stack.Pop() as IDisposable;if(done!=null)done.Dispose();continue;}
    var nested=next as IEnumerator;
    if(nested!=null){stack.Push(nested);continue;}
    yield return next;
   }
   report.completed=stack.Count==0&&!unavailable;
   if(Time.realtimeSinceStartup>=deadline)Add("Batch time bound","SKIPPED","45 second bound reached; remaining assertions not executed");
   // Error/skip cleanup also travels through the original Esc key. Stop before
   // queuing any further Esc once owned test UI/hand has gone, to avoid pause.
   if(!unavailable){
    deadline=Time.realtimeSinceStartup+3;
    for(int attempt=0;attempt<3&&(UIRoot.instance.uiGame.techTree.active||GameMain.mainPlayer.inhandItemId!=0);attempt++){
     DSPPadInput.QueueEscape();
     float escapeEnd=Time.realtimeSinceStartup+.6f;
     do{Send(currentPoint,0,Vector2.zero,0);yield return null;}while(Time.realtimeSinceStartup<escapeEnd&&!unavailable);
    }
    Add("Original Esc cleanup",!UIRoot.instance.uiGame.techTree.active&&GameMain.mainPlayer.inhandItemId==0?"PASS":"FAIL","Technology active="+UIRoot.instance.uiGame.techTree.active+"; hand item="+GameMain.mainPlayer.inhandItemId+"; no direct UI close or hand assignment");
   }
   // Let original UGUI and fixed input observe an ordinary button-up before
   // ending this source permanently and handing the device back to the user.
   if(!unavailable){
    float releaseEnd=Time.realtimeSinceStartup+.35f;
    deadline=releaseEnd+.2f;
    do{Send(currentPoint,0,Vector2.zero,0);yield return null;}while(Time.realtimeSinceStartup<releaseEnd&&!unavailable);
    report.normalRelease=DSPPadInput.ButtonMask==0;
   }
  }finally{
   try{report.clearAccepted=DSPAOTClearTestPointer()==1;}catch(Exception e){report.nativeError=(report.nativeError??"")+"; clear "+e.GetType().FullName;}
   while(stack.Count>0){var disposable=stack.Pop() as IDisposable;if(disposable!=null)disposable.Dispose();}
   Write();
  }
 }
}
