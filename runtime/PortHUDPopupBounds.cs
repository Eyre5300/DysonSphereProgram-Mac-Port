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
   parentCanvas=popup.parent.GetComponentInParent<Canvas>(true);
   if(parentCanvas==null)return;
   layer=popup.GetComponent<Canvas>();
   if(layer==null)layer=popup.gameObject.AddComponent<Canvas>();
   raycaster=popup.GetComponent<GraphicRaycaster>();
   if(raycaster==null)raycaster=popup.gameObject.AddComponent<GraphicRaycaster>();
  }
  bool wanted=Enabled&&popup.gameObject.activeInHierarchy;
  layer.overrideSorting=wanted;raycaster.enabled=wanted;
  if(wanted){layer.sortingLayerID=parentCanvas.sortingLayerID;layer.sortingOrder=parentCanvas.rootCanvas.sortingOrder+1;}
 }
}
