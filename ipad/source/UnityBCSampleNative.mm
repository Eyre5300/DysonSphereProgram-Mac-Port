// Optional private read-only hooks; add only to the candidate sample build.
#import <Metal/Metal.h>
#include <stdint.h>
extern "C" id<MTLDevice> DSPBCSampleDevice asm("__ZN5metal8g_DeviceE");
extern "C" __attribute__((used,visibility("default"))) int64_t DSPBCSamplePixelFormat(void *texture) {
    if(!texture)return -1;
    id<MTLTexture> native=(__bridge id<MTLTexture>)texture;
    return (int64_t)native.pixelFormat;
}
extern "C" __attribute__((used,visibility("default"))) int64_t DSPBCSampleAllocationBytes() {
    if(!DSPBCSampleDevice)return -1;
    return (int64_t)DSPBCSampleDevice.currentAllocatedSize;
}
