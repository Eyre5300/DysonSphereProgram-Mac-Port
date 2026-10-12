using System;
using System.IO;
using System.Runtime.InteropServices;
using UnityEngine;
public static class PortFolderBrowser {
#if UNITY_STANDALONE_OSX || UNITY_EDITOR_OSX
 #if DSP_EMU_IPAD
 [DllImport("@rpath/UnityFramework.framework/UnityFramework")]
#else
 [DllImport("DSPPortInput")]
#endif
 static extern int DSPPortOpenFolder([MarshalAs(UnmanagedType.LPUTF8Str)] string path);
#endif
 public static bool OpenDirectory(string path) {
#if UNITY_STANDALONE_OSX || UNITY_EDITOR_OSX
  try {
   string full=Path.GetFullPath(path);
   if(!Directory.Exists(full)){Debug.LogWarning("DSP_FOLDER_NOT_FOUND "+full);return false;}
   bool accepted=DSPPortOpenFolder(full)!=0;
   if(!accepted)Debug.LogWarning("DSP_FOLDER_OPEN_FAILED "+full);
   return accepted;
  }catch(Exception e){Debug.LogWarning("DSP_FOLDER_OPEN_FAILED "+e.Message);return false;}
#else
  Application.OpenURL(path);return true;
#endif
 }
}
