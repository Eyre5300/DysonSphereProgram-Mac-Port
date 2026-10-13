using System;
// Replay original VFInput order: Update publishes press; Fixed reads press and
// lastPress, then acknowledges transport. Includes render frames without Fixed.
class InputPublicationChecks {
 static int checks;
 static void C(bool ok,string why){checks++;if(!ok)throw new Exception(why);}
 sealed class Sim {
  public DSPPadKeyQueue q=new DSPPadKeyQueue();public bool press,last;public int downs,ups;float time;
  public void Poll(int taps=0,bool held=false){time+=.005f;q.Poll(held,taps,0,true,time);}
  public void Update(){press=q.Held;q.Published();}
  public void Fixed(){if(press&&!last)downs++;if(!press&&last)ups++;last=press;q.Sampled();}
 }
 static void Main(){
  var s=new Sim();s.Update();s.Poll(1);s.Fixed();s.Fixed();
  C(s.downs==0,"Fixed before publication must still read original old press");
  s.Update();s.Poll();s.Update(); // next frame has no Fixed: observed device failure
  C(s.press,"short press must survive a render-only frame after premature Fixed");
  s.Fixed();C(s.downs==1,"first original Fixed after publication must see short down");
  s.Poll(1);s.Fixed(); // a queued second tap while original press is still true
  C(!s.q.Held,"release pending publication");
  s.Update();s.Poll();s.Update();
  C(!s.press,"release barrier survives Fixed that sampled the previous press");
  s.Fixed();C(s.ups==1,"original sampler observes release before next press");
  s.Poll();s.Update();s.Fixed();C(s.downs==2,"second queued tap reaches original sampler");
  for(int mask=0;mask<1024;mask++){
   s=new Sim();s.Update();
   for(int frame=0;frame<34;frame++){
    s.Poll(frame==0||frame==3?1:0);
    if(frame>=10||(mask&(1<<frame))!=0){s.Fixed();s.Fixed();}
    s.Update();
   }
   C(s.downs==2&&s.ups==2,"two complete taps for Fixed schedule "+mask);
  }
  // A physical hold is not a stream of repeated key-down events.
  s=new Sim();s.Update();
  for(int frame=0;frame<15;frame++){s.Poll(frame==0?1:0,true);s.Fixed();s.Update();}
  C(s.downs==1&&s.ups==0,"held key does not repeat");
  s.q.Clear();s.Poll();s.Update();s.Fixed();C(!s.q.Held,"reset cannot replay pending edges");
  Console.WriteLine("PASS "+checks+" original-sampler scheduling assertions (1024 Fixed/render schedules); device validation pending");
 }
}
