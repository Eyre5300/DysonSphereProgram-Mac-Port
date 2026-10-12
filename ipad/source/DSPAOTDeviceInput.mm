#import <UIKit/UIKit.h>
#import <UIKit/UIGestureRecognizerSubclass.h>
#include "DSPPointerState.hpp"
#import <GameController/GameController.h>
#include <atomic>
#include <string>
#include <cstring>
#include <stdint.h>
#import <Metal/Metal.h>
#include <mach/mach.h>
#include <os/proc.h>
// Native process arguments are authoritative for this mixed-platform AOT host.
extern "C" __attribute__((used,visibility("default"))) int DSPAOTDiagnosticFlags(void){
 static int flags=0;static dispatch_once_t once;dispatch_once(&once,^{NSArray<NSString*> *args=NSProcessInfo.processInfo.arguments;flags=([args containsObject:@"--dsp-port-test-batch"]?1:0)|([args containsObject:@"--dsp-native-pointer-test"]?2:0)|([args containsObject:@"--dsp-human-handoff"]?4:0)|([args containsObject:@"--dsp-diagnostics-only"]?16:0)|([args containsObject:@"--dsp-bc-probe-only"]?32:0)|([args containsObject:@"--dsp-memory-pressure-probe"]?64:0);});return flags;
}
// The installed package can have a resource-only revision; Application.version
// is the short marketing version and is not an evidence-directory identifier.
extern "C" __attribute__((used,visibility("default"))) const char *DSPAOTBuildVersion(void){
 static std::string version;static dispatch_once_t once;
 dispatch_once(&once,^{NSString *value=[NSBundle.mainBundle objectForInfoDictionaryKey:@"CFBundleVersion"];version=value.UTF8String?:"unknown";});
 return version.c_str();
}
extern "C" __attribute__((used,visibility("default"))) uint64_t DSPAOTAvailableAppMemory(void){return os_proc_available_memory();}
extern "C" __attribute__((used,visibility("default"))) uint64_t DSPAOTPhysicalFootprint(void){task_vm_info_data_t vm={0};mach_msg_type_number_t count=TASK_VM_INFO_COUNT;return task_info(mach_task_self(),TASK_VM_INFO,(task_info_t)&vm,&count)==KERN_SUCCESS?vm.phys_footprint:0;}
extern "C" uint64_t DSPMetalCensusAllocated(void);
extern "C" __attribute__((used,visibility("default"))) uint64_t DSPAOTGPUAllocated(void){static id<MTLDevice> d=MTLCreateSystemDefaultDevice();return d?(uint64_t)d.currentAllocatedSize:0;}
static bool DSPResourceCensusEnabled(void){static bool enabled=[NSProcessInfo.processInfo.arguments containsObject:@"--dsp-resource-census"];return enabled;}
#include <mach/vm_map.h>
#include <mach/vm_region.h>
extern "C" __attribute__((used,visibility("default"))) int DSPAOTCaptureVMMap(void){
 @autoreleasepool{
 NSMutableDictionary *groups=[NSMutableDictionary dictionary];vm_address_t address=0;uint32_t depth=0;unsigned regions=0;
 while(regions<100000){vm_size_t size=0;vm_region_submap_info_data_64_t info={0};mach_msg_type_number_t count=VM_REGION_SUBMAP_INFO_COUNT_64;kern_return_t result=vm_region_recurse_64(mach_task_self(),&address,&size,&depth,(vm_region_recurse_info_t)&info,&count);if(result!=KERN_SUCCESS||size==0)break;if(info.is_submap){depth++;continue;}
 NSString *key=[NSString stringWithFormat:@"tag%u_external%d_share%d",info.user_tag,info.external_pager,info.share_mode];NSMutableDictionary *g=groups[key];if(!g){g=[NSMutableDictionary dictionaryWithDictionary:@{@"regions":@0,@"virtualBytes":@0,@"residentPages":@0,@"dirtyPages":@0,@"swappedPages":@0}];groups[key]=g;}
 g[@"regions"]=@([g[@"regions"] unsignedLongLongValue]+1);g[@"virtualBytes"]=@([g[@"virtualBytes"] unsignedLongLongValue]+size);g[@"residentPages"]=@([g[@"residentPages"] unsignedLongLongValue]+info.pages_resident);g[@"dirtyPages"]=@([g[@"dirtyPages"] unsignedLongLongValue]+info.pages_dirtied);g[@"swappedPages"]=@([g[@"swappedPages"] unsignedLongLongValue]+info.pages_swapped_out);regions++;if(address+size<=address)break;address+=size;
 }
 NSDictionary *report=@{@"build":[NSBundle.mainBundle objectForInfoDictionaryKey:@"CFBundleVersion"],@"pid":@(getpid()),@"pageSize":@(vm_page_size),@"regions":@(regions),@"scope":@"VM region tag aggregate; shared aliases may overlap; resident pages are not physical footprint",@"groups":groups};NSString *doc=NSSearchPathForDirectoriesInDomains(NSDocumentDirectory,NSUserDomainMask,YES).firstObject;NSString *file=[doc stringByAppendingPathComponent:@"memory-vm-startup.json"];NSData *data=[NSJSONSerialization dataWithJSONObject:report options:NSJSONWritingPrettyPrinted error:nil];return [data writeToFile:file atomically:YES]?1:0;
 }
}
static bool DSPTelemetryEnabled(void){return (DSPAOTDiagnosticFlags()&17)!=0;}
// Mirror the original Unity cursor request at the UIKit platform boundary.
// UIKit can decline it; never treat a requested lock as a granted lock.
#import "Classes/UI/UnityViewControllerBase.h"
static std::atomic<bool> dspPointerLockWanted{false};
@interface UnityViewControllerBase (DSPPointerLock)
@end
@implementation UnityViewControllerBase (DSPPointerLock)
-(BOOL)prefersPointerLocked{return dspPointerLockWanted.load()&&self.presentedViewController==nil&&self.view.window.isKeyWindow&&self.view.window.windowScene.activationState==UISceneActivationStateForegroundActive;}
@end
extern "C" __attribute__((used,visibility("default"))) void DSPAOTSetPointerLock(int value){
 bool wanted=value!=0;if(dspPointerLockWanted.exchange(wanted)==wanted)return;
 dispatch_async(dispatch_get_main_queue(),^{for(UIScene *scene in UIApplication.sharedApplication.connectedScenes)if([scene isKindOfClass:UIWindowScene.class])for(UIWindow *w in ((UIWindowScene*)scene).windows)[w.rootViewController setNeedsUpdateOfPrefersPointerLocked];});
}
extern "C" __attribute__((used,visibility("default"))) int DSPAOTPointerLockStatus(void){
 int result=dspPointerLockWanted.load()?1:0;
 for(UIScene *scene in UIApplication.sharedApplication.connectedScenes)if([scene isKindOfClass:UIWindowScene.class]&&scene.activationState==UISceneActivationStateForegroundActive){result|=8;UIWindowScene *ws=(UIWindowScene*)scene;if(ws.pointerLockState.locked)result|=4;for(UIWindow *w in ws.windows)if(w.isKeyWindow&&w.rootViewController.prefersPointerLocked)result|=2;}
 if(GCMouse.current)result|=16;return result;
}
static NSString *DSPBatchIdentifier(void){for(NSString *arg in NSProcessInfo.processInfo.arguments)if([arg hasPrefix:@"--dsp-batch-id="])return [arg substringFromIndex:15];return @"";}
extern "C" __attribute__((used,visibility("default"))) const char *DSPAOTBatchIdentifier(void){static std::string value;static dispatch_once_t once;dispatch_once(&once,^{value=DSPBatchIdentifier().UTF8String?:"";});return value.c_str();}
// Same physical Caps Lock press rule as the validated Mac adapter.
static bool DSPHasUIKitPointer(void);
static void DSPInstallUIKitPointerObservers(void);
static GCDeviceButtonInput *capsButton;
static GCControllerButtonValueChangedHandler previousHandler,installedHandler;
static std::atomic<uint64_t> capsSequence{0};
extern "C" __attribute__((used,visibility("default"))) int DSPAOTHasKeyboardAndMouse(void){return GCKeyboard.coalescedKeyboard!=nil&&(GCMouse.current!=nil||DSPHasUIKitPointer());}
extern "C" __attribute__((used,visibility("default"))) uint64_t DSPPortCapsSequence(void){
 GCDeviceButtonInput *button=[GCKeyboard.coalescedKeyboard.keyboardInput buttonForKeyCode:GCKeyCodeCapsLock];
 if(button!=capsButton){
  if(capsButton&&capsButton.pressedChangedHandler==installedHandler)capsButton.pressedChangedHandler=previousHandler;
  capsButton=button;previousHandler=button.pressedChangedHandler;GCControllerButtonValueChangedHandler previous=previousHandler;
  installedHandler=^(GCControllerButtonInput *key,float value,BOOL pressed){if(pressed)capsSequence.fetch_add(1,std::memory_order_relaxed);if(previous)previous(key,value,pressed);};
  button.pressedChangedHandler=installedHandler;
 }
 return capsSequence.load(std::memory_order_relaxed);
}
extern "C" __attribute__((used,visibility("default"))) int DSPPortCapsAvailable(void){return capsButton!=nil;}
// Preserve physical modifier identities, including independent Command/GUI.
// Original VFInput/CombineKey still decide each action.
extern "C" __attribute__((used,visibility("default"))) int DSPAOTModifierMask(void){
 GCKeyboardInput *input=GCKeyboard.coalescedKeyboard.keyboardInput;
 if(!input)return -1;
 if(UIApplication.sharedApplication.applicationState!=UIApplicationStateActive)return 0;
 const GCKeyCode codes[]={GCKeyCodeLeftShift,GCKeyCodeRightShift,GCKeyCodeLeftControl,GCKeyCodeRightControl,GCKeyCodeLeftAlt,GCKeyCodeRightAlt,GCKeyCodeLeftGUI,GCKeyCodeRightGUI};
 int mask=0;for(int i=0;i<8;i++)if([input buttonForKeyCode:codes[i]].pressed)mask|=1<<i;
 return mask;
}

