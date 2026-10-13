import tempfile,unittest,json
from pathlib import Path
from unity_paths import ios_support
from run_release_smoke import validate,CHECKS
from migrate import Workflow,canonical,write

class ReleaseWorkflowTests(unittest.TestCase):
    def test_supported_module_layouts_and_missing_module(self):
        for relative in ['Contents/PlaybackEngines/iOSSupport','../PlaybackEngines/iOSSupport']:
            with tempfile.TemporaryDirectory() as t:
                app=Path(t)/'Editor/Unity.app';app.mkdir(parents=True)
                with self.assertRaises(ValueError):ios_support(app)
                archive=app/relative/'Trampoline/Libraries/libiPhone-lib.a';archive.parent.mkdir(parents=True);archive.write_bytes(b'fixture')
                self.assertEqual(ios_support(app).resolve(),archive.resolve().parents[2])
    def test_smoke_rejects_stale_menu_and_incomplete_evidence(self):
        identity={'batchIdentifier':'fresh','buildVersion':'47'}
        native=dict(identity,diagnosticFlags=16385)
        game=dict(identity,phase='batch_finished_normal_exit',autoTestCompleted=True,errors=[])
        report=dict(identity,phase='passed',completed=True,restored=True,errors=[],checks=list(CHECKS),startTick=120,endTick=240)
        self.assertTrue(validate(native,game,report,'fresh','47'))
        for target,field,value in [(native,'batchIdentifier','old'),(native,'diagnosticFlags',16),(game,'phase','main_menu'),(game,'errors',['error']),(report,'restored',False),(report,'checks',[]),(report,'endTick',120)]:
            before=target[field];target[field]=value;self.assertFalse(validate(native,game,report,'fresh','47'));target[field]=before
    def test_launch_options_precede_forwarded_app_arguments(self):
        with tempfile.TemporaryDirectory() as t:
            flow=Workflow.__new__(Workflow);flow.c={'device':'device'};flow.logs=Path(t);calls=[]
            def run(name,args,env=None):
                calls.append(list(map(str,args)));write(flow.logs/(name+'.json'),{'result':{'ok':True}})
            flow.run=run
            self.assertEqual(flow.device('launch','process','launch','bundle','--dsp-diagnostics-only'),{'ok':True})
            args=calls[0];self.assertLess(args.index('--device'),args.index('bundle'));self.assertEqual(args[-1],'--dsp-diagnostics-only')
    def test_completed_stage_checks_artifacts_before_reuse(self):
        with tempfile.TemporaryDirectory() as t:
            flow=Workflow.__new__(Workflow);flow.work=Path(t);flow.path=flow.work/'migration.json';flow.state={'stages':{}};calls=[];output=flow.work/'artifact'
            def create():calls.append(True);output.write_text('verified')
            flow.stage('stage',create,[output]);flow.stage('stage',create,[output]);self.assertEqual(len(calls),1)
            output.write_text('changed')
            with self.assertRaises(ValueError):flow.stage('stage',create,[output])
    def test_failed_build_is_archived_not_deleted(self):
        with tempfile.TemporaryDirectory() as t:
            flow=Workflow.__new__(Workflow);flow.work=Path(t);flow.path=flow.work/'migration.json';flow.state={'stages':{},'activeStage':'release-build'}
            old=flow.work/'release-build';old.mkdir();(old/'evidence').write_text('failure')
            output=flow.work/'receipt';flow.stage('release-build',lambda:output.write_text('new'),[output])
            self.assertEqual(len(list(flow.work.glob('release-build.failed-*/evidence'))),1)
    def test_configuration_requires_explicit_source_and_rejects_touch(self):
        c={k:'fixture' for k in ('game','workspace','unity','upstream','spirv_cross','vkd3d','team','bundle','device','identity')};c['version']='47'
        with self.assertRaises(ValueError):canonical(c)
        c['exported_project']='original';self.assertEqual(canonical(c)['version'],'47')
        c['version']='47.1.2'
        with self.assertRaises(ValueError):canonical(c)
        c['version']='47'
        c['assetripper']='ripper'
        with self.assertRaises(ValueError):canonical(c)
        del c['assetripper'];c['bundle']='local.touch.preview'
        with self.assertRaises(ValueError):canonical(c)
if __name__=='__main__':unittest.main()
