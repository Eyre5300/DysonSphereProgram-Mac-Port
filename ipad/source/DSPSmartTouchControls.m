#import "DSPSmartTouchControls.h"
#import <GameController/GameController.h>
#include <math.h>

@interface DSPSmartTouchControls()
@property(nonatomic,strong) UITouch *moveTouch;
@property(nonatomic,strong) UITouch *lookTouch;
@property(nonatomic) CGPoint moveOrigin;
@property(nonatomic) CGPoint lookPrevious;
@property(nonatomic) double moveX;
@property(nonatomic) double moveY;
@end
@implementation DSPSmartTouchControls
-(instancetype)initWithFrame:(CGRect)frame {
    if((self=[super initWithFrame:frame])){
        self.multipleTouchEnabled=YES;self.backgroundColor=UIColor.clearColor;
        _gameplayActive=YES;
        NSNotificationCenter *nc=NSNotificationCenter.defaultCenter;
        for(NSString *name in @[GCKeyboardDidConnectNotification,GCKeyboardDidDisconnectNotification,GCMouseDidConnectNotification,GCMouseDidDisconnectNotification])
            [nc addObserver:self selector:@selector(deviceChanged:) name:name object:nil];
        [nc addObserver:self selector:@selector(inactive:) name:UIApplicationWillResignActiveNotification object:nil];
        [self updateVisibility];
    }return self;
}
-(void)dealloc{[NSNotificationCenter.defaultCenter removeObserver:self];}
-(void)publishDX:(double)dx DY:(double)dy{if(self.inputChanged)self.inputChanged(self.moveX,self.moveY,dx,dy);}
-(void)resetInput{self.moveTouch=nil;self.lookTouch=nil;self.moveX=0;self.moveY=0;[self publishDX:0 DY:0];}
-(void)menuStateDidChange{[self resetInput];}
-(void)updateVisibility{BOOL hide=!self.gameplayActive||(GCKeyboard.coalescedKeyboard!=nil&&GCMouse.current!=nil);if(self.hidden!=hide)[self resetInput];self.hidden=hide;}
-(void)deviceChanged:(NSNotification*)n{[self resetInput];[self updateVisibility];}
-(void)inactive:(NSNotification*)n{[self resetInput];}
-(void)setGameplayActive:(BOOL)active{_gameplayActive=active;[self resetInput];[self updateVisibility];}
-(BOOL)pointInside:(CGPoint)p withEvent:(UIEvent*)event{
    if(!self.gameplayActive || self.hidden || (self.menuBlocksPoint&&self.menuBlocksPoint(p)))return NO;
    return [super pointInside:p withEvent:event];
}
-(void)touchesBegan:(NSSet<UITouch*>*)touches withEvent:(UIEvent*)event{
    for(UITouch *t in touches){CGPoint p=[t locationInView:self];if(p.x<self.bounds.size.width*.5){if(!self.moveTouch){self.moveTouch=t;self.moveOrigin=p;self.moveX=0;self.moveY=0;}}else if(!self.lookTouch){self.lookTouch=t;self.lookPrevious=p;}}
    [self publishDX:0 DY:0];
}
-(void)touchesMoved:(NSSet<UITouch*>*)touches withEvent:(UIEvent*)event{
    double dx=0,dy=0;
    if(self.moveTouch&&[touches containsObject:self.moveTouch]){
        CGPoint p=[self.moveTouch locationInView:self];double x=p.x-self.moveOrigin.x,y=self.moveOrigin.y-p.y;
        if(self.menuBlocksPoint&&self.menuBlocksPoint(p)){self.moveTouch=nil;self.moveX=0;self.moveY=0;}
        else{
            double length=hypot(x,y),radius=MIN(120.,self.bounds.size.width*.12),dead=radius*.10;
            double magnitude=length>dead?MIN(1.,(length-dead)/(radius-dead)):0;
            self.moveX=length>0?x/length*magnitude:0;self.moveY=length>0?y/length*magnitude:0;
        }
    }
    if(self.lookTouch&&[touches containsObject:self.lookTouch]){CGPoint p=[self.lookTouch locationInView:self];if(self.menuBlocksPoint&&self.menuBlocksPoint(p))self.lookTouch=nil;else{dx=p.x-self.lookPrevious.x;dy=self.lookPrevious.y-p.y;self.lookPrevious=p;}}
    [self publishDX:dx DY:dy];
}
-(void)touchesEnded:(NSSet<UITouch*>*)touches withEvent:(UIEvent*)event{
    if(self.moveTouch&&[touches containsObject:self.moveTouch]){self.moveTouch=nil;self.moveX=0;self.moveY=0;}
    if(self.lookTouch&&[touches containsObject:self.lookTouch])self.lookTouch=nil;
    [self publishDX:0 DY:0];
}
-(void)touchesCancelled:(NSSet<UITouch*>*)touches withEvent:(UIEvent*)event{[self touchesEnded:touches withEvent:event];}
@end
