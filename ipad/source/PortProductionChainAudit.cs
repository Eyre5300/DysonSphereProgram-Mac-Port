using System;
using System.Collections;
using System.Collections.Generic;
using System.IO;
using UnityEngine;
// Dedicated generated world only. Construction connections are fixtures;
// all mined material, belt movement, sorting and production use normal ticks.
public static class PortProductionChainAudit {
 static PlanetFactory F=>GameMain.localPlanet.factory;
 static Vector3 origin,right,forward;
 static int miner,smelter,assembler,box;static readonly List<int> veins=new List<int>(),belts=new List<int>(),sorters=new List<int>();
 static string FileName=>Path.Combine(Application.persistentDataPath,"production-chain-audit.txt");
 public static bool Passed {get;private set;}
 static void Note(string s){File.AppendAllText(FileName,s+"\n");}
 static Vector3 Pos(float x,float y,float lift=.05f){var d=(origin+right*x+forward*y).normalized;return d*(GameMain.localPlanet.data.QueryHeight(d)+lift);}
 static Quaternion Rot(Vector3 p){return Quaternion.LookRotation(Vector3.ProjectOnPlane(forward,p.normalized),p.normalized);}
 static int Build(int proto,float x,float y,int[] pars=null,int filter=0,int recipe=0,int input=0,int inputSlot=-1,int output=0,Vector3? end=null){
  var item=LDB.items.Select(proto);if(item==null||!item.IsEntity)throw new Exception("Invalid building "+proto);
  var pos=Pos(x,y,item.prefabDesc.isBelt?.15f:.05f);var rot=Rot(pos);
  var pre=new PrebuildData{protoId=(short)proto,modelIndex=(short)item.ModelIndex,pos=pos,rot=rot,pos2=end??pos,rot2=end.HasValue?Rot(end.Value):rot,itemRequired=0,parameters=pars,paramCount=pars==null?0:pars.Length,filterId=filter,recipeId=recipe};
  int id=F.AddPrebuildDataWithComponents(pre);
  if(input>0)F.WriteObjectConn(-id,1,false,input,inputSlot);
  if(output>0)F.WriteObjectConn(-id,0,true,output,-1);
  F.BuildFinally(GameMain.mainPlayer,id);
  int entity=0;for(int i=1;i<F.entityCursor;i++)if(F.entityPool[i].id==i&&F.entityPool[i].protoId==proto&&(F.entityPool[i].pos-pos).sqrMagnitude<.01f)entity=i;
  if(entity==0)throw new Exception("Construction failed "+proto);
  var e=F.entityPool[entity];Note("build "+proto+" "+item.name+" entity="+entity+" model="+e.modelId+" input="+input+" output="+output);return entity;
 }
 static int Recipe(int product,ERecipeType type){foreach(var r in LDB.recipes.dataArray)if(r.Type==type&&r.Results.Length==1&&r.Results[0]==product&&r.Items.Length==1)return r.ID;throw new Exception("recipe missing");}
 static long Ore(){long n=0;foreach(int v in veins)n+=F.veinPool[v].amount;return n;}
 static int Gears(){return F.factoryStorage.storagePool[F.entityPool[box].storageId].GetItemCount(1201);}
 static void Snapshot(string phase){
  var fs=F.factorySystem;var m=fs.minerPool[F.entityPool[miner].minerId];var s=fs.assemblerPool[F.entityPool[smelter].assemblerId];var a=fs.assemblerPool[F.entityPool[assembler].assemblerId];
  Note(phase+" tick="+GameMain.gameTick+" ore="+Ore()+" veins="+m.veinCount+" minerBuffer="+m.productCount+" minerOut="+m.insertTarget+" smeltServed="+s.served[0]+" smeltProduced="+s.produced[0]+" asmServed="+a.served[0]+" asmProduced="+a.produced[0]+" storedGears="+Gears());
  foreach(int e in sorters){var i=fs.inserterPool[F.entityPool[e].inserterId];int net=F.powerSystem.consumerPool[i.pcId].networkId;Note("sorter="+e+" pick="+i.pickTarget+" insert="+i.insertTarget+" stage="+i.stage+" item="+i.itemId+" count="+i.itemCount+" power="+F.powerSystem.networkServes[net]);}
 }
 static void Setup(){
  veins.Clear();belts.Clear();sorters.Clear();int nearest=0;float dist=float.MaxValue;
  for(int i=1;i<F.veinCursor;i++){var v=F.veinPool[i];if(v.id!=i||v.type!=EVeinType.Iron||v.amount<1000)continue;float d=(v.pos-GameMain.mainPlayer.position).sqrMagnitude;if(d<dist){dist=d;nearest=i;}}
  if(nearest==0)throw new Exception("No iron vein");
  origin=F.veinPool[nearest].pos;var up=origin.normalized;right=Vector3.Cross(up,Vector3.forward).normalized;if(right.sqrMagnitude<.5f)right=Vector3.Cross(up,Vector3.right).normalized;forward=Vector3.Cross(right,up).normalized;
  var mp=Pos(0,4);var pose=new Pose(mp,Rot(mp));var desc=LDB.items.Select(2301).prefabDesc;
  for(int i=1;i<F.veinCursor;i++){var v=F.veinPool[i];if(v.id==i&&v.type==EVeinType.Iron&&v.amount>1000&&MinerComponent.IsTargetVeinInRange(v.pos,pose,desc))veins.Add(i);}
  if(veins.Count==0)throw new Exception("Miner fixture has no vein in range");
  GameMain.mainPlayer.position=Pos(5,6);GameMain.mainPlayer.uPosition=Maths.QRotateLF(GameMain.localPlanet.runtimeRotation,GameMain.mainPlayer.position)+GameMain.localPlanet.uPosition;
  foreach(var p in new[]{new Vector2(-6,0),new Vector2(-6,8),new Vector2(-6,16),new Vector2(10,0),new Vector2(10,18)})Build(2203,p.x,p.y);
  Build(2201,0,8);Build(2201,7,7);
  miner=Build(2301,0,4,veins.ToArray(),1001);
  int previous=miner;
  for(int y=7;y<=13;y++){int b=Build(2001,0,y,input:previous,inputSlot:previous==miner?0:0);belts.Add(b);previous=b;}
  smelter=Build(2302,3,13,recipe:Recipe(1101,ERecipeType.Smelt));assembler=Build(2303,7,13,recipe:Recipe(1201,ERecipeType.Assemble));box=Build(2101,11,13);
  sorters.Add(Build(2011,0,13,new[]{2},input:previous,output:smelter,end:Pos(2,13)));
  sorters.Add(Build(2011,4,13,new[]{2},input:smelter,output:assembler,end:Pos(6,13)));
  sorters.Add(Build(2011,8,13,new[]{2},input:assembler,output:box,end:Pos(10,13)));
  foreach(int e in belts){var b=F.cargoTraffic.beltPool[F.entityPool[e].beltId];Note("belt="+e+" path="+b.segPathId+" pivot="+b.pivotOnPath+" output="+b.outputId+" input="+b.backInputId);}
 }
 static IEnumerator Run(){
  Passed=false;File.WriteAllText(FileName,"Real iron veins -> miner -> seven belts -> sorter -> smelter -> sorter -> assembler -> sorter -> storage. No item injection or hand transfer. Original construction APIs; pointer placement not tested.\n");Setup();
  long ore=Ore(),tick=GameMain.gameTick;float deadline=Time.realtimeSinceStartup+100;Snapshot("start");
  while(Time.realtimeSinceStartup<deadline&&Gears()<8){yield return new WaitForSecondsRealtime(5);Snapshot("producing");}
  bool production=Gears()>=8&&Ore()<ore&&GameMain.gameTick>tick;Note("continuousProductionPassed="+production);
  yield return new WaitForEndOfFrame();var image=ScreenCapture.CaptureScreenshotAsTexture();File.WriteAllBytes(Path.Combine(Application.persistentDataPath,"production-chain.png"),image.EncodeToPNG());UnityEngine.Object.Destroy(image);yield return null;
  if(!production)yield break;
  int before=Gears();long beforeOre=Ore();bool save=GameSave.SaveCurrentGame("PortFactory-ContinuousChain");Note("saved="+save+" stored="+before+" ore="+beforeOre);if(!save)yield break;
  DSPGame.StartGame("PortFactory-ContinuousChain");yield return null;deadline=Time.realtimeSinceStartup+180;
  while((!GameMain.isRunning||DSPGame.IsMenuDemo||GameMain.localPlanet==null||!GameMain.localPlanet.factoryLoaded)&&Time.realtimeSinceStartup<deadline)yield return new WaitForSecondsRealtime(1);
  if(!GameMain.isRunning||DSPGame.IsMenuDemo){Note("reload_timeout");yield break;}
  Snapshot("reloaded");bool preserved=Gears()>=before&&Ore()<=beforeOre;deadline=Time.realtimeSinceStartup+80;
  while(Time.realtimeSinceStartup<deadline&&Gears()<before+4){yield return new WaitForSecondsRealtime(5);Snapshot("afterReload");}
  Passed=preserved&&Gears()>=before+4&&Ore()<beforeOre;Note("reloadAndContinuedProductionPassed="+Passed);
  yield return new WaitForEndOfFrame();image=ScreenCapture.CaptureScreenshotAsTexture();File.WriteAllBytes(Path.Combine(Application.persistentDataPath,"production-chain-reloaded.png"),image.EncodeToPNG());UnityEngine.Object.Destroy(image);yield return null;
 }
 public static IEnumerator SafeRun(){var run=Run();while(true){object next=null;bool more=false;Exception failure=null;try{more=run.MoveNext();if(more)next=run.Current;}catch(Exception e){failure=e;}if(failure!=null){Note("FAIL "+failure);Debug.LogError("Production chain audit: "+failure);break;}if(!more)break;yield return next;}var dispose=run as IDisposable;if(dispose!=null)dispose.Dispose();}
}
