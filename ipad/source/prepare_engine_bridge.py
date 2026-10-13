from pathlib import Path
import subprocess,json,hashlib,shutil,plistlib,argparse
parser=argparse.ArgumentParser();parser.add_argument('--project',required=True,type=Path);parser.add_argument('--mac-app',required=True,type=Path);parser.add_argument('--upstream',required=True,type=Path);parser.add_argument('--output-reports',required=True,type=Path);parser.add_argument('--team',required=True);parser.add_argument('--bundle',required=True);parser.add_argument('--resource-clone',action='store_true',help='Finalize Data using finalize_resource_clone.py after Xcode build; avoids redundant resource allocation');parser.add_argument('--bc-archive',type=Path,help='Explicit independently validated private BC candidate archive; no automatic activation');args=parser.parse_args();project=args.project.resolve();mac=args.mac_app.resolve();source=Path(__file__).resolve().parent;reports=args.output_reports.resolve();reports.mkdir(parents=True,exist_ok=True)
lib=mac/'Contents/Frameworks/GameAssembly.dylib';sha=hashlib.sha256(lib.read_bytes()).hexdigest()
subprocess.run(['python3',str(source/'retarget_mono.py'),'--source',str(lib),'--output',str(project/'Vendor/MacAOT.framework'),'--upstream',str(args.upstream),'--name','MacAOT','--sha256',sha,'--report',str(reports/'mac-aot-retarget.json')],check=True)
pbx=project/'Unity-iPhone.xcodeproj/project.pbxproj';backup=project/'Unity-iPhone.xcodeproj/project.before-mac-aot.pbxproj'
if not backup.exists():shutil.copy2(pbx,backup)
d=json.loads(subprocess.check_output(['plutil','-convert','json','-o','-',str(backup)],text=True));o=d['objects'];targets={x['name']:(k,x) for k,x in o.items() if x.get('isa')=='PBXNativeTarget'};ufid,uf=targets['UnityFramework'];appid,app=targets['Unity-iPhone']
frameworkPhase=next(o[k] for k in uf['buildPhases'] if o[k]['isa']=='PBXFrameworksBuildPhase')
removed=[];retained=[]
for b in frameworkPhase['files']:
 path=o[o[b]['fileRef']].get('path','')
 if path in ['libGameAssembly.a','Libraries/libil2cpp.a']:removed.append(path)
 else:retained.append(b)
if sorted(removed)!=['Libraries/libil2cpp.a','libGameAssembly.a']:raise RuntimeError('Unexpected runtime link graph')
frameworkPhase['files']=retained
uf['dependencies']=[k for k in uf.get('dependencies',[]) if o[k].get('target')!=targets['GameAssembly'][0]]
# iOS-generated game C++ is never compiled. Only engine type-registration glue
# joins the iOS engine; game/runtime/managed image is the unchanged Mac binary.
refs={
 'B00000000000000000000001':{'isa':'PBXFileReference','lastKnownFileType':'wrapper.framework','path':'Vendor/MacAOT.framework','sourceTree':'SOURCE_ROOT'},
 'B00000000000000000000002':{'isa':'PBXFileReference','lastKnownFileType':'sourcecode.cpp.objcpp','path':'DSPAOTDeviceInput.mm','sourceTree':'SOURCE_ROOT'},
 'B00000000000000000000003':{'isa':'PBXFileReference','lastKnownFileType':'sourcecode.cpp.cpp','path':'Il2CppOutputProject/Source/il2cppOutput/UnityClassRegistration.cpp','sourceTree':'SOURCE_ROOT'},
 'B00000000000000000000004':{'isa':'PBXFileReference','lastKnownFileType':'sourcecode.cpp.cpp','path':'Il2CppOutputProject/Source/il2cppOutput/UnityICallRegistration.cpp','sourceTree':'SOURCE_ROOT'}}
refs['B00000000000000000000005']={'isa':'PBXFileReference','lastKnownFileType':'sourcecode.c.objc','path':'DSPMetalCensus.m','sourceTree':'SOURCE_ROOT'}
if args.bc_archive:
 receipt=json.loads((args.bc_archive.parent/'receipt.json').read_text())
 assert hashlib.sha256(args.bc_archive.read_bytes()).hexdigest()==receipt['candidateArchiveSHA256'] and receipt['allOtherMembersExact']
 assert receipt['changedMember']['instructionsUnchanged']
 for suffix,name in [('06','DSPBCTextureFormats.mm'),('07','UnityBCSampleNative.mm')]:
  refs['B000000000000000000000'+suffix]={'isa':'PBXFileReference','lastKnownFileType':'sourcecode.cpp.objcpp','path':name,'sourceTree':'SOURCE_ROOT'}
  shutil.copy2(source/name,project/name)
 libraryRefs=[v for v in o.values() if v.get('isa')=='PBXFileReference' and v.get('path')=='Libraries/libiPhone-lib.a']
 assert len(libraryRefs)==1
 libraryRefs[0]['path']='Vendor/libiPhoneBCCandidate.a'
 shutil.copy2(args.bc_archive,project/'Vendor/libiPhoneBCCandidate.a')
o.update(refs)
for n,ref in [('11','01'),('12','01'),('13','02'),('14','03'),('15','04'),('16','05')]+([('17','06'),('18','07')] if args.bc_archive else []):
 o['B000000000000000000000'+n]={'isa':'PBXBuildFile','fileRef':'B000000000000000000000'+ref}
 if n=='16':o['B000000000000000000000'+n]['settings']={'COMPILER_FLAGS':'-fno-objc-arc'}
 if n=='12':o['B000000000000000000000'+n]['settings']={'ATTRIBUTES':['CodeSignOnCopy','RemoveHeadersOnCopy']}
