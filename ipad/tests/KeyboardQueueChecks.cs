using System;
class KeyboardQueueChecks {
 static int n;static void C(bool b,string m){n++;if(!b)throw new Exception(m);}
 static void S(DSPPadKeyQueue q){q.Published();q.Sampled();}
 static void Main(){
  var q=new DSPPadKeyQueue();q.Poll(false,1,4,true,0);C(q.Held,"tap between frames");q.Poll(false,0,0,true,.01f);C(q.Held,"hold until fixed");S(q);q.Poll(false,0,0,true,.02f);C(!q.Held,"up published");
  q.Poll(false,1,0,true,.03f);C(!q.Held,"up cannot disappear before fixed");S(q);q.Poll(false,0,0,true,.04f);C(q.Held,"next tap survives release barrier");S(q);q.Poll(false,0,0,true,.05f);S(q);q.Poll(false,0,0,true,.06f);C(!q.Held,"no repeat after tap");
  q.Clear();q.Poll(true,1,1,true,1);S(q);q.Poll(true,0,0,true,1.1f);C(q.Held&&q.Modifiers==1,"hold and associated Shift retained");q.Poll(false,0,0,true,1.2f);C(!q.Held,"real release");S(q);q.Poll(false,0,0,true,1.3f);C(q.Modifiers==0,"modifiers released after action");
  q.Clear();int downs=0,ups=0;bool last=false;q.Poll(false,4,0,true,2);
  for(int i=0;i<12;i++){bool state=q.Held;if(state&&!last)downs++;if(!state&&last)ups++;last=state;S(q);q.Poll(false,0,0,true,2+(i+1)*.016f);}C(downs==4&&ups==4,"four taps preserve four press/release pairs");
  q.Poll(false,1,0,true,3);q.Poll(false,0,0,false,3.01f);C(!q.Held,"focus/text suppression cancels queued action");q.Poll(false,0,0,true,3.02f);C(!q.Held,"no queued replay after focus returns");
  q.Clear();q.Poll(true,1,1,true,4);C(q.UnsampledModifiers==1,"short Shift chord reaches first sample");S(q);C(q.UnsampledModifiers==0,"released Shift not latched for entire held R");q.Poll(true,0,0,true,4.1f);C(q.Held&&q.UnsampledModifiers==0,"base key stays down after Shift release");
  q.Clear();q.Poll(false,1,1,true,5);q.Poll(false,1,0,true,5.01f);
  C(q.Held&&q.UnsampledModifiers==1,"later plain press cannot overwrite first unsampled Shift chord");
  S(q);q.Poll(false,0,0,true,5.02f);C(!q.Held,"chord release barrier");S(q);q.Poll(false,0,0,true,5.03f);
  C(q.Held&&q.UnsampledModifiers==0,"second plain press retains its own modifier snapshot");
  q.Clear();q.Poll(false,1,4,true,6);q.Poll(false,1,1,true,6.01f);q.Poll(false,1,0,true,6.02f);
  foreach(int mod in new[]{4,1,0}){C(q.Held&&q.UnsampledModifiers==mod,"ordered modifier snapshot "+mod);S(q);q.Poll(false,0,0,true,6.03f);S(q);q.Poll(false,0,0,true,6.04f);}
  Console.WriteLine("PASS "+n+" production key queue assertions; device test pending");
 }
}
