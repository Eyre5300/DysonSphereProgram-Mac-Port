using System;using System.Runtime.InteropServices;using UnityEngine;
// USB keyboard usages -> existing Unity KeyCode identities; no action binding.
public static class DSPPadKeyboard {
 [DllImport("@rpath/UnityFramework.framework/UnityFramework")]
 static extern int DSPAOTPollKeyboard([In] int[] codes,[Out] int[] packets,int count);
 static readonly int[] indices=new int[512];static readonly int[] codes,packets;static readonly KeyCode[] keys;
 static readonly DSPPadKeyQueue[] queues;static bool unavailable,native;static readonly bool[] rawPrevious=new bool[512];
 static int modifiers,previousModifiers;static bool escapeDown,escapeUp;public static int PhysicalModifiers {get;private set;}
 public static bool AnyHeld {get;private set;}public static bool AnyDown {get;private set;}
 static DSPPadKeyboard(){
  for(int i=0;i<indices.Length;i++)indices[i]=-1;var kk=new System.Collections.Generic.List<KeyCode>();var cc=new System.Collections.Generic.List<int>();
  Action<int,int> add=(key,code)=>{indices[key]=kk.Count;kk.Add((KeyCode)key);cc.Add(code);};
  for(int i=0;i<26;i++)add(97+i,4+i);for(int i=0;i<9;i++)add(49+i,30+i);add(48,39);add(301,57);add(319,101);
  int[] a={13,27,8,9,32,45,61,91,93,92,59,39,96,44,46,47};int[] b={40,41,42,43,44,45,46,47,48,49,51,52,53,54,55,56};for(int i=0;i<a.Length;i++)add(a[i],b[i]);
  for(int i=0;i<12;i++)add(282+i,58+i);
  a=new[]{316,302,19,277,278,280,127,279,281,275,276,274,273,300,267,268,269,270,271,256,266,272,294,295,296};b=new[]{70,71,72,73,74,75,76,77,78,79,80,81,82,83,84,85,86,87,88,98,99,103,104,105,106};for(int i=0;i<a.Length;i++)add(a[i],b[i]);for(int i=0;i<9;i++)add(257+i,89+i);
  a=new[]{304,303,306,305,308,307,310,309};b=new[]{225,229,224,228,226,230,227,231};for(int i=0;i<a.Length;i++)add(a[i],b[i]);indices[311]=indices[310];indices[312]=indices[309];
  keys=kk.ToArray();codes=cc.ToArray();packets=new int[codes.Length];queues=new DSPPadKeyQueue[codes.Length];for(int i=0;i<queues.Length;i++)queues[i]=new DSPPadKeyQueue();
 }
 public static int HID(KeyCode key){int i=Index(key);return i<0?-1:codes[i];}
 static int Index(KeyCode key){int k=(int)key;return k>=0&&k<indices.Length?indices[k]:-1;}
 static int ModifierBit(KeyCode key){switch(key){case KeyCode.LeftShift:return 1;case KeyCode.RightShift:return 2;case KeyCode.LeftControl:return 4;case KeyCode.RightControl:return 8;case KeyCode.LeftAlt:return 16;case KeyCode.RightAlt:return 32;case KeyCode.LeftCommand:return 64;case KeyCode.RightCommand:return 128;default:return 0;}}
 public static void Poll(){
  previousModifiers=modifiers;native=false;
  if(!unavailable)try{native=DSPAOTPollKeyboard(codes,packets,codes.Length)!=0;}catch(DllNotFoundException){unavailable=true;}catch(EntryPointNotFoundException){unavailable=true;}
  if(!native)Array.Clear(packets,0,packets.Length);
  PhysicalModifiers=0;int retainedModifiers=0;AnyHeld=AnyDown=false;
  for(int i=0;i<keys.Length;i++){
   int packet=packets[i],key=(int)keys[i],bit=ModifierBit(keys[i]);bool supported=native&&(packet&(1<<17))!=0;
   bool raw=Application.isFocused&&(supported?(packet&1)!=0:UnityEngine.Input.GetKey(keys[i]));
   int presses=supported?(packet>>1)&255:UnityEngine.Input.GetKeyDown(keys[i])?1:0;
   if(raw&&!rawPrevious[key]&&presses==0)presses=1;
   if(!Application.isFocused)presses=0;
   rawPrevious[key]=raw;
   if(bit!=0&&raw)PhysicalModifiers|=bit;
   bool wasHeld=queues[i].Held;
   bool ready=keys[i]!=KeyCode.Escape||(!DSPPadEscapeOrder.WaitingForPauseMenu&&(VFInput.axis_button==null||VFInput.axis_button.useCounter[5]==0));
   queues[i].Poll(raw,presses,(packet>>18)&255,Application.isFocused&&!VFInput.inputing&&bit==0,Time.realtimeSinceStartup,ready);
   // UI and fixed world input must refer to the SAME Escape press. Otherwise
   // raw rapid edges close UI now while their queued world edges arrive later.
   if(keys[i]==KeyCode.Escape){escapeDown=!wasHeld&&queues[i].Held;escapeUp=wasHeld&&!queues[i].Held;}
   if(bit==0)retainedModifiers|=queues[i].UnsampledModifiers;
   AnyHeld|=raw;AnyDown|=presses>0;
  }
  // Windows CombineKey recognizes Shift/Ctrl/Alt. Keep Command/Windows GUI
  // independent; never silently turn it into Ctrl or alter exact modifiers.
  modifiers=PhysicalModifiers|retainedModifiers;
 }
 public static void UpdatePublished(){for(int i=0;i<queues.Length;i++)queues[i].Published();}
 public static void FixedSampled(){for(int i=0;i<queues.Length;i++)queues[i].Sampled();}
 public static void ClearEscape(){queues[Index(KeyCode.Escape)].ResetDelivery(false);escapeDown=escapeUp=false;}
 public static bool Read(KeyCode key,int mode,out bool value){
  value=false;int i=Index(key);if(i<0)return false;if(DSPPadInputMode.UseTouch||DSPPadDocuments.Busy)return true;
  int bit=ModifierBit(key);if(bit!=0){value=mode==0?(modifiers&bit)!=0:mode==1?(modifiers&bit)!=0&&(previousModifiers&bit)==0:(modifiers&bit)==0&&(previousModifiers&bit)!=0;return true;}
  if(key==KeyCode.Escape){value=Application.isFocused&&(mode==0?queues[i].Held:mode==1?escapeDown:escapeUp);return true;}
  if(!native||(packets[i]&(1<<17))==0)return false;
  if(!Application.isFocused)return true;
  value=mode==0?queues[i].Held:mode==1?((packets[i]>>1)&255)!=0:((packets[i]>>9)&255)!=0;return true;
 }
 public static void Reset(){
  bool preserve=DSPPadEscapeOrder.ResettingPauseMenu,wasEscape=rawPrevious[(int)KeyCode.Escape];
  for(int i=0;i<queues.Length;i++){if(preserve&&keys[i]==KeyCode.Escape)queues[i].ResetDelivery(true);else queues[i].Clear();}
  Array.Clear(rawPrevious,0,rawPrevious.Length);if(preserve)rawPrevious[(int)KeyCode.Escape]=wasEscape;
  modifiers=previousModifiers=PhysicalModifiers=0;AnyHeld=AnyDown=escapeDown=escapeUp=false;DSPPadEscapeOrder.Consumed();
 }
}
