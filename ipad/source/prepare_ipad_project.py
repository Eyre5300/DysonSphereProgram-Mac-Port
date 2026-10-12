"""Apply authored iPad adapters to a PRIVATE COPY of the prepared Mac project.
Not a game export: run the repository's Mac conversion/asset recovery first.
"""
import argparse,hashlib,json,re,shutil,subprocess,sys
from pathlib import Path
from private_paths import private_output
from apply_managed_input_trace import insert_method_tail

def once(text,old,new):
    if new in text:return text
    if text.count(old)!=1:raise ValueError('Unsupported source anchor: '+old[:80])
    return text.replace(old,new,1)
def main():
    p=argparse.ArgumentParser(description=__doc__)
    for n in ['project','original-export','game-assembly','report']:p.add_argument('--'+n,type=Path,required=True)
    a=p.parse_args();project=private_output(a.project);original=a.original_export.resolve();private_output(a.report,[original]);source=Path(__file__).resolve().parent
    if project==original or original in project.parents or project in original.parents:raise ValueError('Do not edit the untouched export')
    # Use the authoritative version pin already maintained by the Mac converter.
    prepare=source.parents[1]/'tools/prepare_project.py'
    match=re.search(r"SUPPORTED_SHA\s*=\s*['\"]([0-9a-f]{64})",prepare.read_text())
    if not match:raise ValueError('Missing shared Windows version pin')
    if hashlib.sha256(a.game_assembly.read_bytes()).hexdigest()!=match.group(1):raise ValueError('Unsupported Windows game assembly')
    a.report.parent.mkdir(parents=True,exist_ok=True)
    assets=project/'Assets';game=assets/'Scripts/Assembly-CSharp';before={}
    def edit(name,fn):
        q=game/name;s=q.read_text();t=fn(s);before[name]=hashlib.sha256(s.encode()).hexdigest();q.write_text(t)
    alias='#if DSP_EMU_IPAD\nusing Input = DSPPadInput;\n#endif\n'
    for q in game.rglob('*.cs'):
        s=q.read_text()
        if re.search(r'(?<![\w.])Input\.(GetKey(?:Down|Up)?|GetMouseButton(?:Down|Up)?|GetAxis|ResetInputAxes|mousePosition|mouseScrollDelta|anyKey(?:Down)?)\b',s) and 'using Input = DSPPadInput;' not in s:
            if re.search(r'using\s+Input\s*=',s):raise ValueError('Conflicting Input alias')
            q.write_text(alias+s)
    def vf(s):
        s=once(s,'\t\tUpdateGameStates();\n\t\tint frameCount = Time.frameCount;','\t\tUpdateGameStates();\n#if DSP_EMU_IPAD\n\t\tDSPPadInput.Poll();\n\t\tDSPSmartTouchFrame.Sample(GameMain.isRunning && !DSPGame.IsMenuDemo && !GameMain.isPaused && !inFullscreenGUI && !inputing && !inScreenshotMode);\n\t\tmouseMoveAxis += DSPSmartTouchFrame.Look;\n#endif\n\t\tPortMacInput.Poll();\n\t\tint frameCount = Time.frameCount;')
        s=insert_method_tail(s,'OnUpdate','DSPPadInput.UpdateInputPublished()')
        return insert_method_tail(s,'OnFixedUpdate','DSPPadInput.FixedInputSampled()')
    edit('VFInput.cs',vf)
    edit('DSPGame.cs',lambda s:once(s,'globalOption.LoadGlobal();','globalOption.LoadGlobal();\n\t\tPortDisplayPresets.ConfigureStartup(ref globalOption);'))
    edit('VFPreload.cs',lambda s:once(s,'private IEnumerator PreloadThread()\n\t{','private IEnumerator PreloadThread()\n\t{\n#if DSP_EMU_IPAD\n\t\tif(DSPPadDiagnosticLaunch.BCProbeRequested){yield return DSPPadBCBootstrap.Run();yield break;}\n#endif'))
    for q in (source.parents[1]/'runtime').glob('*.cs'):
        shutil.copy2(q,assets/q.name)
    for q in source.glob('*.cs'):
        if q.name=='DSPFullGameBridgeBuild.cs':dest=assets/'Editor'/q.name
        else:dest=assets/q.name
        dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(q,dest)
    def run(script,*args):subprocess.run([sys.executable,str(source/script),*map(str,args)],check=True)
    run('apply_touch_escape_patch.py','--project',project,'--source',source)
    run('apply_touch11_patch.py','--project',project,'--source',source)
    run('apply_mouse_input_patch.py','--project',project)
    starmap=game/'UIStarmap.cs';text=starmap.read_text()
    if text.startswith(alias):starmap.write_text(text[len(alias):])
    try:
        run('apply_starmap_touch_patch.py','--project',project,'--apply','--receipt',a.report.with_name('starmap-adapter.json'),'--preview',a.report.with_name('unused-preview.cs'))
    finally:
        text=starmap.read_text()
        if not text.startswith(alias):starmap.write_text(alias+text)
    run('apply_cursor_bridge.py','--file',game/'UICursor.cs','--report',a.report.with_name('cursor-adapter.json'))
    run('apply_dof_alpha_patch.py','--project',project)
    run('apply_textasset_stream.py','--original',original/'Assets/Scripts/Assembly-CSharp/HashSystem.cs','--target',game/'HashSystem.cs','--report',a.report.with_name('hash-adapter.json'))
    bloom=game/'UnityEngine/PostProcessing/BloomComponent.cs';s=bloom.read_text();anchor='RenderTextureFormat format = (Application.isMobilePlatform ? RenderTextureFormat.Default : RenderTextureFormat.DefaultHDR);';bloom.write_text(once(s,anchor,anchor+'\n#if DSP_EMU_IPAD\n            if (DSPPadRenderFormats.DesktopBloomCandidate) format = RenderTextureFormat.ARGBHalf;\n#endif'))
    # Avoid carrying Mac's optional lazy-target experiment into the iPad build.
    helper=assets/'PortUIRenderTargets.cs'
    s=helper.read_text().replace('Application.platform==RuntimePlatform.OSXPlayer&&','Application.platform==RuntimePlatform.OSXPlayer&&!Application.isMobilePlatform&&');helper.write_text(s)
    (assets/'link.xml').write_text('<linker><assembly fullname="Assembly-CSharp" preserve="all"/><assembly fullname="UnityEngine.UI" preserve="all"/></linker>\n')
    a.report.parent.mkdir(parents=True,exist_ok=True);a.report.write_text(json.dumps({'mode':'authored adapters applied to private prepared project','gameVersion':'0.10.35.29104','miniSupported':False,'newMachineEndToEndVerified':False,'directHooksBefore':before},indent=2))
    print('iPad source adapters prepared; compile and device validation still required.')
if __name__=='__main__':main()