// iPad has no Finder. Browse the app's own save/blueprint folder inside UIKit,
// with the system share sheet for export, preserving all user files.
@interface DSPPortFolderController:UITableViewController
@property(nonatomic,copy) NSString *folder;
@property(nonatomic,strong) NSArray<NSString*> *entries;
@end
@implementation DSPPortFolderController
-(void)viewDidLoad{[super viewDidLoad];self.title=self.folder.lastPathComponent;self.entries=[[[NSFileManager defaultManager] contentsOfDirectoryAtPath:self.folder error:nil] sortedArrayUsingSelector:@selector(localizedStandardCompare:)];self.navigationItem.rightBarButtonItem=[[UIBarButtonItem alloc] initWithBarButtonSystemItem:UIBarButtonSystemItemDone target:self action:@selector(done)];}
-(void)done{[self.navigationController dismissViewControllerAnimated:YES completion:nil];}
-(NSInteger)tableView:(UITableView*)tableView numberOfRowsInSection:(NSInteger)section{return self.entries.count;}
-(UITableViewCell*)tableView:(UITableView*)tableView cellForRowAtIndexPath:(NSIndexPath*)indexPath{UITableViewCell *cell=[tableView dequeueReusableCellWithIdentifier:@"file"];if(!cell)cell=[[UITableViewCell alloc] initWithStyle:UITableViewCellStyleDefault reuseIdentifier:@"file"];NSString *name=self.entries[indexPath.row];cell.textLabel.text=name;BOOL dir=NO;[[NSFileManager defaultManager] fileExistsAtPath:[self.folder stringByAppendingPathComponent:name] isDirectory:&dir];cell.accessoryType=dir?UITableViewCellAccessoryDisclosureIndicator:UITableViewCellAccessoryNone;return cell;}
-(void)tableView:(UITableView*)tableView didSelectRowAtIndexPath:(NSIndexPath*)indexPath{NSString *path=[self.folder stringByAppendingPathComponent:self.entries[indexPath.row]];BOOL dir=NO;[[NSFileManager defaultManager] fileExistsAtPath:path isDirectory:&dir];if(dir){DSPPortFolderController *child=[[DSPPortFolderController alloc] initWithStyle:UITableViewStyleInsetGrouped];child.folder=path;[self.navigationController pushViewController:child animated:YES];}else{UIActivityViewController *share=[[UIActivityViewController alloc] initWithActivityItems:@[[NSURL fileURLWithPath:path]] applicationActivities:nil];share.popoverPresentationController.sourceView=tableView;share.popoverPresentationController.sourceRect=[tableView rectForRowAtIndexPath:indexPath];[self presentViewController:share animated:YES completion:nil];}[tableView deselectRowAtIndexPath:indexPath animated:YES];}
@end
static UIViewController *DSPTopController(void){UIWindow *window=nil;for(UIScene *scene in UIApplication.sharedApplication.connectedScenes)if([scene isKindOfClass:UIWindowScene.class]&&scene.activationState==UISceneActivationStateForegroundActive)for(UIWindow *candidate in ((UIWindowScene*)scene).windows)if(candidate.isKeyWindow)window=candidate;UIViewController *top=window.rootViewController;while(top.presentedViewController)top=top.presentedViewController;return top;}
extern "C" __attribute__((used,visibility("default"))) int DSPPortOpenFolder(const char *utf8){
 if(!utf8)return 0;NSString *path=[[NSString stringWithUTF8String:utf8] stringByStandardizingPath];NSString *home=[NSHomeDirectory() stringByAppendingString:@"/"];BOOL dir=NO;
 if(!path||![path hasPrefix:home]||![[NSFileManager defaultManager] fileExistsAtPath:path isDirectory:&dir]||!dir)return 0;
 dispatch_async(dispatch_get_main_queue(),^{DSPPortFolderController *browser=[[DSPPortFolderController alloc] initWithStyle:UITableViewStyleInsetGrouped];browser.folder=path;UINavigationController *nav=[[UINavigationController alloc] initWithRootViewController:browser];nav.modalPresentationStyle=UIModalPresentationFullScreen;[DSPTopController() presentViewController:nav animated:YES completion:nil];});return 1;
}

