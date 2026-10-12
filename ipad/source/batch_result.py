"""Fail closed when a successful process exit lacks completed game evidence."""
def failures(state, functional):
    result=[]
    if not state.get('flagsVerified') or not state.get('enteredWorld'):result.append('Fresh native acknowledgement and world entry required')
    if state.get('consoleExitCode') != 0:result.append('Console did not exit normally')
    game=state.get('finalGameReport') or {}
    if game.get('batchIdentifier') != state.get('batchIdentifier') or str(game.get('buildVersion')) != state.get('expectedVersion'):result.append('Final report identity mismatch')
    if game.get('phase') != 'batch_finished_normal_exit' or not game.get('autoTestCompleted') or game.get('errors'):result.append('Game batch incomplete or reported errors')
    stages=(functional or {}).get('stages',[])
    if not functional or not functional.get('completed') or functional.get('phase') != 'passed' or functional.get('errors') or len(stages)!=14 or any(s.get('status')!='passed' for s in stages):result.append('Functional stages incomplete or failed')
    return result
