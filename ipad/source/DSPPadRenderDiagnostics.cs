using System;
using System.IO;
using System.Reflection;
using System.Collections;
using System.Collections.Generic;
using UnityEngine;
using UnityEngine.Rendering;
using UnityEngine.PostProcessing;

// Every probe preserves and restores the original game rendering configuration.
public static class DSPPadRenderDiagnostics {
 [Serializable] sealed class CameraInfo {public string name,path,target,matrix,components,profile,commandBuffers;public int mask,depthMode;public float depth,near,far;public bool enabled,active,hdr;public Vector3 position,rotation;}
 [Serializable] sealed class LightInfo {public string name,type;public float intensity;public Color color;public bool enabled;public int mask;}
 [Serializable] sealed class Audit {public string graphics,mainCamera,uiGrid;public int shaderLevel;public List<CameraInfo> cameras=new List<CameraInfo>();public List<LightInfo> lights=new List<LightInfo>();public List<string> unsupportedShaders=new List<string>();}
 [Serializable] sealed class FrameInfo {public string label,components;public float centerMean,centerBlackFraction;public int width,height;public long tick;public bool dofEnabled,bloomEnabled,lutEnabled,colorGradingEnabled,alphaHDRCandidate,desktopBloomCandidate;public DSPPadRenderFormats.TextureInfo[] textures;public DSPPadRenderFormats.PixelInfo[] pixels;}
 static string Folder=>Application.persistentDataPath;
 public static string PathOf(Transform t){string s=t.name;while(t.parent!=null){t=t.parent;s=t.name+"/"+s;}return s;}
 static string Components(Camera c){string s=c.actualRenderingPath.ToString();foreach(var b in c.GetComponents<Behaviour>())s+=";"+b.GetType().FullName+"="+b.enabled;return s;}
 public static void AuditNow(){
  var a=new Audit{graphics=SystemInfo.graphicsDeviceName,shaderLevel=SystemInfo.graphicsShaderLevel,mainCamera=Camera.main?PathOf(Camera.main.transform):"null"};
  foreach(var c in Resources.FindObjectsOfTypeAll<Camera>()){
   var x=new CameraInfo{name=c.name,path=PathOf(c.transform),target=c.targetTexture?c.targetTexture.name+":"+c.targetTexture.graphicsFormat+":"+c.targetTexture.width+"x"+c.targetTexture.height:"screen",mask=c.cullingMask,depthMode=(int)c.depthTextureMode,depth=c.depth,near=c.nearClipPlane,far=c.farClipPlane,enabled=c.enabled,active=c.gameObject.activeInHierarchy,hdr=c.allowHDR,position=c.transform.position,rotation=c.transform.eulerAngles,matrix=c.projectionMatrix.ToString("F5"),components=Components(c)};
   var p=c.GetComponent<PostProcessingBehaviour>();if(p&&p.profile)x.profile=JsonUtility.ToJson(p.profile);
   foreach(CameraEvent e in Enum.GetValues(typeof(CameraEvent)))foreach(var b in c.GetCommandBuffers(e))x.commandBuffers+=e+":"+b.name+";";
   if(c.targetTexture)DSPPadRenderFormats.Note("camera-target-"+x.path,c.targetTexture);a.cameras.Add(x);
  }
  foreach(var l in UnityEngine.Object.FindObjectsOfType<Light>())a.lights.Add(new LightInfo{name=PathOf(l.transform),type=l.type.ToString(),intensity=l.intensity,color=l.color,enabled=l.enabled,mask=l.cullingMask});
  var known=new HashSet<string>();foreach(var m in Resources.FindObjectsOfTypeAll<Material>())if(m.shader&&!m.shader.isSupported&&known.Add(m.shader.name)&&a.unsupportedShaders.Count<100)a.unsupportedShaders.Add(m.shader.name);
  for(int y=1;y<5;y++)for(int x=1;x<5;x++){var point=new Vector2(Screen.width*x/5f,Screen.height*y/5f);a.uiGrid+=point+":"+DSPSmartTouchFrame.BlockerAt(point)+"\n";}
  File.WriteAllText(System.IO.Path.Combine(Folder,"emu-render-audit.json"),JsonUtility.ToJson(a,true));
 }
 public static IEnumerator Capture(string label){
  DSPPadRenderFormats.BeginSample(label);yield return new WaitForEndOfFrame();
  try{
   foreach(var key in new[]{"_CameraDepthTexture","_Global_AtmoBlurTex"}){var t=Shader.GetGlobalTexture(key);if(t)DSPPadRenderFormats.Sample(key,t);}
   var image=ScreenCapture.CaptureScreenshotAsTexture();try{
    var data=image.GetPixels32();double sum=0;int dark=0,n=0;for(int y=image.height/4;y<image.height*3/4;y+=8)for(int x=image.width/4;x<image.width*3/4;x+=8){var c=data[y*image.width+x];sum+=(c.r+c.g+c.b)/765.0;if(c.r<4&&c.g<4&&c.b<4)dark++;n++;}
    var f=new FrameInfo{label=label,width=image.width,height=image.height,tick=GameMain.gameTick,centerMean=(float)(sum/n),centerBlackFraction=(float)dark/n,alphaHDRCandidate=DSPPadRenderFormats.AlphaHDRCandidate,desktopBloomCandidate=DSPPadRenderFormats.DesktopBloomCandidate,textures=DSPPadRenderFormats.Textures,pixels=DSPPadRenderFormats.Pixels};
    var camera=Camera.main;if(camera){f.components=Components(camera);var p=camera.GetComponent<PostProcessingBehaviour>();if(p&&p.profile){f.dofEnabled=p.profile.depthOfField.enabled;f.bloomEnabled=p.profile.bloom.enabled;f.lutEnabled=p.profile.userLut.enabled;f.colorGradingEnabled=p.profile.colorGrading.enabled;}}
    File.WriteAllText(System.IO.Path.Combine(Folder,"emu-render-"+label+".json"),JsonUtility.ToJson(f,true));File.WriteAllBytes(System.IO.Path.Combine(Folder,"emu-render-"+label+".png"),image.EncodeToPNG());
   }finally{UnityEngine.Object.Destroy(image);}
  }finally{DSPPadRenderFormats.EndSample();}
  yield return null;
 }
 public static IEnumerator RegressionViews(){
  // Exercise the adopted fix with the original controller continuously enabled.
  // Only the test-owned camera viewpoint is varied; restore every value.
  AuditNow();yield return new WaitForSecondsRealtime(2);yield return Capture("12-world-default");
  var poser=GameCamera.instance?GameCamera.instance.rtsPoser:null;
  if(poser){
   float zoom=poser.distCoefWanted,pitch=poser.pitchCoefWanted,yaw=poser.yawWanted;
   try{
    poser.distCoefWanted=.05f;yield return new WaitForSecondsRealtime(3);yield return Capture("12-world-close");
    poser.distCoefWanted=.95f;yield return new WaitForSecondsRealtime(3);yield return Capture("12-world-far");
    poser.pitchCoefWanted=.95f;poser.yawWanted=yaw+120;yield return new WaitForSecondsRealtime(3);yield return Capture("12-world-horizon");
   }finally{poser.distCoefWanted=zoom;poser.pitchCoefWanted=pitch;poser.yawWanted=yaw;}
   yield return new WaitForSecondsRealtime(3);yield return Capture("12-world-restored");
  }
  AuditNow();
 }
 public static IEnumerator RenderAB(){
  AuditNow();yield return Capture("10-baseline");
  var camera=Camera.main;var post=camera.GetComponent<PostProcessingBehaviour>();var controller=camera.GetComponent<PostEffectController>();var profile=post?post.profile:null;
  bool projection=PortCameraProjection.Enabled,controllerEnabled=controller&&controller.enabled,postEnabled=post&&post.enabled,alpha=DSPPadRenderFormats.AlphaHDRCandidate,bloomHDR=DSPPadRenderFormats.DesktopBloomCandidate;
  bool dof=profile&&profile.depthOfField.enabled,bloom=profile&&profile.bloom.enabled,lut=profile&&profile.userLut.enabled,color=profile&&profile.colorGrading.enabled;
  var shadows=QualitySettings.shadows;
  try{
   // The original controller re-enables effects every Update; hold it stopped.
   if(controller)controller.enabled=false;
   PortCameraProjection.Enabled=false;yield return new WaitForSecondsRealtime(2);yield return Capture("10-original-projection");PortCameraProjection.Enabled=projection;
   if(post){post.enabled=false;yield return new WaitForSecondsRealtime(2);yield return Capture("10-post-disabled-held");post.enabled=postEnabled;}
   if(profile){
    profile.depthOfField.enabled=false;yield return new WaitForSecondsRealtime(2);yield return Capture("10-dof-disabled-held");profile.depthOfField.enabled=dof;
    profile.userLut.enabled=false;profile.colorGrading.enabled=false;yield return new WaitForSecondsRealtime(2);yield return Capture("10-color-lut-disabled-held");profile.userLut.enabled=lut;profile.colorGrading.enabled=color;
   }
   var effects=new Dictionary<Behaviour,bool>();
   foreach(var c in Camera.allCameras)foreach(var b in c.GetComponents<Behaviour>())if(b.GetType().GetMethod("OnRenderImage",BindingFlags.Instance|BindingFlags.Public|BindingFlags.NonPublic)!=null)effects[b]=b.enabled;
   try{foreach(var b in effects.Keys)b.enabled=false;yield return new WaitForSecondsRealtime(2);yield return Capture("10-main-ui-image-effects-disabled-held");}finally{foreach(var b in effects)if(b.Key)b.Key.enabled=b.Value;}
   DSPPadRenderFormats.AlphaHDRCandidate=true;yield return new WaitForSecondsRealtime(2);yield return Capture("10-dof-alpha-hdr");
   DSPPadRenderFormats.DesktopBloomCandidate=true;yield return new WaitForSecondsRealtime(2);yield return Capture("10-dof-and-bloom-hdr");
   DSPPadRenderFormats.AlphaHDRCandidate=alpha;DSPPadRenderFormats.DesktopBloomCandidate=bloomHDR;
   QualitySettings.shadows=ShadowQuality.Disable;yield return new WaitForSecondsRealtime(2);yield return Capture("10-shadows-disabled-held");QualitySettings.shadows=shadows;
  }finally{
   PortCameraProjection.Enabled=projection;DSPPadRenderFormats.AlphaHDRCandidate=alpha;DSPPadRenderFormats.DesktopBloomCandidate=bloomHDR;QualitySettings.shadows=shadows;
   if(profile){profile.depthOfField.enabled=dof;profile.bloom.enabled=bloom;profile.userLut.enabled=lut;profile.colorGrading.enabled=color;}
   if(post)post.enabled=postEnabled;if(controller)controller.enabled=controllerEnabled;
  }
  yield return new WaitForSecondsRealtime(2);yield return Capture("10-restored");AuditNow();
 }
}
