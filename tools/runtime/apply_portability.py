"""Apply reproducible, narrow patches to the working copy of recovered sources."""
from pathlib import Path
import hashlib, json, re

ROOT=Path('work/dsp-runtime/port-project');SRC=ROOT/'Assets/Scripts/Assembly-CSharp'
BASE=Path('work/dsp-runtime/recovered-project/ExportedProject/Assets/Scripts/Assembly-CSharp')
COND='UNITY_IOS || UNITY_EDITOR_OSX || UNITY_STANDALONE_OSX || DSP_PORTABLE_PLATFORM'
records=[]
def save(name,text):
    original=(BASE/name).read_bytes();(SRC/name).write_text(text)
    records.append(dict(file=name,original_sha256=hashlib.sha256(original).hexdigest(),patched_sha256=hashlib.sha256(text.encode()).hexdigest()))

for name in ['PerformanceCounter.cs','HighStopwatch.cs','DeepProfiler.cs']:
    text=(BASE/name).read_text()
    counter='\t[DllImport("kernel32.dll", ExactSpelling = true)]\n\tprivate static extern int QueryPerformanceCounter(ref long count);'
    frequency='\t[DllImport("kernel32.dll", ExactSpelling = true)]\n\tprivate static extern int QueryPerformanceFrequency(ref long frequency);'
    assert text.count(counter)==text.count(frequency)==1
    for original,body in [(counter,'\tprivate static int QueryPerformanceCounter(ref long count)\n\t{\n\t\tcount = System.Diagnostics.Stopwatch.GetTimestamp();\n\t\treturn 1;\n\t}'),(frequency,'\tprivate static int QueryPerformanceFrequency(ref long frequency)\n\t{\n\t\tfrequency = System.Diagnostics.Stopwatch.Frequency;\n\t\treturn 1;\n\t}')]:
        text=text.replace(original,'#if '+COND+'\n'+body+'\n#else\n'+original+'\n#endif')
    save(name,text)

text=(BASE/'HybridBarrier.cs').read_text()
def add_after(anchor, body):
    global text
    assert text.count(anchor)==1, anchor
    text=text.replace(anchor,anchor+'\n#if '+COND+'\n'+body+'\n#endif')

# IL2CPP 2022.3's Generic/Handle.cpp implements WaitAny by polling every
# 10 ms. Use condition-variable notification for frequent game phase barriers.
# The predicate is read under the monitor; both completion and cancellation
# acquire that monitor before waking, so a signal cannot be lost at Wait().
add_after('\tprivate CancellationToken cancellationToken;', '''
    private readonly object phaseMonitor = new object();
    private readonly CancellationTokenRegistration[] participantWakeups;
    private CancellationTokenRegistration barrierWakeup;

    private void WakePhaseWaiters()
    {
        lock (phaseMonitor) Monitor.PulseAll(phaseMonitor);
    }

    private int WaitForPhase(long expectedPhase, CancellationToken participantToken)
    {
        lock (phaseMonitor)
        {
            // Check cancellation before completion: disabling a waiting
            // participant can itself complete the phase.
            while (true)
            {
                participantToken.ThrowIfCancellationRequested();
                cancellationToken.ThrowIfCancellationRequested();
                if (Interlocked.Read(ref _currentPhase) > expectedPhase) return 0;
                Monitor.Wait(phaseMonitor);
            }
        }
    }''')
add_after('\t\tparticipants = new Participant[participantCapacity];', '\t\tparticipantWakeups = new CancellationTokenRegistration[participantCapacity];')
add_after('\t\t\tparticipants[participant_index].cancellationTokenSource = new CancellationTokenSource();', '\t\t\tparticipantWakeups[participant_index] = participants[participant_index].cancellationTokenSource.Token.Register(WakePhaseWaiters);')
add_after('\t\t\t\tparticipants[participant_index].cancellationTokenSource.Cancel();', '\t\t\t\tparticipantWakeups[participant_index].Dispose();')
add_after('\t\tlong num = Interlocked.Exchange(ref _currentPhase, Interlocked.Read(ref participants[participant_index].phase) + 1);', '\t\tWakePhaseWaiters();')
anchor='\tpublic void SetCancellationToken(CancellationToken token)\n\t{'
add_after(anchor, '\t\tbarrierWakeup.Dispose();')
add_after('\t\tcancellationToken = token;', '\t\tbarrierWakeup = token.Register(WakePhaseWaiters);')
add_after('\tpublic void Dispose()\n\t{', '\t\tbarrierWakeup.Dispose();\n\t\tforeach (var registration in participantWakeups) registration.Dispose();')
anchor='\t\t\t\tint num5 = WaitForMultipleObjects((waitHandles[2] == IntPtr.Zero) ? 2 : 3, waitHandles, bWaitAll: false, -1);'
assert text.count(anchor)==1
text=text.replace(anchor,'#if '+COND+'\n\t\t\t\tint num5 = WaitForPhase(num, token);\n#else\n'+anchor+'\n#endif')
anchor='\t[DllImport("kernel32.dll", SetLastError = true)]\n\tprivate static extern int WaitForMultipleObjects(int nCount, IntPtr[] lpHandles, bool bWaitAll, int dwMilliseconds);'
assert text.count(anchor)==1
text=text.replace(anchor,'#if !('+COND+')\n'+anchor+'\n#endif')
save('HybridBarrier.cs',text)

# AssetRipper cannot read this build's BuildSettings. Restore the single scene
# actually present in the source depot, retaining its recovered asset GUID.
scene_guid=re.search(r'^guid: (\w+)$',(ROOT/'Assets/Scenes/level0.unity.meta').read_text(),re.M).group(1)
(ROOT/'ProjectSettings/EditorBuildSettings.asset').write_text('%YAML 1.1\n%TAG !u! tag:unity3d.com,2011:\n--- !u!1045 &1\nEditorBuildSettings:\n  m_ObjectHideFlags: 0\n  serializedVersion: 2\n  m_Scenes:\n  - enabled: 1\n    path: Assets/Scenes/level0.unity\n    guid: '+scene_guid+'\n  m_configObjects: {}\n')
(ROOT/'ProjectSettings/ProjectVersion.txt').write_text('m_EditorVersion: 2022.3.62f3c1\nm_EditorVersionWithRevision: 2022.3.62f3c1 (1623fc0bbb97)\n')
Path('work/dsp-runtime/portability-patches.json').write_text(json.dumps(records,indent=2)+'\n')
print('Patched',len(records),'files; restored scene build settings and exact editor version.')
