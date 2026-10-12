using System;
using System.Runtime.InteropServices;
using UnityEngine;
using UnityEngine.UI;
// Game FPS/UPS retains original calculations. Only visibility is changed.
public sealed class DSPPadPerformanceHUD:MonoBehaviour {
 [DllImport("@rpath/UnityFramework.framework/UnityFramework")]static extern ulong DSPAOTPhysicalFootprint();
 static DSPPadPerformanceHUD instance;Text memory;float next;public static ulong Bytes{get;private set;}
 public static void EnsureInstalled(){if(instance||DSPTouchControls.Enabled)return;var go=new GameObject("iPad performance status");DontDestroyOnLoad(go);instance=go.AddComponent<DSPPadPerformanceHUD>();}
 public static bool AlwaysFPS=>!DSPTouchControls.Enabled;
 void LateUpdate(){if(Time.unscaledTime<next)return;next=Time.unscaledTime+1;if(!UIRoot.instance)return;
  var fps=UIRoot.instance.GetComponentInChildren<UIFpsStat>(true);if(!fps||!fps.fpsTextComp)return;
  if(!memory){var obj=new GameObject("App memory",typeof(RectTransform),typeof(Text));obj.layer=fps.fpsTextComp.gameObject.layer;obj.transform.SetParent(fps.fpsTextComp.transform.parent,false);memory=obj.GetComponent<Text>();memory.font=fps.fpsTextComp.font;memory.fontSize=fps.fpsTextComp.fontSize;memory.color=fps.fpsTextLabel.color;memory.alignment=TextAnchor.MiddleRight;memory.raycastTarget=false;memory.supportRichText=false;
   var dst=memory.rectTransform;var src=fps.fpsTextComp.rectTransform;dst.anchorMin=src.anchorMin;dst.anchorMax=src.anchorMax;dst.pivot=src.pivot;dst.sizeDelta=new Vector2(250,24);dst.anchoredPosition=src.anchoredPosition+new Vector2(0,-24);}
  Bytes=DSPAOTPhysicalFootprint();memory.text=Bytes>0?"App 内存 "+(Bytes/1073741824.0).ToString("F2")+" GiB":"App 内存 —";memory.enabled=GameMain.isRunning;
 }
}
