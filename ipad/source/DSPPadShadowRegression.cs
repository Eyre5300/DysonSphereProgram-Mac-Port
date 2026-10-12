using System;using System.IO;using System.Collections;using System.Collections.Generic;using UnityEngine;using UnityEngine.Rendering;using UnityEngine.PostProcessing;
// Private diagnosis: temporary switches are always restored, never a production
// fix by removing shadows, vegetation, or post-processing.
public static class DSPPadShadowRegression {
 [Serializable] sealed class State {public string label;public bool noScreenSpaceShadows,vegetation,controller,sunshaft,dof,bloom;public string shadows;public int cascades;public List<string> textures=new List<string>();}
 static State Record(string label){
  var c=Camera.main;var controller=c.GetComponent<PostEffectController>();var post=c.GetComponent<PostProcessingBehaviour>();
  var s=new State{label=label,noScreenSpaceShadows=GraphicsSettings.HasShaderDefine(BuiltinShaderDefine.UNITY_NO_SCREENSPACE_SHADOWS),vegetation=GameMain.gpuiManager.renderVegetable,controller=controller&&controller.enabled,shadows=QualitySettings.shadows.ToString(),cascades=QualitySettings.shadowCascades,sunshaft=controller&&controller.sunShaft&&controller.sunShaft.enabled,dof=post&&post.profile&&post.profile.depthOfField.enabled,bloom=post&&post.profile&&post.profile.bloom.enabled};
  foreach(var key in new[]{"_ShadowMapTexture","_ScreenSpaceShadowmapTexture","_CameraDepthTexture"}){var t=Shader.GetGlobalTexture(key);if(t)s.textures.Add(key+":"+t.GetType().Name+":"+t.width+"x"+t.height);}
  File.WriteAllText(Path.Combine(Application.persistentDataPath,"shadow-"+label+".json"),JsonUtility.ToJson(s,true));return s;
 }
 static IEnumerator Shot(string name){yield return new WaitForSecondsRealtime(1);Record(name);yield return DSPPadRenderDiagnostics.Capture(name);}
 public static IEnumerator Run(){
  if(!DSPPadDiagnosticLaunch.AutomaticActionsAllowed||!Camera.main||GameMain.gpuiManager==null)yield break;
  var c=Camera.main;var controller=c.GetComponent<PostEffectController>();var post=c.GetComponent<PostProcessingBehaviour>();var profile=post?post.profile:null;var manager=GameMain.gpuiManager;
  bool ctrl=controller&&controller.enabled,veg=manager.renderVegetable,sun=controller&&controller.sunShaft&&controller.sunShaft.enabled,dof=profile&&profile.depthOfField.enabled,bloom=profile&&profile.bloom.enabled;var shadows=QualitySettings.shadows;
  yield return Shot("14-shadow-default");
  try{
   if(controller)controller.enabled=false;
   QualitySettings.shadows=ShadowQuality.Disable;yield return Shot("14-shadow-off-held");QualitySettings.shadows=shadows;
   manager.renderVegetable=false;yield return Shot("14-vegetation-off");manager.renderVegetable=veg;
   if(controller&&controller.sunShaft)controller.sunShaft.enabled=false;if(profile){profile.depthOfField.enabled=false;profile.bloom.enabled=false;}
   yield return Shot("14-post-lighting-off-held");
  }finally{
   QualitySettings.shadows=shadows;manager.renderVegetable=veg;if(profile){profile.depthOfField.enabled=dof;profile.bloom.enabled=bloom;}if(controller){if(controller.sunShaft)controller.sunShaft.enabled=sun;controller.enabled=ctrl;}
  }
  yield return Shot("14-shadow-restored");
 }
}
