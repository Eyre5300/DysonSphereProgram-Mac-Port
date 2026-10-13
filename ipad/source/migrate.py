"""Configured iPad Pro migration: prepare, build, verify, back up and deploy.

Only owned inputs and private generated directories are used. A journal resumes
completed stages with unchanged configuration/tools. SDKs, licensing, signing
and device trust are prerequisites, not bypassed by this workflow.
"""
import argparse,hashlib,importlib.metadata,json,os,platform,plistlib,re,shutil,subprocess,sys,time
from pathlib import Path
from private_paths import private_output
from unity_paths import ios_support

ROOT=Path(__file__).resolve().parents[2]
SOURCE=Path(__file__).resolve().parent
PIN='be2060bd1fbdf70545f954a3e4dc90c8f1a27cb0'
def digest(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as f:
        for block in iter(lambda:f.read(8*1024*1024),b''):h.update(block)
    return h.hexdigest()
def inventory(folder):
    return {str(p.relative_to(folder)):digest(p) for p in sorted(Path(folder).rglob('*')) if p.is_file()}
def write(path,value):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True);tmp=path.with_suffix(path.suffix+'.tmp');tmp.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n');tmp.replace(path)
def canonical(config):
    result=dict(config)
    for key in ('game','workspace','unity','upstream','exported_project','assetripper','spirv_cross','vkd3d'):
        if result.get(key):result[key]=str(Path(result[key]).expanduser().resolve())
    for key in ('game','workspace','unity','upstream','spirv_cross','vkd3d','team','bundle','device','identity','version'):
        if not result.get(key):raise ValueError('Missing configuration: '+key)
    if bool(result.get('exported_project'))==bool(result.get('assetripper')):raise ValueError('Choose exported_project OR assetripper')
    if not re.fullmatch(r'[0-9]+',str(result['version'])):raise ValueError('Use an integer build version, e.g. 47')
    result['version']=str(result['version'])
    if '.touch.' in result['bundle']:raise ValueError('This workflow deploys the keyboard Pro App only')
    return result
def preflight(c):
    if platform.system()!='Darwin' or platform.machine()!='arm64':raise ValueError('Apple Silicon macOS required')
    if sys.version_info[:2]!=(3,12):raise ValueError('Use Python 3.12 with the documented requirements')
    for package,version in [('UnityPy','1.25.4'),('PyYAML','6.0.3'),('texture2ddecoder','1.0.6'),('pefile','2024.8.26'),('Pillow','12.3.0')]:
        if importlib.metadata.version(package)!=version:raise ValueError('Install the pinned requirements: '+package+'=='+version)
    game=Path(c['game']);workspace=private_output(c['workspace'],[c[k] for k in ('game','unity','upstream','exported_project','assetripper','spirv_cross','vkd3d') if c.get(k)])
    if 'local-private' not in workspace.parts:raise ValueError('Workspace path must contain local-private')
    if any(part in ('Mobile Documents','CloudStorage') for part in workspace.parts):raise ValueError('Use a local workspace outside cloud sync')
    from importlib.util import spec_from_file_location,module_from_spec
    spec=spec_from_file_location('editor_preflight',ROOT/'tools/editor_preflight.py');m=module_from_spec(spec);spec.loader.exec_module(m)
    editor=m.validate_editor(Path(c['unity'])/'Contents/MacOS/Unity');module=ios_support(c['unity'])
    dll=game/'DSPGAME_Data/Managed/Assembly-CSharp.dll'
    if not dll.is_file() or digest(dll)!='6c122e5443e6843979b4064050dfcb5e0d75577a0b64f6ae4111290238b33c12':raise ValueError('Expected owned Windows DSP 0.10.35.29104')
    for key in ('spirv_cross','vkd3d','assetripper'):
        if c.get(key) and not (Path(c[key]).is_file() and os.access(c[key],os.X_OK)):raise ValueError('Missing executable: '+key)
    if c.get('exported_project') and not (Path(c['exported_project'])/'Assets/Scripts/Assembly-CSharp/DSPGame.cs').is_file():raise ValueError('Untouched AssetRipper export unavailable')
    commit=subprocess.check_output(['git','-C',c['upstream'],'rev-parse','HEAD'],text=True).strip()
    if commit!=PIN:raise ValueError('Use the pinned emu commit '+PIN)
    identities=subprocess.check_output(['security','find-identity','-v','-p','codesigning'],text=True)
    if c['identity'] not in identities:raise ValueError('Requested signing identity is not installed in Keychain')
    subprocess.run(['xcrun','--sdk','iphoneos','--show-sdk-path'],check=True,stdout=subprocess.DEVNULL)
    existing=workspace
    while not existing.exists():existing=existing.parent
    free=shutil.disk_usage(existing).free
    if not (workspace/'migration.json').exists() and free<65*1024**3:raise ValueError('At least 65 GiB free space recommended before a fresh migration')
    return {'unity':editor,'iosSupport':str(module),'freeGiB':round(free/1024**3,1),'gameAssemblySHA256':digest(dll),'upstreamCommit':commit}

