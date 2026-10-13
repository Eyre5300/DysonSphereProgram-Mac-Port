// Preserve both sides of a quick tap until the original fixed sampler sees
// them. UI uses raw native edges and never waits on this world-input queue.
public sealed class DSPPadKeyQueue {
 public bool Held {get;private set;}
 public int Modifiers {get;private set;}
 public int Overflow {get;private set;}
 readonly int[] pendingModifiers=new int[32];int pending,head;bool acknowledged=true,releaseBarrier;bool published,freshPressRequired;float changed;
 // Preserve a short chord only until its press reaches VFInput. A modifier
 // released while the base key stays down must then use live physical state.
 public int UnsampledModifiers=>Held&&!acknowledged?Modifiers:0;
 // Only the original Update publishes press values. A FixedUpdate that
 // precedes that publication still samples the previous state.
 public void Published(){published=true;}
 public void Sampled(){if(published)acknowledged=true;}
 public void Clear(){Held=false;Modifiers=0;pending=0;head=0;acknowledged=true;releaseBarrier=false;published=freshPressRequired=false;}
 // Reset the currently published state, retaining future events only when the
 // caller explicitly owns that transition. A held old key is not a new press.
 public void ResetDelivery(bool keepPending){int n=pending,h=head;Clear();if(keepPending){pending=n;head=h;}freshPressRequired=true;}
 public void Poll(bool physical,int presses,int modifiers,bool enabled,float now,bool allowPress=true){
  if(!enabled){Clear();Held=physical;return;}
  if(!physical)freshPressRequired=false;
  if(presses>0){for(int i=0;i<presses;i++){if(pending==pendingModifiers.Length){Overflow++;continue;}pendingModifiers[(head+pending)%pendingModifiers.Length]=modifiers;pending++;}changed=now;}
  if(now-changed>2&&!physical){Clear();return;}
  if(Held){
   if(acknowledged&&(!physical||pending>0)){Held=false;releaseBarrier=true;acknowledged=false;published=false;}
  }else if(allowPress&&(!releaseBarrier||acknowledged)){
   releaseBarrier=false;
   if(pending>0){Modifiers=pendingModifiers[head];head=(head+1)%pendingModifiers.Length;pending--;Held=true;acknowledged=false;published=false;freshPressRequired=false;changed=now;}
   else if(physical&&!freshPressRequired){Modifiers=modifiers;Held=true;acknowledged=false;published=false;changed=now;}
   else Modifiers=0;
  }
 }
}
