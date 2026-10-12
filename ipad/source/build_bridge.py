"""Package a prepared iPad bridge without development-machine paths or old logs.
Run both documented Unity exports first; --project/--engine must be private copies.
No installation/upload is performed by this command.
"""
import argparse,hashlib,json,os,plistlib,shutil,subprocess,sys
from pathlib import Path
from private_paths import private_output

def main():
    p=argparse.ArgumentParser(description=__doc__)
    for n in ['project','engine','unity','upstream','work','derived','bc-archive']:p.add_argument('--'+n,type=Path,required=True)
    for n in ['bc-manifest','source-data','bc-sample-report']:p.add_argument('--'+n,type=Path)
    p.add_argument('--bc-probe-package',action='store_true',help='First native BC probe package; keeps exported resources until samples pass')
    p.add_argument('--original-exe',type=Path,help='Optional owned Windows executable from which to derive the private original app icon')
    for n in ['team','bundle','device','identity','version']:p.add_argument('--'+n,required=True)
    a=p.parse_args();src=Path(__file__).resolve().parent;work=private_output(a.work);derived=private_output(a.derived);project=private_output(a.project);engine=private_output(a.engine)
    if not a.bc_probe_package and not all([a.bc_manifest,a.source_data,a.bc_sample_report]):p.error('Final package requires manifest, original Data and passing Unity BC sample report')
    work.mkdir(parents=True,exist_ok=False);reports=work/'reports';reports.mkdir();env=os.environ.copy()
    commit=subprocess.check_output(['git','-C',str(a.upstream),'rev-parse','HEAD'],text=True).strip()
    if commit!='be2060bd1fbdf70545f954a3e4dc90c8f1a27cb0':raise ValueError('Use documented emu commit')
    def run(name,args):
        with (reports/(name+'.log')).open('w') as log:subprocess.run(list(map(str,args)),stdout=log,stderr=subprocess.STDOUT,check=True,env=env)
        print(name,'passed',flush=True)
    def tool(name,*args):run(name,[sys.executable,src/name,*args])
    aot=work/'aot';tool('rebuild_mobile_audio_bindings.py','--project',project,'--output',aot,'--unity',a.unity)
    mac=work/'MacAOT.app';framework=mac/'Contents/Frameworks';framework.mkdir(parents=True);shutil.copy2(aot/'GameAssembly.dylib',framework/'GameAssembly.dylib');shutil.copytree(aot/'data',mac/'Contents/Resources/Data/il2cpp_data')
    info=engine/'Info.plist';data=plistlib.loads(info.read_bytes());data['CFBundleVersion']=a.version;data['CFBundleDisplayName']='DSP Touch' if '.touch.' in a.bundle else '戴森球计划';info.write_bytes(plistlib.dumps(data))
    tool('prepare_engine_bridge.py','--project',engine,'--mac-app',mac,'--upstream',a.upstream,'--output-reports',reports/'prepare','--team',a.team,'--bundle',a.bundle,'--resource-clone','--bc-archive',a.bc_archive)
    sdk=a.unity.resolve().parent/'PlaybackEngines/iOSSupport/Trampoline/Libraries/libiPhone-lib.a'
    tool('augment_engine_icalls.py','--cpp',aot/'cpp','--registration',engine/'Il2CppOutputProject/Source/il2cppOutput/UnityICallRegistration.cpp','--ios-library',sdk,'--report',reports/'icalls.json')
    if a.original_exe:tool('configure_ipad_branding.py','--exe',a.original_exe,'--catalog',engine/'Unity-iPhone/Images.xcassets/AppIcon.appiconset')
    run('xcode',['xcodebuild','-project',engine/'Unity-iPhone.xcodeproj','-scheme','Unity-iPhone','-configuration','Release','-sdk','iphoneos','-destination','id='+a.device,'-derivedDataPath',derived,'COPY_PHASE_STRIP=NO','STRIP_INSTALLED_PRODUCT=NO','-allowProvisioningUpdates','-allowProvisioningDeviceRegistration','build'])
    for script in ['apply_hdr_tiers.py','apply_shadow_tiers.py']:tool(script,'--target',engine/'Data/globalgamemanagers','--report',reports/(script+'.json'))
    resources=engine/'Data'
    if not a.bc_probe_package:
        resources=work/'full-game-bc-data-release/Data';mh=hashlib.sha256(a.bc_manifest.read_bytes()).hexdigest()
        tool('restore_manifest_bc.py','--manifest',a.bc_manifest,'--manifest-sha256',mh,'--source-data',a.source_data,'--target-data',engine/'Data','--report',reports/'bc.json','--apply','--output-data',resources,'--validated-sample-report',a.bc_sample_report)
        tool('apply_din_cjk_fallback.py','--asset',resources/'sharedassets0.assets','--report',reports/'font.json','--apply')
    app=derived/'Build/Products/Release-iphoneos/DSPemuiPad.app'
    entitlements=derived/'Build/Intermediates.noindex/Unity-iPhone.build/Release-iphoneos/Unity-iPhone.build/DSPemuiPad.app.xcent'
    tool('finalize_resource_clone.py','--app',app,'--data',resources,'--identity',a.identity,'--entitlements',entitlements,'--report',reports/'resources.json')
    sys.path.insert(0,str(a.upstream));from tools import macho
    expected=json.loads((reports/'prepare/mac-aot-retarget.json').read_text())['arm64TextSha256']
    if macho.code_hash((app/'Frameworks/MacAOT.framework/MacAOT').read_bytes())!=expected:raise ValueError('AOT instructions changed')
    if (app/'Data/Managed/Metadata/global-metadata.dat').read_bytes()!=(aot/'data/Metadata/global-metadata.dat').read_bytes():raise ValueError('Metadata mismatch')
    (reports/'package.json').write_text(json.dumps({'version':a.version,'app':str(app),'machineCodeUnchanged':True,'metadataExact':True,'deviceRegressionRequired':True},indent=2))
    print('Signed package ready; install and combined regression are separate explicit steps.')
if __name__=='__main__':main()
