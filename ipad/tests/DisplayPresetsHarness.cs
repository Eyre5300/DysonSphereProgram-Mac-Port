// Synthetic engine boundary to execute the real display adapter on the host.
using System;using System.Collections.Generic;using UnityEngine;
namespace UnityEngine {
 public enum RuntimePlatform {OSXPlayer,IPhonePlayer} public enum FullScreenMode {FullScreenWindow,Windowed}
 public struct RefreshRate {public uint numerator,denominator;}
 public struct Resolution {public int width,height;public RefreshRate refreshRateRatio;}
 public struct Vector2Int {public int x,y;public Vector2Int(int a,int b){x=a;y=b;}}
 public static class Application {public static RuntimePlatform platform=RuntimePlatform.IPhonePlayer;}
 public static class Mathf {public static int Min(int a,int b){return Math.Min(a,b);}public static int Max(int a,int b){return Math.Max(a,b);}public static int RoundToInt(float a){return (int)Math.Round(a);}}
 public static class Debug {public static void Log(object text){}}
 public static class Screen {public static Resolution currentResolution,applied;public static FullScreenMode mode;public static void SetResolution(int w,int h,FullScreenMode m,RefreshRate r){applied=new Resolution{width=w,height=h,refreshRateRatio=r};mode=m;}}
}
public enum EOptionDisplayMode {BorderlessFullScreenWithCursorConfined,Windowed}
public struct GameOption {public Resolution resolution;public EOptionDisplayMode displayMode;}
public static class GameResolutions {
 public struct Resolution {public int width,height;public string displayName;public RefreshRate rawRefreshRate,formattedRefreshRate;}
 public static List<Resolution> choices;
 public static List<Resolution> GetResolutions(EOptionDisplayMode mode){return choices;}
 public static RefreshRate DoubleToRefreshRate(double rate){return new RefreshRate{numerator=(uint)rate,denominator=1};}
 public static UnityEngine.Resolution ToEngineResolution(this Resolution r){return new UnityEngine.Resolution{width=r.width,height=r.height,refreshRateRatio=r.rawRefreshRate};}
}
public static class Test {
 static void Check(bool value,string why){if(!value)throw new Exception(why);}
 public static void Main(string[] args){
  int nw=int.Parse(args[0]),nh=int.Parse(args[1]),sw=int.Parse(args[2]),sh=int.Parse(args[3]),ew=int.Parse(args[4]),eh=int.Parse(args[5]);
  int rate=args.Length>6?int.Parse(args[6]):120;
  Screen.currentResolution=new Resolution{width=nw,height=nh,refreshRateRatio=GameResolutions.DoubleToRefreshRate(rate)};
  int nativeWidth=Math.Max(nw,nh),nativeHeight=Math.Min(nw,nh);
  foreach(bool windowed in new[]{false,true}){
   var list=new List<GameResolutions.Resolution>{new GameResolutions.Resolution{width=2266,height=1488}};
   PortDisplayPresets.Add(list,windowed);int count=list.Count;Check(count==5,"expected native plus four render widths");PortDisplayPresets.Add(list,windowed);Check(list.Count==count,"duplicate modes");
   var seen=new HashSet<string>();foreach(var r in list){Check(seen.Add(r.width+"x"+r.height),"duplicate size");Check((long)Math.Abs((long)r.width*nativeHeight-(long)r.height*nativeWidth)<=nativeWidth,"aspect");Check(r.rawRefreshRate.numerator==rate&&r.rawRefreshRate.denominator==1,"refresh rate");}
   if(nativeWidth==2752&&nativeHeight==2064)foreach(int w in new[]{1280,1376,1600,1920,2752})Check(list.Exists(r=>r.width==w&&r.height==w*3/4),"missing 4:3 preset");
   GameResolutions.choices=list;
  }
  var option=new GameOption{resolution=new Resolution{width=sw,height=sh,refreshRateRatio=GameResolutions.DoubleToRefreshRate(60)}};
  PortDisplayPresets.ConfigureStartup(ref option);Check(option.resolution.width==ew&&option.resolution.height==eh,"saved resolution not preserved/fallback wrong");
  Check(option.resolution.refreshRateRatio.numerator==rate,"stale refresh rate not normalized");
  PortDisplayPresets.Apply(option.resolution,FullScreenMode.Windowed);Check(Screen.applied.width==ew&&Screen.applied.height==eh&&Screen.mode==FullScreenMode.FullScreenWindow,"startup render size");
  var later=GameResolutions.choices[GameResolutions.choices.Count-1].ToEngineResolution();PortDisplayPresets.Apply(later,FullScreenMode.Windowed);Check(Screen.applied.width==later.width&&Screen.applied.height==later.height,"later apply overridden");
  Console.WriteLine("PASS native="+nw+"x"+nh+" saved="+sw+"x"+sh+" selected="+ew+"x"+eh);
 }
}
