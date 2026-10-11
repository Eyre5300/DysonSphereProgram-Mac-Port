from pathlib import Path
import re
root=Path('work/dsp-runtime/port-project/Assets/Scripts/Assembly-CSharp')
base=Path('work/dsp-runtime/recovered-project/ExportedProject/Assets/Scripts/Assembly-CSharp')
cond='UNITY_IOS || UNITY_EDITOR_OSX || UNITY_STANDALONE_OSX'
def edit(name,fn):
 s=fn((base/name).read_text());(root/name).write_text(s)
def wrap_method(s,signature,body):
 start=s.index(signature); op=s.index('{',start);level=1;i=op+1
 while level:
  if s[i]=='{':level+=1
  if s[i]=='}':level-=1
  i+=1
 return s[:op+1]+'\n#if '+cond+'\n'+body+'\n#else'+s[op+1:i-1]+'\n#endif\n'+s[i-1:]
def win(s):
 for sig,body in [('public static double GetDpiScale()','return 1.0;'),('public static int GetTitleBarHeight()','return 0;'),('public static int GetTaskbarHeight()','return 0;')]:s=wrap_method(s,sig,body)
 return s
edit('WinAPI/WinAPIs.cs',win)
edit('TimingPrecision.cs',lambda s:wrap_method(wrap_method(s,'public static uint TimeBeginPeriod(uint uMilliseconds)','return 0;'),'public static uint TimeEndPeriod(uint uMilliseconds)','return 0;'))
edit('SteamManager.cs',lambda s:wrap_method(s,'protected virtual void Awake()','// This local port has no Steam client SDK. Keep Initialized false.\ns_instance = this;\nm_bInitialized = false;'))
edit('StandaloneManager.cs',lambda s:s.replace('\tpublic static bool init => false;','#if '+cond+'\n\tpublic static bool init => true;\n#else\n\tpublic static bool init => false;\n#endif'))
edit('PARTNER.cs',lambda s:wrap_method(s,'public static void UserLogin()','AccountData.me = AccountData.NULL;\nAccountData.me.platform = ESalePlatform.Standalone;\nAccountData.me.userId = 1; // Local profile only; never a Steam identity.\nAccountData.me.detail.userName = "Local Player";\nlogined = true;'))
edit('VFPreload.cs',lambda s:s.replace('if (!SteamManager.Initialized)','if (!SteamManager.Initialized && !PARTNER.STANDALONE)'))
def affinity(s):
 sigs=re.findall(r'public static void BindCurrentThreadToProcessor(?:Ex)?\([^\n]*\)',s)
 for sig in sigs:s=wrap_method(s,sig,'// Let the Apple platform scheduler place worker threads.\nreturn;')
 return wrap_method(s,'public static int GetCurrentThreadRunningProcessorIndex()','return -1;')
edit('ThreadAffinity.cs',affinity)
edit('SystemSleepPreventer.cs',lambda s:s.replace('\t[DllImport("kernel32.dll", CharSet = CharSet.Auto, SetLastError = true)]\n\tprivate static extern EXECUTION_STATE SetThreadExecutionState(EXECUTION_STATE esFlags);','#if '+cond+'\n\tprivate static EXECUTION_STATE SetThreadExecutionState(EXECUTION_STATE esFlags) { Screen.sleepTimeout = (esFlags & EXECUTION_STATE.ES_DISPLAY_REQUIRED) != 0 ? SleepTimeout.NeverSleep : SleepTimeout.SystemSetting; return esFlags; }\n#else\n\t[DllImport("kernel32.dll", CharSet = CharSet.Auto, SetLastError = true)]\n\tprivate static extern EXECUTION_STATE SetThreadExecutionState(EXECUTION_STATE esFlags);\n#endif'))
# Preserve user's keybinds: translate Windows virtual key codes into Unity keys.
body='''if (!Application.isFocused || vkey == VKey.NULL) return false;
int v=(int)vkey;
if(v>=65 && v<=90)return Input.GetKey((KeyCode)(v+32));
if(v>=48 && v<=57)return Input.GetKey((KeyCode)v);
if(v>=96 && v<=105)return Input.GetKey((KeyCode)((int)KeyCode.Keypad0+v-96));
if(v>=112 && v<=126)return Input.GetKey((KeyCode)((int)KeyCode.F1+v-112));
switch(vkey) {
case VKey.LBUTTON:return Input.GetMouseButton(0);
case VKey.RBUTTON:return Input.GetMouseButton(1);
case VKey.MBUTTON:return Input.GetMouseButton(2);
case VKey.XBUTTON1:return Input.GetMouseButton(3);
case VKey.XBUTTON2:return Input.GetMouseButton(4);
case VKey.SHIFT:return Input.GetKey(KeyCode.LeftShift)||Input.GetKey(KeyCode.RightShift);
case VKey.CONTROL:return Input.GetKey(KeyCode.LeftControl)||Input.GetKey(KeyCode.RightControl);
case VKey.MENU:return Input.GetKey(KeyCode.LeftAlt)||Input.GetKey(KeyCode.RightAlt);
'''
keys={'BACK':'Backspace','TAB':'Tab','RETURN':'Return','PAUSE':'Pause','CAPITAL':'CapsLock','ESCAPE':'Escape','SPACE':'Space','PRIOR':'PageUp','NEXT':'PageDown','END':'End','HOME':'Home','LEFT':'LeftArrow','UP':'UpArrow','RIGHT':'RightArrow','DOWN':'DownArrow','SNAPSHOT':'Print','Insert':'Insert','Delete':'Delete','LWIN':'LeftCommand','RWIN':'RightCommand','NUMLOCK':'Numlock','SCROLL':'ScrollLock','LSHIFT':'LeftShift','RSHIFT':'RightShift','LCONTROL':'LeftControl','RCONTROL':'RightControl','LMENU':'LeftAlt','RMENU':'RightAlt'}
body+=''.join('case VKey.%s:return Input.GetKey(KeyCode.%s);\n'%(a,b)for a,b in keys.items())+'default:return false;\n}'
edit('WinInput.cs',lambda s:wrap_method(s,'public static bool GetKey(VKey vkey)',body))
print('Applied Apple platform startup, local standalone identity, timer, scheduler, sleep and input adapters')