extern bool _unityAppReady;
extern "C" void *il2cpp_resolve_icall(const char *);
static void DSPWriteInputTelemetry(void);
static void DSPWriteDeviceStatus(void){
 DSPInstallUIKitPointerObservers();
 id<MTLDevice> device=MTLCreateSystemDefaultDevice();task_vm_info_data_t vm={};mach_msg_type_number_t count=TASK_VM_INFO_COUNT;bool valid=task_info(mach_task_self(),TASK_VM_INFO,(task_info_t)&vm,&count)==KERN_SUCCESS;
 typedef bool (*TextureSupport)(int);
 TextureSupport support=_unityAppReady?(TextureSupport)il2cpp_resolve_icall("UnityEngine.SystemInfo::SupportsTextureFormatNative(UnityEngine.TextureFormat)"):nullptr;
 NSDictionary *report=@{@"batchIdentifier":DSPBatchIdentifier(),@"processIdentifier":@(NSProcessInfo.processInfo.processIdentifier),@"buildVersion":[NSBundle.mainBundle objectForInfoDictionaryKey:@"CFBundleVersion"]?:@"unknown",@"diagnosticFlags":@(DSPAOTDiagnosticFlags()),@"pointerLockStatus":@(DSPAOTPointerLockStatus()),@"unityTextureSupportQueried":@(support!=nullptr),@"unityDXT1":@(support&&support(10)),@"unityDXT5":@(support&&support(12)),@"unityBC6H":@(support&&support(24)),@"unityBC7":@(support&&support(25)),@"gpu":device.name?:@"unknown",@"hardwareBCCompression":@(device.supportsBCTextureCompression),@"gpuAllocatedBytes":@(device.currentAllocatedSize),@"gpuRecommendedWorkingSet":@(device.recommendedMaxWorkingSetSize),@"physicalMemory":@(NSProcessInfo.processInfo.physicalMemory),@"ownPhysicalFootprint":@(valid?vm.phys_footprint:0),@"availableAppMemory":@(os_proc_available_memory()),@"thermalState":@(NSProcessInfo.processInfo.thermalState),@"keyboardAndMouse":@(DSPAOTHasKeyboardAndMouse()!=0)};
 NSString *doc=NSSearchPathForDirectoriesInDomains(NSDocumentDirectory,NSUserDomainMask,YES).firstObject;[[NSJSONSerialization dataWithJSONObject:report options:NSJSONWritingPrettyPrinted error:nil] writeToFile:[doc stringByAppendingPathComponent:@"emu-native-device-report.json"] atomically:YES];
 DSPWriteInputTelemetry();
}
// Independent of the Unity/main thread: retains evidence if preload is killed by Jetsam.
// Strictly diagnostic; ordinary launches create no timer or output.
#include <fcntl.h>
#include <unistd.h>
#include <mutex>
static std::mutex dspMemoryStageMutex;
static std::string dspMemoryStage="native-launch";
extern "C" __attribute__((used,visibility("default"))) void DSPAOTMemoryStage(const char *stage){
 if(!DSPTelemetryEnabled())return;
 std::lock_guard<std::mutex> lock(dspMemoryStageMutex);dspMemoryStage=stage?stage:"unknown";
 for(char &c:dspMemoryStage)if(c=='\t'||c=='\r'||c=='\n')c=' ';
}
extern "C" int DSPMetalCensusInstall(void);
extern "C" int DSPMetalCensusSnapshot(const char *filename);
extern "C" __attribute__((used,visibility("default"))) int DSPAOTCaptureMetalCensus(const char *label){
 if(!DSPTelemetryEnabled()||!label)return 0;
 @autoreleasepool {
  NSString *name=[NSString stringWithUTF8String:label];if(!name||name.length>100)return 0;
  NSCharacterSet *invalid=[[NSCharacterSet characterSetWithCharactersInString:@"abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_"] invertedSet];
  if([name rangeOfCharacterFromSet:invalid].location!=NSNotFound)return 0;
  NSString *doc=NSSearchPathForDirectoriesInDomains(NSDocumentDirectory,NSUserDomainMask,YES).firstObject;
  NSString *path=[doc stringByAppendingPathComponent:[NSString stringWithFormat:@"emu-metal-census-%@.json",name]];
  return DSPResourceCensusEnabled()?DSPMetalCensusSnapshot(path.fileSystemRepresentation):0;
 }
}
static void DSPStartMemoryPulse(void){
 if(!DSPTelemetryEnabled())return;
 static dispatch_once_t once;dispatch_once(&once,^{
  if(DSPResourceCensusEnabled()||[NSProcessInfo.processInfo.arguments containsObject:@"--dsp-allocation-events"])DSPMetalCensusInstall();
  NSString *doc=NSSearchPathForDirectoriesInDomains(NSDocumentDirectory,NSUserDomainMask,YES).firstObject;
  NSString *path=[doc stringByAppendingPathComponent:[NSString stringWithFormat:@"emu-memory-%@-%d.tsv",[NSBundle.mainBundle objectForInfoDictionaryKey:@"CFBundleVersion"],getpid()]];
  int fd=open(path.fileSystemRepresentation,O_WRONLY|O_CREAT|O_TRUNC,0600);if(fd<0)return;
  const char *header="uptime\tfootprint\tgpu_allocated\tapp_available\tstage\n";write(fd,header,strlen(header));
  id<MTLDevice> device=MTLCreateSystemDefaultDevice();
  static dispatch_source_t timer;
  __block unsigned samples=0;
  timer=dispatch_source_create(DISPATCH_SOURCE_TYPE_TIMER,0,0,dispatch_queue_create("local.dsp.memory-pulse",DISPATCH_QUEUE_SERIAL));
  dispatch_source_set_timer(timer,DISPATCH_TIME_NOW,NSEC_PER_SEC,NSEC_PER_SEC/10);
  dispatch_source_set_event_handler(timer,^{@autoreleasepool{
   task_vm_info_data_t vm={};mach_msg_type_number_t count=TASK_VM_INFO_COUNT;
   bool valid=task_info(mach_task_self(),TASK_VM_INFO,(task_info_t)&vm,&count)==KERN_SUCCESS;
   std::string stage;{std::lock_guard<std::mutex> lock(dspMemoryStageMutex);stage=dspMemoryStage;}
   NSString *line=[NSString stringWithFormat:@"%.3f\t%llu\t%llu\t%llu\t%s\n",NSProcessInfo.processInfo.systemUptime,(unsigned long long)(valid?vm.phys_footprint:0),(unsigned long long)device.currentAllocatedSize,(unsigned long long)os_proc_available_memory(),stage.c_str()];
   NSData *data=[line dataUsingEncoding:NSUTF8StringEncoding];write(fd,data.bytes,data.length);
   if(DSPResourceCensusEnabled()&&(samples++<30||(samples%5)==0)){NSString *censusPath=[doc stringByAppendingPathComponent:@"emu-metal-census-latest.json"];DSPMetalCensusSnapshot(censusPath.fileSystemRepresentation);}
  }});dispatch_resume(timer);
 });
}

