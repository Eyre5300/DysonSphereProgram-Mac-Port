using System;
using System.Runtime.InteropServices;
// Process-local opt-in only. No saved flag or command file can enable tests.
public static class DSPPadDiagnosticLaunch {
 public const string BatchFlag="--dsp-port-test-batch";
 [DllImport("@rpath/UnityFramework.framework/UnityFramework")]
 static extern int DSPAOTDiagnosticFlags();
 [DllImport("@rpath/UnityFramework.framework/UnityFramework")]
 static extern IntPtr DSPAOTBuildVersion();
 [DllImport("@rpath/UnityFramework.framework/UnityFramework")]
 static extern IntPtr DSPAOTBatchIdentifier();
 public static string BatchIdentifier {get {
#if DSP_EMU_IPAD
  return Marshal.PtrToStringAnsi(DSPAOTBatchIdentifier())??"";
#else
  return "";
#endif
 }}
 static string buildVersion;
 public static string BuildVersion {
  get {
   if(buildVersion!=null)return buildVersion;
#if DSP_EMU_IPAD
   string value=Marshal.PtrToStringAnsi(DSPAOTBuildVersion());
#else
   string value=ApplicationVersionFallback();
#endif
   if(string.IsNullOrEmpty(value))throw new InvalidOperationException("Native build version unavailable");
   foreach(char c in value)if(!char.IsLetterOrDigit(c)&&c!='.'&&c!='-'&&c!='_')throw new InvalidOperationException("Invalid native build version");
   return buildVersion=value;
  }
 }
#if !DSP_EMU_IPAD
 static string ApplicationVersionFallback(){return UnityEngine.Application.version;}
#endif
 static bool resolved,allowed;static int nativeFlags;
 public static bool TelemetryAllowed {get{bool batch=AutomaticActionsAllowed;return batch||(nativeFlags&16)!=0;}}
 public static bool FlightAuditRequested=>AutomaticActionsAllowed&&(nativeFlags&4096)!=0;
 public static bool PerformanceAuditRequested=>AutomaticActionsAllowed&&(DSPAOTDiagnosticFlags()&2048)!=0;
 public static bool SceneAuditRequested=>AutomaticActionsAllowed&&(nativeFlags&1024)!=0;
 public static bool PowerAuditRequested=>AutomaticActionsAllowed&&(nativeFlags&512)!=0;
 public static bool WorldAuditRequested=>AutomaticActionsAllowed&&(nativeFlags&256)!=0;
 public static bool InputFilesRequested=>AutomaticActionsAllowed&&(nativeFlags&128)!=0;
 public static bool BCProbeRequested=>AutomaticActionsAllowed&&(nativeFlags&32)!=0;
 public static bool MemoryPressureProbeRequested=>AutomaticActionsAllowed&&(nativeFlags&64)!=0;
 public static bool NativePointerTestAllowed=>AutomaticActionsAllowed&&(nativeFlags&2)!=0;
 public static bool HumanHandoffRequested=>AutomaticActionsAllowed&&(nativeFlags&4)!=0;
 public static string ArgumentError {get;private set;}
 public static bool HasBatchFlag(string[] args){
  if(args==null)return false;
  // Environment.GetCommandLineArgs includes the executable at index zero.
  for(int i=1;i<args.Length;i++)if(string.Equals(args[i],BatchFlag,StringComparison.Ordinal))return true;
  return false;
 }
 public static bool AutomaticActionsAllowed {
  get {
   if(resolved)return allowed;
   resolved=true;
   try{
#if DSP_EMU_IPAD
    // The Mac AOT Environment API does not receive iOS process arguments.
    // Query the native process directly; exact flags only, never saved files.
    nativeFlags=DSPAOTDiagnosticFlags();allowed=(nativeFlags&1)!=0;
#else
    allowed=HasBatchFlag(Environment.GetCommandLineArgs());
#endif
   }
   catch(Exception e){ArgumentError=e.GetType().FullName;allowed=false;}
   return allowed;
  }
 }
}
