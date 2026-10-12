using System;
using System.Collections;
using System.Collections.Generic;
using System.IO;
using System.Runtime.InteropServices;
using UnityEngine;
using UnityEngine.EventSystems;

// Explicit diagnostic world only. Fixtures use original construction and power simulation.
public static class DSPPadPowerAudit {
 const string Native="@rpath/UnityFramework.framework/UnityFramework";
 [DllImport(Native)] static extern int DSPAOTQueueTestKey(int code,int pressed);
 [DllImport(Native)] static extern int DSPAOTQueueTestPointer(float x,float y,int buttons,float dx,float dy,float wheel);
 [Serializable] public class State {
  public string phase,click;
  public bool graph,escVisible,fpsVisible,gpuSignsMatch,coverBufferMatches;
  public ulong appMemory;
  public uint[] signs;
  public float[] serves;
 }
 [Serializable] public class Report {
  public string buildVersion=DSPPadDiagnosticLaunch.BuildVersion,batchIdentifier=DSPPadDiagnosticLaunch.BatchIdentifier;
  public bool completed,fixturesRemoved;
  public List<string> errors=new List<string>();
  public List<State> states=new List<State>();
 }
 static Report report;
 static Vector3 origin,right,forward;
 static Vector2 pointer=new Vector2(.5f,.5f);
 static int mask,connected,isolated,generator;
 static readonly List<int> fixtures=new List<int>();
 static string click;
 static bool oldGraph,oldSigns,oldIcons,oldEntitySigns;
 static PlanetFactory F=>GameMain.localPlanet.factory;
 public static bool Passed=>report!=null&&report.completed&&report.fixturesRemoved&&report.errors.Count==0;
 static void Check(bool value,string message){if(!value)report.errors.Add(message);}
 static void Write(){File.WriteAllText(Path.Combine(Application.persistentDataPath,"power-audit.json"),JsonUtility.ToJson(report,true));}
 static IEnumerator Wait(float seconds){
  float end=Time.realtimeSinceStartup+seconds;
  do {if(DSPAOTQueueTestPointer(pointer.x,pointer.y,mask,0,0,0)!=1)throw new Exception("Native pointer rejected");yield return null;}while(Time.realtimeSinceStartup<end);
 }
 static int Build(int id,float x,float y){
  var item=LDB.items.Select(id);var n=(origin+right*x+forward*y).normalized;
  var pos=n*(GameMain.localPlanet.data.QueryHeight(n)+.05f);
  var pre=new PrebuildData{protoId=(short)id,modelIndex=(short)item.ModelIndex,pos=pos,rot=Quaternion.LookRotation(Vector3.ProjectOnPlane(forward,n),n),itemRequired=0};
  int preId=F.AddPrebuildDataWithComponents(pre);F.BuildFinally(GameMain.mainPlayer,preId);
  for(int i=1;i<F.entityCursor;i++)if(F.entityPool[i].id==i&&F.entityPool[i].protoId==id&&(F.entityPool[i].pos-pos).sqrMagnitude<.01f){fixtures.Add(i);return i;}
  throw new Exception("Fixture build failed "+id);
 }
 static void Snapshot(string phase){
  var model=GameMain.localPlanet.factoryModel;var renderer=model.powerSystemRenderer;
  var signs=new SignData[model.entitySignBuffer.count];model.entitySignBuffer.GetData(signs);
  var covers=new PowerDiskRD[renderer.coverBuffer.count];renderer.coverBuffer.GetData(covers);
  bool equal=true;for(int i=0;i<Math.Min(covers.Length,renderer.coverArr.Length);i++)equal&=covers[i].Equals(renderer.coverArr[i]);
  var fps=UIRoot.instance.GetComponentInChildren<UIFpsStat>(true);
  var state=new State{phase=phase,click=click,graph=PowerSystemRenderer.powerGraphOn,escVisible=DSPPadEscapeButton.Visible,fpsVisible=fps&&fps.fpsTextComp&&fps.fpsTextComp.gameObject.activeInHierarchy,appMemory=DSPPadPerformanceHUD.Bytes,signs=new[]{F.entitySignPool[connected].signType,F.entitySignPool[isolated].signType},serves=(float[])F.powerSystem.networkServes.Clone(),gpuSignsMatch=signs[connected].signType==F.entitySignPool[connected].signType&&signs[isolated].signType==F.entitySignPool[isolated].signType,coverBufferMatches=equal};
  Check(state.gpuSignsMatch&&state.coverBufferMatches,phase+" GPU data mismatch");Check(!state.escVisible&&state.fpsVisible&&state.appMemory>0,phase+" performance/ESC visibility mismatch");
  Check(state.signs[1]==SignData.NO_POWER_CONN,phase+" isolated warning missing");
  report.states.Add(state);Write();
 }
 static IEnumerator Capture(string phase){yield return Wait(1);yield return new WaitForEndOfFrame();Snapshot(phase);yield return DSPPadRenderDiagnostics.Capture("power-"+phase);}
 static IEnumerator Key(KeyCode key){Check(DSPAOTQueueTestKey(DSPPadKeyboard.HID(key),1)==1&&DSPAOTQueueTestKey(DSPPadKeyboard.HID(key),0)==1,"Native key rejected");yield return Wait(.4f);}
 static IEnumerator ClickPower(){
  yield return Key(KeyCode.H);
  var menu=UIRoot.instance.uiGame.gameMenu;var rt=menu.dfPowerButton.button.transform as RectTransform;var canvas=rt.GetComponentInParent<Canvas>();
  var xy=RectTransformUtility.WorldToScreenPoint(canvas.renderMode==RenderMode.ScreenSpaceOverlay?null:canvas.worldCamera,rt.TransformPoint(rt.rect.center));
  var hits=new List<RaycastResult>();EventSystem.current.RaycastAll(new PointerEventData(EventSystem.current){position=xy},hits);
  click="group="+menu.detailFuncGroup.gameObject.activeInHierarchy+" button="+rt.gameObject.activeInHierarchy+" point="+xy+" hits=";
  foreach(var h in hits)click+=h.gameObject.name+"/";
  bool before=PowerSystemRenderer.powerGraphOn;
  pointer=new Vector2(xy.x/Screen.width,xy.y/Screen.height);mask=0;yield return Wait(.25f);mask=1;yield return Wait(.22f);mask=0;yield return Wait(.25f);
  Check(PowerSystemRenderer.powerGraphOn!=before,"H power button did not toggle");yield return Key(KeyCode.H);
 }
 static IEnumerator Body(){
  DSPPadBatchFixture.Prepare();origin=GameMain.mainPlayer.position;var up=origin.normalized;right=Vector3.Cross(up,Vector3.forward).normalized;forward=Vector3.Cross(right,up).normalized;
  Build(2201,0,10);connected=Build(2302,3,12);isolated=Build(2302,-16,4);yield return Wait(3);
  EntitySignRenderer.entitySignOn=true;EntitySignRenderer.showSign=true;EntitySignRenderer.showIcon=true;PowerSystemRenderer.powerGraphOn=false;
  yield return Capture("off");Check(F.entitySignPool[connected].signType==SignData.NO_POWER,"Connected unpowered warning missing");
  yield return ClickPower();Check(PowerSystemRenderer.powerGraphOn,"H enable failed");yield return Capture("on-no-power");
  yield return ClickPower();Check(!PowerSystemRenderer.powerGraphOn,"H disable failed");yield return Capture("off-again");yield return ClickPower();
  generator=Build(2203,0,16);int gid=F.entityPool[generator].powerGenId,cid=F.entityPool[connected].powerConId;
  // Diagnostic load only, removed before the next regression phase.
  F.powerSystem.consumerPool[cid].idleEnergyPerTick=10000;
  F.powerSystem.genPool[gid].genEnergyPerTick=(long)(3000/Math.Max(.1f,GameMain.localPlanet.windStrength));
  yield return Wait(3);yield return Capture("low-power");Check(F.entitySignPool[connected].signType==SignData.LOW_POWER,"Original low power simulation did not produce warning3");
  F.powerSystem.genPool[gid].genEnergyPerTick=10000000;yield return Wait(3);yield return Capture("powered");
  var sign=F.entitySignPool[connected].signType;Check(sign!=SignData.LOW_POWER&&sign!=SignData.NO_POWER&&sign!=SignData.NO_POWER_CONN,"Adequate supply retained power warning");
 }
 static void Cleanup(){
  for(int i=fixtures.Count-1;i>=0;i--){int id=fixtures[i];if(F.entityPool[id].id==id)F.RemoveEntityWithComponents(id,false);}
  report.fixturesRemoved=true;foreach(int id in fixtures)report.fixturesRemoved&=F.entityPool[id].id!=id;
  PowerSystemRenderer.powerGraphOn=oldGraph;EntitySignRenderer.showSign=oldSigns;EntitySignRenderer.showIcon=oldIcons;EntitySignRenderer.entitySignOn=oldEntitySigns;
  mask=0;DSPAOTQueueTestPointer(.5f,.5f,0,0,0,0);DSPPadInput.ResetInputAxes();
 }
 public static IEnumerator Run(){
  if(!DSPPadDiagnosticLaunch.PowerAuditRequested)yield break;
  report=new Report();fixtures.Clear();oldGraph=PowerSystemRenderer.powerGraphOn;oldSigns=EntitySignRenderer.showSign;oldIcons=EntitySignRenderer.showIcon;oldEntitySigns=EntitySignRenderer.entitySignOn;Write();
  var stack=new Stack<IEnumerator>();stack.Push(Body());
  while(stack.Count>0){bool more;object value=null;try{more=stack.Peek().MoveNext();if(more)value=stack.Peek().Current;}catch(Exception e){report.errors.Add(e.ToString());break;}if(!more){stack.Pop();continue;}if(value is IEnumerator){stack.Push((IEnumerator)value);continue;}yield return value;}
  try{Cleanup();}catch(Exception e){report.errors.Add("Cleanup: "+e);}
  report.completed=true;Write();
 }
}