@interface DSPDeviceStatus:NSObject
@end
@implementation DSPDeviceStatus
+(void)load{[[NSNotificationCenter defaultCenter] addObserverForName:UIApplicationDidFinishLaunchingNotification object:nil queue:NSOperationQueue.mainQueue usingBlock:^(NSNotification *notification){DSPInstallUIKitPointerObservers();if(!DSPTelemetryEnabled())return;DSPStartMemoryPulse();DSPWriteDeviceStatus();[NSTimer scheduledTimerWithTimeInterval:5 repeats:YES block:^(NSTimer *timer){DSPWriteDeviceStatus();}];}];}
@end

// The test app ends only after the game end/save lifecycle and GPU drain complete.
extern "C" __attribute__((used,visibility("default"))) void DSPPortFinishTest(void){dispatch_async(dispatch_get_main_queue(),^{exit(EXIT_SUCCESS);});}

#include <mutex>

// All physical keyboard edges, including complete taps between render frames.
// The existing engine callback is chained; text/IME stays owned by Unity.
#include <cstring>
struct DSPKeyboardEvents {
 bool held[256]={};unsigned char down[256]={},up[256]={},mods[256]={};
 void reset(){std::memset(this,0,sizeof(*this));}
 void set(int code,bool pressed,int modifiers){if(code<0||code>=256||held[code]==pressed)return;held[code]=pressed;if(pressed){if(down[code]<255)down[code]++;mods[code]=modifiers;}else if(up[code]<255)up[code]++;}
 int take(int code,bool supported){int value=(held[code]?1:0)|(down[code]<<1)|(up[code]<<9)|(supported?1<<17:0)|(mods[code]<<18);down[code]=up[code]=0;return value;}
};
static std::mutex keyboardMutex;
static GCKeyboardInput *trackedKeyboard;
static GCKeyboardValueChangedHandler priorKeyboardHandler,installedKeyboardHandler;
static DSPKeyboardEvents keyboardEvents,testKeyboardEvents;
static bool testKeyboardActive,testKeyboardClosed;
static int DSPKeyboardModifiers(GCKeyboardInput *input){
 const GCKeyCode codes[]={GCKeyCodeLeftShift,GCKeyCodeRightShift,GCKeyCodeLeftControl,GCKeyCodeRightControl,GCKeyCodeLeftAlt,GCKeyCodeRightAlt,GCKeyCodeLeftGUI,GCKeyCodeRightGUI};
 int mask=0;for(int i=0;i<8;i++)if([input buttonForKeyCode:codes[i]].pressed)mask|=1<<i;return mask;
}
extern "C" __attribute__((used,visibility("default"))) int DSPAOTPollKeyboard(const int *codes,int *packets,int count){
 if(count<0||count>256)return 0;
 GCKeyboardInput *input=GCKeyboard.coalescedKeyboard.keyboardInput;
 if(input!=trackedKeyboard){
  if(trackedKeyboard&&trackedKeyboard.keyChangedHandler==installedKeyboardHandler)trackedKeyboard.keyChangedHandler=priorKeyboardHandler;
  {std::lock_guard<std::mutex> lock(keyboardMutex);trackedKeyboard=input;keyboardEvents.reset();}
  installedKeyboardHandler=nil;priorKeyboardHandler=nil;
 }
 if(input&&(!installedKeyboardHandler||input.keyChangedHandler!=installedKeyboardHandler)){
  priorKeyboardHandler=input.keyChangedHandler;GCKeyboardValueChangedHandler previous=priorKeyboardHandler;
  installedKeyboardHandler=^(GCKeyboardInput *profile,GCDeviceButtonInput *key,GCKeyCode code,BOOL pressed){
   int modifiers=DSPKeyboardModifiers(profile);
   {std::lock_guard<std::mutex> lock(keyboardMutex);if(profile==trackedKeyboard)keyboardEvents.set((int)code,pressed,modifiers);}
   if(previous)previous(profile,key,code,pressed);
  };input.keyChangedHandler=installedKeyboardHandler;
 }
 bool foreground=UIApplication.sharedApplication.applicationState==UIApplicationStateActive;
 int modifiers=DSPKeyboardModifiers(input);
 std::lock_guard<std::mutex> lock(keyboardMutex);
 if(!foreground){keyboardEvents.reset();testKeyboardEvents.reset();}
 for(int i=0;i<count;i++){
  int code=codes[i];if(code<0||code>=256){packets[i]=0;continue;}
  if(testKeyboardActive){packets[i]=testKeyboardEvents.take(code,true);continue;}
  GCDeviceButtonInput *button=[input buttonForKeyCode:(GCKeyCode)code];
  keyboardEvents.set(code,foreground&&button.pressed,modifiers);packets[i]=keyboardEvents.take(code,button!=nil);
 }
 return input||testKeyboardActive?1:0;
}
extern "C" __attribute__((used,visibility("default"))) int DSPAOTQueueTestKey(int code,int pressed){
 if((DSPAOTDiagnosticFlags()&3)!=3||UIApplication.sharedApplication.applicationState!=UIApplicationStateActive||code<0||code>=256)return 0;
 std::lock_guard<std::mutex> lock(keyboardMutex);if(testKeyboardClosed)return 0;testKeyboardActive=true;
 const int mods[]={225,229,224,228,226,230,227,231};int mask=0;for(int i=0;i<8;i++)if(testKeyboardEvents.held[mods[i]])mask|=1<<i;
 testKeyboardEvents.set(code,pressed!=0,mask);return 1;
}
extern "C" __attribute__((used,visibility("default"))) void DSPAOTEndTestKeyboard(){std::lock_guard<std::mutex> lock(keyboardMutex);testKeyboardActive=false;testKeyboardClosed=true;testKeyboardEvents.reset();keyboardEvents.reset();}
static GCMouseInput *trackedMouse;
static GCDeviceButtonInput *trackedButtons[7];
static GCControllerButtonValueChangedHandler previousButtonHandlers[7],installedButtonHandlers[7];
static uintptr_t observedButtonHandlerIDs[7];
static uint64_t buttonEvents,buttonDownEvents,buttonUpEvents,buttonHandlerInstalls;
static GCMouseMoved previousMove,installedMove;
static GCControllerDirectionPadValueChangedHandler previousScroll,installedScroll;
static std::mutex mouseMutex;
static float mouseDX,mouseDY,mouseWheel;
static DSPPointerState pointerState;
static DSPTestPointerState testPointer;
static uint64_t hoverEvents,uiScrollEvents,pointerTouchEvents,fingerTouchEvents,uiObserverInstalls,lifecycleResets;
static double totalUIScrollPoints,lastUIUptime,lastScrollUptime;
static int lastUIEventType,lastUITouchType=-1,lastUIPhase=-1;
static uint64_t lastUIRawButtons,lastUIModifiers;
static __weak UIView *pointerView;
static NSMutableArray<NSDictionary*> *uiInputTrace;
static uintptr_t observedMoveID,observedScrollID,callbackMoveProfileID,callbackScrollProfileID;
static bool moveCallbackMain,scrollCallbackMain;
extern "C" UIView *UnityGetGLView(void);
static bool DSPHasUIKitPointer(void){std::lock_guard<std::mutex> lock(mouseMutex);return pointerState.foreground&&pointerState.observed;}

