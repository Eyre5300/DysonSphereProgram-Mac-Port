using System.Collections.Generic;
using UnityEngine;
using UnityEngine.EventSystems;
using UnityEngine.UI;

// Platform transport only. The original UI event performs the actual selection;
// this helper never emits a second Mouse0 or invokes any game selection method.
public static class DSPPadStarmapTouch
{
    struct Gesture
    {
        public Vector2 origin;
        public bool blocked;
        public float lastSeen;
    }
    static readonly Dictionary<int, Gesture> gestures = new Dictionary<int, Gesture>();
    static readonly List<int> expired = new List<int>();
    static readonly List<RaycastResult> hits = new List<RaycastResult>();
    static bool installed;
    static int sampledFrame = -1;
    public static int RefreshedTaps { get; private set; }
    public static int RejectedTaps { get; private set; }
    public static string LastRejection { get; private set; }

#if DSP_EMU_IPAD
    [RuntimeInitializeOnLoadMethod(RuntimeInitializeLoadType.BeforeSceneLoad)]
    static void Install() { EnsureInstalled(); }
#endif

    // The incremental bridge can retain an old RuntimeInitializeOnLoads.json.
    // DSPPadInput.Poll explicitly calls this, so activation never depends on
    // discovery of a newly added runtime initializer in exported Unity Data.
    public static void EnsureInstalled()
    {
        if (!installed)
        {
            installed = true;
            var go = new GameObject("DSP iPad starmap touch observer");
            Object.DontDestroyOnLoad(go);
            go.AddComponent<DSPPadStarmapTouchObserver>();
        }
        SampleTouches();
    }

    static float DragSlop()
    {
        // Use the original EventSystem click threshold, not a new world rule.
        return EventSystem.current != null ? Mathf.Max(1, EventSystem.current.pixelDragThreshold) : 5;
    }

    internal static void SampleTouches()
    {
        if (sampledFrame == Time.frameCount) return;
        sampledFrame = Time.frameCount;
        float now = Time.realtimeSinceStartup;
        bool multiple = Input.touchCount > 1;
        float slop = DragSlop();
        foreach (var touch in Input.touches)
        {
            Gesture g;
            if (touch.phase == TouchPhase.Began || !gestures.TryGetValue(touch.fingerId, out g))
                g = new Gesture { origin = touch.position };
            g.lastSeen = now;
            g.blocked |= multiple || touch.phase == TouchPhase.Canceled ||
                         (touch.position - g.origin).sqrMagnitude > slop * slop;
            gestures[touch.fingerId] = g;
        }
        expired.Clear();
        foreach (var pair in gestures)
            if (now - pair.Value.lastSeen > 0.75f) expired.Add(pair.Key);
        foreach (int id in expired) gestures.Remove(id);
    }

    internal static void ClearGestures() { gestures.Clear(); sampledFrame = -1; }

    static bool Reject(string reason)
    {
        LastRejection = reason;
        RejectedTaps++;
        return false;
    }

    public static bool MayRefresh(UIStarmap map, PointerEventData evt)
    {
        // The call site only enters here for a real touch pointer. Preserve all
        // physical and synthetic mouse event paths without changing their input.
        if (evt == null || evt.pointerId < 0) return false;
        // The original click can arrive in the observer's creation frame or
        // after the regular input sample. Update End/Canceled ownership here too.
        SampleTouches();
        DSPSmartTouchFrame.CheckPeripherals();
        if (DSPSmartTouchFrame.KeyboardAndMouse) return Reject("keyboard and mouse active");
        if (!Application.isFocused || map == null || !map.active || map.screenImage == null)
            return Reject("starmap unavailable");
        if (evt.dragging || Input.touchCount > 1) return Reject("drag or multiple fingers");
        Gesture g;
        if (gestures.TryGetValue(evt.pointerId, out g) && g.blocked)
            return Reject("gesture already dragged or canceled");
        float slop = DragSlop();
        if ((evt.position - evt.pressPosition).sqrMagnitude > slop * slop)
            return Reject("click moved past UI threshold");
        Canvas canvas = map.screenImage.GetComponentInParent<Canvas>();
        Camera uiCamera = canvas != null ? canvas.worldCamera : null;
        if (!RectTransformUtility.RectangleContainsScreenPoint(map.screenImage.rectTransform, evt.position, uiCamera))
            return Reject("outside starmap image");
        // A gesture that started over a foreground menu cannot select a body
        // behind it even if it ends over the map.
        GameObject pressed = evt.pointerPressRaycast.gameObject;
        if (pressed != null && pressed != map.screenImage.gameObject)
            return Reject("pressed foreground UI: " + pressed.name);
        if (EventSystem.current == null) return Reject("no EventSystem");
        hits.Clear();
        EventSystem.current.RaycastAll(new PointerEventData(EventSystem.current) { position = evt.position }, hits);
        foreach (var hit in hits)
        {
            if (!(hit.module is GraphicRaycaster)) continue;
            if (hit.gameObject != map.screenImage.gameObject)
                return Reject("foreground UI: " + hit.gameObject.name);
            // Exact viewport only: never whitelist its entire parent UI tree.
            LastRejection = "";
            RefreshedTaps++;
            return true;
        }
        // If the content image does not raycast, an explicit original event may
        // still arrive. Permit only when no other Graphic covers this point.
        if (!map.screenImage.raycastTarget)
        {
            LastRejection = "";
            RefreshedTaps++;
            return true;
        }
        return Reject("starmap image was not the first UI hit");
    }
}

// No visual objects or UI interception. This records drag/multitouch ownership
// before Unity dispatches the original PointerClick event on finger release.
[DefaultExecutionOrder(-32000)]
public sealed class DSPPadStarmapTouchObserver : MonoBehaviour
{
    void Update() { DSPPadStarmapTouch.SampleTouches(); }
    void OnApplicationFocus(bool focus) { if (!focus) DSPPadStarmapTouch.ClearGestures(); }
    void OnApplicationPause(bool pause) { if (pause) DSPPadStarmapTouch.ClearGestures(); }
}
