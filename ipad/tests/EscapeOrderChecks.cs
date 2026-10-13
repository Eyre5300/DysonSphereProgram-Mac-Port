using System;
class EscapeOrderChecks {
 static void Check(bool value,string name){if(!value)throw new Exception(name);}
 static void Main(){
  var s=new DSPPadEscapeSequence();
  s.Publish(true,10);Check(!s.CanPause(11,false),"render alone must not pause");
  s.AfterLogic();Check(!s.CanPause(12,false),"logic before input sample must not pause");
  s.Sample(true);Check(!s.CanPause(13,false),"sampler alone must not pause");
  s.AfterLogic();Check(s.CanPause(14,false),"unconsumed world event may pause");
  s.Clear();Check(!s.CanPause(15,false),"consumed cannot pause");
  s.Publish(true,20);Check(!s.CanPause(20,true)&&s.CanPause(21,true),"resume works with suspended simulation");
  s.Clear();s.Publish(true,30);s.Sample(false);s.AfterLogic();Check(!s.CanPause(31,false),"previous published release is not this press");
  s.Clear();Check(!s.CanPause(100,true),"focus/reset cancels pending");
  // Exercise simultaneous short taps through the real key queue at varied
  // render:fixed ratios. The abstract consumers deliberately differ from game
  // windows; they test transport ordering and exactly-once ownership only.
  for(int ratio=1;ratio<=8;ratio++)for(int phase=0;phase<ratio;phase++)Run(ratio,phase,false);
  for(int ratio=1;ratio<=8;ratio++)Run(ratio,0,true);
  var hold=new DSPPadKeyQueue();hold.Poll(true,1,0,true,0);hold.ResetDelivery(true);hold.Poll(true,0,0,true,.1f);Check(!hold.Held,"pause reset must not repeat a held Escape");hold.Poll(false,0,0,true,.2f);hold.Poll(true,1,0,true,.3f);Check(hold.Held,"fresh press after reset works");
  Console.WriteLine("PASS Escape scheduling: 36 phase schedules + 8 held-key schedules");
 }
 static void Run(int ratio,int phase,bool held){
  var s=new DSPPadEscapeSequence();var q=new DSPPadKeyQueue();bool published=false,last=false,paused=false,opening=false;int use=0,ui=held?0:2,world=2,consumed=0,pauseChanges=0;
  for(int frame=0;frame<500;frame++){
   if((frame+phase)%ratio==0){
    bool down=published&&!last&&use==0;last=published;if(use>0)use--;q.Sampled();s.Sample(published);
    if(!paused&&down&&world>0){world--;consumed++;use=2;s.Clear();}
    if(!paused)s.AfterLogic();
   }
   bool old=q.Held;q.Poll(held&&frame<250,frame==0?(held?1:6):0,0,true,frame/240f,use==0&&!opening);
   bool edge=!old&&q.Held;published=q.Held;q.Published();s.Publish(edge,frame);
   if(opening){q.ResetDelivery(true);s.Clear();published=last=false;if(use>0)use--;opening=false;}
   if(edge&&ui>0){ui--;consumed++;use=2;s.Clear();}
   if(s.CanPause(frame,paused)){paused=!paused;opening=paused;pauseChanges++;use=2;s.Clear();}
  }
  Check(held?consumed==1&&pauseChanges==0:consumed==4&&pauseChanges==2&&!paused,"queue delivery ratio="+ratio+" phase="+phase+" held="+held+" consumed="+consumed+" pause="+pauseChanges);
 }
}