class Workflow:
    def __init__(self,config):
        self.c=canonical(config);self.preflight=preflight(self.c);self.work=Path(self.c['workspace'])
        if self.work.exists() and any(self.work.iterdir()) and not (self.work/'migration.json').is_file():raise ValueError('Workspace is not empty and is not owned by this workflow')
        self.work.mkdir(parents=True,exist_ok=True)
        self.path=self.work/'migration.json';self.logs=self.work/'logs';self.logs.mkdir(exist_ok=True)
        fingerprint=hashlib.sha256(json.dumps(self.c,sort_keys=True).encode()).hexdigest()
        tools=hashlib.sha256(json.dumps({str(p.relative_to(ROOT)):digest(p) for p in sorted(ROOT.rglob('*')) if p.is_file() and p.suffix in ('.py','.cs','.mm','.m','.h','.hpp','.c') and '.git' not in p.parts and '__pycache__' not in p.parts},sort_keys=True).encode()).hexdigest()
        if self.path.exists():
            self.state=json.loads(self.path.read_text())
            if self.state['configSHA256']!=fingerprint or self.state['toolsSHA256']!=tools:raise ValueError('Configuration/tools changed; use a new workspace to avoid stale-stage reuse')
        else:self.state={'configSHA256':fingerprint,'toolsSHA256':tools,'stages':{},'preflight':self.preflight}
        self.save()
    def save(self):write(self.path,self.state)
    def run(self,name,args,env=None):
        print(name,flush=True)
        with (self.logs/(name+'.log')).open('a') as log:subprocess.run(list(map(str,args)),stdout=log,stderr=subprocess.STDOUT,env=env,check=True)
    def tool(self,name,*args):return [sys.executable,SOURCE/name,*args]
    def stage(self,name,action,outputs):
        prior=self.state['stages'].get(name)
        if prior and prior.get('done'):
            if all(Path(p).is_file() and digest(p)==h for p,h in prior['outputs'].items()):print('Verified completed stage:',name,flush=True);return
            raise ValueError('Completed stage output changed or was removed: '+name)
        if self.state.get('activeStage')==name:
            retry_paths={'prepare':['source-work'],'probe-build':['probe-build','probe-derived'],'release-build':['release-build','release-derived'],'backup':['user-backup'],'user-data':['user-after','user-verified']}
            for rel in retry_paths.get(name,[]):
                generated=self.work/rel
                if generated.exists():generated.rename(self.work/(rel+'.failed-'+str(time.time_ns())))
        self.state['activeStage']=name;self.save();action()
        self.state['stages'][name]={'done':True,'outputs':{str(p):digest(p) for p in outputs},'finishedUtc':time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime())};self.save()
    def device(self,name,*args):
        path=self.logs/(name+'.json');self.run(name,['xcrun','devicectl','device',*args[:2],'--device',self.c['device'],'--json-output',path,'--quiet','--timeout','120',*args[2:]])
        return json.loads(path.read_text())['result']
    def copy(self,direction,source,dest):
        self.run('device-copy-'+direction,['xcrun','devicectl','device','copy',direction,'--device',self.c['device'],'--domain-type','appDataContainer','--domain-identifier',self.c['bundle'],'--source',source,'--destination',dest,'--quiet','--timeout','120'])
    def install(self,name,app):self.device(name,'install','app',str(app))
    def backup(self):
        apps=self.device('apps-before','info','apps').get('apps',[]);app=next((x for x in apps if x.get('bundleIdentifier')==self.c['bundle']),None)
        if app and not self.c.get('replace_existing',False):raise ValueError('App exists. Set replace_existing=true only if stopping/upgrading this App is intended')
        if app:
            # Match only this App's exact installation directory, never another game.
            prefix=app['url'].rstrip('/')+'/'
            for process in self.device('processes-before','info','processes').get('runningProcesses',[]):
                if process.get('executable','').startswith(prefix):self.device('stop-before-backup','process','terminate','--pid',str(process['processIdentifier']))
            self.copy('from','Documents/LocalPortData',str(self.work/'user-backup'))
        write(self.work/'backup.json',{'existingApp':app,'files':inventory(self.work/'user-backup') if app else {}})
    def restore_profile(self):
        saved=json.loads((self.work/'backup.json').read_text())
        if not saved['existingApp']:write(self.work/'user-data-verification.json',{'newInstallation':True});return
        self.copy('from','Documents/LocalPortData',str(self.work/'user-after'))
        before=saved['files'];after=inventory(self.work/'user-after');changed=[p for p,h in before.items() if after.get(p)!=h]
        # Tests use isolated saves. An altered existing save/options is a failure,
        # never silently replaced; the complete original backup remains available.
        protected=[p for p in changed if p.lower().endswith('.dsv') or Path(p).name.lower()=='options.xml']
        if protected:raise ValueError('Existing save/options changed unexpectedly: '+str(protected))
        for name in changed:
            if not any(x in ('Achievement','Property') for x in Path(name).parts):raise ValueError('Unexpected profile change; inspect backup before restoring: '+name)
            self.copy('to',str(self.work/'user-backup'/name),'Documents/LocalPortData/'+name)
        self.copy('from','Documents/LocalPortData',str(self.work/'user-verified'))
        verified=inventory(self.work/'user-verified')
        if any(verified.get(p)!=h for p,h in before.items()):raise ValueError('User profile restoration verification failed')
        write(self.work/'user-data-verification.json',{'originalFilesExact':len(before),'restoredTestSideEffects':changed,'newFiles':[p for p in verified if p not in before]})
    def execute(self):
        c=self.c;w=self.work;prep=w/'source-work';project=prep/'work/dsp-runtime/port-project';engine=w/'ios-engine';mac=w/'MacAOT.app';bc=w/'bc-engine';manifest=w/'bc-manifest.json';samples=w/'unity-bc-samples';data=Path(c['game'])/'DSPGAME_Data';unity=Path(c['unity'])/'Contents/MacOS/Unity'
        device=self.device('device-preflight','info','details');hardware=device.get('properties',{}).get('hardware',device.get('hardwareProperties',{}));software=device.get('deviceProperties',{})
        if 'iPad Pro' not in hardware.get('marketingName',''):raise ValueError('Only iPad Pro is supported; Mini is retired')
        enabled=software.get('developerModeStatus')=='enabled' or 'enabled' in device.get('properties',{}).get('state',{}).get('developerModeStatus',{})
        if not enabled:raise ValueError('Enable developer mode on the iPad and finish its confirmation first')
        sourcearg=['--exported-project',c['exported_project']] if c.get('exported_project') else ['--assetripper',c['assetripper']]
        self.stage('prepare',lambda:self.run('prepare',self.tool('prepare_from_windows.py','--game',c['game'],'--workspace',prep,'--spirv-cross',c['spirv_cross'],'--vkd3d',c['vkd3d'],*sourcearg)),[prep/'reports/ipad-source.json'])
        env=dict(os.environ,TMPDIR='/tmp',DSP_MAC_AOT_OUTPUT=str(mac),DSP_IOS_BRIDGE_OUTPUT=str(engine),DSP_IOS_BUNDLE_ID=c['bundle'],DSP_IOS_BUILD_NUMBER=c['version'])
        def export(target,method,log):self.run(log,[unity,'-batchmode','-quit','-projectPath',project,'-buildTarget',target,'-executeMethod',method,'-logFile',self.logs/(log+'-unity.log')],env)
        self.stage('mac-aot-export',lambda:export('StandaloneOSX','DSPFullGameBridgeBuild.BuildMacAOT','mac-export'),[mac/'Contents/Frameworks/GameAssembly.dylib'])
        self.stage('ios-export',lambda:export('iOS','DSPFullGameBridgeBuild.ExportIOS','ios-export'),[engine/'Libraries/libiPhone-lib.a'])
        self.stage('bc-archive',lambda:self.run('bc-archive',self.tool('prepare_bc_archive.py','--archive',engine/'Libraries/libiPhone-lib.a','--output',bc)),[bc/'receipt.json',bc/'libiPhone-bc-candidate.a'])
        self.stage('bc-manifest',lambda:self.run('bc-manifest',self.tool('create_bc_manifest.py','--source-data',data,'--target-data',engine/'Data','--output',manifest)),[manifest])
        self.stage('bc-samples',lambda:self.run('bc-samples',self.tool('prepare_unity_bc_samples.py','--manifest',manifest,'--source-data',data,'--output',samples)),[samples/'manifest.json'])
        common=['--project',project,'--engine',engine,'--unity',c['unity'],'--upstream',c['upstream'],'--team',c['team'],'--bundle',c['bundle'],'--device',c['device'],'--identity',c['identity'],'--bc-archive',bc/'libiPhone-bc-candidate.a','--original-exe',Path(c['game'])/'DSPGAME.exe']
        probeversion=c['version']+'.0';probebuild=w/'probe-build';probederived=w/'probe-derived';probeapp=probederived/'Build/Products/Release-iphoneos/DSPemuiPad.app'
        self.stage('probe-build',lambda:self.run('probe-build',self.tool('build_bridge.py',*common,'--work',probebuild,'--derived',probederived,'--version',probeversion,'--bc-probe-package')),[probebuild/'reports/package.json'])
        self.stage('backup',self.backup,[w/'backup.json'])
        def probe():
            self.install('install-probe',probeapp);self.copy('to',str(samples),'Documents/unity-bc-samples')
            self.run('bc-device',self.tool('run_bc_device_probe.py','--device',c['device'],'--bundle',c['bundle'],'--version',probeversion,'--output',w/'bc-results'))
        self.stage('bc-device',probe,[w/'bc-results/run.json',w/'bc-results/report-0.json'])
        build=w/'release-build';derived=w/'release-derived';app=derived/'Build/Products/Release-iphoneos/DSPemuiPad.app'
        self.stage('release-build',lambda:self.run('release-build',self.tool('build_bridge.py',*common,'--work',build,'--derived',derived,'--version',c['version'],'--bc-manifest',manifest,'--source-data',data,'--bc-sample-report',w/'bc-results/report-0.json')),[build/'reports/package.json',app/'Info.plist'])
        def release():
            self.install('install-release',app)
            self.run('release-smoke',self.tool('run_release_smoke.py','--device',c['device'],'--bundle',c['bundle'],'--version',c['version'],'--output',w/'release-smoke'))
        self.stage('release-smoke',release,[w/'release-smoke/result.json'])
        self.stage('user-data',self.restore_profile,[w/'user-data-verification.json'])
        self.device('normal-launch','process','launch','--terminate-existing',c['bundle'],'--dsp-diagnostics-only')
        self.state['status']='deployed_limited_smoke_passed';self.state['app']=str(app);self.save()
        print('Deployed. Review '+str(w/'release-smoke/release-smoke.png')+'. Physical input and new-machine equivalence remain separate.',flush=True)

