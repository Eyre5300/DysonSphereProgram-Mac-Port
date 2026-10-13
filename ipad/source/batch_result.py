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


def world_audit_failures(state, report):
    result=integration_failures(state, False)
    if not report or report.get('batchIdentifier')!=state.get('batchIdentifier') or str(report.get('buildVersion'))!=state.get('expectedVersion'):
        return result+['World audit missing or stale']
    if not report.get('completed') or report.get('errors'):
        result.append('World audit incomplete or failed')
    if not report.get('cameraRestored') or len(report.get('cameraBefore',[]))!=6 or report.get('cameraBefore')!=report.get('cameraAfter'):
        result.append('World audit left a different camera fixture')
    snaps=report.get('snapshots',[])
    if [s.get('label') for s in snaps]!=['normal','globe']:
        result.append('Both world views required')
    for s in snaps:
        if s.get('label')=='globe' and (not s.get('veinDistribution') or s.get('visibleVeinIcons',0)<=0):
            result.append('Enabled vein distribution icons missing')
        if not s.get('loaded') or not s.get('renderVein') or s.get('liveVeins',0)<=0 or s.get('animMismatch')!=0:
            result.append('Vein data/upload invalid: '+s.get('label',''))
        draws=0
        for m in s.get('models',[]):
            for b in m.get('batches',[]):
                if b.get('instanceMismatch')!=0: result.append('Instance upload mismatch')
                for mat in b.get('materials',[]):
                    if not mat.get('supported') or mat.get('vertaWords')!=b.get('expectedVertaWords'):
                        result.append('Unsupported shader or wrong animation length')
                    if m.get('type')=='Vein' and mat.get('frameCount',0)>0 and b.get('expectedVertaWords',0)>0:
                        draws+=sum(b.get('args',[])[1::5])
        if draws<=0:result.append('No animated vein draw evidence')
    inputs=report.get('inputs',[])
    if len(inputs)!=4 or not inputs[0].startswith('Normal zoom limit: Normal distance=1') or inputs[-1]!='Globe zoom transition: Starmap star=True':
        result.append('Original zoom path evidence missing')
    return result


def power_audit_failures(state, report):
    """Data/input gates; screenshots still require separate visual review."""
    if not report or report.get('batchIdentifier') != state.get('batchIdentifier') or str(report.get('buildVersion')) != state.get('expectedVersion'):
        return ['Power audit missing or stale']
    result = []
    if not report.get('completed') or not report.get('fixturesRemoved') or report.get('errors'):
        result.append('Power audit incomplete, failed, or fixtures not removed')
    states = report.get('states', [])
    if [s.get('phase') for s in states] != ['off', 'on-no-power', 'off-again', 'low-power', 'powered']:
        return result + ['Power stages missing']
    if [s.get('graph') for s in states] != [False, True, False, True, True]:
        result.append('Original power toggle did not follow expected states')
    for index, s in enumerate(states):
        signs = s.get('signs', [])
        if len(signs) != 2 or signs[1] != 1 or (index < 3 and signs[0] != 2) or (index == 3 and signs[0] != 3) or (index == 4 and signs[0] in [1, 2, 3]):
            result.append('Original power warning state mismatch')
        if s.get('escVisible') is not False or s.get('fpsVisible') is not True or s.get('appMemory', 0) <= 0:
            result.append('Performance/ESC status mismatch')
        if s.get('gpuSignsMatch') is not True or s.get('coverBufferMatches') is not True:
            result.append('Power GPU data mismatch')
    return result


def file_layout_failures(state, report):
    required={window+' file buttons '+check for window in ('load','save') for check in ('use original style','clear original controls')}
    if not report or report.get('batchIdentifier')!=state.get('batchIdentifier') or str(report.get('buildVersion'))!=state.get('expectedVersion'):
        return ['File layout report missing or stale']
    checks=report.get('checks',[])
    if not report.get('completed') or report.get('phase')!='passed' or report.get('errors') or {c.get('name') for c in checks}!=required or len(checks)!=4 or any(c.get('passed') is not True for c in checks):
        return ['Changed file-button layout incomplete or failed']
    return []


