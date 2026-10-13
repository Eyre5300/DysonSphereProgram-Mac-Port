"""Gate only iPad pause scheduling; preserve the owned original window policy."""
import argparse, hashlib, json
from pathlib import Path
from private_paths import private_output

HOOKS = {'VFInput.cs': [('public static void OnUpdate()', 'AfterUpdate'),
                        ('public static void OnFixedUpdate()', 'AfterFixed'),
                        ('public static void UseEscape()', 'Consumed')],
         'GameMain.cs': [('private void FixedUpdate()', 'AfterLogic')], 'UIEscMenu.cs': []}
ORIGINAL = '\t\tif (!isMenuDemo && _running && VFInput.delayedEscape && !inOtherScene && !mainPlayer.respawning)'
BRIDGED = '#if DSP_EMU_IPAD\n'+ORIGINAL.replace('VFInput.delayedEscape', 'DSPPadEscapeOrder.PauseRequested')+'\n#else\n'+ORIGINAL+'\n#endif'
PAUSE_CALL='\t\t\t\tPause();'
PAUSE_BRIDGED='#if DSP_EMU_IPAD\n\t\t\t\tDSPPadEscapeOrder.BeginPause();\n#endif\n'+PAUSE_CALL
RESET='\t\tVFInput.ResetAllAxes();'
RESET_BRIDGED='#if DSP_EMU_IPAD\n\t\tDSPPadEscapeOrder.ResetForPauseMenu();\n#else\n'+RESET+'\n#endif'

def marker(call):
    return '\n#if DSP_EMU_IPAD\n\t\tDSPPadEscapeOrder.'+call+'();\n#endif\n'

def strip(source):
    for hooks in HOOKS.values():
        for _, call in hooks: source=source.replace(marker(call), '\n')
    return source.replace(BRIDGED, ORIGINAL).replace(PAUSE_BRIDGED,PAUSE_CALL).replace(RESET_BRIDGED,RESET)

def patch(source, name):
    result=source
    for signature, call in HOOKS[name]:
        if marker(call) in result: continue
        if result.count('\t'+signature+'\n\t{')!=1: raise ValueError('Unsupported method: '+signature)
        start=result.index('{',result.index('\t'+signature)); end=start+1; depth=1
        while depth:
            if result[end]=='{': depth+=1
            elif result[end]=='}': depth-=1
            end+=1
        if result[end-3:end]!='\n\t}': raise ValueError('Unsupported method tail: '+signature)
        result=result[:end-3]+marker(call)+result[end-2:]
    if name=='GameMain.cs' and BRIDGED not in result:
        if result.count(ORIGINAL)!=1: raise ValueError('Unsupported pause condition')
        result=result.replace(ORIGINAL,BRIDGED,1)
    for file,old,new in [('GameMain.cs',PAUSE_CALL,PAUSE_BRIDGED),('UIEscMenu.cs',RESET,RESET_BRIDGED)]:
        if name==file and new not in result:
            if result.count(old)!=1:raise ValueError('Unsupported pause transition: '+file)
            result=result.replace(old,new,1)
    if strip(result)!=strip(source): raise ValueError('Original method body changed')
    return result

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--project',type=Path,required=True);parser.add_argument('--report',type=Path,required=True)
    args=parser.parse_args();project=private_output(args.project);report=private_output(args.report)
    changes={}
    for name in HOOKS:
        path=project/'Assets/Scripts/Assembly-CSharp'/name;before=path.read_text();after=patch(before,name)
        if patch(after,name)!=after: raise ValueError('Not idempotent')
        changes[name]={'before':hashlib.sha256(before.encode()).hexdigest(),'after':hashlib.sha256(after.encode()).hexdigest(),'originalBodyUnchangedAfterStrip':True}
        path.write_text(after)
    report.parent.mkdir(parents=True,exist_ok=True);report.write_text(json.dumps(changes,indent=2))

if __name__=='__main__':main()
