import copy
import unittest
from batch_result import power_audit_failures

class PowerEvidence(unittest.TestCase):
    def fixture(self):
        state={'batchIdentifier':'fresh','expectedVersion':'36'}
        report={'batchIdentifier':'fresh','buildVersion':'36','completed':True,'fixturesRemoved':True,'errors':[],'states':[]}
        for phase,graph,sign in [('off',False,2),('on-no-power',True,2),('off-again',False,2),('low-power',True,3),('powered',True,4)]:
            report['states'].append(dict(phase=phase,graph=graph,signs=[sign,1],escVisible=False,fpsVisible=True,appMemory=9000000000,gpuSignsMatch=True,coverBufferMatches=True))
        return state,report

    def test_rejects_stale_incomplete_or_failed_power_evidence(self):
        state,report=self.fixture()
        self.assertEqual(power_audit_failures(state,report),[])
        for field,value in [('batchIdentifier','old'),('buildVersion','32'),('completed',False),('fixturesRemoved',False),('errors',['failed']),('states',[])]:
            broken=copy.deepcopy(report);broken[field]=value
            self.assertTrue(power_audit_failures(state,broken))
        for field,value in [('graph',False),('signs',[2,1]),('gpuSignsMatch',False),('coverBufferMatches',False),('escVisible',True),('fpsVisible',False),('appMemory',0)]:
            broken=copy.deepcopy(report);broken['states'][3][field]=value
            self.assertTrue(power_audit_failures(state,broken))
        broken=copy.deepcopy(report);broken['states'][4]['signs']=[3,1]
        self.assertTrue(power_audit_failures(state,broken))

if __name__=='__main__':unittest.main()