def configure(path):
    if path.exists():return
    print('本机配置仅保存到私有目录。此流程会构建并安装；不会下载游戏、绕过许可或配置签名。')
    fields=[('game','已购买的Windows游戏目录'),('workspace','新的本机工作目录（云同步目录之外）'),('unity','Unity.app 路径'),('upstream','固定版本emu仓库路径'),('exported_project','未修改的AssetRipper导出目录'),('spirv_cross','spirv-cross可执行文件'),('vkd3d','vkd3d-compiler可执行文件'),('team','Apple Team ID'),('bundle','本次App的Bundle ID'),('device','iPad Pro UDID'),('identity','钥匙串中的签名identity名称或SHA'),('version','构建号，例如47')]
    config={key:input(label+': ').strip().strip('\"\'') for key,label in fields}
    config['replace_existing']=input('若该Bundle已安装，是否备份后停止并升级？输入 yes 启用: ').strip().lower()=='yes'
    write(path,canonical(config))
def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--config',type=Path,required=True);p.add_argument('--configure',action='store_true');p.add_argument('--check',action='store_true');a=p.parse_args();config=private_output(a.config)
    if a.configure:configure(config)
    c=canonical(json.loads(config.read_text()))
    if a.check:print(json.dumps(preflight(c),indent=2));return
    Workflow(c).execute()
if __name__=='__main__':
    try:main()
    except (ValueError,OSError,subprocess.CalledProcessError,importlib.metadata.PackageNotFoundError) as error:raise SystemExit('Migration stopped: '+str(error)+'\nInspect the last stage log. Original inputs and backup are retained; no success is claimed.')
