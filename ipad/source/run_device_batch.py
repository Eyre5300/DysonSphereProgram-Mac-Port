"""Run a user-authorized iPad batch; verify this process's opt-in and world entry.

--restart-existing is explicit: use only after user authorizes restarting tests.
A menu, old JSON file, successful launch command, or install is never a test pass.
"""
from pathlib import Path
import argparse,json,subprocess,time,uuid
from device_report_identity import ReportIdentity
p=argparse.ArgumentParser(description=__doc__)
p.add_argument('--device',required=True);p.add_argument('--bundle',required=True);p.add_argument('--version',required=True)
p.add_argument('--integration',action='store_true',help='Validate shared files, mode switching and keyboard/mouse, plus touch when applicable');p.add_argument('--touch',action='store_true',help='Validate the separate touch App first-phase report');p.add_argument('--allocation-events',action='store_true');p.add_argument('--memory-pressure-probe',action='store_true');p.add_argument('--restart-existing',action='store_true');p.add_argument('--output-dir',type=Path,required=True);a=p.parse_args()
out=a.output_dir or Path(__file__).resolve().parents[1]/'local-private/outputs/full-game-bridge'
from private_paths import private_output
out=private_output(out)
out.mkdir(parents=True,exist_ok=True);batch_id=str(uuid.uuid4());version=a.version
state={'batchIdentifier':batch_id,'expectedVersion':version,'flagsVerified':False,'enteredWorld':False,'finished':False,'phases':[]}
state_path=out/('launch-validation-'+version+'.json')
def write():state_path.write_text(json.dumps(state,indent=2))
def read_remote(name):
 target=out/('live-'+version+'-'+name.replace('/','-'))
 args=['xcrun','devicectl','device','copy','from','--device',a.device,'--domain-type','appDataContainer','--domain-identifier',a.bundle,'--source','Documents/'+name,'--destination',str(target)]
 r=subprocess.run(args,capture_output=True,text=True,timeout=20)
 if r.returncode:return None
 try:return json.loads(target.read_text())
 except (ValueError,FileNotFoundError):return None
baseline_game=read_remote('emu-full-game-report.json')
identity=ReportIdentity(batch_id,version,baseline_game)
args=['xcrun','devicectl','device','process','launch','--device',a.device,'--console','--json-output',str(out/('launch-'+version+'.json'))]
if a.restart_existing:args+=['--terminate-existing']
args += [a.bundle,'--dsp-port-test-batch','--dsp-native-pointer-test','--dsp-batch-id='+batch_id]
if a.memory_pressure_probe:args+=['--dsp-memory-pressure-probe']
if a.allocation_events:args+=['--dsp-allocation-events']
input_files_flag=a.integration and '.touch.' not in a.bundle
if input_files_flag:args+=['--dsp-input-files-test']
expected_flags=3|(64 if a.memory_pressure_probe else 0)|(128 if input_files_flag else 0)
state['command']=args;write();begin=time.monotonic();last_phase=None
with (out/('console-'+version+'.log')).open('w') as console:
 child=subprocess.Popen(args,stdout=console,stderr=subprocess.STDOUT)
 while child.poll() is None:
  time.sleep(4)
  try:
   native=read_remote('emu-native-device-report.json')
   valid=native and native.get('batchIdentifier')==batch_id and str(native.get('buildVersion'))==version and native.get('diagnosticFlags')==expected_flags
   if valid:
    if not state['flagsVerified']:
     state['flagsVerified']=True;state['processIdentifier']=native['processIdentifier'];print('Verified fresh batch identifier, build and native flags; PID',state['processIdentifier'],flush=True)
    game=read_remote('emu-full-game-report.json')
    if identity.accept(game):
     phase=game.get('phase')
     if phase!=last_phase:
      last_phase=phase;state['phases'].append(phase);print('Phase:',phase,'tick:',game.get('tick'),'errors:',len(game.get('errors',[])),flush=True)
     if identity.entered_world(game):state['enteredWorld']=True
     state['lastGameReport']=game
     if phase and phase.startswith('functional_batch_'):
      functional=read_remote('functional-batch-'+version+'/report.json')
      if functional:
       if functional.get('phase')!=state.get('functionalPhase'):
        print('Functional:',functional.get('phase'),'errors:',len(functional.get('errors',[])),flush=True)
       state['functionalPhase']=functional.get('phase');state['functionalReport']=functional
   elif time.monotonic()-begin>90 and not state['flagsVerified']:
    state['failure']='No matching native batch/build/flag acknowledgement after90s; do not count test as started';print(state['failure'],flush=True);write();break
   write()
  except subprocess.TimeoutExpired: print('Device report transfer timed out; console left running',flush=True)
 # Do not terminate the child on a reporting failure: console signals forward
 # to the game. Caller can inspect and explicitly restart under authorization.
 if child.poll() is not None:
  state['consoleExitCode']=child.returncode;state['finished']=True
  native=read_remote('emu-native-device-report.json')
  if native and native.get('batchIdentifier')==batch_id:
   final_game=read_remote('emu-full-game-report.json')
   if identity.accept(final_game):
    state['finalGameReport']=final_game
    functional=read_remote('functional-batch-'+version+'/report.json')
    if functional:state['functionalReport']=functional;state['functionalPhase']=functional.get('phase')
   else:state['finalReportRejected']='Missing or stale managed final report'
  from batch_result import failures
  if a.integration:
   from batch_result import integration_failures
   state['integrationReport']=read_remote('input-files-regression.json')
   state['keyboardReport']=read_remote('dsp-keyboard-regression.json')
   state['mouseReport']=read_remote('dsp-native-mouse-regression.json')
   if '.touch.' in a.bundle:state['touchReport']=read_remote('touch-regression.json')
   state['validationFailures']=integration_failures(state,'.touch.' in a.bundle)
  elif a.touch:
   from batch_result import touch_failures
   state['touchReport']=read_remote('touch-regression.json')
   state['validationFailures']=touch_failures(state,state['touchReport'])
  else:state['validationFailures']=failures(state,state.get('functionalReport'))
  state['passed']=not state['validationFailures']
  write();print('Console finished:',child.returncode,'worldEntered:',state['enteredWorld'],flush=True)
  if not state['passed']:raise SystemExit(child.returncode or 1)
