"""Apply the authored macOS input bridge to a private recovered project."""
from pathlib import Path
import argparse, shutil, subprocess

def apply(project, runtime):
    assets=project/'Assets'; src=assets/'Scripts/Assembly-CSharp'
    updates={}
    def transform(name, old, new, marker):
        path=src/name; text=updates.get(path,path.read_text())
        if marker in text:return
        if text.count(old)!=1:raise ValueError('Unsupported input anchor: '+name)
        updates[path]=text.replace(old,new,1)
    transform('VFInput.cs','return _InputValueNoFullscreen(axis_button, 29).onDown;',
              'return PortMacInput.DefaultWarp(_InputValueNoFullscreen(axis_button, 29).onDown);','PortMacInput.DefaultWarp(')
    transform('VFInput.cs','\t\tUpdateGameStates();\n\t\tint frameCount = Time.frameCount;',
              '\t\tUpdateGameStates();\n\t\tPortMacInput.Poll();\n\t\tint frameCount = Time.frameCount;','PortMacInput.Poll();')
    plugin=assets/'Plugins/macOS';plugin.mkdir(parents=True,exist_ok=True)
    subprocess.run(['xcrun','clang','-x','objective-c','-fobjc-arc','-fblocks','-dynamiclib','-arch','arm64','-arch','x86_64','-mmacosx-version-min=11.0','-framework','AppKit','-framework','GameController',str(runtime/'port_mac_input.c'),'-o',str(plugin/'libDSPPortInput.dylib')],check=True)
    shutil.copy2(runtime/'PortMacInput.cs',assets/'PortMacInput.cs')
    for path,text in updates.items():path.write_text(text)

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--project',type=Path,required=True);p.add_argument('--runtime',type=Path,required=True);a=p.parse_args();apply(a.project,a.runtime)
