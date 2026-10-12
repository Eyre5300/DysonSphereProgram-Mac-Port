import copy,tempfile,unittest
from pathlib import Path
from private_paths import private_output
from batch_result import failures
class Guards(unittest.TestCase):
 def test_repository_overlap(self):
  repo=Path(__file__).resolve().parents[2]
  for path in [repo,repo/'generated',repo.parent]:
   with self.assertRaises(ValueError):private_output(path)
 def test_input_overlap(self):
  for path in ['/tmp/guard-owned','/tmp/guard-owned/child','/tmp']:
   with self.assertRaises(ValueError):private_output(path,['/tmp/guard-owned'])
 def test_symlink_overlap(self):
  with tempfile.TemporaryDirectory() as d:
   link=Path(d)/'alias';link.symlink_to(Path(__file__).resolve().parents[2],target_is_directory=True)
   with self.assertRaises(ValueError):private_output(link/'generated')
 def test_independent_output(self):
  self.assertEqual(private_output('/tmp/guard-result',['/tmp/guard-input']),Path('/tmp/guard-result').resolve())
 def state(self):
  return {'flagsVerified':True,'enteredWorld':True,'consoleExitCode':0,'batchIdentifier':'new','expectedVersion':'27','finalGameReport':{'batchIdentifier':'new','buildVersion':'27','phase':'batch_finished_normal_exit','autoTestCompleted':True,'errors':[]}}, {'completed':True,'phase':'passed','errors':[],'stages':[{'status':'passed'} for i in range(14)]}
 def test_complete(self):
  s,f=self.state();self.assertEqual(failures(s,f),[])
 def test_zero_exit_menu_or_old_report_rejected(self):
  for key,value in [('phase','main_menu'),('batchIdentifier','old'),('buildVersion','24'),('autoTestCompleted',False),('errors',['error'])]:
   s,f=self.state();s['finalGameReport'][key]=value;self.assertTrue(failures(s,f))
 def test_stale_incomplete_functional_rejected(self):
  s,f=self.state();f['stages'][-1]['status']='running';self.assertTrue(failures(s,f))
 def test_missing_functional_rejected(self):
  s,f=self.state();self.assertTrue(failures(s,None))
 def touch_state(self):
  names=['HUD included in original UI camera', 'simultaneous move and look', 'release clears movement and look', 'look tap never clicks world', 'camera zoom buttons', 'three rapid rotation buttons', 'miner original fine rotation', 'fine pointer nudge', 'cancel releases modifier', 'preview drag does not place', 'original building placement', 'belt height controls', 'belt start stage', 'belt endpoint edit does not place', 'original belt segment placement', 'sorter fixture containers', 'sorter selects source', 'sorter valid target preview', 'sorter preview does not place', 'original sorter placement', 'fullscreen blocks movement', 'save touch-built world', 'reload touch-built world']
  state,_=self.state()
  return state,{'batchIdentifier':'new','buildVersion':'27','completed':True,'phase':'passed','errors':[], 'checks':[{'name':name,'passed':True} for name in names]}
 def test_touch_evidence_identity_and_completeness(self):
  from batch_result import touch_failures
  state,report=self.touch_state();self.assertEqual(touch_failures(state,report),[])
  for key,value in [('batchIdentifier','old'),('buildVersion','28'),('completed',False),('errors',['error'])]:
   bad=copy.deepcopy(report);bad[key]=value;self.assertTrue(touch_failures(state,bad))
  for bad in [None,{},dict(report,checks=report['checks'][:-1]),dict(report,checks=report['checks']+report['checks'][:1])]:
   self.assertTrue(touch_failures(state,bad))
  bad=copy.deepcopy(report);bad['checks'][0]['passed']=False;self.assertTrue(touch_failures(state,bad))
  state['enteredWorld']=False;self.assertTrue(touch_failures(state,report))
