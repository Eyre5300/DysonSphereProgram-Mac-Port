using System;using System.Diagnostics;using System.Globalization;using System.IO;using System.Runtime.InteropServices;using UnityEngine;using UnityEngine.Profiling;
// Opt-in measurements only. Two startup collections and at most two bounded
// critical-pressure collections; never changes assets, textures or game rules.
public static class DSPPadMemoryPressureProbe {
 [DllImport("@rpath/UnityFramework.framework/UnityFramework")] static extern ulong DSPAOTAvailableAppMemory();
 [DllImport("@rpath/UnityFramework.framework/UnityFramework")] static extern ulong DSPAOTPhysicalFootprint();
 [DllImport("@rpath/UnityFramework.framework/UnityFramework")] static extern ulong DSPAOTGPUAllocated();
 static bool installed,pending,collecting;static float next,afterTime;static int count,pressureCount,afterFrame;static string file,afterReason;static bool nextFramePending,secondPending;
 public static void Install(){if(!DSPPadDiagnosticLaunch.MemoryPressureProbeRequested||installed)return;installed=true;file=Path.Combine(Application.persistentDataPath,"memory-pressure-"+DSPPadDiagnosticLaunch.BuildVersion+"-"+DSPPadDiagnosticLaunch.BatchIdentifier+".tsv");File.WriteAllText(file,"reason\tframe\tseconds\tmanaged_used\tmanaged_heap\tcollections\tunity_allocated\tunity_reserved\tphysical\tgpu_allocated\tavailable\tmilliseconds\n");Application.lowMemory+=LowMemory;}
 static void LowMemory(){pending=true;}
 [DllImport("@rpath/UnityFramework.framework/UnityFramework")] static extern int DSPAOTCaptureVMMap();
 public static void AfterStartup(){if(DSPPadDiagnosticLaunch.MemoryPressureProbeRequested){DSPPadMemoryInventory.StartupObjects();DSPAOTCaptureVMMap();}Boundary("dsp_start_complete");}
 public static void BeforeMenuDemo(){Boundary("before_menu_demo");}
 static void Boundary(string reason){if(!DSPPadDiagnosticLaunch.MemoryPressureProbeRequested)return;Install();Collect(reason);}
 static void Sample(string reason,double ms=0){File.AppendAllText(file,string.Join("\t",reason,Time.frameCount,Time.realtimeSinceStartup.ToString("R",CultureInfo.InvariantCulture),GC.GetTotalMemory(false),Profiler.GetMonoHeapSizeLong(),GC.CollectionCount(0),Profiler.GetTotalAllocatedMemoryLong(),Profiler.GetTotalReservedMemoryLong(),DSPAOTPhysicalFootprint(),DSPAOTGPUAllocated(),DSPAOTAvailableAppMemory(),ms.ToString("R",CultureInfo.InvariantCulture))+"\n");}
 public static void Poll(){
  if(!installed||collecting)return;
  if(nextFramePending&&Time.frameCount>afterFrame){Sample(afterReason+"_next_frame");nextFramePending=false;}
  if(secondPending&&Time.realtimeSinceStartup>=afterTime){Sample(afterReason+"_after_1s");secondPending=false;}
  if(Time.realtimeSinceStartup<next)return;next=Time.realtimeSinceStartup+1;
  bool warning=pending;pending=false;if(warning)Sample("application_low_memory_event");
  if(pressureCount>=2||count>=4)return;
  if(!warning&&DSPAOTAvailableAppMemory()>=192UL*1024*1024)return;
  pressureCount++;Collect(warning?"application_low_memory":"available_below_192MiB");
 }
 static void Collect(string reason){if(!installed||collecting||count>=4)return;collecting=true;count++;try{Sample(reason+"_before");var sw=Stopwatch.StartNew();GC.Collect();sw.Stop();Sample(reason+"_after",sw.Elapsed.TotalMilliseconds);afterReason=reason;afterFrame=Time.frameCount;afterTime=Time.realtimeSinceStartup+1;nextFramePending=secondPending=true;}finally{collecting=false;next=Time.realtimeSinceStartup+10;}}
}
