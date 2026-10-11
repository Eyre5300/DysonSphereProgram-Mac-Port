#import <AppKit/AppKit.h>
#import <GameController/GameController.h>
#include <stdatomic.h>
#include <stdint.h>
// GameController reports physical press/release, independent of Caps Lock/IME state.
// Only observe; never suppress events, change input sources or require an event tap.
static GCDeviceButtonInput *capsButton;
static GCControllerButtonValueChangedHandler previousHandler, installedHandler;
static atomic_uint_least64_t capsSequence;
uint64_t DSPPortCapsSequence(void) {
    GCDeviceButtonInput *button = [GCKeyboard.coalescedKeyboard.keyboardInput buttonForKeyCode:GCKeyCodeCapsLock];
    if (button != capsButton) {
        if (capsButton && capsButton.pressedChangedHandler == installedHandler)
            capsButton.pressedChangedHandler = previousHandler;
        capsButton = button;
        previousHandler = button.pressedChangedHandler;
        GCControllerButtonValueChangedHandler previous = previousHandler;
        installedHandler = ^(GCControllerButtonInput *key, float value, BOOL pressed) {
            if (pressed) atomic_fetch_add_explicit(&capsSequence, 1, memory_order_relaxed);
            if (previous) previous(key, value, pressed);
        };
        button.pressedChangedHandler = installedHandler;
    }
    return atomic_load_explicit(&capsSequence, memory_order_relaxed);
}
int DSPPortCapsAvailable(void) { return capsButton != nil; }

// Use Finder's file URL entry point; no shell, command parsing, or browser URL.
int DSPPortOpenFolder(const char *utf8Path) {
    if (!utf8Path) return 0;
    NSString *path = [NSString stringWithUTF8String:utf8Path];
    BOOL directory = NO;
    if (!path || ![[NSFileManager defaultManager] fileExistsAtPath:path isDirectory:&directory] || !directory) return 0;
    __block BOOL accepted = NO;
    void (^request)(void) = ^{ accepted = [[NSWorkspace sharedWorkspace] openURL:[NSURL fileURLWithPath:path isDirectory:YES]]; };
    if ([NSThread isMainThread]) request(); else dispatch_sync(dispatch_get_main_queue(), request);
    return accepted ? 1 : 0;
}
