using UnityEngine;
using UnityEngine.UI;
// H controls and popup geometry remain original. Only put the active popup
// above its overlay toolbar, including pointer raycast priority.
public sealed class PortHUDPopupBounds : MonoBehaviour {
 public static bool Enabled=true;
 RectTransform popup; Canvas layer; Canvas parentCanvas; GraphicRaycaster raycaster;
 public static void Attach(UIGameMenu menu){
#if UNITY_STANDALONE_OSX || UNITY_EDITOR_OSX
  if(menu==null||menu.detailFuncGroup==null||menu.GetComponent<PortHUDPopupBounds>()!=null)return;
  var instance=menu.gameObject.AddComponent<PortHUDPopupBounds>();
  instance.popup=menu.detailFuncGroup;

#endif
 }
 void LateUpdate(){
  if(popup==null)return;
  // UIGameMenu is created while its UI hierarchy is inactive. Resolve the
  // original parent canvas only when displaying, including inactive ancestors.
  if(layer==null){
#if DSP_EMU_IPAD
   // Original scene order within Game Menu is popup FIRST, then the circular
   // buttons. Promoting only the popup inverts their hit-test/render order.
   var layerRoot=transform;
#else
   var layerRoot=popup;
#endif
   parentCanvas=layerRoot.parent.GetComponentInParent<Canvas>(true);
   if(parentCanvas==null)return;
   layer=layerRoot.GetComponent<Canvas>();
   if(layer==null)layer=layerRoot.gameObject.AddComponent<Canvas>();
   raycaster=layerRoot.GetComponent<GraphicRaycaster>();
   if(raycaster==null)raycaster=layerRoot.gameObject.AddComponent<GraphicRaycaster>();
  }
  bool wanted=Enabled&&popup.gameObject.activeInHierarchy;
#if DSP_EMU_IPAD
  wanted=wanted&&!VFInput.inFullscreenGUI&&!VFInput.inCombatScreenGUI&&!GameMain.isPaused&&UIMessageBox.activeCount==0;
  if(UIRoot.instance&&UIRoot.instance.uiMechaEditor&&UIRoot.instance.uiMechaEditor.active)wanted=false;
  // A disabled nested Canvas hides its registered child Graphics; it does
  // not return them to the parent registry. Keep drawing/hit-testing active
  // while only the sorting override follows the original popup state.
  layer.enabled=true;layer.additionalShaderChannels=parentCanvas.additionalShaderChannels;
#endif
  layer.overrideSorting=wanted;
#if DSP_EMU_IPAD
  raycaster.enabled=true;
#else
  raycaster.enabled=wanted;
#endif
  if(wanted){layer.sortingLayerID=parentCanvas.sortingLayerID;layer.sortingOrder=parentCanvas.rootCanvas.sortingOrder+1;}
 }
}
