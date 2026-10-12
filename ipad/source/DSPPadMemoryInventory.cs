using System;
using System.Collections.Generic;
using System.IO;
using System.Runtime.InteropServices;
using UnityEngine;
using UnityEngine.Profiling;

// Opt-in resource census. Reads original resources; never changes their lifetime or quality.
public static class DSPPadMemoryInventory {
 [DllImport("@rpath/UnityFramework.framework/UnityFramework")] static extern void DSPAOTMemoryStage(string stage);
 [DllImport("@rpath/UnityFramework.framework/UnityFramework")] static extern int DSPAOTCaptureMetalCensus(string label);
 public static bool CaptureNative(string label){return DSPPadDiagnosticLaunch.TelemetryAllowed&&DSPAOTCaptureMetalCensus(label)==1;}
 [Serializable] sealed class Item {public string name,type,format;public int id,width,height,depth,mips,samples,memoryless;public bool readable,created;public long bytes;}
 [Serializable] sealed class Report {public string stage,preloadText;public float seconds,preloadProgress;public int frame;public long managed,allocated,reserved,textureBytes,meshBytes,audioBytes;public List<Item> textures=new List<Item>();public List<Item> meshes=new List<Item>();public List<Item> audio=new List<Item>();public List<string> errors=new List<string>();}
 [Serializable] sealed class ObjectGroup {public string type;public long bytes;public int count;}
 [Serializable] sealed class ObjectAudit {public string scope="Unity runtime estimates may overlap; not a resident-memory partition";public string build,batch;public long managed,heap,allocated,reserved,graphics;public List<ObjectGroup> groups=new List<ObjectGroup>();public List<Item> largest=new List<Item>();}
 public static void StartupObjects(){
  if(!DSPPadDiagnosticLaunch.MemoryPressureProbeRequested)return;
  var a=new ObjectAudit{build=DSPPadDiagnosticLaunch.BuildVersion,batch=DSPPadDiagnosticLaunch.BatchIdentifier,managed=GC.GetTotalMemory(false),heap=Profiler.GetMonoHeapSizeLong(),allocated=Profiler.GetTotalAllocatedMemoryLong(),reserved=Profiler.GetTotalReservedMemoryLong(),graphics=Profiler.GetAllocatedMemoryForGraphicsDriver()};
  var groups=new Dictionary<string,ObjectGroup>();
  foreach(var o in Resources.FindObjectsOfTypeAll<UnityEngine.Object>()){
   if(!o)continue;string type=o.GetType().Name;ObjectGroup g;if(!groups.TryGetValue(type,out g)){g=new ObjectGroup{type=type};groups[type]=g;}
   long n=Profiler.GetRuntimeMemorySizeLong(o);g.bytes+=n;g.count++;
   if(a.largest.Count<32||n>a.largest[a.largest.Count-1].bytes){a.largest.Add(new Item{name=o.name,type=type,id=o.GetInstanceID(),bytes=n});a.largest.Sort((x,y)=>y.bytes.CompareTo(x.bytes));if(a.largest.Count>32)a.largest.RemoveAt(32);}
  }
  a.groups.AddRange(groups.Values);a.groups.Sort((x,y)=>y.bytes.CompareTo(x.bytes));File.WriteAllText(Path.Combine(Application.persistentDataPath,"memory-objects-"+a.build+"-"+a.batch+".json"),JsonUtility.ToJson(a,true));
 }
 static int preloadBucket=-1;
 static string phase="boot";
 static bool finished;
 static float lastPoll;
 public static void Stage(string value){if(!DSPPadDiagnosticLaunch.TelemetryAllowed)return;phase=value;DSPAOTMemoryStage(value);Capture(value,null);}
 public static void Poll(){
  if(!DSPPadDiagnosticLaunch.TelemetryAllowed||finished||Time.realtimeSinceStartup-lastPoll<.5f)return;
  lastPoll=Time.realtimeSinceStartup;
  var p=UnityEngine.Object.FindObjectOfType<VFPreload>();
  if(p==null)return;
  int bucket=Mathf.FloorToInt(p.progress*20);
  string label="preload-"+bucket.ToString("D2")+" "+(p.stateText?p.stateText.text:"");
  DSPAOTMemoryStage(label);
  if(bucket!=preloadBucket){preloadBucket=bucket;Capture("preload-"+bucket.ToString("D2"),p);}
  if(VFPreload.done){finished=true;DSPAOTMemoryStage(phase);}
 }
 static void Capture(string stage,VFPreload preload){
  var r=new Report{stage=stage,seconds=Time.realtimeSinceStartup,frame=Time.frameCount,managed=GC.GetTotalMemory(false),allocated=Profiler.GetTotalAllocatedMemoryLong(),reserved=Profiler.GetTotalReservedMemoryLong(),preloadProgress=preload?preload.progress:-1,preloadText=preload&&preload.stateText?preload.stateText.text:""};
  foreach(var t in Resources.FindObjectsOfTypeAll<Texture>()){
   if(!t)continue;
   try{
    var i=new Item{name=t.name,type=t.GetType().Name,id=t.GetInstanceID(),width=t.width,height=t.height,bytes=Profiler.GetRuntimeMemorySizeLong(t)};
    if(t is Texture2D){var x=(Texture2D)t;i.format=x.format.ToString();i.mips=x.mipmapCount;i.readable=x.isReadable;}
    else if(t is Cubemap){var x=(Cubemap)t;i.format=x.format.ToString();i.mips=x.mipmapCount;i.readable=x.isReadable;i.depth=6;}
    else if(t is Texture2DArray){var x=(Texture2DArray)t;i.format=x.format.ToString();i.mips=x.mipmapCount;i.readable=x.isReadable;i.depth=x.depth;}
    else if(t is Texture3D){var x=(Texture3D)t;i.format=x.format.ToString();i.mips=x.mipmapCount;i.readable=x.isReadable;i.depth=x.depth;}
    else if(t is RenderTexture){var x=(RenderTexture)t;i.format=x.graphicsFormat.ToString();i.samples=x.antiAliasing;i.memoryless=(int)x.memorylessMode;i.created=x.IsCreated();i.depth=x.depth;}
    r.textureBytes+=i.bytes;r.textures.Add(i);
   }catch(Exception ex){r.errors.Add(t.name+": "+ex.Message);}
  }
  foreach(var m in Resources.FindObjectsOfTypeAll<Mesh>()){if(!m)continue;long n=Profiler.GetRuntimeMemorySizeLong(m);r.meshBytes+=n;r.meshes.Add(new Item{name=m.name,type="Mesh",id=m.GetInstanceID(),width=m.vertexCount,readable=m.isReadable,bytes=n});}
  foreach(var a in Resources.FindObjectsOfTypeAll<AudioClip>()){if(!a)continue;long n=Profiler.GetRuntimeMemorySizeLong(a);r.audioBytes+=n;r.audio.Add(new Item{name=a.name,type="AudioClip",id=a.GetInstanceID(),width=a.samples,depth=a.channels,bytes=n});}
  r.textures.Sort((a,b)=>b.bytes.CompareTo(a.bytes));r.meshes.Sort((a,b)=>b.bytes.CompareTo(a.bytes));
  string folder=Path.Combine(Application.persistentDataPath,"memory-inventory");Directory.CreateDirectory(folder);
  File.WriteAllText(Path.Combine(folder,Time.frameCount.ToString("D8")+"-"+stage+".json"),JsonUtility.ToJson(r,true));
 }
}
