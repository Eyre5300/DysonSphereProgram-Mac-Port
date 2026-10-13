#include "../source/DSPCapsPressCounter.hpp"
#include <cassert>
int main(){
 DSPCapsPressCounter caps;
 for(int phase=0;phase<2;phase++){
  assert(caps.keyChanged(57,true));
  for(int key=0;key<256;key++)if(key!=57){assert(!caps.keyChanged(key,true));assert(!caps.keyChanged(key,false));}
  assert(!caps.keyChanged(57,true)); // held/repeated notification
  assert(!caps.keyChanged(57,false));
 }
 caps.reset();assert(!caps.keyChanged(57,false));assert(caps.keyChanged(57,true));
}
