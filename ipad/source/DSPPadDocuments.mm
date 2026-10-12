// Original platform adapter. System picker handles iCloud/File Provider access.
#import <UniformTypeIdentifiers/UniformTypeIdentifiers.h>
#include <mutex>
static UIViewController *DSPTopController(void){UIWindow *window=nil;for(UIScene *scene in UIApplication.sharedApplication.connectedScenes)if([scene isKindOfClass:UIWindowScene.class]&&scene.activationState==UISceneActivationStateForegroundActive)for(UIWindow *candidate in ((UIWindowScene*)scene).windows)if(candidate.isKeyWindow)window=candidate;UIViewController *top=window.rootViewController;while(top.presentedViewController)top=top.presentedViewController;return top;}
static std::atomic<bool> documentsBusy{false};static std::mutex documentMutex;static std::string documentResult,documentReturned;
static NSString *DSPDocumentsRoot(){return NSSearchPathForDirectoriesInDomains(NSDocumentDirectory,NSUserDomainMask,YES).firstObject;}
static bool DSPDocumentFolder(NSString *folder){NSString *p=folder.stringByStandardizingPath.stringByResolvingSymlinksInPath,*root=DSPDocumentsRoot().stringByResolvingSymlinksInPath;BOOL dir=NO;return [p hasPrefix:[root stringByAppendingString:@"/"]]&&[[NSFileManager defaultManager] fileExistsAtPath:p isDirectory:&dir]&&dir;}
static void DSPDocumentFinish(NSDictionary *value){NSData *data=[NSJSONSerialization dataWithJSONObject:value options:0 error:nil];{std::lock_guard<std::mutex> lock(documentMutex);documentResult.assign((const char*)data.bytes,data.length);}documentsBusy=false;}
@interface DSPDocumentSession:NSObject<UIDocumentPickerDelegate,UIAdaptivePresentationControllerDelegate>
@property(nonatomic,copy)NSString *folder;@property(nonatomic,copy)NSString *snapshotFolder;@property(nonatomic,strong)UIDocumentPickerViewController *picker;@property(nonatomic)BOOL exporting;
@end
static DSPDocumentSession *documentSession;
@interface DSPExportList:UITableViewController
@property(nonatomic,copy)NSString *folder;@property(nonatomic,strong)NSArray<NSString*> *entries;
@end
@implementation DSPExportList
-(void)viewDidLoad{[super viewDidLoad];self.title=@"选择导出文件";NSMutableArray *items=[NSMutableArray array];for(NSString *name in [[NSFileManager defaultManager] contentsOfDirectoryAtPath:self.folder error:nil]){NSString *ext=name.pathExtension.lowercaseString;if([ext isEqual:@"dsv"]||[ext isEqual:@"txt"])[items addObject:name];}self.entries=[items sortedArrayUsingSelector:@selector(localizedStandardCompare:)];self.navigationItem.rightBarButtonItem=[[UIBarButtonItem alloc] initWithBarButtonSystemItem:UIBarButtonSystemItemCancel target:self action:@selector(cancel)];if(!self.entries.count){UILabel *label=[[UILabel alloc] init];label.text=@"当前目录没有可导出的存档或蓝图";label.textAlignment=NSTextAlignmentCenter;self.tableView.backgroundView=label;}}
-(void)cancel{[self dismissViewControllerAnimated:YES completion:^{DSPDocumentFinish(@{@"status":@"cancelled"});}];}
-(NSInteger)tableView:(UITableView*)t numberOfRowsInSection:(NSInteger)s{return self.entries.count;}
-(UITableViewCell*)tableView:(UITableView*)t cellForRowAtIndexPath:(NSIndexPath*)i{UITableViewCell *c=[t dequeueReusableCellWithIdentifier:@"file"];if(!c)c=[[UITableViewCell alloc] initWithStyle:UITableViewCellStyleDefault reuseIdentifier:@"file"];c.textLabel.text=self.entries[i.row];return c;}
-(void)tableView:(UITableView*)t didSelectRowAtIndexPath:(NSIndexPath*)i{NSString *path=[self.folder stringByAppendingPathComponent:self.entries[i.row]];NSString *stage=[NSTemporaryDirectory() stringByAppendingPathComponent:[[NSUUID UUID] UUIDString]];NSError *error=nil;[[NSFileManager defaultManager] createDirectoryAtPath:stage withIntermediateDirectories:YES attributes:nil error:&error];NSString *snapshot=[stage stringByAppendingPathComponent:path.lastPathComponent];if(!error)[[NSFileManager defaultManager] copyItemAtPath:path toPath:snapshot error:&error];if(error){DSPDocumentFinish(@{@"status":@"error",@"message":error.localizedDescription});[self dismissViewControllerAnimated:YES completion:nil];return;}documentSession.exporting=YES;documentSession.snapshotFolder=stage;UIDocumentPickerViewController *picker=[[UIDocumentPickerViewController alloc] initForExportingURLs:@[[NSURL fileURLWithPath:snapshot]] asCopy:YES];documentSession.picker=picker;picker.delegate=documentSession;picker.modalInPresentation=YES;[self dismissViewControllerAnimated:YES completion:^{[DSPTopController() presentViewController:picker animated:YES completion:nil];}];}
@end
@implementation DSPDocumentSession
-(void)documentPickerWasCancelled:(UIDocumentPickerViewController*)controller{if(self.snapshotFolder)[[NSFileManager defaultManager] removeItemAtPath:self.snapshotFolder error:nil];DSPDocumentFinish(@{@"status":@"cancelled"});}
-(void)presentationControllerDidDismiss:(UIPresentationController*)controller{DSPDocumentFinish(@{@"status":@"cancelled"});}
-(void)documentPicker:(UIDocumentPickerViewController*)controller didPickDocumentsAtURLs:(NSArray<NSURL*>*)urls{
 if(self.exporting){if(self.snapshotFolder)[[NSFileManager defaultManager] removeItemAtPath:self.snapshotFolder error:nil];DSPDocumentFinish(@{@"status":@"exported"});return;}
 NSString *folder=self.folder;dispatch_async(dispatch_get_global_queue(QOS_CLASS_USER_INITIATED,0),^{
  NSMutableArray *files=[NSMutableArray array];NSString *stage=[DSPDocumentsRoot() stringByAppendingPathComponent:[@".port-import-" stringByAppendingString:NSUUID.UUID.UUIDString]];NSError *directoryError=nil;[[NSFileManager defaultManager] createDirectoryAtPath:stage withIntermediateDirectories:YES attributes:nil error:&directoryError];
  for(NSURL *url in urls){NSString *name=url.lastPathComponent,*ext=name.pathExtension.lowercaseString;NSMutableDictionary *item=[@{@"name":name?:@""} mutableCopy];if(directoryError)item[@"error"]=directoryError.localizedDescription;else if(!([ext isEqual:@"dsv"]||[ext isEqual:@"txt"]))item[@"error"]=@"请选择 .dsv 存档或 .txt 蓝图";else{
   BOOL access=[url startAccessingSecurityScopedResource];NSFileCoordinator *coordinator=[[NSFileCoordinator alloc] initWithFilePresenter:nil];NSError *coordError=nil;__block NSError *copyError=nil;NSString *dest=[stage stringByAppendingPathComponent:[NSUUID.UUID.UUIDString stringByAppendingPathExtension:ext]];
   [coordinator coordinateReadingItemAtURL:url options:0 error:&coordError byAccessor:^(NSURL *readURL){NSNumber *regular=nil;[readURL getResourceValue:&regular forKey:NSURLIsRegularFileKey error:&copyError];if(!copyError&&regular.boolValue)[[NSFileManager defaultManager] copyItemAtURL:readURL toURL:[NSURL fileURLWithPath:dest] error:&copyError];else if(!copyError)copyError=[NSError errorWithDomain:@"DSPDocument" code:1 userInfo:@{NSLocalizedDescriptionKey:@"所选项目不是普通文件"}];}];
   if(access)[url stopAccessingSecurityScopedResource];NSError *error=coordError?:copyError;if(error)item[@"error"]=error.localizedDescription;else item[@"path"]=dest;
  }[files addObject:item];}
  DSPDocumentFinish(@{@"status":@"imported",@"folder":folder,@"stage":stage,@"files":files});
 });
}
@end
extern "C" __attribute__((used,visibility("default"))) int DSPAOTDocumentsBusy(){return documentsBusy?1:0;}
extern "C" __attribute__((used,visibility("default"))) const char *DSPAOTDocumentsResult(){std::lock_guard<std::mutex> lock(documentMutex);documentReturned=documentResult;documentResult.clear();return documentReturned.c_str();}
extern "C" __attribute__((used,visibility("default"))) int DSPAOTOpenDocuments(const char *utf8,int exportFiles){
 NSString *folder=utf8?[NSString stringWithUTF8String:utf8]:nil;if(!folder||!DSPDocumentFolder(folder)||documentsBusy.exchange(true))return 0;
 dispatch_async(dispatch_get_main_queue(),^{UIViewController *top=DSPTopController();if(!top||top.isBeingDismissed){DSPDocumentFinish(@{@"status":@"error",@"message":@"文件窗口暂不可用，请重试"});return;}documentSession=[DSPDocumentSession new];documentSession.folder=folder;
  if(exportFiles){DSPExportList *list=[[DSPExportList alloc] initWithStyle:UITableViewStyleInsetGrouped];list.folder=folder;UINavigationController *nav=[[UINavigationController alloc] initWithRootViewController:list];nav.modalInPresentation=YES;[top presentViewController:nav animated:YES completion:nil];}
  else{UIDocumentPickerViewController *picker=[[UIDocumentPickerViewController alloc] initForOpeningContentTypes:@[UTTypeData,UTTypePlainText] asCopy:YES];picker.allowsMultipleSelection=YES;picker.delegate=documentSession;picker.modalInPresentation=YES;documentSession.picker=picker;[top presentViewController:picker animated:YES completion:nil];}
 });return 1;
}
extern "C" __attribute__((used,visibility("default"))) int DSPPortOpenFolder(const char *utf8){return DSPAOTOpenDocuments(utf8,0);}
// Diagnostic-only native presentation/cancellation and local file-provider callback.
extern "C" __attribute__((used,visibility("default"))) int DSPAOTDocumentProbe(int operation,const char *path){
 if((DSPAOTDiagnosticFlags()&3)!=3)return 0;
 if(operation==0)return documentSession.picker&&documentSession.picker.presentingViewController?1:0;
 if(operation==1){dispatch_async(dispatch_get_main_queue(),^{[DSPTopController() dismissViewControllerAnimated:NO completion:^{[documentSession documentPickerWasCancelled:documentSession.picker];}];});return 1;}
 if(operation==2&&path&&documentSession){NSString *file=[NSString stringWithUTF8String:path];if(![file.stringByStandardizingPath hasPrefix:[DSPDocumentsRoot() stringByAppendingString:@"/"]])return 0;dispatch_async(dispatch_get_main_queue(),^{DSPDocumentSession *session=documentSession;[DSPTopController() dismissViewControllerAnimated:NO completion:^{[session documentPicker:session.picker didPickDocumentsAtURLs:@[[NSURL fileURLWithPath:file]]];}];});return 1;}
 if(operation==4){dispatch_async(dispatch_get_main_queue(),^{UIViewController *top=DSPTopController();if([top isKindOfClass:UINavigationController.class]){UIViewController *vc=((UINavigationController*)top).topViewController;if([vc isKindOfClass:DSPExportList.class]&&((DSPExportList*)vc).entries.count)[(DSPExportList*)vc tableView:((DSPExportList*)vc).tableView didSelectRowAtIndexPath:[NSIndexPath indexPathForRow:0 inSection:0]];}});return 1;}
 if(operation==3&&path){NSString *name=[NSString stringWithUTF8String:path];if(![name.lastPathComponent isEqual:name])return 0;dispatch_async(dispatch_get_main_queue(),^{UIWindow *w=DSPTopController().view.window;UIGraphicsImageRenderer *render=[[UIGraphicsImageRenderer alloc] initWithSize:w.bounds.size];UIImage *image=[render imageWithActions:^(UIGraphicsImageRendererContext *ctx){[w drawViewHierarchyInRect:w.bounds afterScreenUpdates:YES];}];[UIImagePNGRepresentation(image) writeToFile:[DSPDocumentsRoot() stringByAppendingPathComponent:name] atomically:YES];});return 1;}
 return 0;
}
