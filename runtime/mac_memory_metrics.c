#include <mach/mach.h>
#include <stdint.h>
uint64_t DSPMacPhysicalFootprint(void) {
 task_vm_info_data_t info={0};mach_msg_type_number_t count=TASK_VM_INFO_COUNT;
 return task_info(mach_task_self(),TASK_VM_INFO,(task_info_t)&info,&count)==KERN_SUCCESS?info.phys_footprint:0;
}

#import <Metal/Metal.h>
#import <dispatch/dispatch.h>
uint64_t DSPMacMetalAllocated(void) {
 static id<MTLDevice> device; static dispatch_once_t once;
 dispatch_once(&once, ^{ device = MTLCreateSystemDefaultDevice(); });
 return device ? (uint64_t)device.currentAllocatedSize : 0;
}
