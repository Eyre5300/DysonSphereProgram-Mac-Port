using UnityEngine;
// Keep Unity's analytic symmetric perspective path when the original off-axis bias is zero.
public static class PortCameraProjection {
 public static bool Enabled=true;
 public static bool Supported => (Application.platform==RuntimePlatform.OSXPlayer||Application.platform==RuntimePlatform.IPhonePlayer) && SystemInfo.graphicsDeviceType==UnityEngine.Rendering.GraphicsDeviceType.Metal;
 public static bool TryReset(Camera camera,float originalBias){
  if(!Enabled||!Supported||originalBias!=0f)return false;
  camera.ResetProjectionMatrix();return true;
 }
}
