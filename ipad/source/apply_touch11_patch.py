#!/usr/bin/env python3
"""Incremental full-game iPad touch11 patch; requires the touch/Esc foundation.
Only authored platform adapters are distributed; game input implementations
remain in the owner's private export and keep their original control rules.
"""
from __future__ import annotations
import argparse
from pathlib import Path
import shutil


def alias_input(path):
    text=path.read_text();prefix='#if DSP_EMU_IPAD\nusing Input = DSPPadInput;\n#endif\n'
    if not text.startswith(prefix):path.write_text(prefix+text)


def apply(project: Path,source: Path,rsp: Path|None=None):
    game=project/'Assets/Scripts/Assembly-CSharp'
    vf=game/'VFInput.cs';text=vf.read_text()
    if 'DSPPadInput.FixedInputSampled();' not in text or 'DSPSmartTouchFrame.Sample(' not in text:
        raise ValueError('Install the touch/Esc foundation first, then apply touch11.')
    # The canonical world pointer must feed both original terrain/entity raycasts
    # and all build tools. No raycast masks or selection/build logic are changed.
    for name in ['BuildTool.cs','RaycastLogic.cs','SpaceColliderLogic.cs','CreativeTool.cs','PlayerAction_Plant.cs','PlayerMove_Sail.cs','PlayerAction_Rts.cs']:
        alias_input(game/name)
    # IsPointerOverGameObject(-1) describes the old physical cursor. Only while
    # a synthetic world click is active, determine UI ownership at its own point.
    marker='DSPPadInput.VirtualPointerActive'
    if marker not in text:
        old='onGUI = inFullscreenGUI || (EventSystem.current != null && EventSystem.current.IsPointerOverGameObject());'
        if text.count(old)!=1:raise ValueError('Unexpected original GUI ownership path; review this game version.')
        text=text.replace(old,old+'\n#if DSP_EMU_IPAD\n\t\t\tif (DSPPadInput.VirtualPointerActive) onGUI = inFullscreenGUI || DSPSmartTouchFrame.UIBlocks(DSPPadInput.mousePosition);\n#endif')
        vf.write_text(text)
    # Original inventory callbacks already receive PointerEventData. A touch's
    # explicit position is authoritative; keep ordinary desktop mouse paths exact.
    storage=game/'UIStorageGrid.cs';text=storage.read_text()
    for method,next_method in [('OnContentMouseDown','OnContentMouseUp'),('OnContentMouseUp','OnStorageGridChanged')]:
        signature='\tpublic void '+method+'(BaseEventData eventData)'
        start=text.index(signature);brace=text.index('{',start);depth=1;end=brace+1
        while depth:
            if text[end]=='{':depth+=1
            elif text[end]=='}':depth-=1
            end+=1
        body=text[start:end]
        if 'touchPointerPosition' not in body:
            old='UIRoot.ScreenPointIntoRect(Input.mousePosition, contentRect, out rectPoint)'
            if body.count(old)!=1:raise ValueError('Unexpected inventory pointer callback: '+method)
            # Restrict to Unity's nonnegative touch IDs; physical mouse IDs stay -1/-2/-3.
            insert="""#if DSP_EMU_IPAD
\t\tVector3 touchPointerPosition = Input.mousePosition;
\t\tif (eventData is PointerEventData touchEvent && touchEvent.pointerId >= 0) touchPointerPosition = touchEvent.position;
#endif
\t\t"""
            needle='Vector2 rectPoint = Vector2.zero;'
            assert body.count(needle)==1
            body=body.replace(needle,insert+needle)
            condition='if (!'+old+')'
            assert body.count(condition)==1
            patched='#if DSP_EMU_IPAD\n\t\tif (!UIRoot.ScreenPointIntoRect(touchPointerPosition, contentRect, out rectPoint))\n#else\n\t\t'+condition+'\n#endif'
            body=body.replace(condition,patched)
            text=text[:start]+body+text[end:]
    storage.write_text(text)
    for name in ['DSPPadInput.cs','DSPSmartTouchFrame.cs','DSPPadTapGesture.cs','DSPPadEscapeButton.cs']:
        shutil.copyfile(source/name,project/'Assets'/name)
    if rsp:
        text=rsp.read_text();new='"Assets/DSPPadTapGesture.cs"'
        if new not in text:rsp.write_text(text.rstrip()+'\n'+new+'\n')


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--project',type=Path,required=True);p.add_argument('--source',type=Path,default=Path(__file__).resolve().parent);p.add_argument('--rsp',type=Path)
    a=p.parse_args();apply(a.project.resolve(),a.source.resolve(),a.rsp.resolve() if a.rsp else None)
