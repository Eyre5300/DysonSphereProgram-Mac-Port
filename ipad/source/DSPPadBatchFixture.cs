using System;using System.IO;using System.Collections;using UnityEngine;
// Only the explicitly opted-in, previously created diagnostic world is used.
// Fixture setup calls the original tech/inventory APIs, never changes rules.
public static class DSPPadBatchFixture {
 [Serializable] sealed class Report {public string source="PROGRAMMATIC TEST FIXTURE: technology/items supplied, not natural progression proof",save,status;public bool saved,reloaded,inventoryExact;public long beforeTick,afterTick;public int seed;public int[] itemIDs={2001,2011,2203,2301,2302};public int[] supplied,countsBefore,countsAfter;public string error;}
 static Report report;public static string HandoffSave=>report!=null&&report.reloaded?report.save:null;
 static void Write(){File.WriteAllText(Path.Combine(Application.persistentDataPath,"dsp-batch-fixture.json"),JsonUtility.ToJson(report,true));}
 public static void Prepare(){
  if(!DSPPadDiagnosticLaunch.AutomaticActionsAllowed||!DSPPadDiagnosticLaunch.NativePointerTestAllowed||!GameMain.isRunning)return;
  report=new Report{status="fixture-prepared",seed=GameMain.data.gameDesc.galaxySeed,supplied=new int[5]};
  GameMain.history.UnlockTechUnlimitedWithAllPre(1001);
  for(int i=0;i<report.itemIDs.Length;i++)report.supplied[i]=GameMain.mainPlayer.TryAddItemToPackage(report.itemIDs[i],20,0,false);
  Write();
 }
 public static IEnumerator Roundtrip(){
  if(report==null)yield break;
  yield return null;
  report.save="DSPemu-Batch22-"+DateTime.UtcNow.ToString("yyyyMMdd-HHmmss");report.beforeTick=GameMain.gameTick;report.countsBefore=new int[report.itemIDs.Length];
  for(int i=0;i<report.itemIDs.Length;i++)report.countsBefore[i]=GameMain.mainPlayer.package.GetItemCount(report.itemIDs[i]);
  report.saved=GameSave.SaveCurrentGame(report.save);report.status="saved";Write();
  if(!report.saved){report.error="Original GameSave failed";Write();yield break;}
  yield return null;DSPGame.StartGame(report.save);yield return null;
  float end=Time.realtimeSinceStartup+240;
  while((!GameMain.isRunning||GameMain.isLoading||GameMain.localPlanet==null||!GameMain.localPlanet.factoryLoaded)&&Time.realtimeSinceStartup<end)yield return new WaitForSecondsRealtime(1);
  if(!GameMain.isRunning||GameMain.isLoading||GameMain.localPlanet==null||!GameMain.localPlanet.factoryLoaded){report.error="Reload timed out";Write();yield break;}
  yield return new WaitForSecondsRealtime(3);
  report.afterTick=GameMain.gameTick;report.reloaded=GameMain.data.gameDesc.galaxySeed==report.seed&&report.afterTick>report.beforeTick;report.countsAfter=new int[report.itemIDs.Length];report.inventoryExact=true;
  for(int i=0;i<report.itemIDs.Length;i++){report.countsAfter[i]=GameMain.mainPlayer.package.GetItemCount(report.itemIDs[i]);report.inventoryExact&=report.countsAfter[i]==report.countsBefore[i];}
  report.status="roundtrip-finished";Write();yield return DSPPadRenderDiagnostics.Capture("22-reloaded");
 }
}
