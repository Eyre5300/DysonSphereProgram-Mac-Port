using System.IO;using UnityEngine;
// Opt-in while lifecycle validation is in progress. No size, format or MSAA change.
public static class PortUIRenderTargets {
 public static readonly bool Enabled=Application.platform==RuntimePlatform.OSXPlayer&&File.Exists(Path.Combine(Application.persistentDataPath,"port-lazy-ui-targets.flag"));
 public static void Prepare(RenderTexture texture,string owner){texture.name=owner;if(Enabled&&!texture.IsCreated())texture.Create();}
}
