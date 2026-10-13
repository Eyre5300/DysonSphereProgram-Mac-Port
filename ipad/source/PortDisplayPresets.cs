using System.Collections.Generic;
using UnityEngine;

public static class PortDisplayPresets {
 public struct Preset { public string name; public int width,height; public Preset(string n,int w,int h){name=n;width=w;height=h;} }
 public static readonly Preset[] Devices={new Preset("iPad Air 11\"",2360,1640),new Preset("iPad Air 13\"",2732,2048),new Preset("iPad Pro 11\"",2420,1668),new Preset("iPad Pro 13\"",2752,2064)};
 public static bool StartupConfigured { get; private set; }
 public static Resolution StartupResolution { get; private set; }
 static bool startupPending;

 public static bool TryGetNativeResolution(out Resolution native) {
  native=Screen.currentResolution;
#if !DSP_EMU_IPAD && (UNITY_STANDALONE_OSX || UNITY_EDITOR_OSX)
  // Read the display containing the game window, including its current pixel size/rate.
  var display=Screen.mainWindowDisplayInfo;
  if(display.width>0&&display.height>0){native.width=display.width;native.height=display.height;native.refreshRateRatio=display.refreshRate;}
#elif (UNITY_IOS || DSP_EMU_IPAD) && !UNITY_EDITOR
  // DSP uses landscape; use device-reported dimensions, not a named iPad preset.
  int width=native.width,height=native.height;
  native.width=Mathf.Max(width,height);native.height=Mathf.Min(width,height);
#endif
  if(native.width<=0||native.height<=0)return false;
  if(native.refreshRateRatio.numerator==0||native.refreshRateRatio.denominator==0)
   native.refreshRateRatio=GameResolutions.DoubleToRefreshRate(60);
  return true;
 }

 public static void ConfigureStartup(ref GameOption option) {
  if(StartupConfigured)return;
  if(Application.platform!=RuntimePlatform.OSXPlayer&&Application.platform!=RuntimePlatform.IPhonePlayer)return;
  Resolution native;
  if(!TryGetNativeResolution(out native))return;
  var selected=native;
#if UNITY_IOS || DSP_EMU_IPAD
  // The window remains fullscreen; its rendering resolution is a saved option.
  var choices=GameResolutions.GetResolutions(EOptionDisplayMode.BorderlessFullScreenWithCursorConfined);
  if(choices!=null)foreach(var item in choices)
   if(item.width==option.resolution.width&&item.height==option.resolution.height&&SameAspect(item.width,item.height,native)){
    selected=item.ToEngineResolution();break;
   }
#endif
  option.resolution=selected;
  option.displayMode=EOptionDisplayMode.BorderlessFullScreenWithCursorConfined;
  StartupResolution=selected;StartupConfigured=true;startupPending=true;
  Debug.Log("DSP_PORT_STARTUP_RENDER_FULLSCREEN "+selected.width+"x"+selected.height);
 }

 static bool SameAspect(int width,int height,Resolution native){
  // Accept at most one pixel of rounding for non-4:3 iPad displays.
  return width>0&&height>0&&width<=native.width&&height<=native.height&&
   System.Math.Abs((long)width*native.height-(long)height*native.width)<=native.width;
 }
 static void AddRenderSize(List<GameResolutions.Resolution> list,Resolution native,int width,int height,string label){
  if(!SameAspect(width,height,native))return;
  var item=new GameResolutions.Resolution{width=width,height=height,rawRefreshRate=native.refreshRateRatio,formattedRefreshRate=native.refreshRateRatio,displayName=label};
  int index=list.FindIndex(r=>r.width==width&&r.height==height);
  if(index<0)list.Add(item);else list[index]=item;
 }
 public static void Add(List<GameResolutions.Resolution> list,bool windowed){
  Resolution native;bool hasNative=TryGetNativeResolution(out native);
#if UNITY_IOS || DSP_EMU_IPAD
  if(hasNative){
   // Only the connected display's aspect ratio; names of other devices do not
   // represent usable render modes on this iPad. Refresh rate remains native.
   list.Clear();
   AddRenderSize(list,native,native.width,native.height,"原生分辨率");
   foreach(int width in new[]{1920,1600,1376,1280}){
    if(width>=native.width)continue;
    int height=Mathf.RoundToInt((float)width*native.height/native.width);
    AddRenderSize(list,native,width,height,"渲染分辨率");
   }
   return;
  }
#endif
  foreach(var p in Devices){
   int index=list.FindIndex(r=>r.width==p.width&&r.height==p.height);
   if(index<0){list.Add(new GameResolutions.Resolution{width=p.width,height=p.height,rawRefreshRate=GameResolutions.DoubleToRefreshRate(60),formattedRefreshRate=GameResolutions.DoubleToRefreshRate(60),displayName=p.name});}
   else {var r=list[index];r.displayName=p.name;list[index]=r;}
  }
  if(windowed){foreach(var size in new[]{new Vector2Int(1280,960),new Vector2Int(1600,1200),new Vector2Int(1920,1440)})if(!list.Exists(r=>r.width==size.x&&r.height==size.y))list.Add(new GameResolutions.Resolution{width=size.x,height=size.y,rawRefreshRate=GameResolutions.DoubleToRefreshRate(60),formattedRefreshRate=GameResolutions.DoubleToRefreshRate(60)});}
  else if(hasNative){int index=list.FindIndex(r=>r.width==native.width&&r.height==native.height);var r=new GameResolutions.Resolution{width=native.width,height=native.height,rawRefreshRate=native.refreshRateRatio,formattedRefreshRate=native.refreshRateRatio,displayName="自动适应屏幕"};if(index>=0)list[index]=r;else list.Insert(0,r);}
 }

 public static void Apply(Resolution resolution,FullScreenMode mode){
#if (UNITY_IOS || DSP_EMU_IPAD) && !UNITY_EDITOR
  if(startupPending){startupPending=false;var native=StartupResolution;Screen.SetResolution(native.width,native.height,FullScreenMode.FullScreenWindow,native.refreshRateRatio);return;}
  // iPadOS owns the fullscreen window; respect the original chosen render size.
  Screen.SetResolution(resolution.width,resolution.height,FullScreenMode.FullScreenWindow,resolution.refreshRateRatio);return;
#elif UNITY_STANDALONE_OSX && !UNITY_EDITOR
  // Consume only the startup override. Later user changes retain the original Apply path.
  if(startupPending){startupPending=false;var native=StartupResolution;Screen.SetResolution(native.width,native.height,FullScreenMode.FullScreenWindow,native.refreshRateRatio);return;}
#endif
  Screen.SetResolution(resolution.width,resolution.height,mode,resolution.refreshRateRatio);
 }
}
