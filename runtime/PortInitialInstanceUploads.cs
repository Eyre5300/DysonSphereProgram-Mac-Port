using UnityEngine;
using UnityEngine.Rendering;
// Defer redundant intermediate uploads during original factory loading.
// Stage 8 submits all buffers before factoryLoaded allows rendering; loaded-world edits stay immediate.
// The original stage8 complete SyncInstBuffer remains unmodified.
public static class PortInitialInstanceUploads {
 public static bool Enabled=true;public static long DeferredCalls;public static readonly bool Supported=Application.platform==RuntimePlatform.OSXPlayer&&SystemInfo.graphicsDeviceType==GraphicsDeviceType.Metal&&SystemInfo.graphicsDeviceName.StartsWith("Apple");
 public static bool Defer(ObjectRenderer renderer){if(!Enabled||(!GameMain.isRunning&&!GameMain.isLoading)||DSPGame.IsMenuDemo||renderer==null||renderer.manager==null||renderer.bpManager!=null||!Supported)return false;var planet=renderer.manager.activePlanet;if(planet==null||!planet.factoryLoading||planet.factoryLoaded)return false;DeferredCalls++;return true;}
}
