using System;using System.Collections;using System.Collections.Generic;using System.IO;using UnityEngine;
public static class PortBlueprintAudit {
 static BuildTool_BlueprintPaste tool;static Vector3 anchor;static string folder;static void Note(string text){File.AppendAllText(Path.Combine(folder,"blueprint-audit.txt"),text+"\n");}
 public static void PinPreview(){if(tool==null)return;tool.cursorValid=true;tool.dotsCursor=1;tool.dotsSnapped[0]=anchor;tool.castGroundPos=anchor;tool.castGroundPosSnapped=anchor;tool.GenerateBlueprintGratBoxes();tool.DeterminePreviewsPrestage();}
 public static IEnumerator Run(string output){
  folder=output;File.WriteAllText(Path.Combine(folder,"blueprint-audit.txt"),"Private blueprint import/export and original preview pipeline. No placement claimed by preview alone.\n");
  var paths=Directory.GetFiles(Path.Combine(Application.persistentDataPath,"PrivateBlueprintFixtures"),"*.txt");Array.Sort(paths,StringComparer.Ordinal);int index=0;
  foreach(string path in paths){
   var data=new BlueprintData();var error=data.FromBase64String(File.ReadAllText(path).Trim());if(error!=BlueprintDataIOError.OK)throw new Exception("Blueprint import "+Path.GetFileName(path)+": "+error);
   string encoded=data.ToBase64String();var again=new BlueprintData();if(again.FromBase64String(encoded)!=BlueprintDataIOError.OK||again.ToBase64String()!=encoded)throw new Exception("Blueprint roundtrip mismatch");
   int links=0;foreach(var b in data.buildings){if(LDB.items.Select(b.itemId)==null||LDB.models.Select(b.modelIndex)==null)throw new Exception("Missing blueprint item/model");if(b.inputObj!=null)links++;if(b.outputObj!=null)links++;}
   Note("file="+Path.GetFileName(path)+" buildings="+data.buildings.Length+" areas="+data.areas.Length+" links="+links+" importAndRoundtrip=True blueprintLimit="+GameMain.history.blueprintLimit);
   if(GameMain.history.blueprintLimit<data.buildings.Length){Note("preview skipped: original research capacity too low");continue;}
   var player=GameMain.mainPlayer;player.controller.OpenBlueprintPasteMode(data,path);yield return null;tool=player.controller.actionBuild.blueprintPasteTool;if(player.controller.actionBuild.blueprintMode!=EBlueprintMode.Paste)throw new Exception("Paste UI did not open");
   anchor=player.position.normalized*(GameMain.localPlanet.realRadius+.2f);PinPreview();yield return new WaitForSecondsRealtime(3);int valid=0;for(int i=0;i<tool.bpCursor;i++)if(tool.bpPool[i].bpgpuiModelId>0)valid++;Note("previews="+tool.bpCursor+" models="+valid);if(tool.bpCursor!=data.buildings.Length||valid!=tool.bpCursor)throw new Exception("Incomplete blueprint preview");
   if(data.buildings.Length>1000)yield return new WaitForSecondsRealtime(3);
   yield return new WaitForEndOfFrame();var tex=ScreenCapture.CaptureScreenshotAsTexture();File.WriteAllBytes(Path.Combine(folder,"blueprint-"+(++index)+".png"),tex.EncodeToPNG());UnityEngine.Object.Destroy(tex);yield return null;tool=null;player.controller.actionBuild.Close();player.controller.cmd.SetNoneCommand();yield return new WaitForSecondsRealtime(1);
  }
  Note("allImportsAndPreviewsFinished=True");
 }
 public static void Clear(){tool=null;}
 public static IEnumerator BuildSample(){
  var player=GameMain.mainPlayer;var planet=GameMain.localPlanet;var factory=planet.factory;
  string path=Path.Combine(Application.persistentDataPath,"PrivateBlueprintFixtures","1级爪子.txt");var data=new BlueprintData();if(data.FromBase64String(File.ReadAllText(path).Trim())!=BlueprintDataIOError.OK)throw new Exception("Build sample import failed");
  if(GameMain.history.blueprintLimit<data.buildings.Length){Note("construction skipped: original blueprint research capacity too low");yield break;}
  var counts=new Dictionary<int,int>();foreach(var b in data.buildings){if(!counts.ContainsKey(b.itemId))counts[b.itemId]=0;counts[b.itemId]++;}
  foreach(var item in counts){int added=player.package.AddItemStacked(item.Key,item.Value,0,out var _);if(added!=item.Value)throw new Exception("Fixture inventory full for "+item.Key);}
  Note("construction fixture supplies required items and repositions player; original collision/terrain/technology checks and construction drones retained");
  player.controller.OpenBlueprintPasteMode(data,path);yield return null;tool=player.controller.actionBuild.blueprintPasteTool;bool found=false;
  foreach(float latitude in new[]{0f,15f,-15f,25f,-25f}){
   for(int longitude=0;longitude<360;longitude+=15){
    anchor=planet.aux.Snap(Quaternion.Euler(0,longitude,0)*new Vector3(Mathf.Cos(latitude*Mathf.Deg2Rad),Mathf.Sin(latitude*Mathf.Deg2Rad),0)*planet.realRadius,true);
    tool.ClearErrorMessage(true);tool.cursorValid=true;tool.dotsCursor=1;tool.dotsSnapped[0]=anchor;tool.GenerateBlueprintGratBoxes();tool.DeterminePreviewsPrestage(true);if(!tool.CheckBuildConditionsPrestage())continue;
    tool.ActiveColliders(player.controller.actionBuild.model);bool valid=tool.CheckBuildConditions();tool.DeactiveColliders(player.controller.actionBuild.model);for(int i=0;i<tool.bpCursor;i++)valid&=tool.bpPool[i].condition==EBuildCondition.Ok&&tool.bpPool[i].coverObjId==0;
    if(valid){found=true;break;}
   }
   if(found)break;yield return null;
  }
  if(!found){Note("construction placement: no valid empty site found; conditions respected");tool=null;player.controller.actionBuild.Close();yield break;}
  var positions=new Vector3[tool.bpCursor];var protos=new int[tool.bpCursor];for(int i=0;i<tool.bpCursor;i++){positions[i]=tool.bpPool[i].lpos;protos[i]=tool.bpPool[i].item.ID;}
  player.position=anchor.normalized*(planet.data.QueryModifiedHeight(anchor)+1.6f);player.mecha.coreEnergy=player.mecha.coreEnergyCap;
  Note("validSite="+anchor+" expected="+positions.Length);tool.CreatePrebuilds();tool=null;player.controller.actionBuild.Close();player.controller.cmd.SetNoneCommand();
  int built=0;float end=Time.realtimeSinceStartup+120;
  while(Time.realtimeSinceStartup<end){yield return new WaitForSecondsRealtime(5);built=0;for(int i=0;i<positions.Length;i++)for(int e=1;e<factory.entityCursor;e++)if(factory.entityPool[e].id==e&&factory.entityPool[e].protoId==protos[i]&&(factory.entityPool[e].pos-positions[i]).sqrMagnitude<.01f){built++;break;}Note("droneConstruction tick="+GameMain.gameTick+" completed="+built+"/"+positions.Length);if(built==positions.Length)break;}
  if(built!=positions.Length)throw new Exception("Blueprint drone construction incomplete");
  Note("actualBlueprintConstructionPassed=True");yield return new WaitForEndOfFrame();var tex=ScreenCapture.CaptureScreenshotAsTexture();File.WriteAllBytes(Path.Combine(folder,"blueprint-built.png"),tex.EncodeToPNG());UnityEngine.Object.Destroy(tex);yield return null;
 }
}