// Diagnostic counters only. All original input delivery/chaining stays intact.
static uint64_t inputPolls,moveEvents,scrollEvents,mouseProfileChanges,moveRewraps,scrollRewraps;
static double totalRawDX,totalRawDY,totalRawWheel,lastMoveUptime,lastPollUptime,lastTraceUptime;
static int sampledMask,sampledKeyMask,sampledGCButtonMask,lastTraceMask=-1,lastTraceKeys=-1;
static uintptr_t sampledMouseID,sampledProfileID,sampledKeyboardID,lastTraceProfileID,lastTraceKeyboardID;
static NSMutableArray<NSDictionary*> *inputTrace;
static int DSPInputKeyboardMask(GCKeyboardInput *input){
 int mask=0;
 if([input buttonForKeyCode:GCKeyCodeKeyW].pressed)mask|=1;
 if([input buttonForKeyCode:GCKeyCodeKeyA].pressed)mask|=2;
 if([input buttonForKeyCode:GCKeyCodeKeyS].pressed)mask|=4;
 if([input buttonForKeyCode:GCKeyCodeKeyD].pressed)mask|=8;
 if([input buttonForKeyCode:GCKeyCodeLeftControl].pressed||[input buttonForKeyCode:GCKeyCodeRightControl].pressed)mask|=16;
 if([input buttonForKeyCode:GCKeyCodeLeftShift].pressed||[input buttonForKeyCode:GCKeyCodeRightShift].pressed)mask|=32;
 if([input buttonForKeyCode:GCKeyCodeLeftAlt].pressed||[input buttonForKeyCode:GCKeyCodeRightAlt].pressed)mask|=64;
 if([input buttonForKeyCode:GCKeyCodeLeftGUI].pressed||[input buttonForKeyCode:GCKeyCodeRightGUI].pressed)mask|=128;
 return mask;
}
static void DSPRecordInputSample(GCMouse *mouse,GCMouseInput *input,int mask,float dx,float dy,float wheel){
 if(!DSPTelemetryEnabled())return;
 GCKeyboard *keyboard=GCKeyboard.coalescedKeyboard;int keys=DSPInputKeyboardMask(keyboard.keyboardInput);
 double now=NSProcessInfo.processInfo.systemUptime;
 std::lock_guard<std::mutex> lock(mouseMutex);
 inputPolls++;lastPollUptime=now;sampledMask=mask;sampledKeyMask=keys;
 sampledMouseID=(uintptr_t)(__bridge void*)mouse;sampledProfileID=(uintptr_t)(__bridge void*)input;sampledKeyboardID=(uintptr_t)(__bridge void*)keyboard;
 bool changed=mask!=lastTraceMask||keys!=lastTraceKeys||sampledProfileID!=lastTraceProfileID||sampledKeyboardID!=lastTraceKeyboardID;
 if(changed||now-lastTraceUptime>=.5){
  if(!inputTrace)inputTrace=[NSMutableArray new];
  NSMutableArray *buttonHandlers=[NSMutableArray new];for(int i=0;i<7;i++)[buttonHandlers addObject:@{@"index":@(i),@"buttonID":@((uintptr_t)(__bridge void*)trackedButtons[i]),@"observedHandlerID":@(observedButtonHandlerIDs[i]),@"installedHandlerID":@((uintptr_t)(__bridge void*)installedButtonHandlers[i]),@"previousHandlerID":@((uintptr_t)(__bridge void*)previousButtonHandlers[i]),@"ownedAfterPoll":@(trackedButtons[i]&&trackedButtons[i].pressedChangedHandler==installedButtonHandlers[i])}];
  NSDictionary *sample=@{@"syntheticDiagnostic":@((mask&(1<<24))!=0),@"testPacketsQueued":@(testPointer.queued),@"testPacketsConsumed":@(testPointer.consumed),@"buttonHandlers":buttonHandlers,@"downEdgeMask":@((mask>>10)&127),@"upEdgeMask":@((mask>>17)&127),@"uptime":@(now),@"poll":@(inputPolls),@"mouseID":@(sampledMouseID),@"profileID":@(sampledProfileID),@"keyboardID":@(sampledKeyboardID),@"heldMask":@(mask),@"keyMaskWASDModifiers":@(keys),@"keyboardPresent":@(keyboard!=nil),@"anyKeyPressed":@(keyboard.keyboardInput.anyKeyPressed),@"dx":@(dx),@"dy":@(dy),@"wheel":@(wheel),@"moveEvents":@(moveEvents),@"scrollEvents":@(scrollEvents),@"totalDX":@(totalRawDX),@"totalDY":@(totalRawDY),@"totalWheel":@(totalRawWheel),@"profileChanges":@(mouseProfileChanges),@"moveHandlerInstalls":@(moveRewraps),@"scrollHandlerInstalls":@(scrollRewraps),@"middleSupported":@(input.middleButton!=nil),@"rightSupported":@(input.rightButton!=nil),@"applicationState":@(UIApplication.sharedApplication.applicationState),@"buttonEvents":@(buttonEvents),@"buttonDownEvents":@(buttonDownEvents),@"buttonUpEvents":@(buttonUpEvents),@"buttonHandlerInstalls":@(buttonHandlerInstalls),@"GCButtonMask":@(sampledGCButtonMask),@"UIKitButtonMask":@(pointerState.buttons),@"pointerLocked":@(pointerState.locked),@"UIKitObserved":@(pointerState.observed),@"UIKitPositionValid":@(pointerState.valid),@"observedMoveHandlerID":@(observedMoveID),@"installedMoveHandlerID":@((uintptr_t)(__bridge void*)installedMove),@"previousMoveHandlerID":@((uintptr_t)(__bridge void*)previousMove),@"observedScrollHandlerID":@(observedScrollID),@"installedScrollHandlerID":@((uintptr_t)(__bridge void*)installedScroll),@"previousScrollHandlerID":@((uintptr_t)(__bridge void*)previousScroll),@"moveOwnedAfterPoll":@(input&&input.mouseMovedHandler==installedMove),@"scrollOwnedAfterPoll":@(input&&input.scroll.valueChangedHandler==installedScroll),@"callbackMoveProfileID":@(callbackMoveProfileID),@"callbackScrollProfileID":@(callbackScrollProfileID),@"moveCallbackMainThread":@(moveCallbackMain),@"scrollCallbackMainThread":@(scrollCallbackMain),@"GCHandlerQueue":mouse.handlerQueue?@(dispatch_queue_get_label(mouse.handlerQueue)):@"none",@"mouseVendor":mouse.vendorName?:@"none",@"mouseCategory":mouse.productCategory?:@"none"};
  [inputTrace addObject:sample];while(inputTrace.count>512)[inputTrace removeObjectAtIndex:0];
  lastTraceMask=mask;lastTraceKeys=keys;lastTraceProfileID=sampledProfileID;lastTraceKeyboardID=sampledKeyboardID;lastTraceUptime=now;
 }
}
static void DSPWriteInputTelemetry(void){
 NSDictionary *report;
 {std::lock_guard<std::mutex> lock(mouseMutex);
  report=@{@"uptime":@(NSProcessInfo.processInfo.systemUptime),@"inputPolls":@(inputPolls),@"lastPollUptime":@(lastPollUptime),@"lastMoveUptime":@(lastMoveUptime),@"heldMask":@(sampledMask),@"keyMaskWASDModifiers":@(sampledKeyMask),@"mouseID":@(sampledMouseID),@"profileID":@(sampledProfileID),@"keyboardID":@(sampledKeyboardID),@"moveEvents":@(moveEvents),@"scrollEvents":@(scrollEvents),@"totalDX":@(totalRawDX),@"totalDY":@(totalRawDY),@"totalWheel":@(totalRawWheel),@"profileChanges":@(mouseProfileChanges),@"moveHandlerInstalls":@(moveRewraps),@"scrollHandlerInstalls":@(scrollRewraps),@"samples":inputTrace?[inputTrace copy]:@[],@"testPointer":@{@"queued":@(testPointer.queued),@"consumed":@(testPointer.consumed),@"pending":@(testPointer.pending),@"closed":@(testPointer.closed)},@"UIKit":@{@"hoverEvents":@(hoverEvents),@"scrollEvents":@(uiScrollEvents),@"pointerTouchEvents":@(pointerTouchEvents),@"fingerTouchEvents":@(fingerTouchEvents),@"observerInstalls":@(uiObserverInstalls),@"lifecycleResets":@(lifecycleResets),@"lastUptime":@(lastUIUptime),@"lastScrollUptime":@(lastScrollUptime),@"totalScrollPoints":@(totalUIScrollPoints),@"wheelPointsPerNativeUnit":@(pointerState.wheelPointsPerUnit),@"lastEventType":@(lastUIEventType),@"lastTouchType":@(lastUITouchType),@"lastPhase":@(lastUIPhase),@"lastRawButtons":@(lastUIRawButtons),@"lastModifiers":@(lastUIModifiers),@"observed":@(pointerState.observed),@"valid":@(pointerState.valid),@"foreground":@(pointerState.foreground),@"pointerLocked":@(pointerState.locked),@"normalizedX":@(pointerState.nx),@"normalizedY":@(pointerState.ny),@"samples":uiInputTrace?[uiInputTrace copy]:@[]}};
 }
 NSString *doc=NSSearchPathForDirectoriesInDomains(NSDocumentDirectory,NSUserDomainMask,YES).firstObject;
 [[NSJSONSerialization dataWithJSONObject:report options:NSJSONWritingPrettyPrinted error:nil] writeToFile:[doc stringByAppendingPathComponent:@"emu-native-input-report.json"] atomically:YES];
}


