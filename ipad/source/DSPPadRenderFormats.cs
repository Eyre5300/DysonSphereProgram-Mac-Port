using System;
using System.Collections.Generic;
using UnityEngine;

// iPad DefaultHDR resolves to RGB111110Float, which drops the signed CoC
// and coverage alpha required by the original DoF shaders. Build10 device A/B
// proved ARGBHalf restores the image while preserving the complete effect.
// Windows uses HDR Bloom. Device17/18 format probes preserve finite HDR pixels;
// use FP16 instead of the mobile LDR clamp while retaining the original effect.
public static class DSPPadRenderFormats {
 public static bool AlphaHDRCandidate=true;
 public static bool DesktopBloomCandidate=true;
 public static string SamplingLabel="";
 [Serializable] public sealed class TextureInfo {public string stage,format,graphicsFormat;public int width,height,samples,memoryless;public bool srgb,created;}
 [Serializable] public sealed class PixelInfo {public string stage,error;public float minR,maxR,meanR,minA,maxA,meanA,nearMean,farMean;public int nonFinite;}
 static readonly Dictionary<string,TextureInfo> textures=new Dictionary<string,TextureInfo>();
 static readonly Dictionary<string,PixelInfo> pixels=new Dictionary<string,PixelInfo>();
 static readonly HashSet<string> sampled=new HashSet<string>();
 public static TextureInfo[] Textures {get {var a=new TextureInfo[textures.Count];textures.Values.CopyTo(a,0);return a;}}
 public static PixelInfo[] Pixels {get {var a=new PixelInfo[pixels.Count];pixels.Values.CopyTo(a,0);return a;}}
 public static void BeginSample(string label){SamplingLabel=label;sampled.Clear();pixels.Clear();}
 public static void EndSample(){SamplingLabel="";}
 public static void Note(string name,RenderTexture t){if(!t||!DSPPadDiagnosticLaunch.TelemetryAllowed)return;textures[name]=new TextureInfo{stage=name,format=t.format.ToString(),graphicsFormat=t.graphicsFormat.ToString(),width=t.width,height=t.height,samples=t.antiAliasing,memoryless=(int)t.memorylessMode,srgb=t.sRGB,created=t.IsCreated()};if(SamplingLabel!=""&&sampled.Add(name))Sample(name,t);}
 public static void Sample(string name,Texture source){
  if(!source)return;var p=new PixelInfo{stage=name,minR=float.PositiveInfinity,maxR=float.NegativeInfinity,minA=float.PositiveInfinity,maxA=float.NegativeInfinity};
  RenderTexture old=RenderTexture.active,temp=null;Texture2D image=null;
  try{
   if(!SystemInfo.SupportsRenderTextureFormat(RenderTextureFormat.ARGBFloat))throw new InvalidOperationException("ARGBFloat readback unsupported");
   temp=RenderTexture.GetTemporary(128,96,0,RenderTextureFormat.ARGBFloat,RenderTextureReadWrite.Linear);Graphics.Blit(source,temp);RenderTexture.active=temp;
   image=new Texture2D(128,96,TextureFormat.RGBAFloat,false,true);image.ReadPixels(new Rect(0,0,128,96),0,0,false);image.Apply(false,false);
   var colors=image.GetPixels();double r=0,a=0,near=0,far=0;int count=0,nn=0,nf=0;
   for(int i=0;i<colors.Length;i++){var c=colors[i];if(float.IsNaN(c.r)||float.IsInfinity(c.r)||float.IsNaN(c.a)||float.IsInfinity(c.a)){p.nonFinite++;continue;}p.minR=Mathf.Min(p.minR,c.r);p.maxR=Mathf.Max(p.maxR,c.r);p.minA=Mathf.Min(p.minA,c.a);p.maxA=Mathf.Max(p.maxA,c.a);r+=c.r;a+=c.a;count++;int y=i/128,x=i%128;if(x>=32&&x<96&&y>=24&&y<48){near+=(c.r+c.g+c.b)/3;nn++;}if(x>=32&&x<96&&y>=48&&y<72){far+=(c.r+c.g+c.b)/3;nf++;}}
   if(count>0){p.meanR=(float)(r/count);p.meanA=(float)(a/count);p.nearMean=nn>0?(float)(near/nn):0;p.farMean=nf>0?(float)(far/nf):0;}else p.error="No finite readback pixels";
  }catch(Exception e){p.error=e.GetType().Name+": "+e.Message;}
  finally{RenderTexture.active=old;if(image)UnityEngine.Object.Destroy(image);if(temp)RenderTexture.ReleaseTemporary(temp);}
  pixels[name]=p;
 }
}
