// Private process-local allocation census. MRC preserves original +1 new* returns.
// Weak keys do not keep any Metal resource alive. Never installed in public builds.
#import <Foundation/Foundation.h>
#import <Metal/Metal.h>
#import <objc/runtime.h>
#import <mach/mach.h>
#include <fcntl.h>
#include <unistd.h>
#include <os/proc.h>
static bool eventsOnly=false;
static int eventFD=-1;
static void allocationEvent(const char *phase,const char *kind,uint64_t size,MTLTextureDescriptor *desc){
 if(eventFD<0)return;if(!desc&&size<8*1024*1024)return;if(desc&&(uint64_t)desc.width*desc.height*desc.depth*desc.arrayLength<1024*1024)return;
 task_vm_info_data_t vm={0};mach_msg_type_number_t n=TASK_VM_INFO_COUNT;task_info(mach_task_self(),TASK_VM_INFO,(task_info_t)&vm,&n);
 char line[512];int count=snprintf(line,sizeof(line),"%.6f\t%s\t%s\t%llu\t%llu\t%llu\t%llu\t%llu\t%llu\t%llu\t%llu\t%llu\t%llu\n",NSProcessInfo.processInfo.systemUptime,phase,kind,(unsigned long long)size,(unsigned long long)(desc?desc.width:0),(unsigned long long)(desc?desc.height:0),(unsigned long long)(desc?desc.depth:0),(unsigned long long)(desc?desc.mipmapLevelCount:0),(unsigned long long)(desc?desc.sampleCount:0),(unsigned long long)(desc?desc.pixelFormat:0),(unsigned long long)(desc?desc.storageMode:0),(unsigned long long)vm.phys_footprint,(unsigned long long)os_proc_available_memory());if(count>0)write(eventFD,line,MIN((size_t)count,sizeof(line)-1));
}
static NSMapTable *resources;
static NSMutableDictionary *originals;
static id<MTLDevice> device;
static NSUInteger created;
static void hookHeap(id heap);
static NSString *key(Class c,SEL s){return [NSString stringWithFormat:@"%p:%s",c,sel_getName(s)];}
static IMP previous(id self,SEL sel){@synchronized(originals){for(Class c=object_getClass(self);c;c=class_getSuperclass(c)){NSValue *v=originals[key(c,sel)];if(v)return [v pointerValue];}}abort();}
static void track(id object,NSString *kind){if(eventsOnly||!object)return;@autoreleasepool{@synchronized(resources){created++;[resources setObject:@{@"kind":kind,@"serial":@(created)} forKey:object];}}}
static id buffer(id self,SEL sel,NSUInteger n,MTLResourceOptions o){allocationEvent("before","buffer",n,nil);id r=((id(*)(id,SEL,NSUInteger,MTLResourceOptions))previous(self,sel))(self,sel,n,o);allocationEvent("after","buffer",n,nil);track(r,@"buffer");return r;}
static id bufferBytes(id self,SEL sel,const void *p,NSUInteger n,MTLResourceOptions o){allocationEvent("before","bufferBytes",n,nil);id r=((id(*)(id,SEL,const void*,NSUInteger,MTLResourceOptions))previous(self,sel))(self,sel,p,n,o);allocationEvent("after","bufferBytes",n,nil);track(r,@"buffer");return r;}
static id bufferNoCopy(id self,SEL sel,void *p,NSUInteger n,MTLResourceOptions o,void(^release)(void*,NSUInteger)){allocationEvent("before","bufferNoCopy",n,nil);id r=((id(*)(id,SEL,void*,NSUInteger,MTLResourceOptions,void(^)(void*,NSUInteger)))previous(self,sel))(self,sel,p,n,o,release);allocationEvent("after","bufferNoCopy",n,nil);track(r,@"buffer");return r;}
static id bufferOffset(id self,SEL sel,NSUInteger n,MTLResourceOptions o,NSUInteger offset){allocationEvent("before","bufferOffset",n,nil);id r=((id(*)(id,SEL,NSUInteger,MTLResourceOptions,NSUInteger))previous(self,sel))(self,sel,n,o,offset);allocationEvent("after","bufferOffset",n,nil);track(r,@"buffer");return r;}
static id texture(id self,SEL sel,MTLTextureDescriptor *d){allocationEvent("before","texture",0,d);id r=((id(*)(id,SEL,MTLTextureDescriptor*))previous(self,sel))(self,sel,d);allocationEvent("after","texture",r?[(id<MTLResource>)r allocatedSize]:0,d);track(r,@"texture");return r;}
static id textureOffset(id self,SEL sel,MTLTextureDescriptor *d,NSUInteger offset){allocationEvent("before","texture",0,d);id r=((id(*)(id,SEL,MTLTextureDescriptor*,NSUInteger))previous(self,sel))(self,sel,d,offset);allocationEvent("after","texture",r?[(id<MTLResource>)r allocatedSize]:0,d);track(r,@"texture");return r;}
static id textureSurface(id self,SEL sel,MTLTextureDescriptor *d,IOSurfaceRef surface,NSUInteger plane){allocationEvent("before","texture",0,d);id r=((id(*)(id,SEL,MTLTextureDescriptor*,IOSurfaceRef,NSUInteger))previous(self,sel))(self,sel,d,surface,plane);allocationEvent("after","texture",r?[(id<MTLResource>)r allocatedSize]:0,d);track(r,@"texture");return r;}
static id heap(id self,SEL sel,MTLHeapDescriptor *d){id r=((id(*)(id,SEL,MTLHeapDescriptor*))previous(self,sel))(self,sel,d);track(r,@"heap");if(r)hookHeap(r);return r;}
static void install(Class c,const char *name,IMP replacement){SEL sel=sel_registerName(name);@synchronized(originals){Method m=class_getInstanceMethod(c,sel);if(!m)return;IMP old=method_getImplementation(m);if(old==replacement)return;NSString*k=key(c,sel);if(originals[k])return;originals[k]=[NSValue valueWithPointer:old];if(!class_addMethod(c,sel,replacement,method_getTypeEncoding(m)))method_setImplementation(m,replacement);}}
static void hookHeap(id h){Class c=object_getClass(h);install(c,"newBufferWithLength:options:",(IMP)buffer);install(c,"newBufferWithLength:options:offset:",(IMP)bufferOffset);install(c,"newTextureWithDescriptor:",(IMP)texture);install(c,"newTextureWithDescriptor:offset:",(IMP)textureOffset);}
int DSPMetalCensusInstall(void){@autoreleasepool{static dispatch_once_t once;dispatch_once(&once,^{eventsOnly=![NSProcessInfo.processInfo.arguments containsObject:@"--dsp-resource-census"];if([NSProcessInfo.processInfo.arguments containsObject:@"--dsp-allocation-events"]){NSString *doc=NSSearchPathForDirectoriesInDomains(NSDocumentDirectory,NSUserDomainMask,YES).firstObject;NSString *path=[doc stringByAppendingPathComponent:[NSString stringWithFormat:@"emu-metal-events-%@-%d.tsv",[NSBundle.mainBundle objectForInfoDictionaryKey:@"CFBundleVersion"],getpid()]];eventFD=open(path.fileSystemRepresentation,O_WRONLY|O_CREAT|O_TRUNC,0600);const char *header="uptime\tphase\tkind\tbytes\twidth\theight\tdepth\tmips\tsamples\tformat\tstorage\tfootprint\tavailable\n";if(eventFD>=0)write(eventFD,header,strlen(header));}resources=[[NSMapTable weakToStrongObjectsMapTable]retain];originals=[[NSMutableDictionary alloc]init];device=MTLCreateSystemDefaultDevice();if(!device)return;Class c=object_getClass(device);install(c,"newBufferWithLength:options:",(IMP)buffer);install(c,"newBufferWithBytes:length:options:",(IMP)bufferBytes);install(c,"newBufferWithBytesNoCopy:length:options:deallocator:",(IMP)bufferNoCopy);install(c,"newTextureWithDescriptor:",(IMP)texture);install(c,"newTextureWithDescriptor:iosurface:plane:",(IMP)textureSurface);install(c,"newHeapWithDescriptor:",(IMP)heap);});return device?1:0;}}
int DSPMetalCensusSnapshot(const char *filename){@autoreleasepool{if(!resources||!filename)return 0;NSMutableArray*rows=[NSMutableArray array];NSMutableArray *stable=[[NSMutableArray alloc]init];NSUInteger totalCreated;@synchronized(resources){for(id object in resources.keyEnumerator){id info=[resources objectForKey:object];if(object&&info)[stable addObject:@[object,info]];}totalCreated=created;}
 uint64_t standalone=0,heapSize=0,heapUsed=0,heapAllocated=0,aliasAllocated=0;NSUInteger bufferCount=0,textureCount=0,heapCount=0;
 for(NSArray *pair in stable){id object=pair[0];NSMutableDictionary*r=[NSMutableDictionary dictionaryWithDictionary:pair[1]];NSString*kind=r[@"kind"];r[@"pointer"]=[NSString stringWithFormat:@"%p",object];r[@"nativeClass"]=NSStringFromClass(object_getClass(object));
  if([kind isEqualToString:@"heap"]){id<MTLHeap>h=object;heapCount++;r[@"label"]=h.label?:@"";r[@"size"]=@(h.size);r[@"usedSize"]=@(h.usedSize);r[@"currentAllocatedSize"]=@(h.currentAllocatedSize);r[@"storageMode"]=@(h.storageMode);r[@"heapType"]=@(h.type);heapSize+=h.size;heapUsed+=h.usedSize;heapAllocated+=h.currentAllocatedSize;}
  else{id<MTLResource>q=object;r[@"label"]=q.label?:@"";r[@"allocatedSize"]=@(q.allocatedSize);r[@"storageMode"]=@(q.storageMode);r[@"heapPointer"]=q.heap?[NSString stringWithFormat:@"%p",q.heap]:@"";if(q.heap)aliasAllocated+=q.allocatedSize;else standalone+=q.allocatedSize;
   if([kind isEqualToString:@"buffer"]){id<MTLBuffer>b=object;bufferCount++;r[@"length"]=@(b.length);}
   else{id<MTLTexture>t=object;textureCount++;r[@"width"]=@(t.width);r[@"height"]=@(t.height);r[@"depth"]=@(t.depth);r[@"arrayLength"]=@(t.arrayLength);r[@"mipLevels"]=@(t.mipmapLevelCount);r[@"pixelFormat"]=@(t.pixelFormat);r[@"textureType"]=@(t.textureType);r[@"samples"]=@(t.sampleCount);r[@"usage"]=@(t.usage);}
  }[rows addObject:r];
 }[stable release];
 task_vm_info_data_t vm={0};mach_msg_type_number_t count=TASK_VM_INFO_COUNT;task_info(mach_task_self(),TASK_VM_INFO,(task_info_t)&vm,&count);
 NSMutableArray *supported=[NSMutableArray array];for(NSNumber *n in @[@1,@2,@4,@8,@16])if([device supportsTextureSampleCount:n.unsignedIntegerValue])[supported addObject:n];
 NSDictionary*report=@{@"supportedSampleCounts":supported,@"uptime":@(NSProcessInfo.processInfo.systemUptime),@"scope":@"Native Metal resources created after install; weak refs, views not separately traced; heap aliases not additive to backing heaps. Device allocated minus captured backing is unattributed, not a leak proof.",@"device":device.name?:@"",@"deviceAllocated":@(device.currentAllocatedSize),@"physicalFootprint":@(vm.phys_footprint),@"createdEvents":@(totalCreated),@"liveBuffers":@(bufferCount),@"liveTextures":@(textureCount),@"liveHeaps":@(heapCount),@"standaloneAllocated":@(standalone),@"heapSize":@(heapSize),@"heapUsed":@(heapUsed),@"heapAllocated":@(heapAllocated),@"heapAliasAllocatedNotAdditive":@(aliasAllocated),@"resources":rows};
 NSError*error=nil;NSData*data=[NSJSONSerialization dataWithJSONObject:report options:NSJSONWritingPrettyPrinted error:&error];return data&&[data writeToFile:[NSString stringWithUTF8String:filename] options:NSDataWritingAtomic error:&error]?1:0;
}}
uint64_t DSPMetalCensusAllocated(void){return device?(uint64_t)device.currentAllocatedSize:0;}
uint64_t DSPMetalCensusPhysical(void){task_vm_info_data_t vm={0};mach_msg_type_number_t n=TASK_VM_INFO_COUNT;return task_info(mach_task_self(),TASK_VM_INFO,(task_info_t)&vm,&n)==KERN_SUCCESS?vm.phys_footprint:0;}
