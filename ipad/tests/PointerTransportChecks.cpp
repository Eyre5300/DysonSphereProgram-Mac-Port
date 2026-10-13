#include "../source/DSPPointerState.hpp"
#include <cassert>
#include <cmath>
#include <iostream>
int main(){
 DSPPointerState s; s.setPosition(.5,.5,2000,1000);s.setButtons(4);auto p=s.poll(true,4,9,9,9);assert((p.state&127)==4&&p.dx==0&&p.wheel==0);
 s.setPosition(.6,.4,2000,1000);p=s.poll(true,4,9,9,9);assert(std::abs(p.dx-200)<.01&&std::abs(p.dy+100)<.01);
 s.setButtons(0);p=s.poll(true,0,0,0,0);assert(((p.state>>17)&127)==4);
 s.setButtons(1);s.setButtons(0);p=s.poll(true,0,0,0,0);assert(((p.state>>10)&127)==1&&((p.state>>17)&127)==1);p=s.poll(true,0,0,0,0);assert((p.state>>10)==0);
 s.addScroll(20);p=s.poll(true,0,0,0,9);assert(p.wheel==2);p=s.poll(true,0,0,0,9);assert(p.wheel==0);
 s.setForeground(false);p=s.poll(true,4,5,5,1);assert(p.state==0);s.setForeground(true);p=s.poll(false,0,0,0,0);assert(p.state==0);
 s.setLocked(true);s.addGCButtonEdge(2,true);p=s.poll(true,4,5,6,1);assert((p.state&127)==4&&p.dx==5&&p.dy==6&&p.wheel==1);
 DSPTestPointerState t;assert(!t.queue(false,.5,.5,1,0,0,0));assert(t.queue(true,.5,.5,1,0,0,0));assert(t.consume(p)&&((p.state>>10)&127)==1);assert(!t.consume(p));t.end();assert(!t.queue(true,.5,.5,1,0,0,0));
 std::cout<<"pointer transport contracts passed (not physical input proof)\n";
}
