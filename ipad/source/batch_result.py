"""Fail closed when a successful process exit lacks completed game evidence."""
def process_failures(state):
    result=[]
    if not state.get('flagsVerified') or not state.get('enteredWorld'):result.append('Fresh native acknowledgement and world entry required')
    if state.get('consoleExitCode') != 0:result.append('Console did not exit normally')
    game=state.get('finalGameReport') or {}
    if game.get('batchIdentifier') != state.get('batchIdentifier') or str(game.get('buildVersion')) != state.get('expectedVersion'):result.append('Final report identity mismatch')
    if game.get('phase') != 'batch_finished_normal_exit' or not game.get('autoTestCompleted') or game.get('errors'):result.append('Game batch incomplete or reported errors')
    return result

def failures(state, functional):
    result=process_failures(state)
    stages=(functional or {}).get('stages',[])
    if not functional or not functional.get('completed') or functional.get('phase') != 'passed' or functional.get('errors') or len(stages)!=14 or any(s.get('status')!='passed' for s in stages):result.append('Functional stages incomplete or failed')
    return result


def touch_failures(state, report):
    # Reuse identity/world/exit checks, without accepting a keyboard-only report.
    result=process_failures(state)
    if not report:return result+['Touch report missing']
    if report.get('batchIdentifier')!=state.get('batchIdentifier') or str(report.get('buildVersion'))!=state.get('expectedVersion'):
        result.append('Touch report identity mismatch')
    required={
        'HUD included in original UI camera', 'simultaneous move and look',
        'release clears movement and look', 'look tap never clicks world',
        'camera zoom buttons', 'three rapid rotation buttons',
        'miner original fine rotation', 'fine pointer nudge', 'cancel releases modifier',
        'preview drag does not place', 'original building placement',
        'belt height controls', 'belt start stage', 'belt endpoint edit does not place',
        'original belt segment placement', 'sorter fixture containers',
        'sorter selects source', 'sorter valid target preview',
        'sorter preview does not place', 'original sorter placement',
        'fullscreen blocks movement', 'save touch-built world', 'reload touch-built world'}
    checks=report.get('checks',[])
    names=[c.get('name') for c in checks]
    if (not report.get('completed') or report.get('phase')!='passed' or report.get('errors')
        or not required.issubset(names) or len(names)!=len(set(names))
        or any(c.get('passed') is not True for c in checks)):
        result.append('Touch checks incomplete or failed')
    return result