// UIKit owns the normal system pointer position. GCMouse provides independent
// relative motion when the system actually grants pointer lock. Never sum them.
static void DSPTraceUIKit(NSString *kind,int eventType,int touchType,int phase,uint64_t buttons,uint64_t modifiers,CGPoint point,UIView *view,float scrollPoints){
 if(!DSPTelemetryEnabled())return;
 std::lock_guard<std::mutex> lock(mouseMutex);double now=NSProcessInfo.processInfo.systemUptime;
 lastUIUptime=now;lastUIEventType=eventType;lastUITouchType=touchType;lastUIPhase=phase;lastUIRawButtons=buttons;lastUIModifiers=modifiers;
 if(!uiInputTrace)uiInputTrace=[NSMutableArray new];
 [uiInputTrace addObject:@{@"kind":kind,@"uptime":@(now),@"eventType":@(eventType),@"touchType":@(touchType),@"phase":@(phase),@"fullButtonMask":@(buttons),@"modifiers":@(modifiers),@"pointX":@(point.x),@"pointY":@(point.y),@"viewWidth":@(view.bounds.size.width),@"viewHeight":@(view.bounds.size.height),@"viewScale":@(view.contentScaleFactor),@"scrollPoints":@(scrollPoints),@"pointerLocked":@(pointerState.locked)}];
 while(uiInputTrace.count>512)[uiInputTrace removeObjectAtIndex:0];
}
static void DSPUIKitPosition(CGPoint point,UIView *view,bool resetAnchor=false){
 CGFloat w=view.bounds.size.width,h=view.bounds.size.height;if(w<=0||h<=0)return;
 std::lock_guard<std::mutex> lock(mouseMutex);if(resetAnchor)pointerState.valid=false;
 pointerState.setPosition(point.x/w,1-point.y/h,w*view.contentScaleFactor,h*view.contentScaleFactor);
}
static void DSPUIKitButtons(uint64_t fullMask){std::lock_guard<std::mutex> lock(mouseMutex);pointerState.setButtons((uint32_t)fullMask);}

