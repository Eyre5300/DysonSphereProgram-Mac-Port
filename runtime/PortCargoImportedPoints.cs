using System;using System.IO;using UnityEngine;using UnityEngine.Rendering;
// Apple Metal Mac: retain every imported pose at original precision. Only
// uninitialized zero tail capacity is deferred; restore it before any geometry
// mutation. Byte buffers, chunk arrays, capacity field and all original rules
// remain unchanged. No models, geometry samples or active data are removed.
public static class PortCargoImportedPoints {
 public static bool Enabled=true;
 public static readonly bool Supported=Application.platform==RuntimePlatform.OSXPlayer&&SystemInfo.graphicsDeviceType==GraphicsDeviceType.Metal&&SystemInfo.graphicsDeviceName.StartsWith("Apple");
 public static long ImportedPaths,DeferredZeroTailBytes,RestoredPaths;
 public static void ReadCapacity(BinaryReader reader,ref int capacity,ref int length,ref byte[] buffer,ref Vector3[] position,ref Quaternion[] rotation){
  int cap=reader.ReadInt32(),count=reader.ReadInt32();
  if(cap<0||count<0||count>cap)throw new InvalidDataException("Invalid cargo path capacity/length");
  capacity=cap;length=count;buffer=new byte[cap];position=new Vector3[count];rotation=new Quaternion[count];
  ImportedPaths++;DeferredZeroTailBytes+=(long)(cap-count)*28;
 }
 public static void Restore(ref Vector3[] position,ref Quaternion[] rotation,int capacity){
  if(position==null||rotation==null)return;
  if(position.Length==capacity&&rotation.Length==capacity)return;
  // Freshly imported unused tail was zero in the original implementation.
  if(position.Length>capacity||rotation.Length>capacity)throw new InvalidOperationException("Cargo geometry capacity mismatch");
  Array.Resize(ref position,capacity);Array.Resize(ref rotation,capacity);RestoredPaths++;
 }
}
