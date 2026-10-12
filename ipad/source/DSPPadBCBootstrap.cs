using System;
using System.Collections;
using System.IO;
using System.Runtime.InteropServices;
using UnityEngine;
// Isolated opt-in diagnostics before original game preload. No ordinary-launch effect.
public static class DSPPadBCBootstrap {
 [DllImport("@rpath/UnityFramework.framework/UnityFramework")]static extern long DSPBCSamplePixelFormat(IntPtr texture);
 [DllImport("@rpath/UnityFramework.framework/UnityFramework")]static extern long DSPBCSampleAllocationBytes();
 [DllImport("@rpath/UnityFramework.framework/UnityFramework")]static extern void DSPPortFinishTest();
 public static IEnumerator Run(){
  AudioListener.volume=0;AudioListener.pause=true;
  DSPPadMemoryInventory.Stage("bc_probe_start");
  string folder=Application.persistentDataPath;
  for(int pass=0;pass<2;pass++){
   string report=Path.Combine(folder,"unity-bc-sample-report-"+pass+".json");
   yield return UnityBCSampleProbe.Run(Path.Combine(folder,"unity-bc-samples"),report,DSPBCSamplePixelFormat,DSPBCSampleAllocationBytes);
   var result=JsonUtility.FromJson<UnityBCSampleProbe.Report>(File.ReadAllText(report));
   if(!result.sampledSubsetPassed){DSPPadMemoryInventory.Stage("bc_probe_failed");yield return new WaitForSecondsRealtime(1);DSPPortFinishTest();yield break;}
   yield return new WaitForSecondsRealtime(2);
  }
  DSPPadMemoryInventory.Stage("bc_probe_sampled_subset_pass");
  yield return new WaitForSecondsRealtime(1);DSPPortFinishTest();
 }
}
