#pragma once
#include <cstdint>
// Original platform adapter only. No game logic or Unity assets.
// Mouse bits 0..6 match Unity Mouse0..Mouse6. 128=physical device,
// 256=UIKit absolute coordinate, 512=UIKit movement/scroll source.
// Bits 10..16=down edges, bits 17..23=up edges; consumed once per packet.
struct DSPPointerPacket { int state=0;float dx=0,dy=0,wheel=0,nx=0,ny=0; };
struct DSPPointerState {
 bool foreground=true,locked=false,observed=false,valid=false,buttonsKnown=false;
 float nx=0,ny=0,dx=0,dy=0,wheelPoints=0,wheelPointsPerUnit=10;
 uint32_t buttons=0,gcButtons=0,pendingDown=0,pendingUp=0,gcPendingDown=0,gcPendingUp=0;
 void reset(bool clearObserved=true){valid=false;buttonsKnown=false;dx=dy=wheelPoints=0;buttons=gcButtons=0;pendingDown=pendingUp=gcPendingDown=gcPendingUp=0;if(clearObserved)observed=false;}
 void setForeground(bool value){if(value!=foreground){reset();foreground=value;}}
 void setLocked(bool value){if(value!=locked){dx=dy=wheelPoints=0;valid=false;locked=value;}}
 void setPosition(float x,float y,float pixelWidth,float pixelHeight){if(!foreground||locked)return;if(valid&&!locked){dx+=(x-nx)*pixelWidth;dy+=(y-ny)*pixelHeight;}nx=x;ny=y;valid=true;observed=true;}
 void setButtons(uint32_t value){if(!foreground)return;value&=127;pendingDown|=value&~buttons;pendingUp|=buttons&~value;buttons=value;buttonsKnown=true;observed=true;}
 void setGCButtons(uint32_t value){if(!foreground)return;value&=127;gcPendingDown|=value&~gcButtons;gcPendingUp|=gcButtons&~value;gcButtons=value;}
 void addGCButtonEdge(int index,bool pressed){if(!foreground||index<0||index>=7)return;uint32_t bit=1u<<index;if(pressed){gcPendingDown|=bit;gcButtons|=bit;}else{gcPendingUp|=bit;gcButtons&=~bit;}}
 void addScroll(float points){if(foreground){wheelPoints+=points;observed=true;}}
 DSPPointerPacket poll(bool gcPresent,int gcButtons,float gcDX,float gcDY,float gcWheel){
  DSPPointerPacket out;if(!foreground){dx=dy=wheelPoints=0;pendingDown=pendingUp=gcPendingDown=gcPendingUp=0;return out;}
  setGCButtons(gcButtons);
  bool uiSource=observed&&!locked;
  if(gcPresent||observed)out.state=128|(uiSource&&buttonsKnown?buttons:(gcButtons&127));
  if(valid){out.state|=256;out.nx=nx;out.ny=ny;}
  if(uiSource){out.state|=512;out.dx=dx;out.dy=dy;out.wheel=wheelPoints/(wheelPointsPerUnit>0?wheelPointsPerUnit:10);}
  else{out.dx=gcDX;out.dy=gcDY;out.wheel=gcWheel;}
  uint32_t down=uiSource?pendingDown:gcPendingDown,up=uiSource?pendingUp:gcPendingUp;out.state|=(down&127)<<10|(up&127)<<17;pendingDown=pendingUp=gcPendingDown=gcPendingUp=0;dx=dy=wheelPoints=0;return out;
 }
};
// Private, explicitly gated batch-only input. Never writes UIKit / GC state.
struct DSPTestPointerState {
 bool pending=false,closed=false;
 int held=0,down=0,up=0;float nx=0,ny=0,dx=0,dy=0,wheel=0;
 uint64_t queued=0,consumed=0;
 bool queue(bool exactBatchArgument,float x,float y,int buttons,float moveX,float moveY,float scroll){
  if(!exactBatchArgument||closed)return false;
  buttons&=127;down|=buttons&~held;up|=held&~buttons;held=buttons;
  nx=x;ny=y;dx+=moveX;dy+=moveY;wheel+=scroll;pending=true;queued++;return true;
 }
 bool consume(DSPPointerPacket &out){
  if(!pending||closed)return false;
  out={};out.state=128|256|512|(1<<24)|held|((down&127)<<10)|((up&127)<<17);
  out.nx=nx;out.ny=ny;out.dx=dx;out.dy=dy;out.wheel=wheel;
  pending=false;down=up=0;dx=dy=wheel=0;consumed++;return true;
 }
 void cancel(){pending=false;held=down=up=0;dx=dy=wheel=0;}
 void end(){closed=true;cancel();}
};