FLIGHT_KEY_CHECKS = ['three R taps between render frames','plain R held preserves original no-repeat','Shift R original fine rotation','Shift release during held R','rapid Shift R then plain R keeps separate modifiers','LeftControl native click to fuel','RightControl native click to fuel','original double Space enters flight','space fixture active','sailing original cursor request','Tab releases sailing pointer','Tab restores sailing pointer','C opens mecha plus inventory and releases sailing pointer','first Esc closes inventory only and keeps sailing pointer released','second Esc closes mecha and restores sailing pointer','captured pointer rotates ordinary sail view','W follows changed sail heading','released pointer does not rotate sail view','middle drag rotates released sail view','ordinary sail wheel zoom works both ways','physical Caps identity starts original warp','stable warp retains original camera distance rule','second Caps exits original warp','zoom recovers after leaving warp','flight fixture restored to ground']
FLIGHT_KEY_CHECKS += [key+suffix for key in ('W','E','Tab') for suffix in (' does not toggle warp after Caps',' does not restart warp')]

def flight_audit_failures(state, report, keyboard):
    result=process_failures(state)
    for name,r in [('flight',report),('keyboard',keyboard)]:
        if not r or r.get('batchIdentifier')!=state.get('batchIdentifier') or str(r.get('buildVersion'))!=state.get('expectedVersion') or not r.get('completed'):
            result.append(name+': missing, stale or incomplete')
    if not report or not report.get('savePathRestored') or report.get('phase')!='passed' or report.get('errors'):result.append('Flight isolation/phase failed')
    checks=(keyboard or {}).get('checks',[])
    display_checks=(report or {}).get('checks',[])
    expected_display={'PASS '+prefix+str(width)+suffix for width in (1600,1376) for prefix,suffix in [('original options list contains ','x'+str(width*3//4)),('original preview applies ','x'+str(width*3//4)),('original resolution confirmation stores ','')]}
    expected_display|={'PASS save path isolation available','PASS isolated world entered','PASS native move/scroll/button callbacks installed and zero-delta callback delivery works: 31','PASS flight transport assertions complete'}
    if not expected_display.issubset(display_checks) or len(display_checks)!=len(set(display_checks)) or any(c.startswith('FAIL ') for c in display_checks):result.append('Display/callback/isolation checks missing or failed')
    required=FLIGHT_KEY_CHECKS
    if len(checks)!=len(set(checks)) or any(not any(c.startswith('PASS '+name+':') for c in checks) for name in required) or any(c.startswith(('FAIL ','UNVERIFIED ')) for c in checks):result.append('Flight/warp checks missing or failed')
    return result


ESCAPE_CHECKS = {'isolated world entered', 'high refresh without frame cap', 'C opens original window pair', 'picker fixture active', 'picker closes before inventory', 'inventory closes before mecha', 'mecha closes before build', 'six rapid taps preserve every original layer', 'held Esc cancels once', 'release then press leaves build', 'unconsumed Esc opens pause', 'options close before pause resumes', 'Esc resumes suspended simulation', 'technology fixture active', 'technology closes without pause', 'starmap fixture active', 'starmap closes without pause', 'blueprint fixture active', 'blueprint closes without pause', 'no delayed Esc remains', 'render frames without simulation covered'}
ESCAPE_CHECKS |= {label+suffix for label in ['tool '+str(i) for i in (2301,2001,2011)]+['phase '+str(i) for i in range(12)]+['nested windows'] for suffix in (' cancels hand before pause',' leaves build before pause')}
ESCAPE_CHECKS |= {'held Esc does not resume newly opened pause','fresh Esc resumes after long hold'}

def escape_audit_failures(state, report):
    result=process_failures(state)
    if not report or report.get('batchIdentifier')!=state.get('batchIdentifier') or str(report.get('buildVersion'))!=state.get('expectedVersion'):
        return result+['Escape audit missing or stale']
    checks=report.get('checks',[])
    if (not all(report.get(k) for k in ('completed','savePathRestored','optionsUnchanged')) or report.get('phase')!='passed' or report.get('errors') or report.get('measuredFPS',0)<=90 or report.get('framesWithoutLogic',0)<=100 or not ESCAPE_CHECKS.issubset({c.get('name') for c in checks}) or any(c.get('passed') is not True for c in checks)):
        result.append('High-refresh Escape regression incomplete or failed')
    if [t.get('state') for t in report.get('rapidTransitions',[])]!=[27,26,24,16,0,32,0]:
        result.append('Rapid Escape close order missing or incorrect')
    return result