class IntegrationGuards(unittest.TestCase):
 def integration_state(self):
  state,touch=Guards().touch_state()
  names=['system document picker presented','cancel preserves save','native coordinated save import','duplicate save keeps both','original parser reads imported save','invalid save rejected','system export picker presented','export cancellation preserves source','native coordinated blueprint import','original blueprint roundtrip','cross-type import rejected','direct touch selects touch','pointer jitter does not switch','pointer movement selects keyboard','drag defers mode switch','after release selects touch','keyboard action selects keyboard','fixed touch ignores keyboard mode request','fixed keyboard ignores touch mode request','automatic restored']
  state['touchReport']=touch
  for key in ['integrationReport','keyboardReport','mouseReport']:
   state[key]={'batchIdentifier':'new','buildVersion':'27','completed':True,'phase':'passed','errors':[]}
  state['integrationReport']['checks']=[{'name':n,'passed':True} for n in names]
  state['keyboardReport']['checks']=['PASS key '+str(i) for i in range(31)]
  state['mouseReport']['checks']=[{'name':'mouse '+str(i),'status':'PASS'} for i in range(25)]
  return state
 def test_integration_rejects_stale_missing_failed_or_duplicate(self):
  from batch_result import integration_failures
  state=self.integration_state()
  for touch in [False,True]:
   self.assertEqual(integration_failures(state,touch),[])
   for key in ['integrationReport','keyboardReport','mouseReport']:
    for field,value in [('completed',False),('batchIdentifier','old'),('buildVersion','0'),('checks',[])]:
     bad=copy.deepcopy(state);bad[key][field]=value;self.assertTrue(integration_failures(bad,touch))
   bad=copy.deepcopy(state);bad['integrationReport']['checks'][0]['passed']=False;self.assertTrue(integration_failures(bad,touch))
   for key in ['keyboardReport','mouseReport']:
    bad=copy.deepcopy(state);bad[key]['checks']=[bad[key]['checks'][0]]*len(bad[key]['checks']);self.assertTrue(integration_failures(bad,touch))
  state.pop('touchReport');self.assertEqual(integration_failures(state,False),[]);self.assertTrue(integration_failures(state,True))


class WorldGuards(unittest.TestCase):
 def test_rejects_original_zero_length_regression_and_missing_evidence(self):
  from batch_result import world_audit_failures
  state=IntegrationGuards().integration_state()
  batch={'instanceMismatch':0,'expectedVertaWords':100,'args':[3,4,0,0,0],'materials':[{'supported':True,'frameCount':7,'vertaWords':100}]}
  snap={'label':'normal','loaded':True,'renderVein':True,'liveVeins':4,'animMismatch':0,'models':[{'type':'Vein','batches':[batch]}]}
  globe=copy.deepcopy(snap);globe.update(label='globe',veinDistribution=True,visibleVeinIcons=3)
  report={'batchIdentifier':'new','buildVersion':'27','completed':True,'cameraRestored':True,'cameraBefore':[0,.8,.8,0,.8,.8],'cameraAfter':[0,.8,.8,0,.8,.8],'errors':[],'snapshots':[snap,globe],'inputs':['Normal zoom limit: Normal distance=1','Globe left drag angle=0','Globe middle drag angle=19','Globe zoom transition: Starmap star=True']}
  self.assertEqual(world_audit_failures(state,report),[])
  for field,value in [('batchIdentifier','old'),('completed',False),('errors',['failure']),('snapshots',[]),('inputs',[]),('cameraRestored',False),('cameraAfter',[0,.2,.7,0,.2,.7])]:
   bad=copy.deepcopy(report);bad[field]=value;self.assertTrue(world_audit_failures(state,bad))
  for field,value in [('expectedVertaWords',0),('args',[3,0,0,0,0]),('instanceMismatch',1)]:
   bad=copy.deepcopy(report);bad['snapshots'][0]['models'][0]['batches'][0][field]=value;self.assertTrue(world_audit_failures(state,bad))
  bad=copy.deepcopy(report);bad['snapshots'][1]['visibleVeinIcons']=0;self.assertTrue(world_audit_failures(state,bad))
  bad=copy.deepcopy(report);bad['snapshots'][0]['models'][0]['batches'][0]['materials'][0]['vertaWords']=0
  self.assertTrue(world_audit_failures(state,bad))

if __name__=='__main__':unittest.main()
