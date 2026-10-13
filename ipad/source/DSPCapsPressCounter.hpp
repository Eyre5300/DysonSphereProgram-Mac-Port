#pragma once
// Count physical Caps Lock edges, not a latched modifier or another button's
// state callback. Access under the keyboard transport mutex.
struct DSPCapsPressCounter {
 bool held=false;
 bool keyChanged(int code,bool pressed){
  if(code!=57||pressed==held)return false;
  held=pressed;return pressed;
 }
 void reset(){held=false;}
};
