"""Generate private SPIR-V intermediates with local vkd3d; record every failure."""
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor,as_completed
import json,subprocess,os
root=Path.cwd();base=root/'work/dsp-shader-probe/batch'
programs=json.loads((base/'inventory.json').read_text())['programs']
compiler=root/'work/vkd3d-2.1/vkd3d-compiler'
def one(row):
 sha=row['sha256'];p=base/'programs'/sha
 result=subprocess.run([str(compiler),'-x','dxbc-tpf','-b','spirv-binary','--buffer-uav=storage-buffer',str(p)+'.dxbc','-o',str(p)+'.spv'],capture_output=True,text=True,timeout=60)
 return {'sha256':sha,'stage':row['stage'],'returncode':result.returncode,'diagnostics':result.stderr[:6000]}
results=[]
with ThreadPoolExecutor(max_workers=min(4,os.cpu_count()or 1))as pool:
 for f in as_completed([pool.submit(one,row)for row in programs]):
  results.append(f.result())
  if len(results)%500==0:print(len(results),'/',len(programs),flush=True)
(base/'spirv-results.json').write_text(json.dumps(results,indent=2))
failed=[r for r in results if r['returncode']]
print('converted',len(results)-len(failed),'failed',len(failed))
if failed:raise RuntimeError('SPIR-V conversion failures; inspect spirv-results.json')
