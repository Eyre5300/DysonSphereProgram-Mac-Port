using UnityEngine;
// A short stationary contact is left click; a long one is right click. Once a contact becomes a drag
// it can never become a click again, even if it returns to its origin.
public sealed class DSPPadTapGesture {
  public const float MinimumLongTapSeconds=.45f;
 public const float MaximumSampleSeconds=2f;
 public int Finger {get;private set;}=-1;
 public bool Eligible {get;private set;}
 public bool DragCommitted {get;private set;}
 Vector2 start;float started;
 public static float Slop(int width)=>Mathf.Clamp(Mathf.Min(width*.12f,240f)*.1f,12f,24f);
 public void Begin(int finger,Vector2 point,float now){Finger=finger;start=point;started=now;Eligible=true;DragCommitted=false;}
 public void Observe(int finger,Vector2 point,float now,float slop){
  if(finger!=Finger)return;
  if((point-start).sqrMagnitude>=slop*slop){DragCommitted=true;Eligible=false;}
 }
 public int EndButton(int finger,Vector2 point,float now,float slop){
  Observe(finger,point,now,slop);int button=-1;float duration=now-started;
  if(finger==Finger&&Eligible&&!DragCommitted){button=duration<MinimumLongTapSeconds?0:1;}
  if(finger==Finger)Cancel();return button;
 }
 public void Cancel(){Finger=-1;Eligible=false;DragCommitted=false;}
}
