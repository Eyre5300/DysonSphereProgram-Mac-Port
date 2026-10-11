#!/usr/bin/env python3
"""Run a locally installed AssetRipper 2.0 on owned input through its loopback API."""
import argparse, json, re, signal, subprocess, time, urllib.request, urllib.parse
from pathlib import Path

SETTINGS={
 'ScriptContentLevel':'Level2','StreamingAssetsMode':'Extract','DefaultVersion':'0.0.0a0','TargetVersion':'0.0.0a0',
 'EnablePrefabOutlining':'true','EnableStaticMeshSeparation':'true','EnableAssetDeduplication':'true',
 'BundledAssetsExportMode':'DirectExport','AudioExportFormat':'Default','ImageExportFormat':'Png',
 'LightmapTextureExportFormat':'Yaml','ScriptExportMode':'Hybrid','ScriptLanguageVersion':'CSharp9_0',
 'ShaderExportMode':'Dummy','SpriteExportMode':'Yaml','TextExportMode':'Parse'}

def export(executable,game,output):
    executable,game,output=executable.resolve(),game.resolve(),output.resolve()
    if output.exists():raise ValueError('Export target already exists')
    output.parent.mkdir(parents=True,exist_ok=True);log=output.parent/'assetripper-server.log'
    # The server selects its own free loopback port. Never attach to another process.
    with log.open('wb')as stream:
        proc=subprocess.Popen([str(executable),'--headless','--port','0','--log-path',str(output.parent/'assetripper.log')],cwd=output.parent,stdout=stream,stderr=subprocess.STDOUT)
        try:
            end=time.monotonic()+60;base=None
            while time.monotonic()<end:
                if proc.poll()is not None:raise RuntimeError('AssetRipper exited; see '+str(log))
                match=re.search(r'Now listening on: (http://127\.0\.0\.1:\d+)',log.read_text(errors='replace'))
                if match:base=match[1];break
                time.sleep(.25)
            if base is None:raise RuntimeError('AssetRipper loopback startup timeout')
            def post(route,fields):
                data=urllib.parse.urlencode(fields).encode()
                with urllib.request.urlopen(base+route,data=data,timeout=3600)as r:
                    if r.status!=200:raise RuntimeError('AssetRipper HTTP '+str(r.status))
            post('/Settings/Update',SETTINGS)
            post('/LoadFolder',{'Path':str(game)})
            post('/Export/UnityProject',{'Path':str(output),'CreateSubfolder':'false'})
            required=['Assets/Scenes/level0.unity','Assets/Scripts/Assembly-CSharp/DSPGame.cs','ProjectSettings/ProjectSettings.asset']
            for name in required:
                if not (output/'ExportedProject'/name).is_file():raise RuntimeError('Incomplete export: '+name)
            (output.parent/'export-receipt.json').write_text(json.dumps({'settings':SETTINGS,'version':'AssetRipper 2.0.0','source':str(game),'output':str(output)},indent=2))
        finally:
            if proc.poll()is None:
                proc.send_signal(signal.SIGINT)
                try:proc.wait(timeout=15)
                except subprocess.TimeoutExpired:proc.terminate();proc.wait(timeout=15)
    return output/'ExportedProject'
if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for k in ('assetripper','game','output'):p.add_argument('--'+k,type=Path,required=True)
    a=p.parse_args();print(export(a.assetripper,a.game,a.output))
