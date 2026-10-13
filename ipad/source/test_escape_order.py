import unittest
import copy
from apply_escape_order import HOOKS, ORIGINAL, PAUSE_CALL, RESET, patch, strip
from batch_result import ESCAPE_CHECKS, escape_audit_failures

class EscapePatchTests(unittest.TestCase):
    def test_preserves_bodies_and_idempotent(self):
        for name,hooks in HOOKS.items():
            source='class Fixture\n{\n'+''.join('\t'+sig+'\n\t{\n\t\tExample();\n\t}\n' for sig,_ in hooks)
            if name=='GameMain.cs':source+='\tprivate void PauseFixture()\n\t{\n'+ORIGINAL+'\n\t\t{ Example(); }\n\t}\n'
            if name=='GameMain.cs':source+='\tvoid StartPause()\n\t{\n'+PAUSE_CALL+'\n\t}\n'
            if name=='UIEscMenu.cs':source+='\tvoid OpenMenu()\n\t{\n'+RESET+'\n\t}\n'
            source+='}\n'
            with self.subTest(name=name):
                result=patch(source,name)
                self.assertEqual(strip(result),source)
                self.assertEqual(patch(result,name),result)
    def test_rejects_missing_or_duplicate_anchors(self):
        for source in ('', '\tpublic static void OnUpdate()\n\t{\n\t}\n'*2):
            with self.assertRaises(ValueError):patch(source,'VFInput.cs')

class EscapeEvidenceTests(unittest.TestCase):
    def fixture(self):
        identity={'batchIdentifier':'current-test','buildVersion':'45'}
        state={'batchIdentifier':'current-test','expectedVersion':'45','flagsVerified':True,'enteredWorld':True,'consoleExitCode':0,
               'finalGameReport':dict(identity,phase='batch_finished_normal_exit',autoTestCompleted=True,errors=[])}
        report=dict(identity,completed=True,savePathRestored=True,optionsUnchanged=True,phase='passed',errors=[],measuredFPS=120,framesWithoutLogic=1000,
                    checks=[{'name':name,'passed':True} for name in sorted(ESCAPE_CHECKS)],rapidTransitions=[{'state':s} for s in [27,26,24,16,0,32,0]])
        return state,report
    def test_full_batch_required(self):
        self.assertEqual(escape_audit_failures(*self.fixture()),[])
        state,report=self.fixture()
        for i in range(len(report['checks'])):
            changed=copy.deepcopy(report);changed['checks'].pop(i)
            self.assertTrue(escape_audit_failures(state,changed))
    def test_rejects_stale_low_fps_or_wrong_order(self):
        for key,value in [('batchIdentifier','old'),('completed',False),('savePathRestored',False),('optionsUnchanged',False),('measuredFPS',60),('framesWithoutLogic',0),('rapidTransitions',[]),('errors',['failure'])]:
            state,report=self.fixture();report[key]=value
            self.assertTrue(escape_audit_failures(state,report),key)

if __name__=='__main__':unittest.main()
