#!/usr/bin/env python3
"""Restore camera HDR/FP16 on a generated DSP iOS graphics-settings copy.

Original adaptation code only. No game asset is bundled. UnityPy is required.
This changes six fields on the one GraphicsSettings object and verifies every
other object, reference and shader-define bit remains unchanged before replacing
the generated target. Run before resource finalization and app signing.
"""
from pathlib import Path
import argparse
import copy
import hashlib
import json
import os
import stat
import tempfile

import UnityPy

TIERS = ("Tier1", "Tier2", "Tier3")
FP16 = 1  # Unity 2022.3 CameraHDRMode.FP16 = RenderTextureFormat.ARGBHalf.
SOURCES = [
    "https://docs.unity3d.com/2022.3/Documentation/ScriptReference/Camera-allowHDR.html",
    "https://docs.unity3d.com/2022.3/Documentation/ScriptReference/Rendering.CameraHDRMode.html",
    "https://github.com/Unity-Technologies/UnityCsReference/blob/2022.3/Runtime/Export/Graphics/GraphicsEnums.cs",
]


def sha(data):
    return hashlib.sha256(data).hexdigest()


def external_identity(asset):
    return [
        (x.path, str(x.guid), x.type, getattr(x, "temp_empty", None))
        for x in asset.externals
    ]


def graphics_object(env):
    matches = [o for o in env.objects if o.type.name == "GraphicsSettings"]
    if len(matches) != 1 or matches[0].path_id != 7:
        raise ValueError("Expected the generated DSP GraphicsSettings object 7")
    return matches[0]


def apply(target, report_path):
    supplied = Path(target).absolute()
    if supplied.is_symlink():
        raise ValueError("Target must be a generated file, not a symlink")
    target = supplied.resolve(strict=True)
    report_path = Path(report_path).absolute()
    if report_path.resolve() == target or report_path.suffix.lower() != ".json":
        raise ValueError("Report must be a separate JSON file")
    if target.name != "globalgamemanagers" or target.parent.name != "Data":
        raise ValueError("Expected a generated iOS Data/globalgamemanagers copy")
    # Reject user-owned source game/cloud storage. This tool is for build output.
    if "Steam" in target.parts or "CloudStorage" in target.parts:
        raise ValueError("Original Steam or cloud documents must not be modified")
    original = target.read_bytes()
    original_sha = sha(original)
    env = UnityPy.load(original)
    asset = env.file
    if int(asset.target_platform) != 9 or not str(asset.unity_version).startswith("2022.3."):
        raise ValueError("Expected Unity 2022.3 iOS serialized data")
    before = {o.path_id: sha(o.get_raw_data()) for o in env.objects}
    if len(before) != 18:
        raise ValueError("Unexpected DSP manager layout: expected 18 objects")
    obj = graphics_object(env)
    tree = obj.read_typetree()
    expected = copy.deepcopy(tree)
    for tier in TIERS:
        settings = expected["m_TierSettings_" + tier]
        if not isinstance(settings["useHDR"], bool) or settings["hdrMode"] not in (1, 2):
            raise ValueError("Unexpected serialized HDR tier fields")
        settings["useHDR"] = True
        settings["hdrMode"] = FP16
    changed_fields = [
        "m_TierSettings_" + tier + "." + field
        for tier in TIERS
        for field in ("useHDR", "hdrMode")
        if tree["m_TierSettings_" + tier][field] != expected["m_TierSettings_" + tier][field]
    ]
    # An already-patched target is idempotent, including its serialized bytes.
    if changed_fields:
        obj.save_typetree(expected)
        candidate = asset.save()
    else:
        candidate = original
    check = UnityPy.load(candidate)
    checked = check.file.objects
    if set(checked) != set(before):
        raise ValueError("Serialized object identity changed")
    changed_objects = []
    for path_id, old_sha in before.items():
        checked_obj = checked[path_id]
        new_sha = sha(checked_obj.get_raw_data())
        if new_sha != old_sha:
            changed_objects.append({"pathID": path_id, "type": checked_obj.type.name})
        if path_id != 7 and new_sha != old_sha:
            raise ValueError("An unrelated serialized object changed: " + str(path_id))
    actual = graphics_object(check).read_typetree()
    if actual != expected:
        raise ValueError("GraphicsSettings differs outside the six intended fields")
    if external_identity(asset) != external_identity(check.file):
        raise ValueError("External asset references changed")
    if tree["m_ShaderDefinesPerShaderCompiler"] != actual["m_ShaderDefinesPerShaderCompiler"]:
        raise ValueError("Shader compiler defines changed")
    for tier in TIERS:
        if actual["m_TierSettings_" + tier]["useHDR"] is not True or actual["m_TierSettings_" + tier]["hdrMode"] != FP16:
            raise ValueError("HDR/FP16 semantic check failed")
    result = {
        "target": str(target),
        "unityVersion": str(asset.unity_version),
        "beforeSha256": original_sha,
        "afterSha256": sha(candidate),
        "changedFields": changed_fields,
        "changedObjects": changed_objects,
        "objectCount": len(before),
        "other17RawObjectsIdentical": True,
        "externalReferencesIdentical": True,
        "shaderCompilerDefinesIdentical": True,
        "tiersBefore": {tier: tree["m_TierSettings_" + tier] for tier in TIERS},
        "tiersAfter": {tier: actual["m_TierSettings_" + tier] for tier in TIERS},
        "hdrSemantics": {"hdr": True, "hdrMode": "FP16", "renderTextureFormat": "ARGBHalf"},
        "runtimeHDRSourceVerified": False,
        "completeGraphicsParityVerified": False,
        "officialReferences": SOURCES,
    }
    if changed_fields:
        mode = stat.S_IMODE(target.stat().st_mode)
        temporary = None
        try:
            with tempfile.NamedTemporaryFile(prefix=".dsp-hdr-tier-", dir=target.parent, delete=False) as f:
                temporary = Path(f.name)
                f.write(candidate)
                f.flush()
                os.fsync(f.fileno())
            os.chmod(temporary, mode)
            if sha(target.read_bytes()) != original_sha:
                raise ValueError("Target changed concurrently; no replacement performed")
            if sha(temporary.read_bytes()) != result["afterSha256"]:
                raise ValueError("Candidate file hash mismatch")
            os.replace(temporary, target)
            temporary = None
        finally:
            if temporary is not None:
                temporary.unlink(missing_ok=True)
    if sha(target.read_bytes()) != result["afterSha256"]:
        raise ValueError("Written target hash mismatch")
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n")
    return result


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--target", type=Path, required=True)
    p.add_argument("--report", type=Path, required=True)
    args = p.parse_args()
    result = apply(args.target, args.report)
    print("HDR/FP16 tiers verified; unchanged objects:", 17, "changed fields:", len(result["changedFields"]))
