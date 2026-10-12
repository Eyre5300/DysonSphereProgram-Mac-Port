using System;using System.Collections;using System.IO;using UnityEngine;
public static class PortScienceLogisticsAudit {
 static PlanetFactory F=>GameMain.localPlanet.factory;static Vector3 origin,right,forward;static int lab,source,dest,tech;static int matrices,initialPoints;static bool sawFlight;public static bool Passed{get;private set;}
 static string LogPath=>Path.Combine(Application.persistentDataPath,"science-logistics-audit.txt");static void Note(string s){File.AppendAllText(LogPath,s+"\n");}
 static Vector3 Pos(float x,float y){var n=(origin+right*x+forward*y).normalized;return n*(GameMain.localPlanet.data.QueryHeight(n)+.05f);}
 static int Build(int proto,float x,float y){var item=LDB.items.Select(proto);var p=Pos(x,y);var pre=new PrebuildData{protoId=(short)proto,modelIndex=(short)item.ModelIndex,pos=p,rot=Quaternion.LookRotation(Vector3.ProjectOnPlane(forward,p.normalized),p.normalized),itemRequired=0};int id=F.AddPrebuildDataWithComponents(pre);F.BuildFinally(GameMain.mainPlayer,id);for(int i=1;i<F.entityCursor;i++)if(F.entityPool[i].id==i&&F.entityPool[i].protoId==proto&&(F.entityPool[i].pos-p).sqrMagnitude<.01f){Note("build "+proto+" "+item.name+" entity="+i+" model="+F.entityPool[i].modelId);return i;}throw new Exception("Build failed "+proto);}
 static StationComponent Station(int e)=>F.transport.stationPool[F.entityPool[e].stationId];
 static LabComponent Lab()=>F.factorySystem.labPool[F.entityPool[lab].labId];
 static void Configure(int e,ELogisticStorage direction,int max){F.transport.SetStationStorage(F.entityPool[e].stationId,0,1101,max,direction,ELogisticStorage.None,GameMain.mainPlayer);}
 static void Setup(){
  origin=GameMain.mainPlayer.position;var up=origin.normalized;right=Vector3.Cross(up,Vector3.forward).normalized;if(right.sqrMagnitude<.5f)right=Vector3.Cross(up,Vector3.right).normalized;forward=Vector3.Cross(right,up).normalized;
  Build(2203,-8,10);Build(2203,8,10);Build(2203,0,20);Build(2201,0,14);lab=Build(2901,0,10);
  TechProto selected=null;foreach(var t in LDB.techs.dataArray)if(t.Published&&!t.IsHiddenTech&&!t.IsObsolete&&t.IsLabTech&&t.Items.Length==1&&t.Items[0]==6001&&t.UnlockRecipes.Length>0&&!GameMain.history.TechUnlocked(t.ID)&&(selected==null||t.HashNeeded<selected.HashNeeded))selected=t;
  if(selected==null)throw new Exception("No suitable blue-matrix research");tech=selected.ID;
  foreach(int pre in selected.PreTechs)GameMain.history.UnlockTechUnlimitedWithAllPre(pre);foreach(int pre in selected.PreTechsImplicit)GameMain.history.UnlockTechUnlimitedWithAllPre(pre);
  if(GameMain.history.TechUnlocked(tech))throw new Exception("Target research unexpectedly already unlocked");
  GameMain.history.EnqueueTech(tech);if(GameMain.history.currentTech!=tech)throw new Exception("Research did not enter queue");
  F.factorySystem.labPool[F.entityPool[lab].labId].SetFunction(true,0,tech,F.entitySignPool);
  matrices=Math.Min(250,Math.Max(20,(int)Math.Ceiling((double)selected.HashNeeded*selected.ItemPoints[0]/3600)+2));
  Note("target="+tech+" "+selected.name+" hashNeeded="+selected.HashNeeded+" pointPerHash="+selected.ItemPoints[0]+" fixtureMatrices="+matrices+" prerequisitesGranted=true targetGranted=false recipes="+string.Join(",",selected.UnlockRecipes));
  source=Build(2103,-22,38);dest=Build(2103,22,38);Configure(source,ELogisticStorage.Supply,200);Configure(dest,ELogisticStorage.Demand,80);
  var a=Station(source);var b=Station(dest);a.storage[0].count=200;a.idleDroneCount=3;a.energy=a.energyMax;b.energy=b.energyMax;F.transport.RefreshStationTraffic();
  Note("logistics fixture: 200 iron in source, 3 drones, both stations initially charged; no direct destination changes or forced drone movement; demand80 initially");
 }
 static void Snapshot(string phase){var a=Station(source);var b=Station(dest);var l=Lab();var t=GameMain.history.TechState(tech);int net=F.powerSystem.consumerPool[l.pcId].networkId;Note(phase+" tick="+GameMain.gameTick+" hash="+t.hashUploaded+"/"+t.hashNeeded+" unlocked="+t.unlocked+" matrixPoints="+l.matrixServed[0]+" labPower="+F.powerSystem.networkServes[net]+" source="+a.storage[0].count+" dest="+b.storage[0].count+" flying="+a.workDroneCount+" idle="+a.idleDroneCount+" pairs="+a.localPairCount+" energy="+a.energy);}
 static IEnumerator Run(){
  Passed=false;sawFlight=false;File.WriteAllText(LogPath,"Independent test world; prerequisite techs, blue matrices, station stock, drones and initial charge are fixtures. Research completion and drone deliveries must use normal game ticks.\n");Setup();yield return new WaitForSecondsRealtime(1);
  int inserted=F.InsertInto(lab,0,6001,(byte)matrices,0,out var _);if(inserted!=matrices)throw new Exception("Lab fixture feed rejected "+inserted);initialPoints=Lab().matrixServed[0];Snapshot("start");float end=Time.realtimeSinceStartup+180;bool captured=false;int iteration=0;
  while(Time.realtimeSinceStartup<end&&(!GameMain.history.TechUnlocked(tech)||Station(dest).storage[0].count<80||Station(source).workDroneCount>0)){
   yield return new WaitForSecondsRealtime(1);sawFlight|=Station(source).workDroneCount>0;if(++iteration%5==0)Snapshot("running");
   if(!captured&&Station(source).workDroneCount>0){captured=true;yield return new WaitForEndOfFrame();var tex=ScreenCapture.CaptureScreenshotAsTexture();File.WriteAllBytes(Path.Combine(Application.persistentDataPath,"science-logistics-flight.png"),tex.EncodeToPNG());UnityEngine.Object.Destroy(tex);yield return null;}
  }
  var tp=LDB.techs.Select(tech);bool recipes=true;foreach(int r in tp.UnlockRecipes)recipes&=GameMain.history.RecipeUnlocked(r);
  bool research=GameMain.history.TechUnlocked(tech)&&Lab().matrixServed[0]<initialPoints&&recipes;
  bool delivery=sawFlight&&Station(dest).storage[0].count>=80&&Station(source).storage[0].count>0&&Station(dest).storage[0].count+Station(source).storage[0].count==200&&Station(source).workDroneCount==0&&Station(source).idleDroneCount==3;
  Snapshot("beforeSave");Note("researchPassed="+research+" unlockedRecipes="+recipes+" matrixPointsConsumed="+(initialPoints-Lab().matrixServed[0])+" firstDeliveryPassed="+delivery);
  if(!research||!delivery)yield break;int savedSource=Station(source).storage[0].count,savedDest=Station(dest).storage[0].count;bool saved=GameSave.SaveCurrentGame("PortScience-Logistics");Note("saved="+saved);if(!saved)yield break;
  DSPGame.StartGame("PortScience-Logistics");yield return null;end=Time.realtimeSinceStartup+180;while((!GameMain.isRunning||DSPGame.IsMenuDemo||GameMain.localPlanet==null||!GameMain.localPlanet.factoryLoaded)&&Time.realtimeSinceStartup<end)yield return new WaitForSecondsRealtime(1);
  if(!GameMain.isRunning||DSPGame.IsMenuDemo){Note("reload timeout");yield break;}Snapshot("reloaded");bool preserved=GameMain.history.TechUnlocked(tech)&&Station(dest).storage[0].count==savedDest&&Station(source).storage[0].count==savedSource&&Station(source).idleDroneCount==3;
  Configure(dest,ELogisticStorage.Demand,200);end=Time.realtimeSinceStartup+120;while(Time.realtimeSinceStartup<end&&(Station(dest).storage[0].count<200||Station(source).workDroneCount>0)){yield return new WaitForSecondsRealtime(5);Snapshot("afterReload");}
  Passed=preserved&&Station(dest).storage[0].count==200&&Station(source).storage[0].count==0&&Station(source).workDroneCount==0&&Station(source).idleDroneCount==3;Note("reloadAndResumedDeliveryPassed="+Passed);
  yield return new WaitForEndOfFrame();var image=ScreenCapture.CaptureScreenshotAsTexture();File.WriteAllBytes(Path.Combine(Application.persistentDataPath,"science-logistics-reloaded.png"),image.EncodeToPNG());UnityEngine.Object.Destroy(image);yield return null;
 }
 public static IEnumerator SafeRun(){var run=Run();while(true){object next=null;bool more=false;Exception failure=null;try{more=run.MoveNext();if(more)next=run.Current;}catch(Exception e){failure=e;}if(failure!=null){Note("FAIL "+failure);Debug.LogError("Science/logistics audit: "+failure);break;}if(!more)break;yield return next;}((IDisposable)run).Dispose();}
}
