using System;
using System.IO;
using UnityEngine;
using UnityEngine.Rendering;

// Keep the original resolved HDR target, depth, dimensions and sample count.
// Only the transient multisample attachment storage changes on validated Mac GPUs.
public static class PortMemorylessUI {
 public static bool Enabled => Application.platform == RuntimePlatform.OSXPlayer
  && SystemInfo.graphicsDeviceType == GraphicsDeviceType.Metal
  && SystemInfo.graphicsDeviceName.StartsWith("Apple", StringComparison.OrdinalIgnoreCase)
  && !File.Exists(Path.Combine(Application.persistentDataPath, "port-disable-ui-memoryless.flag"));

 public static void Configure(RenderTexture texture) {
  if (!Enabled || texture == null || texture.IsCreated()
   || texture.antiAliasing != 4 || texture.bindTextureMS
   || texture.format != RenderTextureFormat.ARGBHalf) return;
  texture.memorylessMode |= RenderTextureMemoryless.MSAA;
 }
}