// UnityView calls this before UnitySendTouches*. Only real indirect pointer
// touches are consumed. Direct fingers and stylus touches retain Unity delivery.
extern "C" __attribute__((used,visibility("default"))) NSSet<UITouch*> *DSPPortFilterPointerTouches(NSSet<UITouch*> *touches,UIEvent *event,UIView *view){
 NSMutableSet<UITouch*> *fingers=[NSMutableSet new];
 for(UITouch *touch in touches){
  if(touch.type!=UITouchTypeIndirectPointer){[fingers addObject:touch];{std::lock_guard<std::mutex> lock(mouseMutex);fingerTouchEvents++;}continue;}
  CGPoint point=[touch locationInView:view];
  DSPUIKitPosition(point,view);
  uint64_t heldMask=event.buttonMask;
  if(touch.phase==UITouchPhaseEnded||touch.phase==UITouchPhaseCancelled){
   bool anyActivePointer=false;for(UITouch *other in event.allTouches)if(other.type==UITouchTypeIndirectPointer&&other.phase!=UITouchPhaseEnded&&other.phase!=UITouchPhaseCancelled)anyActivePointer=true;
   if(!anyActivePointer)heldMask=0;
  }
  DSPUIKitButtons(heldMask);
  {std::lock_guard<std::mutex> lock(mouseMutex);pointerTouchEvents++;}
  DSPTraceUIKit(@"pointer-touch",event.type,touch.type,touch.phase,event.buttonMask,event.modifierFlags,point,view,0);
 }
 return fingers;
}
@interface DSPPointerHover:UIHoverGestureRecognizer
@end
@implementation DSPPointerHover
-(BOOL)canPreventGestureRecognizer:(UIGestureRecognizer*)other{return NO;}
-(BOOL)canBePreventedByGestureRecognizer:(UIGestureRecognizer*)other{return NO;}
@end
@interface DSPPointerScroll:UIPanGestureRecognizer
@end
@implementation DSPPointerScroll
-(BOOL)canPreventGestureRecognizer:(UIGestureRecognizer*)other{return NO;}
-(BOOL)canBePreventedByGestureRecognizer:(UIGestureRecognizer*)other{return NO;}
@end
@interface DSPPointerObserver:NSObject<UIGestureRecognizerDelegate>
@property(nonatomic,strong) DSPPointerHover *hover;
@property(nonatomic,strong) DSPPointerScroll *scroll;
@end
@implementation DSPPointerObserver
-(BOOL)gestureRecognizer:(UIGestureRecognizer*)gesture shouldRecognizeSimultaneouslyWithGestureRecognizer:(UIGestureRecognizer*)other{return YES;}
-(BOOL)gestureRecognizer:(UIGestureRecognizer*)gesture shouldRequireFailureOfGestureRecognizer:(UIGestureRecognizer*)other{return NO;}
-(BOOL)gestureRecognizer:(UIGestureRecognizer*)gesture shouldBeRequiredToFailByGestureRecognizer:(UIGestureRecognizer*)other{return NO;}
-(void)hoverChanged:(DSPPointerHover*)gesture{
 UIView *view=gesture.view;CGPoint point=[gesture locationInView:view];
 bool ended=gesture.state==UIGestureRecognizerStateEnded||gesture.state==UIGestureRecognizerStateCancelled||gesture.state==UIGestureRecognizerStateFailed;
 if(!ended){DSPUIKitPosition(point,view,gesture.state==UIGestureRecognizerStateBegan);DSPUIKitButtons(gesture.buttonMask);}
 else{std::lock_guard<std::mutex> lock(mouseMutex);if(pointerState.buttons==0){pointerState.valid=false;pointerState.dx=pointerState.dy=0;}}
 {std::lock_guard<std::mutex> lock(mouseMutex);hoverEvents++;}
 DSPTraceUIKit(@"hover",UIEventTypeHover,UITouchTypeIndirectPointer,gesture.state,gesture.buttonMask,gesture.modifierFlags,point,view,0);
}
-(void)scrollChanged:(DSPPointerScroll*)gesture{
 UIView *view=gesture.view;CGPoint delta=[gesture translationInView:view];[gesture setTranslation:CGPointZero inView:view];
 CGPoint point=[gesture locationInView:view];DSPUIKitPosition(point,view);DSPUIKitButtons(gesture.buttonMask);
 // This is scroll/content translation, not pointer displacement. The human
 // Universal Control test found the prior negation reversed every zoom view.
 // Normalize once here; native GC wheel and original game consumers keep their
 // existing signs. Other natural-scroll settings remain a physical test item.
 float points=delta.y;
 {std::lock_guard<std::mutex> lock(mouseMutex);uiScrollEvents++;totalUIScrollPoints+=points;lastScrollUptime=NSProcessInfo.processInfo.systemUptime;pointerState.addScroll(points);}
 DSPTraceUIKit(@"scroll",UIEventTypeScroll,UITouchTypeIndirectPointer,gesture.state,gesture.buttonMask,gesture.modifierFlags,point,view,points);
}
@end
static DSPPointerObserver *pointerObserver;
static void DSPRefreshPointerLifecycle(void){
 UIView *view=pointerView;bool foreground=UIApplication.sharedApplication.applicationState==UIApplicationStateActive&&view.window.windowScene.activationState==UISceneActivationStateForegroundActive;
 bool locked=view.window.windowScene.pointerLockState.locked;
 std::lock_guard<std::mutex> lock(mouseMutex);if(pointerState.foreground!=foreground||pointerState.locked!=locked){lifecycleResets++;mouseDX=mouseDY=mouseWheel=0;}pointerState.setForeground(foreground);pointerState.setLocked(locked);
}
static void DSPInstallUIKitPointerObservers(void){
 if(!NSThread.isMainThread){dispatch_async(dispatch_get_main_queue(),^{DSPInstallUIKitPointerObservers();});return;}
 UIView *view=UnityGetGLView();if(!view)return;
 if(pointerView!=view){
  [pointerObserver.hover.view removeGestureRecognizer:pointerObserver.hover];[pointerObserver.scroll.view removeGestureRecognizer:pointerObserver.scroll];
  pointerView=view;pointerObserver=[DSPPointerObserver new];
  DSPPointerHover *hover=[[DSPPointerHover alloc] initWithTarget:pointerObserver action:@selector(hoverChanged:)];hover.allowedTouchTypes=@[@(UITouchTypeIndirectPointer)];hover.cancelsTouchesInView=NO;hover.delaysTouchesBegan=NO;hover.delaysTouchesEnded=NO;hover.delegate=pointerObserver;
  DSPPointerScroll *scroll=[[DSPPointerScroll alloc] initWithTarget:pointerObserver action:@selector(scrollChanged:)];scroll.allowedTouchTypes=@[];scroll.allowedScrollTypesMask=UIScrollTypeMaskAll;scroll.cancelsTouchesInView=NO;scroll.delaysTouchesBegan=NO;scroll.delaysTouchesEnded=NO;scroll.delegate=pointerObserver;
  pointerObserver.hover=hover;pointerObserver.scroll=scroll;[view addGestureRecognizer:hover];[view addGestureRecognizer:scroll];
  {std::lock_guard<std::mutex> lock(mouseMutex);pointerState.reset();uiObserverInstalls++;}
  static bool notificationsInstalled=false;if(!notificationsInstalled){notificationsInstalled=true;
   for(NSNotificationName name in @[UIApplicationWillResignActiveNotification,UIApplicationDidEnterBackgroundNotification,UIApplicationDidBecomeActiveNotification,UISceneWillDeactivateNotification,UISceneDidActivateNotification,UIPointerLockStateDidChangeNotification])[[NSNotificationCenter defaultCenter] addObserverForName:name object:nil queue:NSOperationQueue.mainQueue usingBlock:^(NSNotification *note){if([note.name isEqualToString:UIApplicationWillResignActiveNotification]||[note.name isEqualToString:UIApplicationDidEnterBackgroundNotification]||[note.name isEqualToString:UISceneWillDeactivateNotification]){std::lock_guard<std::mutex> lock(mouseMutex);pointerState.setForeground(false);mouseDX=mouseDY=mouseWheel=0;lifecycleResets++;}else DSPRefreshPointerLifecycle();}];
  }
 }
 DSPRefreshPointerLifecycle();
}
// Automated end-to-end transport exercise. Argument matching is exact and this
// writes only a single owned packet, never UIEvents / UIKit / a connected mouse.
extern "C" __attribute__((used,visibility("default"))) int DSPAOTQueueTestPointer(float nx,float ny,int buttons,float dx,float dy,float wheel){
 bool batch=[NSProcessInfo.processInfo.arguments containsObject:@"--dsp-port-test-batch"];
 std::lock_guard<std::mutex> lock(mouseMutex);return testPointer.queue(batch&&pointerState.foreground,nx,ny,buttons,dx,dy,wheel)?1:0;
}
extern "C" __attribute__((used,visibility("default"))) int DSPAOTClearTestPointer(void){
 if(![NSProcessInfo.processInfo.arguments containsObject:@"--dsp-port-test-batch"])return 0;
 std::lock_guard<std::mutex> lock(mouseMutex);testPointer.end();return 1;
}
extern "C" __attribute__((used,visibility("default"))) void DSPAOTEndTestPointer(void){DSPAOTClearTestPointer();}
extern "C" __attribute__((used,visibility("default"))) void DSPAOTSetUIKitWheelPointsPerUnit(float value){if(value>0){std::lock_guard<std::mutex> lock(mouseMutex);pointerState.wheelPointsPerUnit=value;}}
extern "C" __attribute__((used,visibility("default"))) int DSPAOTPollPointer(float *dx,float *dy,float *wheel,float *normalizedX,float *normalizedY){
 // The host invokes this once per Unity frame. Installation / scene queries are
 // UIKit main-thread operations; all mutable transport state is mutex-protected.
 if(NSThread.isMainThread)DSPInstallUIKitPointerObservers();
 GCMouse *mouse=GCMouse.current;GCMouseInput *input=mouse.mouseInput;
 observedMoveID=(uintptr_t)(__bridge void*)input.mouseMovedHandler;observedScrollID=(uintptr_t)(__bridge void*)input.scroll.valueChangedHandler;
 if(input!=trackedMouse){
  if(trackedMouse.mouseMovedHandler==installedMove)trackedMouse.mouseMovedHandler=previousMove;
  if(trackedMouse.scroll.valueChangedHandler==installedScroll)trackedMouse.scroll.valueChangedHandler=previousScroll;
  for(int i=0;i<7;i++){if(trackedButtons[i]&&trackedButtons[i].pressedChangedHandler==installedButtonHandlers[i])trackedButtons[i].pressedChangedHandler=previousButtonHandlers[i];previousButtonHandlers[i]=installedButtonHandlers[i]=nil;}
  previousMove=nil;installedMove=nil;previousScroll=nil;installedScroll=nil;
  std::lock_guard<std::mutex> lock(mouseMutex);trackedMouse=input;for(int i=0;i<7;i++)trackedButtons[i]=nil;pointerState.gcButtons=0;mouseDX=mouseDY=mouseWheel=0;mouseProfileChanges++;
 }
 if(input&&input.mouseMovedHandler!=installedMove){
  previousMove=input.mouseMovedHandler;GCMouseMoved saved=previousMove;
  installedMove=^(GCMouseInput *m,float x,float y){{std::lock_guard<std::mutex> lock(mouseMutex);if(m==trackedMouse){mouseDX+=x;mouseDY+=y;}moveEvents++;totalRawDX+=x;totalRawDY+=y;lastMoveUptime=NSProcessInfo.processInfo.systemUptime;callbackMoveProfileID=(uintptr_t)(__bridge void*)m;moveCallbackMain=NSThread.isMainThread;}if(saved)saved(m,x,y);};input.mouseMovedHandler=installedMove;{std::lock_guard<std::mutex> lock(mouseMutex);moveRewraps++;}
 }
 if(input&&input.scroll.valueChangedHandler!=installedScroll){
  previousScroll=input.scroll.valueChangedHandler;GCControllerDirectionPadValueChangedHandler saved=previousScroll;
  installedScroll=^(GCControllerDirectionPad *s,float x,float y){{std::lock_guard<std::mutex> lock(mouseMutex);if(s==trackedMouse.scroll)mouseWheel+=y;scrollEvents++;totalRawWheel+=y;callbackScrollProfileID=(uintptr_t)(__bridge void*)s;scrollCallbackMain=NSThread.isMainThread;}if(saved)saved(s,x,y);};input.scroll.valueChangedHandler=installedScroll;{std::lock_guard<std::mutex> lock(mouseMutex);scrollRewraps++;}
 }
 for(int i=0;i<7;i++){
  GCDeviceButtonInput *button=i==0?input.leftButton:i==1?input.rightButton:i==2?input.middleButton:((NSUInteger)(i-3)<input.auxiliaryButtons.count?input.auxiliaryButtons[i-3]:nil);
  observedButtonHandlerIDs[i]=(uintptr_t)(__bridge void*)button.pressedChangedHandler;
  if(button!=trackedButtons[i]){if(trackedButtons[i]&&trackedButtons[i].pressedChangedHandler==installedButtonHandlers[i])trackedButtons[i].pressedChangedHandler=previousButtonHandlers[i];{std::lock_guard<std::mutex> lock(mouseMutex);trackedButtons[i]=button;}previousButtonHandlers[i]=installedButtonHandlers[i]=nil;}
  if(button&&button.pressedChangedHandler!=installedButtonHandlers[i]){
   GCControllerButtonValueChangedHandler saved=button.pressedChangedHandler;previousButtonHandlers[i]=saved;GCMouseInput *expected=input;int index=i;
   installedButtonHandlers[i]=^(GCControllerButtonInput *key,float value,BOOL pressed){{std::lock_guard<std::mutex> lock(mouseMutex);buttonEvents++;if(pressed)buttonDownEvents++;else buttonUpEvents++;if(trackedMouse==expected&&trackedButtons[index]==key)pointerState.addGCButtonEdge(index,pressed);}if(saved)saved(key,value,pressed);};
   button.pressedChangedHandler=installedButtonHandlers[i];{std::lock_guard<std::mutex> lock(mouseMutex);buttonHandlerInstalls++;}
  }
 }
 int gcButtons=input?(input.leftButton.pressed?1:0)|(input.rightButton.pressed?2:0)|(input.middleButton.pressed?4:0):0;
 for(NSUInteger i=0;i<MIN(input.auxiliaryButtons.count,4);i++)if(input.auxiliaryButtons[i].pressed)gcButtons|=1<<(i+3);
 DSPPointerPacket packet;{std::lock_guard<std::mutex> lock(mouseMutex);sampledGCButtonMask=gcButtons;packet=pointerState.poll(input!=nil,gcButtons,mouseDX,mouseDY,mouseWheel);mouseDX=mouseDY=mouseWheel=0;if(pointerState.foreground)testPointer.consume(packet);else testPointer.cancel();}
 if(dx)*dx=packet.dx;if(dy)*dy=packet.dy;if(wheel)*wheel=packet.wheel;if(normalizedX)*normalizedX=packet.nx;if(normalizedY)*normalizedY=packet.ny;
 DSPRecordInputSample(mouse,input,packet.state,packet.dx,packet.dy,packet.wheel);return packet.state;
}
extern "C" __attribute__((used,visibility("default"))) int DSPAOTPollMouse(float *dx,float *dy,float *wheel){return DSPAOTPollPointer(dx,dy,wheel,nullptr,nullptr);}