frameworkPhase['files'].append('B00000000000000000000011')
sources=next(o[k] for k in uf['buildPhases'] if o[k]['isa']=='PBXSourcesBuildPhase');sources['files']+=['B00000000000000000000013','B00000000000000000000014','B00000000000000000000015','B00000000000000000000016']
if args.bc_archive:sources['files']+=['B00000000000000000000017','B00000000000000000000018']
embed=next(o[k] for k in app['buildPhases'] if o[k]['isa']=='PBXCopyFilesBuildPhase' and str(o[k].get('dstSubfolderSpec'))=='10');embed['files'].append('B00000000000000000000012')
main=o[o[d['rootObject']]['mainGroup']];main['children']+=list(refs)
if args.resource_clone:
 removedData=[]
 for phase in o.values():
  if phase.get('isa')!='PBXResourcesBuildPhase':continue
  keep=[]
  for item in phase.get('files',[]):
   path=o.get(o.get(item,{}).get('fileRef',''),{}).get('path','')
   if path=='Data':removedData.append(path)
   else:keep.append(item)
  phase['files']=keep
 if removedData!=['Data']:raise RuntimeError('Expected one resource Data phase')

for name,(key,t) in targets.items():
 if name not in ['UnityFramework','Unity-iPhone']:continue
 for cid in o[t['buildConfigurationList']]['buildConfigurations']:
  s=o[cid]['buildSettings'];s['DEVELOPMENT_TEAM']=args.team;s['CODE_SIGN_STYLE']='Automatic';s['IPHONEOS_DEPLOYMENT_TARGET']='17.0';s['ENABLE_BITCODE']='NO';s['PRODUCT_BUNDLE_IDENTIFIER']=args.bundle if name=='Unity-iPhone' else args.bundle+'.unityframework';s['FRAMEWORK_SEARCH_PATHS']=['$(inherited)','$(PROJECT_DIR)/Vendor']
  if name=='Unity-iPhone':s['CODE_SIGN_ENTITLEMENTS']='Memory.entitlements'
  if name=='UnityFramework':
   flags=s.get('OTHER_LDFLAGS',['$(inherited)']);flags=[flags] if isinstance(flags,str) else flags
   s['OTHER_LDFLAGS']=flags+['-framework','UniformTypeIdentifiers']
  if args.bc_archive:
   paths=s.get('LIBRARY_SEARCH_PATHS',['$(inherited)']);paths=[paths] if isinstance(paths,str) else paths
   s['LIBRARY_SEARCH_PATHS']=paths+['$(PROJECT_DIR)/Vendor']
def openstep(x):
 if isinstance(x,dict):return '{'+''.join(json.dumps(k)+' = '+openstep(v)+';\n' for k,v in x.items())+'}'
 if isinstance(x,list):return '('+','.join(openstep(v) for v in x)+')'
 if isinstance(x,(int,float)):return str(x)
 return json.dumps(x)
pbx.write_text('// !$*UTF8*$!\n'+openstep(d)+'\n')
if not (project/'Data/Managed/Metadata/global-metadata-ios-original.dat').exists():shutil.copy2(project/'Data/Managed/Metadata/global-metadata.dat',project/'Data/Managed/Metadata/global-metadata-ios-original.dat')
shutil.copytree(mac/'Contents/Resources/Data/il2cpp_data',project/'Data/Managed',dirs_exist_ok=True)
shutil.copy2(source/'DSPAOTDeviceInput.mm',project/'DSPAOTDeviceInput.mm')
shutil.copy2(source/'DSPPadDocuments.mm',project/'DSPPadDocuments.mm')
shutil.copy2(source/'DSPPointerState.hpp',project/'DSPPointerState.hpp')
shutil.copy2(source/'DSPCapsPressCounter.hpp',project/'DSPCapsPressCounter.hpp')
shutil.copy2(source/'DSPKeyboardEvents.hpp',project/'DSPKeyboardEvents.hpp')
shutil.copy2(source/'DSPMetalCensus.m',project/'DSPMetalCensus.m')
subprocess.run(['python3',str(source/'apply_pointer_view.py'),'--view',str(project/'Classes/UI/UnityView+iOS.mm'),'--plist',str(project/'Info.plist'),'--report',str(reports/'pointer-view-patch.json')],check=True)
subprocess.run(['python3',str(source/'apply_scene_lifecycle.py'),str(project)],check=True)
(project/'Memory.entitlements').write_bytes(plistlib.dumps({'com.apple.developer.kernel.increased-memory-limit':True}))
p=project/'Info.plist';info=plistlib.loads(p.read_bytes());info['UIFileSharingEnabled']=True;info['LSSupportsOpeningDocumentsInPlace']=True;info['UIRequiresFullScreen']=True;p.write_bytes(plistlib.dumps(info))
r={'MacAOTInputSha256':sha,'originalMacTextUnchanged':True,'iOSGameCppCompiled':False,'iOSRuntimeArchiveLinked':False,'nativePlatformGlue':['UnityClassRegistration.cpp','UnityICallRegistration.cpp','DSPAOTDeviceInput.mm'],'BCFormatCandidate':bool(args.bc_archive),'requiresResourceCloneFinalization':args.resource_clone,'fullGameTest':False,'engineStarted':False}
(reports/'bridge-preparation.json').write_text(json.dumps(r,indent=2)+'\n');print('Configured iPad engine bridge with Mac AOT guest; iOS game/runtime targets excluded.')
