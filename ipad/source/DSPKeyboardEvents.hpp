#pragma once
#include <cstring>
// Physical state plus ordered per-key press modifier snapshots. Drain one
// press per poll so two rapid chords cannot collapse onto the last modifier.
struct DSPKeyboardEvents {
 bool held[256]={};unsigned char up[256]={},mods[256]={};
 unsigned char pressMods[256][32]={},head[256]={},count[256]={};
 unsigned overflow=0;
 void reset(){std::memset(this,0,sizeof(*this));}
 void set(int code,bool pressed,int modifiers){
  if(code<0||code>=256||held[code]==pressed)return;held[code]=pressed;
  if(pressed){if(count[code]<32){pressMods[code][(head[code]+count[code])%32]=modifiers;count[code]++;}else overflow++;mods[code]=modifiers;}
  else if(up[code]<255)up[code]++;
 }
 int take(int code,bool supported){
  if(code<0||code>=256)return 0;
  int pressed=count[code]>0?1:0,modifier=pressed?pressMods[code][head[code]]:mods[code];
  if(pressed){head[code]=(head[code]+1)%32;count[code]--;}
  int value=(held[code]?1:0)|(pressed<<1)|(up[code]<<9)|(supported?1<<17:0)|(modifier<<18);up[code]=0;return value;
 }
};
