"""Run one explicit BC-only process; stale reports never count as evidence."""
import argparse,hashlib,json,subprocess,time,uuid
from pathlib import Path
p=argparse.ArgumentParser(description=__doc__);p.add_argument('--device',required=True);p.add_argument('--bundle',required=True);p.add_argument('--version',required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();from private_paths import private_output
a.output=private_output(a.output);a.output.mkdir(parents=True,exist_ok=True)
id=str(uuid.uuid4());state={'batchIdentifier':id,'expectedVersion':a.version,'flagsVerified':False,'finished':False,'passed':False};sp=a.output/'run.json'
def save():sp.write_text(json.dumps(state,indent=2)+'\n')
def fetch(name,local):
 path=a.output/local
 r=subprocess.run(['xcrun','devicectl','device','copy','from','--device',a.device,'--domain-type','appDataContainer','--domain-identifier',a.bundle,'--source','Documents/'+name,'--destination',str(path)],capture_output=True,text=True,timeout=25)
 if r.returncode:return None
 try:return json.loads(path.read_text())
 except (ValueError,FileNotFoundError):return None
baseline={}
for i in range(2):baseline[i]=fetch('unity-bc-sample-report-'+str(i)+'.json','previous-report-'+str(i)+'.json')
args=['xcrun','devicectl','device','process','launch','--device',a.device,'--terminate-existing','--console','--json-output',str(a.output/'launch.json'),a.bundle,'--dsp-port-test-batch','--dsp-bc-probe-only','--dsp-batch-id='+id];state['command']=args;save()
with (a.output/'console.log').open('w') as console:
 child=subprocess.Popen(args,stdout=console,stderr=subprocess.STDOUT)
 while child.poll() is None:
  time.sleep(5)
  try:
   n=fetch('emu-native-device-report.json','native.json')
   valid=n and n.get('batchIdentifier')==id and str(n.get('buildVersion'))==a.version and n.get('diagnosticFlags')==33
   if valid and not state['flagsVerified']:state['flagsVerified']=True;state['processIdentifier']=n['processIdentifier'];print('Fresh BC-only native flags/build/UUID verified',n['processIdentifier'],flush=True)
   if valid:state['native']=n
   save()
  except subprocess.TimeoutExpired:print('Read-only report copy timed out; process left running',flush=True)
 state['consoleExitCode']=child.returncode;state['finished']=True
reports=[]
for i in range(2):
 r=fetch('unity-bc-sample-report-'+str(i)+'.json','report-'+str(i)+'.json');fresh=r is not None and r!=baseline[i];passed=bool(fresh and r.get('finishedUtc') and r.get('status')=='sampled-subset-pass' and r.get('sampledSubsetPassed') and not r.get('errors') and len(r.get('results',[]))==233 and len(r.get('transferControls',[]))==512 and all(x.get('passed') and x.get('actualNativeFormat')==x.get('expectedNativeFormat')==x.get('sourceNativeFormat') and x.get('maximumCopyError')==0 for x in r['results']));reports.append({'fresh':fresh,'passed':passed});print('Pass',i, reports[-1],flush=True)
state['reports']=reports;state['passed']=state['flagsVerified'] and state['consoleExitCode']==0 and all(r['passed'] for r in reports);save();print('BC-only result:',state['passed'],flush=True)
if not state['passed']:raise SystemExit(1)
