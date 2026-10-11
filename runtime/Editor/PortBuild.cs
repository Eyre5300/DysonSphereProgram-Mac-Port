using System;using System.IO;using UnityEditor;using UnityEditor.Build.Reporting;using UnityEngine;using UnityEngine.Rendering;
public static class PortBuild {
 public static void BuildMac(){
 PlayerSettings.enableFrameTimingStats=true;
 PlayerSettings.companyName="LocalDSPPort";PlayerSettings.productName="DSPMacDevelopment";
 PlayerSettings.SetApplicationIdentifier(BuildTargetGroup.Standalone,"local.dsp.macdevelopment");
 PlayerSettings.SetScriptingBackend(BuildTargetGroup.Standalone,ScriptingImplementation.Mono2x);
 PlayerSettings.SetArchitecture(BuildTargetGroup.Standalone,1);
 PlayerSettings.SetScriptingDefineSymbolsForGroup(BuildTargetGroup.Standalone,"");
 PlayerSettings.SetUseDefaultGraphicsAPIs(BuildTarget.StandaloneOSX,false);PlayerSettings.SetGraphicsAPIs(BuildTarget.StandaloneOSX,new[]{GraphicsDeviceType.Metal});
 PlayerSettings.defaultIsNativeResolution=true;PlayerSettings.defaultScreenWidth=1440;PlayerSettings.defaultScreenHeight=900;PlayerSettings.fullScreenMode=FullScreenMode.FullScreenWindow;PlayerSettings.runInBackground=true;
 string path=Path.GetFullPath(Environment.GetEnvironmentVariable("DSP_MAC_OUTPUT")??"../../../outputs/DSP-Mac-Development/DSPMac.app");Directory.CreateDirectory(Path.GetDirectoryName(path));
 var report=BuildPipeline.BuildPlayer(new BuildPlayerOptions{scenes=new[]{"Assets/Scenes/level0.unity"},target=BuildTarget.StandaloneOSX,locationPathName=path,options=Environment.GetEnvironmentVariable("DSP_RELEASE_BUILD")=="1"?BuildOptions.None:BuildOptions.Development});
 File.WriteAllText("../mac-game-build-result.txt",report.summary.result+" errors="+report.summary.totalErrors+" bytes="+report.summary.totalSize);
 if(report.summary.result!=BuildResult.Succeeded)throw new Exception("Mac development build failed");
 }
}
