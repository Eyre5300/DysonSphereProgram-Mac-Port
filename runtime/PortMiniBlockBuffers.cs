using System;using System.Collections;using System.Collections.Generic;using UnityEngine;using UnityEngine.Rendering;
// Retire buffers after queued minimap/radar draws have finished using them.
// Pool contents, sizing, shader layout and rendering rules remain unchanged.
public sealed class PortMiniBlockBuffers : MonoBehaviour {
 static PortMiniBlockBuffers instance;static readonly HashSet<ComputeBuffer> pending=new HashSet<ComputeBuffer>();
 public static Action<string> Trace;public static int Released{get;private set;}public static int Pending=>pending.Count;
 public static void Retire(ComputeBuffer buffer){
  if(buffer==null)return;
#if UNITY_STANDALONE_OSX && !UNITY_EDITOR
  if(!buffer.IsValid())return;if(!pending.Add(buffer))return;
  if(instance==null){var go=new GameObject("Mac minimap buffer retirement");DontDestroyOnLoad(go);instance=go.AddComponent<PortMiniBlockBuffers>();}
  Trace?.Invoke("retire frame="+Time.frameCount+" words="+buffer.count*buffer.stride/4+" pending="+Pending);
  instance.StartCoroutine(instance.Finish(buffer));
#else
  buffer.Release();
#endif
 }
 IEnumerator Finish(ComputeBuffer buffer){
  // DrawMeshInstancedIndirect can be queued for more than one camera this frame.
  yield return new WaitForEndOfFrame();
  if(SystemInfo.supportsAsyncGPUReadback){
   // Read one word after this frame's draws. Keep the resource alive until the GPU is done.
   var readback=AsyncGPUReadback.Request(buffer,4,0);
   while(!readback.done)yield return null;
   if(readback.hasError){Trace?.Invoke("readback_error; held until shutdown");yield break;}
   Release(buffer);
  }else{Trace?.Invoke("readback_unsupported; held until shutdown");}
 }
 static void Release(ComputeBuffer b){if(pending.Remove(b)){b.Release();Released++;Trace?.Invoke("released frame="+Time.frameCount+" pending="+Pending);}}
 void OnApplicationQuit(){foreach(var b in pending)if(b!=null&&b.IsValid())b.Release();pending.Clear();}
}
