#if UNITY_STANDALONE_OSX && !UNITY_EDITOR
using System.Collections;
using UnityEngine;

// Called after the original Exit Program fade finishes. Stop submitting new
// geometry before Unity tears down Metal's outstanding dynamic buffer writes.
public sealed class PortMacShutdown : MonoBehaviour {
 static bool requested;
 public static void Request(){
  if(requested)return;
  requested=true;
  var runner=new GameObject("Mac graceful shutdown");
  DontDestroyOnLoad(runner);
  runner.AddComponent<PortMacShutdown>().StartCoroutine(DrainAndQuit());
 }
 static IEnumerator DrainAndQuit(){
  // Finish the game's own save/end lifecycle while Camera.main still exists.
  // The universe and atmosphere update paths require that camera until End().
  DSPGame.EndGame();
  yield return null;
  foreach(var camera in FindObjectsOfType<Camera>())camera.enabled=false;
  foreach(var canvas in FindObjectsOfType<Canvas>())canvas.enabled=false;
  Debug.Log("DSP_MAC_SHUTDOWN_RENDER_SUBMISSION_STOPPED");
  for(int frame=0;frame<3;frame++){yield return new WaitForEndOfFrame();yield return null;}
  Debug.Log("DSP_MAC_SHUTDOWN_DRAINED");
  Application.Quit();
 }
}
#endif
