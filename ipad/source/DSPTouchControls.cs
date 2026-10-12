using System;using System.Collections.Generic;using UnityEngine;using UnityEngine.UI;using UnityEngine.EventSystems;
// Touch-app-only input adapter. All placement and connection rules remain in the original tools.
public sealed class DSPTouchControls:MonoBehaviour {
 static DSPTouchControls instance;static int sampled=-1,left=-1,right=-1,target=-1;static Vector2 origin,lastRight,targetStart;static bool targetDragged;
 static Vector2 look,pendingLook,move;static Vector3 pointer,anchor;static bool hasPointer,hasAnchor;static int hand;static bool fine,basement;static float zoom,pendingZoom;static bool testMode;
 public static bool Enabled=>Application.identifier.Contains(".touch.");
 public static bool Allowed=>Enabled&&Application.isFocused&&GameMain.isRunning&&!DSPGame.IsMenuDemo&&!GameMain.isPaused&&!VFInput.inFullscreenGUI&&!VFInput.inputing&&!VFInput.inScreenshotMode;
 public static bool BuildActive=>Allowed&&GameMain.mainPlayer!=null&&GameMain.mainPlayer.controller.actionBuild.activeTool!=null&&GameMain.mainPlayer.controller.cmd.type==ECommand.Build;
 public static bool PointerActive=>Allowed&&hasPointer;
 public static Vector3 Pointer=>pointer;public static Vector2 Move=>move;public static Vector2 Look=>look;public static bool Looking=>right>=0;
 public static string Message="触控：左侧移动 · 右侧视角";
 public static int ConfirmRequests,Rejected,AcceptedContacts;public static bool Fine=>fine;
 public static Rect MoveRect=>new Rect(Screen.width*.025f,Screen.height*.23f,Screen.width*.19f,Screen.height*.24f);
 public static Rect LookRect=>new Rect(Screen.width*.80f,Screen.height*.43f,Screen.width*.175f,Screen.height*.24f);
 CanvasGroup keyboardHints;Canvas canvas;GameObject panel,buildPanel;Text status,confirmText,fineText;readonly Dictionary<string,Button> buttons=new Dictionary<string,Button>();
 sealed class Key {public DSPPadKeyQueue q=new DSPPadKeyQueue();public int pending;public bool previous,down,up;}
 static readonly Dictionary<KeyCode,Key> keys=new Dictionary<KeyCode,Key>();
 static Key KeyFor(KeyCode key){Key k;if(!keys.TryGetValue(key,out k)){k=new Key();keys[key]=k;}return k;}
 public static void Pulse(KeyCode key){if(!Allowed)return;KeyFor(key).pending++;}
 public static void Published(){foreach(var k in keys.Values)k.q.Published();}
 public static void Sampled(){foreach(var k in keys.Values)k.q.Sampled();}
 public static bool Read(KeyCode key,int mode,out bool value){value=false;if(!Enabled)return false;
  if(key==KeyCode.LeftControl&&basement&&BuildActive){value=mode==0;return true;}
  if(key==KeyCode.LeftShift&&fine&&BuildActive){value=mode==0;return true;}
  Key k;if(!keys.TryGetValue(key,out k))return false;value=mode==0?k.q.Held:mode==1?k.down:k.up;return value||k.previous;
 }
 public static float Zoom=>zoom;
 public static void Reset(){left=right=target=-1;move=look=pendingLook=Vector2.zero;fine=basement=false;zoom=pendingZoom=0;foreach(var k in keys.Values){k.q.Clear();k.pending=0;k.previous=k.down=k.up=false;}DSPPadInput.CancelWorldTap();}
 public static void Ensure(){if(!Enabled||instance)return;var go=new GameObject("DSP Touch controls");DontDestroyOnLoad(go);instance=go.AddComponent<DSPTouchControls>();}
 static bool UIAt(Vector2 p){return DSPSmartTouchFrame.UIBlocks(p);}
 static bool OwnZone(Vector2 p){if(!instance||!instance.panel||!instance.panel.activeInHierarchy)return false;var hits=new List<RaycastResult>();EventSystem.current.RaycastAll(new PointerEventData(EventSystem.current){position=p},hits);return hits.Count>0&&hits[0].gameObject.name.StartsWith("TouchZone");}
 public static void Poll(){Ensure();if(!Enabled||sampled==Time.frameCount)return;sampled=Time.frameCount;look=pendingLook;pendingLook=Vector2.zero;zoom=pendingZoom;pendingZoom=0;
  if(!Allowed){Reset();hasPointer=hasAnchor=false;return;}
  int h=GameMain.mainPlayer.inhandItemId;if(h!=hand){hand=h;fine=basement=false;hasAnchor=false;hasPointer=false;Message="点选位置后微调，再确认";}
  if(hasAnchor&&BuildActive&&Camera.main){var p=Camera.main.WorldToScreenPoint(anchor);pointer=p;if(p.z<=0||p.x<0||p.x>Screen.width||p.y<0||p.y>Screen.height){Message="预览离开画面，请先调整视角";}}
  foreach(var pair in keys){var k=pair.Value;k.previous=k.q.Held;k.q.Poll(false,k.pending,0,true,Time.realtimeSinceStartup);k.pending=0;k.down=k.q.Held&&!k.previous;k.up=!k.q.Held&&k.previous;}
  if(testMode)return;
  bool seenLeft=false,seenRight=false,seenTarget=false;
  foreach(var t in UnityEngine.Input.touches){if(t.type==TouchType.Indirect)continue;Contact(t.fingerId,t.phase,t.position);seenLeft|=t.fingerId==left;seenRight|=t.fingerId==right;seenTarget|=t.fingerId==target;}
  if(!seenLeft){left=-1;move=Vector2.zero;}if(!seenRight)right=-1;if(!seenTarget)target=-1;
 }
 // Diagnostics feed this same contact router, never assign movement/camera/tool results.
 public static void DiagnosticMode(bool on){if(!DSPPadDiagnosticLaunch.AutomaticActionsAllowed)throw new InvalidOperationException("Explicit test process required");testMode=on;Reset();}
 public static void Contact(int id,TouchPhase phase,Vector2 p){
  if(!Allowed){Reset();return;}bool end=phase==TouchPhase.Ended||phase==TouchPhase.Canceled;
  if(phase==TouchPhase.Began){
   if(MoveRect.Contains(p)&&OwnZone(p)&&left<0){left=id;origin=p;AcceptedContacts++;}
   else if(LookRect.Contains(p)&&OwnZone(p)&&right<0){right=id;lastRight=p;AcceptedContacts++;}
   else if(!UIAt(p)&&target<0){target=id;targetStart=p;targetDragged=false;if(BuildActive)SetTarget(p);AcceptedContacts++;}
   else{Rejected++;return;}
  }
  if(id==left){if(end){left=-1;move=Vector2.zero;}else{var d=p-origin;float radius=Mathf.Min(Screen.width*.07f,Screen.height*.11f);move=d.magnitude<radius*.12f?Vector2.zero:Vector2.ClampMagnitude(d/radius,1);}return;}
  if(id==right){if(end)right=-1;else{pendingLook+=(p-lastRight)*.1f;lastRight=p;}return;}
  if(id!=target)return;
  if((p-targetStart).magnitude>Screen.width*.008f)targetDragged=true;
  if(phase==TouchPhase.Canceled){target=-1;return;}
  if(UIAt(p)){target=-1;return;}
  if(BuildActive)SetTarget(p);
  else if(phase==TouchPhase.Ended&&!targetDragged){SetTarget(p);DSPPadInput.QueueWorldTap(p);}
  if(end)target=-1;
 }
 public static bool SetTarget(Vector2 p){if(!Allowed||UIAt(p))return false;pointer=new Vector3(p.x,p.y,1);hasPointer=true;hasAnchor=false;
  // Lock the ray's intersection with this planet's ground sphere, not a factory object transform.
  if(Camera.main&&GameMain.localPlanet!=null){Ray ray=Camera.main.ScreenPointToRay(p);float radius=GameMain.localPlanet.realRadius,b=Vector3.Dot(ray.origin,ray.direction),c=ray.origin.sqrMagnitude-radius*radius,disc=b*b-c;if(disc>=0){float t=-b-Mathf.Sqrt(disc);if(t>0){anchor=ray.GetPoint(t);hasAnchor=true;}}}
  return true;
 }
 public static void Nudge(Vector2 direction){if(!PointerActive||!BuildActive)return;var p=(Vector2)pointer+direction*(fine?1.5f:7f)*Screen.width/1280f;SetTarget(p);}
 public static bool Confirm(){if(!BuildActive||!hasPointer||pointer.z<=0||!new Rect(0,0,Screen.width,Screen.height).Contains(pointer)||UIAt(pointer)){Message="先在世界中选择有效位置";return false;}
  bool ok=DSPPadInput.QueueWorldTap(pointer);if(ok){ConfirmRequests++;Message="已确认当前步骤";}else Message="等待当前操作完成";return ok;
 }
 public static void Action(string id){if(!Allowed)return;switch(id){
 case "confirm":Confirm();break;case "cancel":fine=false;DSPPadInput.QueueEscape();break;
 case "rotate":Pulse(BuildActive&&GameMain.mainPlayer.controller.actionBuild.activeTool==GameMain.mainPlayer.controller.actionBuild.inserterTool?KeyCode.RightArrow:KeyCode.R);break;case "counter":Pulse(KeyCode.LeftArrow);break;
 case "fine":fine=!fine;Message=fine?"精细模式：沿用当前原版工具的 Shift 行为":"标准吸附";break;
 case "style":Pulse(KeyCode.Tab);break;case "up":Pulse(KeyCode.UpArrow);break;case "down":Pulse(KeyCode.DownArrow);break;case "zero":Pulse(KeyCode.Keypad0);break;
 case "slotPrev":Pulse(KeyCode.LeftArrow);break;case "slotNext":Pulse(KeyCode.RightArrow);break;
 case "nleft":Nudge(Vector2.left);break;case "nright":Nudge(Vector2.right);break;case "nup":Nudge(Vector2.up);break;case "ndown":Nudge(Vector2.down);break;
 case "zoomIn":pendingZoom+=1;break;case "zoomOut":pendingZoom-=1;break;
 case "tiltRight":Pulse(KeyCode.RightArrow);break;case "basement":basement=!basement;break;case "zoomReset":GameCamera.instance.rtsPoser.ToWanted();break;
 case "inventory":Pulse(KeyCode.E);break;case "jump":Pulse(KeyCode.Space);break;
 }}
 public static string RenderEvidence(){if(!instance||!instance.canvas)return "missing";var c=instance.canvas.rootCanvas;var camera=c.worldCamera;int hidden=0,count=0;foreach(var g in instance.panel.GetComponentsInChildren<Graphic>()){if(!g.gameObject.activeInHierarchy)continue;count++;if(camera&&(camera.cullingMask&(1<<g.gameObject.layer))==0)hidden++;}return "graphics="+count+" camera="+(camera?camera.name:"overlay")+" excluded="+hidden;}
 public static bool RenderLayersValid(){if(!instance||!instance.canvas||!instance.panel.activeInHierarchy)return false;var c=instance.canvas.rootCanvas.worldCamera;if(!c)return true;foreach(var g in instance.panel.GetComponentsInChildren<Graphic>())if(g.gameObject.activeInHierarchy&&(c.cullingMask&(1<<g.gameObject.layer))==0)return false;return true;}
 public static bool ClickDiagnostic(string id){if(!DSPPadDiagnosticLaunch.AutomaticActionsAllowed||!instance)return false;Button b;if(!instance.buttons.TryGetValue(id,out b)||!b.gameObject.activeInHierarchy)return false;
  var root=instance.canvas.rootCanvas;var p=RectTransformUtility.WorldToScreenPoint(root.renderMode==RenderMode.ScreenSpaceOverlay?null:root.worldCamera,b.transform.position);var hits=new List<RaycastResult>();EventSystem.current.RaycastAll(new PointerEventData(EventSystem.current){position=p},hits);if(hits.Count==0||hits[0].gameObject!=b.gameObject)return false;b.onClick.Invoke();return true;
 }
 void OnApplicationFocus(bool focus){if(!focus)Reset();}void OnApplicationPause(bool pause){if(pause)Reset();}
 static RectTransform Rect(GameObject go,Transform parent,Vector2 min,Vector2 max){var r=go.GetComponent<RectTransform>();r.SetParent(parent,false);go.layer=parent.gameObject.layer;r.anchorMin=min;r.anchorMax=max;r.offsetMin=r.offsetMax=Vector2.zero;return r;}
 Font font;Text Label(Transform parent,string name,string value,int size){var go=new GameObject(name,typeof(RectTransform),typeof(Text));Rect(go,parent,Vector2.zero,Vector2.one);var t=go.GetComponent<Text>();t.font=font;t.text=value;t.fontSize=size;t.color=new Color(.83f,.94f,1);t.alignment=TextAnchor.MiddleCenter;t.raycastTarget=false;return t;}
 GameObject Box(Transform parent,string name,Vector2 min,Vector2 max,Color color,bool ray){var go=new GameObject(name,typeof(RectTransform),typeof(Image));Rect(go,parent,min,max);var im=go.GetComponent<Image>();im.color=color;im.raycastTarget=ray;return go;}
 void ButtonAt(Transform parent,string id,string text,int col,int row,int columns){float gap=.008f,width=1f/columns;var go=Box(parent,"TouchButton "+id,new Vector2(col*width+gap,row*(parent.name=="Construction controls"?1f/3f:.5f)+.025f),new Vector2((col+1)*width-gap,(row+1)*(parent.name=="Construction controls"?1f/3f:.5f)-.025f),new Color(.035f,.09f,.15f,.92f),true);var b=go.AddComponent<Button>();b.targetGraphic=go.GetComponent<Image>();b.navigation=new Navigation{mode=Navigation.Mode.None};b.onClick.AddListener(()=>Action(id));buttons[id]=b;var t=Label(go.transform,"Label",text,17);if(id=="confirm")confirmText=t;if(id=="fine")fineText=t;}
 void Create(){var go=new GameObject("Touch HUD",typeof(RectTransform),typeof(Canvas),typeof(CanvasScaler),typeof(GraphicRaycaster));Rect(go,UIRoot.instance.overlayCanvas.transform,Vector2.zero,Vector2.one);go.transform.SetAsFirstSibling();canvas=go.GetComponent<Canvas>();canvas.overrideSorting=false;var scaler=go.GetComponent<CanvasScaler>();scaler.uiScaleMode=CanvasScaler.ScaleMode.ScaleWithScreenSize;scaler.referenceResolution=new Vector2(1280,960);scaler.matchWidthOrHeight=0;
  foreach(var t in UIRoot.instance.overlayCanvas.GetComponentsInChildren<Text>(true))if(t.font&&t.font.HasCharacter('移')){font=t.font;break;}if(!font)font=Resources.GetBuiltinResource<Font>("LegacyRuntime.ttf");
  panel=new GameObject("Active touch controls",typeof(RectTransform));Rect(panel,go.transform,Vector2.zero,Vector2.one);
  var leftBox=Box(panel.transform,"TouchZone Move",new Vector2(.025f,.23f),new Vector2(.215f,.47f),new Color(.04f,.12f,.2f,.3f),true);Label(leftBox.transform,"Label","移动\n↑\n←  ●  →\n↓",23);
  var rightBox=Box(panel.transform,"TouchZone Look",new Vector2(.80f,.43f),new Vector2(.975f,.67f),new Color(.04f,.12f,.2f,.25f),true);Label(rightBox.transform,"Label","视角\n拖动旋转",23);
  var small=new GameObject("Quick actions",typeof(RectTransform));Rect(small,panel.transform,new Vector2(.80f,.30f),new Vector2(.975f,.42f));ButtonAt(small.transform,"inventory","背包",0,0,2);ButtonAt(small.transform,"jump","跳跃",1,0,2);ButtonAt(small.transform,"zoomIn","拉近",0,1,2);ButtonAt(small.transform,"zoomOut","拉远",1,1,2);
  buildPanel=new GameObject("Construction controls",typeof(RectTransform));Rect(buildPanel,panel.transform,new Vector2(.225f,.23f),new Vector2(.78f,.44f));
  string[] ids={"cancel","nleft","ndown","nup","nright","confirm","counter","rotate","fine","up","down","style","zero","tiltRight","basement"};string[] labels={"取消","←微调","↓微调","↑微调","微调→","确认","逆转","旋转","精细","高度＋","高度－","样式","高度归零","右倾","基座吸附"};for(int i=0;i<ids.Length;i++)ButtonAt(buildPanel.transform,ids[i],labels[i],i%6,i/6,6);
  var strip=Box(panel.transform,"Touch status",new Vector2(.225f,.445f),new Vector2(.78f,.485f),new Color(.02f,.06f,.10f,.82f),false);status=Label(strip.transform,"Label",Message,16);
 }
 void LateUpdate(){if(!UIRoot.instance||!UIRoot.instance.overlayCanvas)return;if(!canvas)Create();bool visible=Allowed;if(!keyboardHints&&UIRoot.instance.uiGame.keyTips)keyboardHints=UIRoot.instance.uiGame.keyTips.gameObject.AddComponent<CanvasGroup>();if(keyboardHints){keyboardHints.alpha=visible?0:1;keyboardHints.blocksRaycasts=!visible;}panel.SetActive(visible);if(!visible)return;bool build=BuildActive;buildPanel.SetActive(build);
  if(build){var a=GameMain.mainPlayer.controller.actionBuild;int stage=GameMain.mainPlayer.controller.cmd.stage;bool belt=a.activeTool==a.pathTool,sorter=a.activeTool==a.inserterTool;
   confirmText.text=(belt||sorter)&&stage==0?"定起点":belt?"铺本段":sorter?"连接":"放置";
   buttons["counter"].GetComponentInChildren<Text>().text=sorter?"接口←":belt?"左倾":"逆转";buttons["rotate"].GetComponentInChildren<Text>().text=sorter?"接口→":belt?"换路径":"旋转";
   fineText.text=(fine?"● ":"")+(belt?"自由定位":"精细");buttons["up"].gameObject.SetActive(belt);buttons["down"].gameObject.SetActive(belt);buttons["style"].gameObject.SetActive(!sorter);buttons["zero"].gameObject.SetActive(belt);buttons["tiltRight"].gameObject.SetActive(belt);buttons["basement"].gameObject.SetActive(belt);buttons["fine"].gameObject.SetActive(!sorter);if(sorter)fine=false;
   buttons["style"].GetComponentInChildren<Text>().text=belt?"换坡道":"样式";
   status.text=(sorter?"分拣器：":belt?"传送带：":"建筑：")+(stage==0?"定位 → 微调 → 确认":"选择终点 → 确认")+"   "+Message;
  }else status.text="触控：左侧移动 · 右侧视角";
 }
}
