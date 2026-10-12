// Platform key edges only. Original game code still selects bindings/actions.
public sealed class DSPPadKeyEdges {
 public int Held {get;private set;}
 public int Down {get;private set;}
 public int Up {get;private set;}
 int pulse,sampled;float started;
 public void Sampled(int mask){sampled|=mask;}
 public void Poll(int physical,int pressed,bool focused,bool textInput,float now){
  int previous=Held;pulse&=~sampled;sampled=0;
  if(physical<0||!focused||textInput)pulse=0;
  else{
   pressed|=physical&~previous;
   if(pressed!=0){pulse|=pressed;started=now;}
   if(now-started>2)pulse=0;
  }
  Held=focused&&physical>=0?(physical|pulse):0;
  Down=Held&~previous;Up=previous&~Held;
 }
 public static int WithCommandAlias(int mask){if((mask&64)!=0)mask|=4;if((mask&128)!=0)mask|=8;return mask;}
}
