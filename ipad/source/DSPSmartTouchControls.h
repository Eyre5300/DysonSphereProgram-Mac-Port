#import <UIKit/UIKit.h>
// Movement is normalized; view deltas remain in UIKit points until the game
// adapter converts them to the guest's render dimensions. No key remapping.
@interface DSPSmartTouchControls : UIView
@property(nonatomic) BOOL gameplayActive;
// The host must supply its topmost game-UI hit test. A blocked point passes
// through to the game view/menu; this view must sit below native menu views.
@property(nonatomic,copy) BOOL (^menuBlocksPoint)(CGPoint);
@property(nonatomic,copy) void (^inputChanged)(double,double,double,double);
// Call when a menu/panel is opened or its input ownership changes, even if
// fingers are stationary. Re-evaluate blocked points in the host hit test.
- (void)menuStateDidChange;
- (void)resetInput;
@end
