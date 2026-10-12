// Preserve both sides of a quick tap until the original fixed sampler sees
// them. UI uses raw native edges and never waits on this world-input queue.
public sealed class DSPPadKeyQueue {
 public bool Held {get;private set;}
 public int Modifiers {get;private set;}
 public int Overflow {get;private set;}
 int pending;bool acknowledged=true,releaseBarrier;bool published;float changed;
 // Preserve a short chord only until its press reaches VFInput. A modifier
 // released while the base key stays down must then use live physical state.
 public int UnsampledModifiers=>Held&&!acknowledged?Modifiers:0;
 // Only the original Update publishes press values. A FixedUpdate that
 // precedes that publication still samples the previous state.
 public void Published(){published=true;}
 public void Sampled(){if(published)acknowledged=true;}
 public void Clear(){Held=false;Modifiers=0;pending=0;acknowledged=true;releaseBarrier=false;published=false;}
 public void Poll(bool physical,int presses,int modifiers,bool enabled,float now){
  if(!enabled){Clear();Held=physical;return;}
  if(presses>0){pending+=presses;if(pending>32){Overflow+=pending-32;pending=32;}Modifiers=modifiers;changed=now;}
  if(now-changed>2&&!physical){Clear();return;}
  if(Held){
   if(acknowledged&&(!physical||pending>0)){Held=false;releaseBarrier=true;acknowledged=false;published=false;}
  }else if(!releaseBarrier||acknowledged){
   releaseBarrier=false;
   if(pending>0){pending--;Held=true;acknowledged=false;published=false;changed=now;}
   else if(physical){Held=true;acknowledged=false;published=false;changed=now;}
   else Modifiers=0;
  }
 }
}
