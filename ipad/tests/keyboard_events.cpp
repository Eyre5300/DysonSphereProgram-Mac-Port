#include <initializer_list>

#include "../source/DSPKeyboardEvents.hpp"
#include <cassert>
int main(){
 DSPKeyboardEvents e;
 for(int key=0;key<256;key++){
  e.set(key,true,1);e.set(key,false,1);e.set(key,true,4);e.set(key,false,4);e.set(key,true,0);e.set(key,false,0);
  for(int modifier:{1,4,0}){int packet=e.take(key,true);assert(((packet>>1)&255)==1);assert(((packet>>18)&255)==modifier);assert(!(packet&1));}
  assert((e.take(key,true)&511)==0);
 }
 e.set(21,true,1);e.set(21,true,1);assert(((e.take(21,true)>>1)&255)==1);assert((e.take(21,true)&511)==1);
 e.reset();assert(e.take(21,true)==(1<<17));
 for(int i=0;i<40;i++){e.set(21,true,i);e.set(21,false,i);}assert(e.overflow==8);
 for(int i=0;i<32;i++){int packet=e.take(21,true);assert(((packet>>18)&255)==i);}assert((e.take(21,true)&511)==0);
}
