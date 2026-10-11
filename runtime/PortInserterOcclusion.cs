using System.IO;
using UnityEngine;
// Ordinary built inserters only. Build/blueprint overlays retain their owned shader.
public static class PortInserterOcclusion {
 public const string OriginalName="VF Shaders/Forward/Inserter Arrow";
 public const string OccludedName="DSPPort/Inserter Arrow Occluded";
 static Shader shader; static bool tried;
 public static Shader LoadShader(){
  if(!tried){tried=true;shader=Resources.Load<Shader>("PortInserterArrowOccluded");
   if(shader==null){string file=Path.Combine(Application.streamingAssetsPath,"port-inserter-occlusion.bundle");
    if(File.Exists(file)){var bundle=AssetBundle.LoadFromFile(file);if(bundle!=null){foreach(var candidate in bundle.LoadAllAssets<Shader>())if(candidate.name==OccludedName)shader=candidate;bundle.Unload(false);}}}}
  return shader;
 }
 public static void Configure(InserterRenderer renderer){
  if(Application.platform!=RuntimePlatform.OSXPlayer||renderer==null||renderer.isPrebuild||renderer.isPreview||renderer.lodBatches==null)return;
  foreach(var batch in renderer.lodBatches){if(batch==null||batch.materials==null)continue;
   foreach(var mat in batch.materials){if(mat==null||mat.shader==null||mat.shader.name!=OriginalName)continue;
    var replacement=LoadShader();if(replacement==null||!replacement.isSupported){Debug.LogError("Inserter occlusion shader missing or unsupported");return;}
    var keywords=mat.shaderKeywords;int queue=mat.renderQueue;mat.shader=replacement;mat.shaderKeywords=keywords;mat.renderQueue=queue;
   }
  }
 }
}
