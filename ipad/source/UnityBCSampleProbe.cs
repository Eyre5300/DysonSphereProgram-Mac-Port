// Private diagnostic fixture. Exact Windows BC bytes, no game rules or assets changed.
using System;
using System.Collections;
using System.Collections.Generic;
using System.IO;
using System.Security.Cryptography;
using UnityEngine;
using UnityEngine.Experimental.Rendering;
using UnityEngine.Profiling;

public static class UnityBCSampleProbe
{
    [Serializable] public class Manifest { public Fixture[] fixtures; }
    [Serializable] public class Fixture {
        public string name, file, type, sha256; public int textureFormat, width, height, mipCount, imageCount, bytes;
        public bool linearConstructor; public Subresource[] subresources;
    }
    [Serializable] public class Subresource {
        public int face, level, width, height, offset, bytes; public string sha256;
        public Golden[] decodedBlockSamples;
    }
    [Serializable] public class Golden { public int x, y; public int[] rgba8; }
    [Serializable] public class Report {
        public string startedUtc, finishedUtc, device, colorSpace, status="running", calibration;
        public bool sampledSubsetPassed, nativeFormatVerificationAvailable, nativeAllocationAvailable;
        public List<string> mipTailCalibrations=new List<string>();
        public long allocationBefore, allocationAfter;
        public float maximumLinearControlError,maximumSRGBControlError;
        public List<TransferControl> transferControls=new List<TransferControl>();
        public List<Result> results=new List<Result>(); public List<string> errors=new List<string>();
        public string[] unverified={"Cubemap direction-vector shader sampling (all six face/mip copies are tested)",
            "BC6H exact HDR decoder golden (finite values, alpha and independent upload/copy equality only)",
            "Compressed subregion copies and sRGB texture views", "Full-game memory and rendering parity"};
    }
    [Serializable] public class TransferControl {public int code;public bool linear,passed=true;public Color actual,expected,error,halfUlpLimit,allowedLower,allowedUpper;}
    [Serializable] public class GoldenCheck {public int x,y;public Color actual,lower,upper;public bool passed;}
    [Serializable] public class Result {
        public string fixture, type, format, graphicsFormat, error;
        public int face, mip, width, height, comparedPixels, goldenPoints,copyBaseWidth,copyBaseHeight,copyDestinationMip;
        public bool hdrAboveOneObserved;public List<GoldenCheck> goldenSamples=new List<GoldenCheck>();
        public long expectedNativeFormat, actualNativeFormat, sourceNativeFormat, allocationDelta, sourceUnityMemory;
        public bool passed; public float maximumCopyError, maximumGoldenError, minRGB, maxRGB;
    }
    static readonly int[] Native={131,130,133,132,135,134,140,141,142,143,151,150,153,152};
    static long NativeFormat(GraphicsFormat f) { int i=(int)f-96; return i>=0&&i<Native.Length?Native[i]:0; }
    static void Require(bool condition,string message) { if(!condition) throw new InvalidOperationException(message); }
    static string Hash(byte[] bytes) { using(var sha=SHA256.Create()) return BitConverter.ToString(sha.ComputeHash(bytes)).Replace("-","").ToLowerInvariant(); }
    static bool Finite(float x) { return !float.IsNaN(x)&&!float.IsInfinity(x); }
    static void Save(string path,Report report) { Directory.CreateDirectory(Path.GetDirectoryName(Path.GetFullPath(path))); File.WriteAllText(path,JsonUtility.ToJson(report,true)); }
    static void Dispose(UnityEngine.Object obj) { if(obj!=null) UnityEngine.Object.Destroy(obj); }
    static Texture2D TwoD(int w,int h,TextureFormat fmt,int mips,bool linear) {
        var t=new Texture2D(w,h,fmt,mips,linear); t.filterMode=FilterMode.Point; t.wrapMode=TextureWrapMode.Clamp; t.anisoLevel=0; return t;
    }
    static Color[] Readback(Texture texture,int w,int h) {
        var previous=RenderTexture.active; bool srgb=GL.sRGBWrite; RenderTexture rt=null; Texture2D read=null;
        try {
            rt=new RenderTexture(w,h,0,RenderTextureFormat.ARGBFloat,RenderTextureReadWrite.Linear);
            rt.filterMode=FilterMode.Point; rt.useMipMap=false; rt.autoGenerateMips=false;
            Require(rt.Create(),"ARGBFloat RT creation failed");
            GL.sRGBWrite=false; Graphics.Blit(texture,rt); RenderTexture.active=rt;
            read=TwoD(w,h,TextureFormat.RGBAFloat,1,true);
            read.ReadPixels(new Rect(0,0,w,h),0,0,false); read.Apply(false,false);
            return read.GetPixels();
        } finally { RenderTexture.active=previous; GL.sRGBWrite=srgb; if(rt!=null)rt.Release(); Dispose(rt); Dispose(read); }
    }
    static Color[] Pattern() {
        var c=new Color[16]; for(int y=0;y<4;y++)for(int x=0;x<4;x++) c[y*4+x]=new Color((x+1)/5f,(y+1)/5f,(x+4*y+1)/17f,(x+y+1)/8f); return c;
    }
    // Orientation is selected ONCE from known uncompressed data, never from BC goldens.
    static int Calibrate() {
        Texture2D t=null; try {
            t=TwoD(4,4,TextureFormat.RGBA32,1,true); var pattern=Pattern(); t.SetPixels(pattern); t.Apply(false,true);
            Color[] pixels=Readback(t,4,4); int selected=-1,matches=0;
            for(int transform=0;transform<4;transform++) {
                bool ok=true; for(int y=0;y<4;y++)for(int x=0;x<4;x++) {
                    Color p=pixels[Index(x,y,4,4,transform)],e=pattern[y*4+x];
                    for(int c=0;c<4;c++)if(Mathf.Abs(p[c]-e[c])>1.1f/255f)ok=false;
                }
                if(ok){selected=transform;matches++;}
            }
            Require(matches==1,"RGBA32 orientation calibration must have exactly one matching orientation, got "+matches); return selected;
        } finally {Dispose(t);}
    }
    // D3D11.3 section 3.2.3.7 allows 0.5 ULP on the encoded sRGB side.
    // Evaluate that independent API bound before default-Blit's half output rounding.
    // BC decoder bounds remain the separate conservative +/-2 encoded-byte window.
    static float SRGBToLinear(float encoded) {double x=Math.Max(0,Math.Min(1,encoded));return (float)(x<=0.04045?x/12.92:Math.Pow((x+0.055)/1.055,2.4));}
    static Color[][] CalibrateBoundaries(int orientation,Report report) {
        var table=new Color[2][];
        for(int linear=0;linear<2;linear++){
            Texture2D t=null;try{
                t=TwoD(256,1,TextureFormat.RGBA32,1,linear==1);var codes=new Color32[256];for(int i=0;i<256;i++)codes[i]=new Color32((byte)i,(byte)i,(byte)i,(byte)i);t.SetPixels32(codes);t.Apply(false,true);var pixels=Readback(t,256,1);table[linear]=new Color[256];
                for(int i=0;i<256;i++){
                    var got=pixels[Index(i,0,256,1,orientation)];table[linear][i]=got;var check=new TransferControl{code=i,linear=linear==1,actual=got};report.transferControls.Add(check);
                    for(int c=0;c<4;c++){
                        bool srgb=linear==0&&c<3;float encoded=i/255f,expected=srgb?SRGBToLinear(encoded):encoded,error=Mathf.Abs(got[c]-expected);
                        float halfUlp=expected>0?Mathf.Max(Mathf.Pow(2,-24),Mathf.Pow(2,Mathf.Floor(Mathf.Log(expected,2))-10)):Mathf.Pow(2,-24);
                        check.expected[c]=expected;check.error[c]=error;check.halfUlpLimit[c]=Mathf.Max(1e-7f,2*halfUlp);
                        check.allowedLower[c]=(srgb?SRGBToLinear((i-.5f)/255f):expected)-check.halfUlpLimit[c];
                        check.allowedUpper[c]=(srgb?SRGBToLinear((i+.5f)/255f):expected)+check.halfUlpLimit[c];
                        check.passed&=Finite(got[c])&&got[c]>=check.allowedLower[c]&&got[c]<=check.allowedUpper[c]&&(i==0||got[c]>=table[linear][i-1][c]);
                        if(i==0||i==255)check.passed&=Mathf.Abs(got[c]-encoded)<=1e-7f;
                        if(linear==0&&c<3)report.maximumSRGBControlError=Mathf.Max(report.maximumSRGBControlError,error);else report.maximumLinearControlError=Mathf.Max(report.maximumLinearControlError,error);
                    }
                }
            }finally{Dispose(t);}
        }
        int bad=0;foreach(var check in report.transferControls)if(!check.passed)bad++;
        if(bad>0)report.errors.Add("Independent RGBA8 transfer control fails D3D sRGB-side 0.5 ULP plus separately recorded Blit half precision, monotonicity or endpoint gate at "+bad+" codes; all actual/expected values retained. Remaining tests collect independent evidence, not an overall PASS.");
        return table;
    }
    static int Index(int x,int y,int w,int h,int orientation) { if((orientation&1)!=0)x=w-1-x;if((orientation&2)!=0)y=h-1-y;return y*w+x; }
    static Texture CreateSource(Fixture f,byte[] bytes) {
        Texture result=null;
        try {
            TextureFormat fmt=(TextureFormat)f.textureFormat;
            Require(SystemInfo.SupportsTextureFormat(fmt),"Unity lacks "+fmt);
            GraphicsFormat expected=GraphicsFormatUtility.GetGraphicsFormat(fmt,!f.linearConstructor);
            Require(SystemInfo.IsFormatSupported(expected,FormatUsage.Sample),"GraphicsFormat not sampleable "+expected);
            Require(SystemInfo.IsFormatSupported(expected,FormatUsage.Linear),"GraphicsFormat not filterable "+expected);
            Require(!SystemInfo.IsFormatSupported(expected,FormatUsage.Render)&&!SystemInfo.IsFormatSupported(expected,FormatUsage.LoadStore),"BC incorrectly advertised as render/UAV");
            if(f.type=="Texture2D") {
                var t=TwoD(f.width,f.height,fmt,f.mipCount,f.linearConstructor);result=t;t.LoadRawTextureData(bytes);t.Apply(false,true);
                Require(t.format==fmt&&t.mipmapCount==f.mipCount,"Texture2D format/mip fallback");
            } else {
                Require(f.type=="Cubemap"&&f.imageCount==6&&f.width==f.height,"Invalid cube metadata");
                var c=new Cubemap(f.width,expected,f.mipCount>1?TextureCreationFlags.MipChain:TextureCreationFlags.None,f.mipCount); result=c;
                c.filterMode=FilterMode.Point;c.wrapMode=TextureWrapMode.Clamp;c.anisoLevel=0;
                foreach(var sub in f.subresources)c.SetPixelData<byte>(bytes,sub.level,(CubemapFace)sub.face,sub.offset);
                c.Apply(false,true);Require(c.format==fmt&&c.mipmapCount==f.mipCount,"Cubemap format/mip fallback");
            }
            Require(result.graphicsFormat==expected,"Unexpected graphics format "+result.graphicsFormat+" expected "+expected);
            return result;
        } catch {Dispose(result);throw;}
    }
    // A mip tail is legal inside a block-aligned texture even when it is not a legal base size.
    // Keep the exact logical mip dimensions; do not pad its sampled image or omit tail tests.
    static int DestinationMip(int w,int h) {int level=0;while(((w<<level)&3)!=0||((h<<level)&3)!=0){level++;Require(level<=2,"Unsupported BC base alignment");}return level;}
    static int BlockBytes(TextureFormat fmt,int w,int h) {return ((w+3)/4)*((h+3)/4)*(fmt==TextureFormat.DXT1?8:16);}
    static Color MipPattern(int level,int x,int y) {return new Color((level+1)/5f,(x%7+1)/9f,(y%7+1)/9f,(level+2)/6f);}
    static void CalibrateMipTail(int w,int h,int orientation) {
        int level=DestinationMip(w,h);if(level==0)return;Texture2D t=null;
        try {
            t=TwoD(w<<level,h<<level,TextureFormat.RGBA32,level+1,true);
            for(int mip=0;mip<=level;mip++){int mw=(w<<level)>>mip,mh=(h<<level)>>mip;var pixels=new Color[mw*mh];for(int y=0;y<mh;y++)for(int x=0;x<mw;x++)pixels[y*mw+x]=MipPattern(mip,x,y);t.SetPixels(pixels,mip);}
            t.Apply(false,true);var actual=Readback(t,w,h);
            for(int y=0;y<h;y++)for(int x=0;x<w;x++){var got=actual[Index(x,y,w,h,orientation)];var expected=MipPattern(level,x,y);for(int c=0;c<4;c++)Require(Mathf.Abs(got[c]-expected[c])<=1.1f/255f,"Implicit mip selection control failed "+w+"x"+h+" level "+level);}
        } finally {Dispose(t);}
    }
    static Result Check(Fixture f,Subresource sub,byte[] data,Texture source,int orientation,Color[][] boundaries,Func<IntPtr,long> pixelFormat,Func<long> allocation) {
        var r=new Result{fixture=f.name,type=f.type,face=sub.face,mip=sub.level,width=sub.width,height=sub.height,
            format=((TextureFormat)f.textureFormat).ToString(),graphicsFormat=source.graphicsFormat.ToString(),minRGB=float.MaxValue,maxRGB=float.MinValue};
        Texture2D copy=null,independent=null; long before=allocation==null?0:allocation();
        try {
            Require(sub.offset>=0&&sub.bytes>0&&sub.offset+sub.bytes<=data.Length,"Subresource bounds");
            byte[] raw=new byte[sub.bytes];Buffer.BlockCopy(data,sub.offset,raw,0,sub.bytes);Require(Hash(raw)==sub.sha256,"Subresource SHA mismatch");
            var fmt=(TextureFormat)f.textureFormat;
            int destinationMip=DestinationMip(sub.width,sub.height),baseWidth=sub.width<<destinationMip,baseHeight=sub.height<<destinationMip;
            r.copyBaseWidth=baseWidth;r.copyBaseHeight=baseHeight;r.copyDestinationMip=destinationMip;
            int prefix=0;for(int level=0;level<destinationMip;level++)prefix+=BlockBytes(fmt,baseWidth>>level,baseHeight>>level);
            Require(BlockBytes(fmt,sub.width,sub.height)==raw.Length,"Exact mip payload size mismatch");
            var upload=new byte[prefix+raw.Length];
            copy=TwoD(baseWidth,baseHeight,fmt,destinationMip+1,f.linearConstructor);copy.LoadRawTextureData(upload);copy.Apply(false,true);
            Buffer.BlockCopy(raw,0,upload,prefix,raw.Length);
            independent=TwoD(baseWidth,baseHeight,fmt,destinationMip+1,f.linearConstructor);independent.LoadRawTextureData(upload);independent.Apply(false,true);
            // Full mip-to-mip copy has identical logical dimensions, including 2x2/1x1 tails.
            // Readback downsamples by exactly 2^destinationMip; a distinct-per-level RGBA control
            // independently verifies that the default blit samples this mip, not the blank base.
            Graphics.CopyTexture(source,sub.face,sub.level,copy,0,destinationMip);
            Require(copy.format==fmt&&copy.graphicsFormat==source.graphicsFormat&&independent.graphicsFormat==source.graphicsFormat,"Copy format fallback");
            r.expectedNativeFormat=NativeFormat(source.graphicsFormat);Require(r.expectedNativeFormat!=0,"Not a BC GraphicsFormat");
            if(pixelFormat!=null) {
                r.sourceNativeFormat=pixelFormat(source.GetNativeTexturePtr());r.actualNativeFormat=pixelFormat(copy.GetNativeTexturePtr());
                Require(r.sourceNativeFormat==r.expectedNativeFormat&&r.actualNativeFormat==r.expectedNativeFormat&&pixelFormat(independent.GetNativeTexturePtr())==r.expectedNativeFormat,"Native Metal format mismatch / decompression");
            }
            r.sourceUnityMemory=Profiler.GetRuntimeMemorySizeLong(source);
            Color[] actual=Readback(copy,sub.width,sub.height),reference=Readback(independent,sub.width,sub.height);
            Require(actual.Length==reference.Length,"Readback dimensions");
            for(int i=0;i<actual.Length;i++)for(int c=0;c<4;c++) {
                float a=actual[i][c],b=reference[i][c];Require(Finite(a)&&Finite(b),"Non-finite FP32 sample");
                float error=Mathf.Abs(a-b);r.maximumCopyError=Mathf.Max(r.maximumCopyError,error);
                Require(error<=Mathf.Max(1e-6f,Mathf.Abs(b)*1e-6f),"Copy differs from independent original-byte upload");
                if(c<3){r.minRGB=Mathf.Min(r.minRGB,a);r.maxRGB=Mathf.Max(r.maxRGB,a);}
                if(fmt==TextureFormat.BC6H&&c==3)Require(Mathf.Abs(a-1f)<1e-6f,"BC6H alpha != 1");
            }
            r.comparedPixels=actual.Length;r.hdrAboveOneObserved=fmt==TextureFormat.BC6H&&r.maxRGB>1f;
            if(sub.decodedBlockSamples!=null)foreach(var golden in sub.decodedBlockSamples) {
                Color got=actual[Index(golden.x,golden.y,sub.width,sub.height,orientation)];
                var point=new GoldenCheck{x=golden.x,y=golden.y,actual=got,passed=true};r.goldenSamples.Add(point);
                for(int c=0;c<4;c++) {
                    int encoded=golden.rgba8[c],lo=Math.Max(0,encoded-2),hi=Math.Min(255,encoded+2),table=f.linearConstructor?1:0;
                    point.lower[c]=boundaries[table][lo][c];point.upper[c]=boundaries[table][hi][c];
                    r.maximumGoldenError=Mathf.Max(r.maximumGoldenError,Mathf.Abs(got[c]-boundaries[table][encoded][c]));
                    point.passed&=got[c]>=point.lower[c]-1e-6f&&got[c]<=point.upper[c]+1e-6f;
                }
                Require(point.passed,"Decoder golden outside calibrated +/-2 encoded-byte window at ("+golden.x+","+golden.y+"): "+got+" lower="+point.lower+" upper="+point.upper);
                r.goldenPoints++;
            }
            r.allocationDelta=allocation==null?0:allocation()-before;r.passed=true;
        } catch(Exception ex){r.error=ex.ToString();} finally {Dispose(copy);Dispose(independent);}
        return r;
    }
    // Call only in an isolated sample mode BEFORE game preload. Hooks must be native read-only queries.
    public static IEnumerator Run(string sampleDirectory,string reportPath,Func<IntPtr,long> nativePixelFormat=null,Func<long> nativeAllocationBytes=null) {
        var report=new Report{startedUtc=DateTime.UtcNow.ToString("o"),device=SystemInfo.graphicsDeviceName,colorSpace=QualitySettings.activeColorSpace.ToString(),
            nativeFormatVerificationAvailable=nativePixelFormat!=null,nativeAllocationAvailable=nativeAllocationBytes!=null};
        Application.LogCallback logs=(condition,stack,type)=>{if(type==LogType.Warning||type==LogType.Error||type==LogType.Exception||type==LogType.Assert)report.errors.Add(type+": "+condition+"\n"+stack);};
        Application.logMessageReceived+=logs;
        try {
        report.allocationBefore=nativeAllocationBytes==null?0:nativeAllocationBytes();
        int orientation=-1;Manifest manifest=null;Color[][] boundaries=null;
        try {
            Require(SystemInfo.SupportsRenderTextureFormat(RenderTextureFormat.ARGBFloat),"ARGBFloat unsupported");
            Require(SystemInfo.SupportsTextureFormat(TextureFormat.RGBAFloat),"RGBAFloat readback unsupported");
            Require(QualitySettings.activeColorSpace==ColorSpace.Linear,"This calibrated sRGB oracle requires a Linear project");
            orientation=Calibrate();report.calibration="RGBA32 4x4 only, xFlip="+((orientation&1)!=0)+", yFlip="+((orientation&2)!=0);
            boundaries=CalibrateBoundaries(orientation,report);report.calibration+="; independent 256-code linear/sRGB boundaries tested against D3D11.3 SRGB-side 0.5 ULP and separate two FP16 output ULP, monotonicity and endpoints; inspect complete transferControls/errors";
            manifest=JsonUtility.FromJson<Manifest>(File.ReadAllText(Path.Combine(sampleDirectory,"manifest.json")));
            Require(manifest!=null&&manifest.fixtures!=null&&manifest.fixtures.Length>0,"Empty manifest");
            var checkedTails=new HashSet<string>();foreach(var fixture in manifest.fixtures)foreach(var sub in fixture.subresources){if(DestinationMip(sub.width,sub.height)==0)continue;string id=sub.width+"x"+sub.height;if(!checkedTails.Add(id))continue;CalibrateMipTail(sub.width,sub.height,orientation);report.mipTailCalibrations.Add(id+" exact mip selection PASS");}
        }catch(Exception ex){report.errors.Add(ex.ToString());}
        Save(reportPath,report);yield return null;
        if(manifest!=null&&orientation>=0)foreach(var f in manifest.fixtures) {
            Texture source=null;byte[] bytes=null;
            try {bytes=File.ReadAllBytes(Path.Combine(sampleDirectory,f.file));Require(bytes.Length==f.bytes&&Hash(bytes)==f.sha256,"Fixture hash/length "+f.name);source=CreateSource(f,bytes);}
            catch(Exception ex){report.errors.Add(f.name+": "+ex);}
            if(source!=null) {
                foreach(var sub in f.subresources) {
                    var result=Check(f,sub,bytes,source,orientation,boundaries,nativePixelFormat,nativeAllocationBytes);report.results.Add(result);
                    Save(reportPath,report);yield return null;
                }
                Dispose(source);source=null;
            }
            bytes=null;yield return null;
        }
        yield return Resources.UnloadUnusedAssets();GC.Collect();yield return null;
        report.allocationAfter=nativeAllocationBytes==null?0:nativeAllocationBytes();
        report.sampledSubsetPassed=report.errors.Count==0&&report.results.Count>0;
        foreach(var r in report.results)if(!r.passed)report.sampledSubsetPassed=false;
        // Even a clean rendering test cannot assert native compressed storage without the native hook.
        report.status=report.sampledSubsetPassed?(nativePixelFormat!=null?"sampled-subset-pass":"sampled-subset-pass-native-storage-unverified"):"failed";
        report.finishedUtc=DateTime.UtcNow.ToString("o");Save(reportPath,report);
        } finally {Application.logMessageReceived-=logs;}
    }
}
