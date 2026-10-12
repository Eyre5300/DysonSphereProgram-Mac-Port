#!/usr/bin/env python3
"""Install authored iPad controls into a user's private recovered game project.
No original game implementation or resources are included in this script.
"""
from __future__ import annotations

import argparse
from pathlib import Path
import shutil


def apply(project: Path, source: Path, rsp: Path | None = None):
    assets = project / 'Assets'
    game = assets / 'Scripts' / 'Assembly-CSharp'
    baseline = (game / 'VFInput.cs').read_text()
    if 'using Input = DSPPadInput;' not in baseline or 'DSPSmartTouchFrame.Sample(' not in baseline:
        raise ValueError('Install the full-game iPad input foundation first; this incremental Esc patch does not export the game.')
    for name in ('DSPPadInput.cs', 'DSPSmartTouchFrame.cs', 'DSPPadEscapeButton.cs'):
        shutil.copyfile(source / name, assets / name)
    vf = game / 'VFInput.cs'
    text = vf.read_text()
    head, body = text.split('\tpublic static void OnFixedUpdate()', 1)
    fixed, tail = body.split('\tpublic static void ResetAllAxes()', 1)
    marker = 'DSPPadInput.FixedInputSampled();'
    if marker not in fixed:
        end = '\t\tDeepProfiler.EndSample(-1, -2L);'
        if fixed.count(end) != 1:
            raise ValueError('Unexpected original fixed input sampler; review this game version.')
        fixed = fixed.replace(end, '#if DSP_EMU_IPAD\n\t\t' + marker + '\n#endif\n' + end)
    vf.write_text(head + '\tpublic static void OnFixedUpdate()' + fixed + '\tpublic static void ResetAllAxes()' + tail)
    # The original mecha editor has its own input reader and Escape consumer.
    mecha = game / 'UIMechaEditorInput.cs'
    alias = '#if DSP_EMU_IPAD\nusing Input = DSPPadInput;\n#endif\n'
    text = mecha.read_text()
    if not text.startswith(alias):
        mecha.write_text(alias + text)
    # A selected text field uses Escape to deselect, before any window closes.
    ui_button = game / 'UIButton.cs'
    text = ui_button.read_text()
    if 'DSPPadInput.GetKeyDown(KeyCode.Escape)' not in text:
        old = 'if (Input.GetKeyDown(KeyCode.Escape) && EventSystem.current.currentSelectedGameObject == base.gameObject)'
        if text.count(old) != 1:
            raise ValueError('Unexpected original input-field Escape consumer; review this game version.')
        replacement = '#if DSP_EMU_IPAD\n\t\t\t' + old.replace('Input.GetKeyDown', 'DSPPadInput.GetKeyDown') + '\n#else\n\t\t\t' + old + '\n#endif'
        ui_button.write_text(text.replace(old, replacement))
    if rsp:
        text = rsp.read_text()
        name = '"Assets/DSPPadEscapeButton.cs"'
        if name not in text:
            rsp.write_text(text.rstrip() + '\n' + name + '\n')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--project', type=Path, required=True)
    parser.add_argument('--source', type=Path, default=Path(__file__).resolve().parent)
    parser.add_argument('--rsp', type=Path)
    args = parser.parse_args()
    apply(args.project.resolve(), args.source.resolve(), args.rsp.resolve() if args.rsp else None)
