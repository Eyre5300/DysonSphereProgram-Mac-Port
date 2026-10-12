// Candidate adaptation for Unity2022.3 iOS Metal BC formats. No resource conversion.
// All existing non-BC code remains in the original static object. BC enabled only
// when the current real MTLDevice reports hardware support. Caps offsets and enum
// values are pinned to the independently audited object; not a generic Unity ABI.
#import <Metal/Metal.h>
#include <stdint.h>
extern "C" id<MTLDevice> DSPBCDevice asm("__ZN5metal8g_DeviceE");
extern "C" unsigned long DSPBCOriginalPixelFormat(int,int*);
extern "C" int DSPBCOriginalUnityGraphicsFormat(unsigned long);
extern "C" void DSPBCOriginalInitFormatUsageFlags(void*);
extern "C" unsigned long DSPBCOriginalPixelFormatElementSize(unsigned long);
extern "C" unsigned long DSPBCOriginalTextureFormatBlockSize(unsigned long);
#ifdef DSP_BC_SHIM_TESTING
extern "C" int DSPBCTestEnabled;int DSPBCTestEnabled=1;
#endif
static bool Enabled(){
#ifdef DSP_BC_SHIM_TESTING
 if(!DSPBCTestEnabled)return false;
#endif
 if (@available(iOS 16.4, *)) return DSPBCDevice&&DSPBCDevice.supportsBCTextureCompression;
 return false;
}
// Values pinned to MTLPixelFormat.h (iOS16.4+); gate checked before use.
static const unsigned long BC[14]={131,130,133,132,135,134,140,141,142,143,151,150,153,152};
static int Index(unsigned long m){for(int i=0;i<14;i++)if(m==BC[i])return i;return -1;}
extern "C" unsigned long DSPBCPixel(int,int*) asm("__ZN5metal11PixelFormatE14GraphicsFormatPS0_");
unsigned long DSPBCPixel(int f,int*out){if(f>=96&&f<=109&&Enabled()){*out=f;return BC[f-96];}return DSPBCOriginalPixelFormat(f,out);}
extern "C" int DSPBCUnity(unsigned long) asm("__ZN5metal19UnityGraphicsFormatE14MTLPixelFormat");
int DSPBCUnity(unsigned long m){int i=Index(m);if(i>=0&&Enabled())return 96+i;return DSPBCOriginalUnityGraphicsFormat(m);}
extern "C" unsigned long DSPBCElement(unsigned long) asm("__ZN5metal22PixelFormatElementSizeE14MTLPixelFormat");
unsigned long DSPBCElement(unsigned long m){int i=Index(m);if(i>=0&&Enabled())return (i<2||i==6||i==7)?8:16;return DSPBCOriginalPixelFormatElementSize(m);}
extern "C" unsigned long DSPBCBlock(unsigned long) asm("__ZN5metal22TextureFormatBlockSizeE14MTLPixelFormat");
unsigned long DSPBCBlock(unsigned long m){if(Index(m)>=0&&Enabled())return 4;return DSPBCOriginalTextureFormatBlockSize(m);}
extern "C" void DSPBCCaps(void*) asm("__ZN5metal20InitFormatUsageFlagsEP12GraphicsCaps");
void DSPBCCaps(void*caps){DSPBCOriginalInitFormatUsageFlags(caps);if(Enabled()){auto flags=(uint32_t*)((uint8_t*)caps+0x160);for(int f=96;f<=109;f++)flags[f]=3;/* Sample+Linear only. Never render, UAV or MSAA. */}}

extern "C" bool DSPBCOriginalIsCompressedPixelFormat(unsigned long);
extern "C" bool DSPBCOriginalIsTextureViewCompatible(unsigned long,unsigned long);
extern "C" bool DSPBCCompressed(unsigned long) asm("__ZN5metal23IsCompressedPixelFormatE14MTLPixelFormat");
bool DSPBCCompressed(unsigned long m){if(Index(m)>=0&&Enabled())return true;return DSPBCOriginalIsCompressedPixelFormat(m);}
extern "C" bool DSPBCView(unsigned long,unsigned long) asm("__ZN5metal23IsTextureViewCompatibleE14MTLPixelFormatS0_");
bool DSPBCView(unsigned long a,unsigned long b){int x=Index(a),y=Index(b);if((x>=0||y>=0)&&Enabled()){if(x<0||y<0)return false;if(a==b)return true;return x/2==y/2&&(x<6||x>=12);/* Only identical BC or SRGB/linear variant of same codec. */}return DSPBCOriginalIsTextureViewCompatible(a,b);}
