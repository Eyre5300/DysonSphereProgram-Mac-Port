using System.Collections.Generic;
using UnityEngine;
using UnityEngine.UI;
using UnityEngine.EventSystems;
// Additive iPad shortcut: first child of the active page backdrop (or the
// original canvas in-world). All original foreground controls keep priority.
// Only this authored button is reparented; no original UI is reordered.
public sealed class DSPPadEscapeButton:MonoBehaviour {
 static DSPPadEscapeButton instance;
 readonly List<RaycastResult> hits=new List<RaycastResult>();
 readonly Vector3[] corners=new Vector3[4];
 RectTransform buttonRect,host;GameObject buttonObject;Canvas canvas;Button button;
 bool originalStyleApplied;Text caption;
 float checkedAt=-10;Rect lastSafe;int lastWidth,lastHeight;
 public static bool Visible=>instance&&instance.buttonObject&&instance.buttonObject.activeInHierarchy;
 public static Vector2 ScreenCenter {get;private set;}
 public static string LastBlockingUI {get;private set;}
 public static string CurrentLayer {get;private set;}
#if DSP_EMU_IPAD
 [RuntimeInitializeOnLoadMethod(RuntimeInitializeLoadType.BeforeSceneLoad)]
 static void Install(){EnsureInstalled();}
#endif
 // Direct DLL rebuilds can reuse Unity's older runtime-init manifest. The
 // production VFInput Poll path installs this idempotently without a test driver.
 public static void EnsureInstalled(){
#if DSP_EMU_IPAD
  if(!DSPTouchControls.Enabled||instance)return;
  UnityEngine.Input.simulateMouseWithTouches=false;
  var go=new GameObject("iPad touch shortcuts");DontDestroyOnLoad(go);instance=go.AddComponent<DSPPadEscapeButton>();
#endif
 }
 void OnApplicationFocus(bool focused){if(!focused){DSPPadInput.CancelVirtualKeys();DSPSmartTouchFrame.Reset();}}
 void OnApplicationPause(bool paused){if(paused){DSPPadInput.CancelVirtualKeys();DSPSmartTouchFrame.Reset();}}
 void LateUpdate(){
  if(!UIRoot.instance||!UIRoot.instance.overlayCanvas)return;
  if(!buttonObject)Create(UIRoot.instance.overlayCanvas);
  if(!originalStyleApplied)ApplyOriginalTechStyle();
  bool show=VFPreload.dbDone&&!DSPGame.IsExitting;
  if(buttonObject.activeSelf!=show)buttonObject.SetActive(show);
  if(!show)return;
  if(Input.touchCount>0)return;
  if(Time.realtimeSinceStartup-checkedAt<.3f&&lastWidth==Screen.width&&lastHeight==Screen.height&&lastSafe==Screen.safeArea)return;
  checkedAt=Time.realtimeSinceStartup;lastWidth=Screen.width;lastHeight=Screen.height;lastSafe=Screen.safeArea;
  SelectBackgroundHost(UIRoot.instance.overlayCanvas);
  FindUncoveredCorner();
 }
 void Create(Canvas original){
  canvas=original;host=original.transform as RectTransform;
  buttonObject=new GameObject("iPad Esc",typeof(RectTransform),typeof(Image),typeof(Button));
  buttonObject.transform.SetParent(original.transform,false);buttonObject.transform.SetAsFirstSibling();
  buttonRect=buttonObject.GetComponent<RectTransform>();buttonRect.anchorMin=buttonRect.anchorMax=new Vector2(.5f,.5f);buttonRect.sizeDelta=new Vector2(48,36);
  var image=buttonObject.GetComponent<Image>();image.color=new Color(.06f,.10f,.16f,.82f);image.raycastTarget=true;
  button=buttonObject.GetComponent<Button>();button.targetGraphic=image;
  button.navigation=new Navigation{mode=Navigation.Mode.None};
  var colors=button.colors;colors.normalColor=Color.white;colors.highlightedColor=new Color(.72f,.88f,1);colors.pressedColor=new Color(.40f,.65f,.92f);button.colors=colors;
  button.onClick.AddListener(DSPPadInput.QueueEscape);
  var textObject=new GameObject("Label",typeof(RectTransform),typeof(Text));textObject.transform.SetParent(buttonRect,false);
  var textRect=textObject.GetComponent<RectTransform>();textRect.anchorMin=Vector2.zero;textRect.anchorMax=Vector2.one;textRect.offsetMin=textRect.offsetMax=Vector2.zero;
  var text=textObject.GetComponent<Text>();caption=text;text.text="ESC";text.alignment=TextAnchor.MiddleCenter;text.fontSize=16;text.color=new Color(.85f,.93f,1);text.raycastTarget=false;
  // Reuse a font the game already loaded; no new font/resource dependency.
  foreach(var label in original.GetComponentsInChildren<Text>(true))if(label!=text&&label.font){text.font=label.font;break;}
 }
 // Reuse the original technology page keycap sprite and ESC typography only.
 // Its quit action and localization components are not copied: this shortcut
 // continues through VFInput so the normal topmost window closes first.
 void ApplyOriginalTechStyle(){
  var root=UIRoot.instance;var game=root?root.uiGame:null;var tech=game?game.techTree:null;
  if(!tech)return;var original=tech.transform.Find("quit-button");if(!original)return;
  var source=original.GetComponent<Image>();if(!source||!source.sprite)return;
  var target=buttonObject.GetComponent<Image>();target.sprite=source.sprite;target.type=source.type;
  target.fillCenter=source.fillCenter;target.preserveAspect=source.preserveAspect;target.color=source.color;
  target.material=source.material;target.pixelsPerUnitMultiplier=source.pixelsPerUnitMultiplier;
  foreach(var text in original.GetComponentsInChildren<Text>(true))if(text.text.Trim()=="ESC"){
   caption.font=text.font;caption.fontStyle=text.fontStyle;caption.color=text.color;caption.text=text.text;break;
  }
  originalStyleApplied=true;
 }
 // These specific background layers were audited in the original scene. Do
 // not search arbitrary "bg" descendants: side panels and masked viewports are
 // real foreground UI. Their raycasts must continue covering this button.
 static Graphic DirectGraphic(Transform parent,string name){
  if(!parent)return null;var child=parent.Find(name);return child?child.GetComponent<Graphic>():null;
 }
 static void Consider(ref Graphic selected,Graphic candidate,Canvas original){
  if(!candidate||!candidate.enabled||!candidate.gameObject.activeInHierarchy||candidate.canvas!=original||candidate.depth<0)return;
  if(!selected||candidate.depth>selected.depth)selected=candidate;
 }
 void SelectBackgroundHost(Canvas original){
  Canvas.ForceUpdateCanvases();Graphic selected=null;var root=UIRoot.instance;var game=root.uiGame;
  if(game){
   if(game.starmap&&game.starmap.active)Consider(ref selected,game.starmap.screenImage,original);
   if(game.dysonEditor&&game.dysonEditor.active){
    Consider(ref selected,game.dysonEditor.screenImage,original);
    // Both decorative layers are normally inactive. Consider only an actually
    // active layer with a valid same-canvas render depth; never its side panels.
    Consider(ref selected,DirectGraphic(game.dysonEditor.transform,"bg-gd-1"),original);
    Consider(ref selected,DirectGraphic(game.dysonEditor.transform,"bg-gd-2"),original);
   }
   if(game.techTree&&game.techTree.active){Consider(ref selected,DirectGraphic(game.techTree.transform,"vignette"),original);Consider(ref selected,DirectGraphic(game.techTree.transform,"BG"),original);}
   if(game.escMenu&&game.escMenu.active)Consider(ref selected,DirectGraphic(game.escMenu.transform,"vignette"),original);
  }
  if(root.uiMechaEditor&&root.uiMechaEditor.active)Consider(ref selected,root.uiMechaEditor.screenImage,original);
  var next=selected?selected.rectTransform:original.transform as RectTransform;
  if(!next)return;
  if(buttonRect.parent!=next){
   buttonRect.SetParent(next,false);buttonRect.SetAsFirstSibling();
   buttonRect.anchorMin=buttonRect.anchorMax=next.pivot;
  }
  host=next;canvas=original;
  CurrentLayer=selected?selected.transform.parent.name+"/"+selected.name:original.name;
 }
 void Place(Vector2 point){
  ScreenCenter=point;Vector2 local;
  if(RectTransformUtility.ScreenPointToLocalPointInRectangle(host,point,canvas.renderMode==RenderMode.ScreenSpaceOverlay?null:canvas.worldCamera,out local))buttonRect.anchoredPosition=local;
 }
 bool Blocked(Vector2 point){
  if(!EventSystem.current){LastBlockingUI="EventSystem not ready";return true;}
  hits.Clear();EventSystem.current.RaycastAll(new PointerEventData(EventSystem.current){position=point},hits);
  // Match the actual click path, including later dynamic popup canvases. A
  // clipped/non-raycastable button must not be accepted as an uncovered spot.
  if(hits.Count==0){LastBlockingUI="no UI hit";return true;}
  var first=hits[0];
  if(first.gameObject.transform.IsChildOf(buttonRect))return false;
  LastBlockingUI=first.gameObject.name;return true;
 }
 bool Uncovered(){
  if(Blocked(ScreenCenter))return false;
  buttonRect.GetWorldCorners(corners);
  foreach(var corner in corners){
   var point=RectTransformUtility.WorldToScreenPoint(canvas.renderMode==RenderMode.ScreenSpaceOverlay?null:canvas.worldCamera,corner);
   // The exact Rect edge can fall outside its own Graphic.Raycast after float
   // rounding, falsely reporting the backdrop. Sample one native pixel inside.
   float distance=Vector2.Distance(point,ScreenCenter);
   if(distance>0)point=Vector2.Lerp(point,ScreenCenter,Mathf.Min(1,1/distance));
   if(Blocked(point))return false;
  }
  return true;
 }
 void FindUncoveredCorner(){
  var safe=Screen.safeArea;Canvas.ForceUpdateCanvases();buttonRect.GetWorldCorners(corners);
  var cam=canvas.renderMode==RenderMode.ScreenSpaceOverlay?null:canvas.worldCamera;
  var lo=RectTransformUtility.WorldToScreenPoint(cam,corners[0]);var hi=RectTransformUtility.WorldToScreenPoint(cam,corners[2]);
  float unitX=Mathf.Abs(hi.x-lo.x)/buttonRect.sizeDelta.x,unitY=Mathf.Abs(hi.y-lo.y)/buttonRect.sizeDelta.y;
  float x=(buttonRect.sizeDelta.x*.5f+16)*unitX,y=(buttonRect.sizeDelta.y*.5f+16)*unitY;
  // Stay within the upper-right area; avoid original metadata/filter buttons
  // instead of covering them or moving the shortcut to a different corner.
  for(int row=0;row<4;row++)for(int col=0;col<5;col++){
   Place(new Vector2(safe.xMax-x-col*56*unitX,safe.yMax-y-row*44*unitY));Canvas.ForceUpdateCanvases();
   if(Uncovered()){LastBlockingUI="";return;}
  }
  Place(new Vector2(safe.xMax-x,safe.yMax-y));Canvas.ForceUpdateCanvases();
 }
 // Automatic UI-event check only. This follows the real Button click handler;
 // it does not prove a physical finger gesture or bypass a covering menu.
 public static bool ClickForDiagnostics(){
  if(!Visible){LastBlockingUI=instance?"Esc UI not ready":"Esc component not installed";return false;}
  if(!EventSystem.current){LastBlockingUI="EventSystem not ready";return false;}
  if(!instance.button.IsInteractable()){LastBlockingUI="Esc disabled";return false;}
  Canvas.ForceUpdateCanvases();
  var pointer=new PointerEventData(EventSystem.current){position=ScreenCenter,button=PointerEventData.InputButton.Left,pointerId=-101,eligibleForClick=true};
  instance.hits.Clear();EventSystem.current.RaycastAll(pointer,instance.hits);
  if(instance.hits.Count==0){LastBlockingUI="no UI hit";return false;}
  var first=instance.hits[0];
  if(!first.gameObject.transform.IsChildOf(instance.buttonRect)){LastBlockingUI=first.gameObject.name;return false;}
  pointer.pointerCurrentRaycast=first;pointer.pointerPressRaycast=first;
  LastBlockingUI="";
  return ExecuteEvents.Execute(instance.button.gameObject,pointer,ExecuteEvents.pointerClickHandler);
 }
 public static bool Contains(Vector2 point){return Visible&&RectTransformUtility.RectangleContainsScreenPoint(instance.buttonRect,point,instance.canvas.renderMode==RenderMode.ScreenSpaceOverlay?null:instance.canvas.worldCamera);}
}
