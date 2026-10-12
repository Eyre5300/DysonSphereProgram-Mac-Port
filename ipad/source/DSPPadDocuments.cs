using System;using System.IO;using System.Collections.Generic;using System.Runtime.InteropServices;using UnityEngine;using UnityEngine.UI;
// Platform-owned file import/export; original parsers and local save locations remain authoritative.
public sealed class DSPPadDocuments:MonoBehaviour {
 const string Native="@rpath/UnityFramework.framework/UnityFramework";
 [DllImport(Native)]static extern int DSPAOTOpenDocuments([MarshalAs(UnmanagedType.LPUTF8Str)]string path,int exportFiles);
 [DllImport(Native)]static extern int DSPAOTDocumentsBusy();
 [DllImport(Native)]static extern IntPtr DSPAOTDocumentsResult();
 [DllImport(Native)]public static extern int DSPAOTDocumentProbe(int operation,[MarshalAs(UnmanagedType.LPUTF8Str)]string path);
 [Serializable]public sealed class Item {public string name,path,error;}
 [Serializable]public sealed class Result {public string status,message,folder,stage;public Item[] files;}
 static DSPPadDocuments instance;static bool processing;public static bool Busy=>processing||DSPAOTDocumentsBusy()!=0;
 public static string LastStatus="",LastMessage="";public static int Imported,Rejected,Cancelled,Exported;public static string LastImported;
 GameObject bar,mode,progress;Text modeText;bool resume;Font font;
 public static void Ensure(){if(instance)return;var go=new GameObject("iPad files and input preference");DontDestroyOnLoad(go);instance=go.AddComponent<DSPPadDocuments>();}
 static bool Under(string path,string root){path=Path.GetFullPath(path);root=Path.GetFullPath(root).TrimEnd(Path.DirectorySeparatorChar);return path==root||path.StartsWith(root+Path.DirectorySeparatorChar,StringComparison.Ordinal);}
 public static string CurrentFolder(){if(!UIRoot.instance)return null;var ui=UIRoot.instance;if(ui.loadGameWindow.active||ui.saveGameWindow.active)return GameConfig.gameSaveFolder;if(ui.uiGame.blueprintBrowser.active)return ui.uiGame.blueprintBrowser.currentDirectoryInfo?.FullName;return null;}
 public static bool Open(string folder,bool export){if(string.IsNullOrEmpty(folder)||Busy)return false;if(!Under(folder,GameConfig.gameSaveFolder)&&!Under(folder,GameConfig.blueprintFolder))return false;Directory.CreateDirectory(folder);return DSPAOTOpenDocuments(folder,export?1:0)!=0;}
 public static string Import(string source,string name,string folder){
  if(!Under(folder,GameConfig.gameSaveFolder)&&!Under(folder,GameConfig.blueprintFolder))throw new IOException("导入目录无效");
  name=Path.GetFileName(name);string ext=Path.GetExtension(name).ToLowerInvariant();bool save=Under(folder,GameConfig.gameSaveFolder);
  if(ext!=(save?".dsv":".txt"))throw new IOException(save?"此处请选择 .dsv 存档":"此处请选择 .txt 蓝图");
  string stem=Path.GetFileNameWithoutExtension(name).ValidFileName();if(string.IsNullOrWhiteSpace(stem))stem="导入文件";if(stem.Length>100)stem=stem.Substring(0,100);
  Directory.CreateDirectory(folder);string temp=Path.Combine(folder,"port-import-"+Guid.NewGuid().ToString("N")+ext);
  try{
   File.Copy(source,temp,false);
   if(save){GameSaveHeader header;GameSave.ReadHeader(Path.GetFileNameWithoutExtension(temp),false,out header);if(header==null)throw new IOException("存档头或文件长度校验失败");}
   else{if(new FileInfo(temp).Length>64L*1024*1024)throw new IOException("蓝图超过当前 64 MiB 导入上限");var bp=new BlueprintData();if(bp.LoadBlueprintData(temp)!=BlueprintDataIOError.OK||!bp.isValid)throw new IOException("蓝图格式或校验和无效");}
   string target=Path.Combine(folder,stem+ext);for(int n=1;File.Exists(target);n++)target=Path.Combine(folder,stem+" (导入"+n+")"+ext);
   File.Move(temp,target);return target;
  }finally{if(File.Exists(temp))File.Delete(temp);}
 }
 void Update(){
  bool native=DSPAOTDocumentsBusy()!=0;if(native&&!resume&&GameMain.isRunning&&!DSPGame.IsMenuDemo&&!GameMain.isPaused){GameMain.Pause();resume=true;DSPTouchControls.Reset();DSPPadInput.CancelVirtualKeys();}
  string json=Marshal.PtrToStringAnsi(DSPAOTDocumentsResult());if(string.IsNullOrEmpty(json))return;processing=true;
  try{var r=JsonUtility.FromJson<Result>(json);LastStatus=r.status;LastMessage=r.message??"";if(r.status=="cancelled")Cancelled++;else if(r.status=="exported"){Exported++;LastMessage="已导出到所选位置";}else if(r.status=="imported"){
   int ok=0;var errors=new List<string>();foreach(var f in r.files??new Item[0]){try{if(!string.IsNullOrEmpty(f.error))throw new IOException(f.error);if(string.IsNullOrEmpty(f.path)||!Under(f.path,r.stage)||!Under(r.stage,Application.persistentDataPath))throw new IOException("导入临时文件路径无效");LastImported=Import(f.path,f.name,r.folder);Imported++;ok++;}catch(Exception e){Rejected++;errors.Add(f.name+"："+e.Message);}}
   LastMessage="已导入 "+ok+" 个文件"+(errors.Count>0?"\n"+string.Join("\n",errors):"");
   if(!string.IsNullOrEmpty(r.stage)&&Under(r.stage,Application.persistentDataPath)&&Path.GetFileName(r.stage).StartsWith(".port-import-"))Directory.Delete(r.stage,true);
   var ui=UIRoot.instance;if(ui.loadGameWindow.active)ui.loadGameWindow.RefreshList();if(ui.saveGameWindow.active)ui.saveGameWindow.RefreshList();if(ui.uiGame.blueprintBrowser.active&&ui.uiGame.blueprintBrowser.currentDirectoryInfo!=null)ui.uiGame.blueprintBrowser.SetCurrentDirectory(ui.uiGame.blueprintBrowser.currentDirectoryInfo.FullName);
  }
  if(r.status!="cancelled"&&!DSPPadDiagnosticLaunch.AutomaticActionsAllowed)UIMessageBox.Show("文件",LastMessage,"确定",0);
  }catch(Exception e){LastStatus="error";LastMessage=e.Message;Rejected++;if(!DSPPadDiagnosticLaunch.AutomaticActionsAllowed)UIMessageBox.Show("文件",LastMessage,"确定",0);}
  finally{processing=false;if(resume&&GameMain.isRunning){GameMain.Resume();resume=false;}}
 }
 RectTransform Rect(GameObject go,Transform parent,Vector2 min,Vector2 max){var r=go.GetComponent<RectTransform>();r.SetParent(parent,false);go.layer=parent.gameObject.layer;r.anchorMin=min;r.anchorMax=max;r.offsetMin=r.offsetMax=Vector2.zero;return r;}
 Button Button(Transform parent,string title,Vector2 min,Vector2 max,Action action){var go=new GameObject(title,typeof(RectTransform),typeof(Image),typeof(Button));Rect(go,parent,min,max);go.GetComponent<Image>().color=new Color(.03f,.09f,.15f,.95f);var b=go.GetComponent<Button>();b.navigation=new Navigation{mode=Navigation.Mode.None};b.onClick.AddListener(()=>action());var label=new GameObject("Label",typeof(RectTransform),typeof(Text));Rect(label,go.transform,Vector2.zero,Vector2.one);var text=label.GetComponent<Text>();text.font=font;text.fontSize=17;text.color=Color.white;text.alignment=TextAnchor.MiddleCenter;text.raycastTarget=false;text.text=title;return b;}
 void Create(){var parent=UIRoot.instance.overlayCanvas.transform;foreach(var t in parent.GetComponentsInChildren<Text>(true))if(t.font&&t.font.HasCharacter('文')){font=t.font;break;}if(!font)font=Resources.GetBuiltinResource<Font>("LegacyRuntime.ttf");bar=new GameObject("iPad file actions",typeof(RectTransform));Rect(bar,parent,new Vector2(.32f,.035f),new Vector2(.68f,.085f));Button(bar.transform,"导入文件",Vector2.zero,new Vector2(.48f,1),()=>Open(CurrentFolder(),false));Button(bar.transform,"导出文件",new Vector2(.52f,0),Vector2.one,()=>Open(CurrentFolder(),true));var chip=Button(parent,"输入：自动",new Vector2(.78f,.88f),new Vector2(.965f,.925f),DSPPadInputMode.Cycle);mode=chip.gameObject;modeText=mode.GetComponentInChildren<Text>();var busy=Button(parent,"正在处理文件，请稍候…",new Vector2(.32f,.09f),new Vector2(.68f,.14f),()=>{});busy.interactable=false;progress=busy.gameObject;}
 void LateUpdate(){if(!UIRoot.instance||!UIRoot.instance.overlayCanvas||!VFPreload.dbDone)return;if(!bar)Create();bar.SetActive(CurrentFolder()!=null&&!Busy);progress.SetActive(Busy);mode.SetActive(DSPTouchControls.Enabled&&!Busy&&GameMain.isRunning&&!DSPGame.IsMenuDemo&&!VFInput.inFullscreenGUI);modeText.text=DSPPadInputMode.Label;}
}
