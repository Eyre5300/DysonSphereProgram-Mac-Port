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


def integration_failures(state, touch_expected):
    result=touch_failures(state,state.get('touchReport')) if touch_expected else process_failures(state)
    for key in ['integrationReport','keyboardReport','mouseReport']:
        r=state.get(key) or {}
        if (r.get('batchIdentifier')!=state.get('batchIdentifier') or str(r.get('buildVersion'))!=state.get('expectedVersion') or not r.get('completed')):
            result.append(key+': missing, incomplete or stale')
    r=state.get('integrationReport') or {}
    names={c.get('name') for c in r.get('checks',[])}
    required={'system document picker presented','cancel preserves save','native coordinated save import','duplicate save keeps both','original parser reads imported save','invalid save rejected','system export picker presented','export cancellation preserves source','native coordinated blueprint import','original blueprint roundtrip','cross-type import rejected'}
    if touch_expected:required|={'direct touch selects touch','pointer jitter does not switch','pointer movement selects keyboard','drag defers mode switch','after release selects touch','keyboard action selects keyboard','fixed touch ignores keyboard mode request','fixed keyboard ignores touch mode request','automatic restored'}
    if r.get('phase')!='passed' or r.get('errors') or not required.issubset(names) or any(c.get('passed') is not True for c in r.get('checks',[])):
        result.append('Input/files checks incomplete or failed')
    keys=(state.get('keyboardReport') or {}).get('checks',[])
    if len(keys)!=len(set(keys)) or sum(c.startswith('PASS ') for c in keys)<31 or any(c.startswith(('FAIL ','UNVERIFIED ')) for c in keys):result.append('Keyboard checks incomplete or failed')
    mouse=(state.get('mouseReport') or {}).get('checks',[])
    if len(mouse)!=len({c.get('name') for c in mouse}) or sum(c.get('status')=='PASS' for c in mouse)<25 or any(c.get('status') in ('FAIL','SKIPPED') for c in mouse):result.append('Mouse checks incomplete or failed')
    return result
