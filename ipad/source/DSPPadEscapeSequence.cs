// Render frames are not simulation ticks. Keep one delivered Escape pending
// until the original UI/world consumers have had their turn. No window policy.
public sealed class DSPPadEscapeSequence {
 public bool Pending {get;private set;}
 bool sampled,logicObserved;int deliveredFrame;
 public void Clear(){Pending=sampled=logicObserved=false;}
 public void Publish(bool down,int frame){if(down){Pending=true;sampled=logicObserved=false;deliveredFrame=frame;}}
 public void Sample(bool pressed){if(Pending&&pressed)sampled=true;}
 // Called AFTER GameMain's original fixed logic, including intentionally
 // suspended simulation. A fixed sampler alone does not authorize pause.
 public void AfterLogic(){if(Pending&&sampled)logicObserved=true;}
 public bool CanPause(int frame,bool alreadyPaused)=>Pending&&frame>deliveredFrame&&(alreadyPaused||logicObserved);
}
