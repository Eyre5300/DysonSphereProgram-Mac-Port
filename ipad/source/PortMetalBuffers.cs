using UnityEngine;
using System.Collections.Generic;
public static class PortMetalBuffers {
 static ComputeBuffer zero;
 static readonly Dictionary<int,int> lengths=new Dictionary<int,int>();
 static readonly string[] names=new string[]{
   "_AnimBuffer",
   "_AntBuffer",
   "_AstroBuffer",
   "_BarBuffer",
   "_BeltStateBuffer",
   "_Buffer",
   "_Buffer1",
   "_Buffer2",
   "_BulletBuffer",
   "_CargoBytesBuffer",
   "_CarrierBuffer",
   "_Color256Buffer",
   "_Color32Buffer",
   "_ColorBuffer",
   "_CombatStatBuffer",
   "_CourierBuffer",
   "_CullBuffer",
   "_CullCheckDirBuffer",
   "_CursorBuffer",
   "_CursorCellsBuffer",
   "_DataBuffer",
   "_DroneBuffer",
   "_ExtraBuffer",
   "_ExtraBuffer0",
   "_ExtraBuffer1",
   "_Global_GalaxyAstroBuffer",
   "_Global_Int32_Vars",
   "_Global_ItemDescBuffer",
   "_Global_ItemIconIndexBuffer",
   "_Global_RecipeIconIndexBuffer",
   "_Global_SignalIconIndexBuffer",
   "_Global_Starmap_GalaxyAstroBuffer",
   "_Global_TechIconIndexBuffer",
   "_Histogram",
   "_IdBuffer",
   "_IndexBuffer",
   "_InfoBuffer",
   "_InstBuffer",
   "_ItemIdBuffer",
   "_MarkerBuffer",
   "_NearIdBuffer",
   "_NodeBuffer",
   "_ObjBuffer",
   "_ObjectBuffer",
   "_OffsetsBuffer",
   "_OrbitColor",
   "_OrdinalMappingBuffer",
   "_PathStateBuffer",
   "_PeriodCargoBytesBuffer",
   "_Pose2Buffer",
   "_Powers",
   "_PreSelectedReforms",
   "_PreviewReformColors",
   "_PreviewReforms",
   "_ProgressBuffer",
   "_RefNormBuffer",
   "_RocketBuffer",
   "_SampleBuffer",
   "_ScaleBuffer",
   "_SelectedReforms",
   "_ShipBuffer",
   "_SignBuffer",
   "_SpaceInstBuffer",
   "_Starmap_AstroBuffer",
   "_StateBuffer",
   "_SwarmBuffer",
   "_SwarmInfoBuffer",
   "_TruckBuffer",
   "_VertaBuffer",
   "_WarningBuffer",
   "_WarningIndexBuffer"
 };
 static void Ensure(){if(zero!=null)return;
  zero=new ComputeBuffer(16,4);zero.SetData(new uint[16]);
  foreach(string name in names)lengths[Shader.PropertyToID(name)]=Shader.PropertyToID("_PortWords"+name);
 }
 static int Words(ComputeBuffer buffer){return buffer==null?0:buffer.count*(buffer.stride/4);}
 [RuntimeInitializeOnLoadMethod(RuntimeInitializeLoadType.AfterAssembliesLoaded)]
 static void Install(){
  Ensure();
  // Real material and global bindings subsequently replace these defaults.
  foreach(string name in names)SetGlobalBuffer(name,null);
  Application.quitting+=Release;
 }
 public static void SetGlobalBuffer(string name,ComputeBuffer buffer){SetGlobalBuffer(Shader.PropertyToID(name),buffer);}
 public static void SetGlobalBuffer(int name,ComputeBuffer buffer){Ensure();Shader.SetGlobalBuffer(name,buffer??zero);if(lengths.TryGetValue(name,out int id))Shader.SetGlobalInt(id,Words(buffer));}
 public static void PortSetBuffer(this Material mat,string name,ComputeBuffer buffer){PortSetBuffer(mat,Shader.PropertyToID(name),buffer);}
 public static void PortSetBuffer(this Material mat,int name,ComputeBuffer buffer){Ensure();mat.SetBuffer(name,buffer??zero);if(lengths.TryGetValue(name,out int id))mat.SetInt(id,Words(buffer));}
 public static void PortSetBuffer(this MaterialPropertyBlock mat,string name,ComputeBuffer buffer){PortSetBuffer(mat,Shader.PropertyToID(name),buffer);}
 public static void PortSetBuffer(this MaterialPropertyBlock mat,int name,ComputeBuffer buffer){Ensure();mat.SetBuffer(name,buffer??zero);if(lengths.TryGetValue(name,out int id))mat.SetInt(id,Words(buffer));}
 // Compute shaders keep their original bindings and layout.
 public static void PortSetBuffer(this ComputeShader shader,int kernel,string name,ComputeBuffer buffer){shader.SetBuffer(kernel,name,buffer);}
 public static void PortSetBuffer(this ComputeShader shader,int kernel,int name,ComputeBuffer buffer){shader.SetBuffer(kernel,name,buffer);}
 static void Release(){if(zero!=null){zero.Release();zero=null;}}
}
