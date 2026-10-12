"""Adapt the exported Unity 2022.3.62 iOS trampoline to UIScene.

Keep the game-matching engine version. Apply after each Unity export.
Only the diagnostic Xcode project is affected, not the installed editor.
"""
from pathlib import Path
import plistlib
import sys

root = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else Path(__file__).resolve().parent / 'ios-runtime-probe'
source = root / 'Classes/UnityAppController.mm'
text = source.read_text()
marker = '// DSP_UISCENE_BRIDGE'
if marker not in text:
    anchor = '@implementation UnityAppController'
    assert text.count(anchor) == 1
    text = text.replace(anchor, '''// DSP_UISCENE_BRIDGE
// The actual connecting scene is available before connectedScenes is guaranteed
// to expose an active scene. Retain this single-window scene for initialization.
static UIWindowScene* DSPStartupWindowScene = nil;

@interface UnityAppController (DSPSceneInitialization)
- (void)initUnityWithApplication:(UIApplication*)application;
@end

@interface DSPUnitySceneDelegate : UIResponder <UIWindowSceneDelegate>
@property(nonatomic, strong) UIWindow* window;
@end

@implementation DSPUnitySceneDelegate
- (void)scene:(UIScene*)scene willConnectToSession:(UISceneSession*)session options:(UISceneConnectionOptions*)options
{
    if (![scene isKindOfClass:UIWindowScene.class]) return;
    DSPStartupWindowScene = (UIWindowScene*)scene;
    NSLog(@"DSP_SCENE connected");
    if (UIApplication.sharedApplication.applicationState != UIApplicationStateBackground)
    {
        [GetAppController() initUnityWithApplication:UIApplication.sharedApplication];
        self.window = GetAppController().window;
    }
}
- (void)sceneDidBecomeActive:(UIScene*)scene
{
    [GetAppController() applicationDidBecomeActive:UIApplication.sharedApplication];
    self.window = GetAppController().window;
}
- (void)sceneWillResignActive:(UIScene*)scene
{
    [GetAppController() applicationWillResignActive:UIApplication.sharedApplication];
}
- (void)sceneWillEnterForeground:(UIScene*)scene
{
    [GetAppController() applicationWillEnterForeground:UIApplication.sharedApplication];
}
- (void)sceneDidEnterBackground:(UIScene*)scene
{
    [GetAppController() applicationDidEnterBackground:UIApplication.sharedApplication];
}
@end

@implementation UnityAppController''')
    anchor = '    [self initUnityWithApplication: application];\n    return YES;\n}'
    assert text.count(anchor) == 1
    text = text.replace(anchor, '    // Window and rendering initialization are deferred to scene connection.\n    return YES;\n}')
    anchor = '_window = [[UIWindow alloc] initWithWindowScene: [self pickStartupWindowScene: application.connectedScenes]];'
    assert text.count(anchor) == 1
    text = text.replace(anchor, '_window = [[UIWindow alloc] initWithWindowScene: DSPStartupWindowScene ?: [self pickStartupWindowScene: application.connectedScenes]];')
    source.write_text(text)

path = root / 'Info.plist'
with path.open('rb') as f:
    info = plistlib.load(f)
info['UIApplicationSceneManifest'] = {
    'UIApplicationSupportsMultipleScenes': False,
    'UISceneConfigurations': {'UIWindowSceneSessionRoleApplication': [{
        'UISceneConfigurationName': 'DSP Unity Scene',
        'UISceneClassName': 'UIWindowScene',
        'UISceneDelegateClassName': 'DSPUnitySceneDelegate',
    }]},
}
# Build number belongs to the caller; preserve it.
with path.open('wb') as f:
    plistlib.dump(info, f, sort_keys=False)
print('Applied UIScene manifest, deferred initialization, and lifecycle forwarding.')
