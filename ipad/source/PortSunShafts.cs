// Preserve the original SunShafts composite; skip its mask/blur only behind the camera.
public static class PortSunShafts {
#if UNITY_STANDALONE_OSX && !UNITY_EDITOR
 public static bool Enabled=true;
#else
 public static bool Enabled=false;
#endif
 public static long Skipped;
}
