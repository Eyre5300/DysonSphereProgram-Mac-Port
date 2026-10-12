"""Prepare an independent iPad project from owned Windows input.

Uses shared resource conversion code in this checkout; no Mac app, prepared
developer project, Unity Library, or previously compiled game data is needed.
"""
import argparse,subprocess,sys
from pathlib import Path
from private_paths import private_output

def main():
    p=argparse.ArgumentParser(description=__doc__)
    for key in ('game','workspace','spirv-cross','vkd3d'):p.add_argument('--'+key,type=Path,required=True)
    source=p.add_mutually_exclusive_group(required=True)
    source.add_argument('--exported-project',type=Path,help='Untouched AssetRipper 2.0 export')
    source.add_argument('--assetripper',type=Path,help='AssetRipper 2.0 executable')
    a=p.parse_args();root=Path(__file__).resolve().parents[2]
    work=private_output(a.workspace,[a.game]+([a.exported_project] if a.exported_project else []))
    if work.exists():p.error('Choose a new workspace; existing projects are never overwritten')
    def run(script,*args):subprocess.run([sys.executable,str(root/script),*map(str,args)],check=True)
    export=['--exported-project',a.exported_project] if a.exported_project else ['--assetripper',a.assetripper]
    run('tools/prepare_project.py','--game',a.game,'--workspace',work,'--spirv-cross',a.spirv_cross,'--vkd3d',a.vkd3d,*export)
    run('tools/recover_pipeline.py','--workspace',work)
    runtime=work/'work/dsp-runtime'
    run('ipad/source/prepare_ipad_project.py','--project',runtime/'port-project','--original-export',runtime/'recovered-project/ExportedProject','--game-assembly',a.game/'DSPGAME_Data/Managed/Assembly-CSharp.dll','--report',work/'reports/ipad-source.json')
    print('Independent iPad project prepared:',runtime/'port-project')
    print('Unity AOT/iOS exports, signing and device regression remain required.')

if __name__=='__main__':main()
