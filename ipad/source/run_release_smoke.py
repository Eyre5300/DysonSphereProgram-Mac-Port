"""One bounded package smoke; accepts only the launched process's evidence."""
import argparse,json,subprocess,time,uuid
from pathlib import Path
from private_paths import private_output

CHECKS={'entered gameplay world','simulation advances','render frames advance','resolution retained','factory veins present','isolated save succeeds','isolated save reloads'}
def validate(native,game,report,batch,version):
    for value in (native,game,report):
        if not value or value.get('batchIdentifier')!=batch or str(value.get('buildVersion'))!=version:return False
    return (native.get('diagnosticFlags')==16385 and game.get('phase')=='batch_finished_normal_exit'
            and game.get('autoTestCompleted') is True and not game.get('errors')
            and report.get('completed') is True and report.get('restored') is True
            and report.get('phase')=='passed' and not report.get('errors')
            and CHECKS.issubset(set(report.get('checks',[])))
            and report.get('endTick',0)>report.get('startTick',0)+60)

def main():
    p=argparse.ArgumentParser(description=__doc__)
    for k in ('device','bundle','version'):p.add_argument('--'+k,required=True)
    p.add_argument('--output',type=Path,required=True);a=p.parse_args();out=private_output(a.output);out.mkdir(parents=True,exist_ok=True)
    batch=str(uuid.uuid4());base=['xcrun','devicectl','device'];state={'batchIdentifier':batch,'version':a.version,'passed':False}
    def fetch(name):
        dest=out/name
        r=subprocess.run(base+['copy','from','--device',a.device,'--domain-type','appDataContainer','--domain-identifier',a.bundle,'--source','Documents/'+name,'--destination',str(dest),'--quiet','--timeout','20'],capture_output=True,timeout=25)
        if r.returncode:return None
        try:return json.loads(dest.read_text())
        except (ValueError,OSError):return None
    command=base+['process','launch','--device',a.device,'--terminate-existing','--console','--json-output',str(out/'launch.json'),a.bundle,'--dsp-port-test-batch','--dsp-release-smoke','--dsp-batch-id='+batch]
    with (out/'console.log').open('w') as log:
        process=subprocess.Popen(command,stdout=log,stderr=subprocess.STDOUT);start=time.monotonic();last=None
        while process.poll() is None:
            time.sleep(4)
            n=fetch('emu-native-device-report.json');g=fetch('emu-full-game-report.json')
            if n and n.get('batchIdentifier')==batch:
                state['processIdentifier']=n.get('processIdentifier')
                if g and g.get('batchIdentifier')==batch and g.get('phase')!=last:
                    last=g.get('phase');print('Smoke:',last,flush=True)
            if time.monotonic()-start>650:
                # Do not kill an unknown or subsequently replaced game process.
                if n and n.get('batchIdentifier')==batch and n.get('processIdentifier'):
                    subprocess.run(base+['process','terminate','--device',a.device,'--pid',str(n['processIdentifier']),'--timeout','20'],capture_output=True,timeout=25)
                state['failure']='Smoke timeout; inspect console and preserve backup';break
        state['consoleExitCode']=process.poll()
    native=fetch('emu-native-device-report.json');game=fetch('emu-full-game-report.json');report=fetch('release-smoke.json')
    state['passed']=state.get('consoleExitCode')==0 and validate(native,game,report,batch,a.version)
    state.update(native=native,game=game,report=report)
    (out/'result.json').write_text(json.dumps(state,indent=2)+'\n')
    if not state['passed']:raise SystemExit('Package smoke failed; see '+str(out))
    subprocess.run(base+['copy','from','--device',a.device,'--domain-type','appDataContainer','--domain-identifier',a.bundle,'--source','Documents/release-smoke.png','--destination',str(out/'release-smoke.png'),'--quiet','--timeout','20'],check=True)
    print('Package smoke passed. No physical input or all-scene parity claim.',flush=True)
if __name__=='__main__':main()
