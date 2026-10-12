#!/usr/bin/env python3
"""Add an iPad-only event coordinate override to the user's recovered starmap.

The default action is a staging preview. --apply is explicit, intended to be
called by the converter after this candidate passes the root review.
The recipe contains no full recovered game method or assets.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import shutil

MARKER = "DSP_PAD_STARMAP_TOUCH_EVENT"
HELPER = "DSPPadStarmapTouch.cs"


def off_platform(source: str) -> str:
    """Evaluate only this recipe's simple DSP_EMU_IPAD regions."""
    kept = []
    include = True
    stack = []
    for line in source.splitlines(keepends=True):
        directive = line.strip()
        if directive == "#if DSP_EMU_IPAD":
            stack.append(include)
            include = False
        elif directive == "#else" and stack:
            include = stack[-1] and not include
        elif directive == "#endif" and stack:
            include = stack.pop()
        elif include:
            kept.append(line)
    if stack:
        raise ValueError("unbalanced DSP preprocessor regions")
    return "".join(kept)


def patch(source: str) -> tuple[str, dict]:
    if MARKER in source:
        if "MouseHoverCheck(pointerEventData.position);" not in source:
            raise ValueError("incomplete pre-existing starmap touch marker")
        return source, {"already_applied": True}
    # UIStarmap has no preprocessor regions before this patch. Refuse unknown
    # upstream conditions rather than claim a byte-identical comparison.
    if any(line.lstrip().startswith("#") for line in source.splitlines()):
        raise ValueError("pre-existing directives require explicit parity review")
    signature = "\tprivate void MouseHoverCheck()\n"
    if source.count(signature) != 1:
        raise ValueError("expected exactly one original MouseHoverCheck")
    candidate = source.replace(signature,
        "#if DSP_EMU_IPAD\n"
        "\tprivate void MouseHoverCheck(Vector3? touchPosition = null)\n"
        "#else\n" + signature + "#endif\n", 1)
    ray = "\t\tPhysics.Raycast(screenCamera.ScreenPointToRay(Input.mousePosition), out var hitInfo, 300f, 1048576);\n"
    position = "\t\tVector3 mousePosition = Input.mousePosition;\n"
    for original, replacement in (
        (ray, ray.replace("Input.mousePosition", "touchPosition ?? Input.mousePosition")),
        (position, position.replace("Input.mousePosition", "touchPosition ?? Input.mousePosition")),
    ):
        if candidate.count(original) != 1:
            raise ValueError("original starmap pointer anchor changed")
        candidate = candidate.replace(original,
            "#if DSP_EMU_IPAD\n" + replacement + "#else\n" + original + "#endif\n", 1)
    event = ("\tpublic void OnScreenClick(BaseEventData evtData)\n\t{\n"
             "\t\tif (!(evtData is PointerEventData pointerEventData))\n"
             "\t\t{\n\t\t\treturn;\n\t\t}\n")
    if candidate.count(event) != 1:
        raise ValueError("original OnScreenClick event anchor changed")
    injection = ("#if DSP_EMU_IPAD\n"
                 "\t\t// " + MARKER + "\n"
                 "\t\tif (pointerEventData.pointerId >= 0)\n"
                 "\t\t{\n"
                 "\t\t\tif (!DSPPadStarmapTouch.MayRefresh(this, pointerEventData)) return;\n"
                 "\t\t\tMouseHoverCheck(pointerEventData.position);\n"
                 "\t\t}\n"
                 "#endif\n")
    candidate = candidate.replace(event, event + injection, 1)
    if off_platform(candidate) != source:
        raise AssertionError("non-iPad branch differs from original bytes")
    if candidate.count("MouseHoverCheck(pointerEventData.position);") != 1:
        raise AssertionError("touch event must refresh exactly once")
    return candidate, {
        "already_applied": False,
        "non_ipad_byte_identical": True,
        "original_sha256": hashlib.sha256(source.encode()).hexdigest(),
        "candidate_sha256": hashlib.sha256(candidate.encode()).hexdigest(),
        "input_reads_overridden": 2,
        "emits_additional_mouse_event": False,
    }


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--project", required=True, type=Path)
    p.add_argument("--apply", action="store_true")
    p.add_argument("--rsp", type=Path, help="Optional existing incremental compiler response file to register the helper in")
    p.add_argument("--preview", type=Path, required=True)
    p.add_argument("--receipt", type=Path, required=True)
    args = p.parse_args()
    from private_paths import private_output
    args.preview=private_output(args.preview);args.receipt=private_output(args.receipt)
    path = args.project / "Assets/Scripts/Assembly-CSharp/UIStarmap.cs"
    with path.open(encoding="utf-8", newline="") as f:
        source = f.read()
    candidate, receipt = patch(source)
    receipt.update(project=str(args.project), applied=args.apply)
    if args.apply:
        if candidate != source:
            path.write_text(candidate)
        shutil.copy2(Path(__file__).parent / HELPER, args.project / "Assets" / HELPER)
        if args.rsp:
            rsp = args.rsp if args.rsp.is_absolute() else args.project / args.rsp
            entry = '"Assets/' + HELPER + '"'
            content = rsp.read_text()
            if entry not in content.splitlines():
                rsp.write_text(content.rstrip("\n") + "\n" + entry + "\n")
                receipt["rsp_registered"] = str(rsp)
    else:
        args.preview.parent.mkdir(parents=True, exist_ok=True)
        args.preview.write_text(candidate)
        receipt["preview"] = str(args.preview)
    args.receipt.write_text(json.dumps(receipt, indent=2) + "\n")
    print(json.dumps(receipt, indent=2))


if __name__ == "__main__":
    main()
