"""Apply a Mac-only zero-contribution SunShafts optimization to a private project.
No game source/assets are distributed. Refuse unknown input rather than guess.
"""
from pathlib import Path
import argparse, shutil

PATCH = """            // Port: preserve original HDR composite, skip the zero-contribution mask/blur.
            if (PortSunShafts.Enabled && vector.z < 0f)
            {
                PortSunShafts.Skipped++;
                sunShaftsMaterial.SetVector("_SunColor", Vector4.zero);
                sunShaftsMaterial.SetTexture("_ColorBuffer", Texture2D.blackTexture);
                Graphics.Blit(source, destination, sunShaftsMaterial, (screenBlendMode != ShaftsScreenBlendMode.Screen) ? 4 : 0);
                if (Application.isPlaying && DeepProfiler.inited && DeepProfiler.watchEnabled) DeepProfiler.EndSample(-1, -2L);
                return;
            }
"""

def patch_text(source):
    if "PortSunShafts.Enabled" in source:
        raise ValueError("Already patched; verify existing adaptation instead of replacing it")
    marker = "\t\t\tint width = source.width / num;"
    required = [marker, "vector.z >= 0f", 'sunShaftsMaterial.SetVector("_SunColor", Vector4.zero)', "DeepProfiler.EndSample(-1, -2L)"]
    if any(source.count(text) != 1 for text in required):
        raise ValueError("Unsupported SunShafts source layout; expected owned DSP0.10.35.29104 export")
    return source.replace(marker, PATCH + marker, 1)

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project", required=True, type=Path)
    parser.add_argument("--helper", required=True, type=Path)
    args = parser.parse_args()
    source = args.project / "Assets/Scripts/Assembly-CSharp/UnityStandardAssets/ImageEffects/SunShafts.cs"
    new_text = patch_text(source.read_text())
    backup = source.with_suffix(".cs.before-port-sun.txt")
    if backup.exists():
        raise ValueError("Backup exists; inspect it before retrying")
    helper = args.helper.read_bytes()
    shutil.copy2(source, backup)
    (args.project / "Assets/PortSunShafts.cs").write_bytes(helper)
    source.write_text(new_text)
    print("Private source patched; build and visual verification still required")

if __name__ == "__main__":
    main()
