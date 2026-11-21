"""Concrete adapters + acquisition parent + real cycle, synthetic external edges."""
import copy
from datetime import timedelta
import hashlib
import json
from pathlib import Path
import subprocess
import sys
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import test_kobe_html_connection as setup
import test_continuous_mayor as fixtures
from mayor_updates import acquire, continuous, kobe_html_connection as k
from mayor_updates.city_scope import validate_selection, validate_storage, signature
from mayor_updates.projection import Hold


class AdapterTests(setup.ConnectionTests):
    # Inherit fixtures, not the old callback tests.
    def setUp(self):
        super().setUp()
        (self.root/'processing').mkdir()
        self.c['processing_state_root'] = str(self.root/'processing')
        identity = json.loads(Path(self.c['series_identity']['path']).read_text())
        identity['processing_state_root'] = self.c['processing_state_root']
        self.c['series_identity'] = self.pin('identity',identity)
        repo=fixtures.REPO
        self.runtime=dict(city='kobe', network_enabled=False,
            state_root=self.c['processing_state_root'], base_revision='synthetic',
            config=self.filepin(repo/'config/mayor_update_sources.json'),
            baseline=self.filepin(repo/'frontend/public/data/kobe_mayor_tracker.json'),
            profile=self.filepin(repo/'config/mayor_offline_weekly.json'))
        self.saved=fixtures.SavedBridge(self.root/'cas',[])
        self.saved.hashes={'synthetic':'pin'}
        self.saved.store.read_index=lambda:copy.deepcopy(self.saved.index)
        self.saved.store.snapshot_bytes=lambda sha:self.saved.bodies[sha]
        self.saved.store.record_failure=lambda **kw:None
        self.label='initial';self.worker_calls=0;self.fail=False;self.unknown=False
        self.factories=[]
        for p in (patch.object(acquire,'assert_owner_only',return_value={'owner_only':True}),
                  patch.object(continuous,'configure_shell'),
                  patch.object(acquire,'P1Bridge',side_effect=self.new_bridge),
                  patch.object(k,'P1Bridge',side_effect=self.new_bridge),
                  patch.object(acquire,'run_confirmed_worker',side_effect=self.synthetic_worker)):
            p.start();self.addCleanup(p.stop)

    def filepin(self,path):
        return {'path':str(path.resolve()),'sha256':hashlib.sha256(path.read_bytes()).hexdigest()}

    def new_bridge(self,*args,**kwargs):
        result=copy.copy(self.saved)
        result.index=copy.deepcopy(self.saved.index)
        self.factories.append(result)
        return result

    def synthetic_worker(self,cmd,env,run):
        self.worker_calls+=1
        scope=json.loads((run/'scope.json').read_text())
        storage=json.loads((run/'storage.json').read_text())
        source=json.loads((run/'source.json').read_text())
        # Same checks used in the actual child, before replacement network/P1.
        validate_selection(scope,[source],'html')
        validate_storage(scope,storage,self.root/'cas',run)
        auth=json.loads((Path(storage['attempt_output'])/'request_authorized.json').read_text())
        self.assertEqual(auth['scope_sha256'],signature(scope))
        if self.unknown:
            (run/'termination.json').write_text(json.dumps({'termination_confirmed':False}))
            raise Hold('synthetic termination unknown')
        if self.fail:
            (run/'termination.json').write_text(json.dumps({'termination_confirmed':True,'returncode':2}))
            raise Hold('synthetic failed worker')
        body=('<div id="tmp_contents"><h2>令和8年度</h2><p>'+self.label+
              '</p><a href="'+self.label+'.pdf">資料</a></div>').encode()
        sha=hashlib.sha256(body).hexdigest()
        prior=self.saved.index['documents'].get(k.URL)
        unchanged=prior and prior['versions'][-1]['sha256']==sha
        observed=self.now.astimezone(k.timezone.utc).isoformat()
        rec=dict(city_code='kobe',document_id='kobe-doc-'+hashlib.sha256(k.URL.encode()).hexdigest()[:24],
            source_url=k.URL,final_url=k.URL,sha256=sha,version_id=sha,mime_type='text/html',
            fiscal_year=2026,document_type='budget_index',source_title=k.SOURCE['title'],
            snapshot_relative_path='objects/'+sha,retrieved_at=observed)
        if not unchanged:
            self.saved.bodies[sha]=body
            self.saved.index['documents'].setdefault(k.URL,{'versions':[]})['versions'].append(
                {'sha256':sha,'record':rec})
        else:
            rec={**prior['versions'][-1]['record'],'retrieved_at':observed}
        self.saved.index['attempts'].append(dict(source_url=k.URL,sha256=sha,
            outcome='unchanged' if unchanged else 'new_version',observed_at=observed))
        outcome=dict(status='unchanged' if unchanged else 'stored_new_version',
            version=rec,http_status=200,final_url=k.URL)
        (run/'worker_outcome.json').write_text(json.dumps(outcome))
        (run/'termination.json').write_text(json.dumps(dict(termination_confirmed=True,returncode=0,
            pid=123, intent_sha256=hashlib.sha256((run/'single_get_started.json').read_bytes()).hexdigest(),
            outcome_sha256=hashlib.sha256((run/'worker_outcome.json').read_bytes()).hexdigest())))
        return subprocess.CompletedProcess(cmd,0,'','')

    def connected(self, through_entry=False):
        cp=self.pin('contract',self.c);self.a['contract_sha256']=cp['sha256']
        self.runtime.update(connection_contract=cp,connection_approval=self.pin('approval',self.a))
        with patch.object(k,'clock',return_value=self.now):
            if through_entry:
                from mayor_updates import dependency_preflight as pre, kobe_acquisition
                from importlib.metadata import version
                import contextlib,io
                package=Path(k.__file__).parent
                self.runtime['code_files']=[self.filepin(p) for p in package.glob('*.py')]
                self.runtime['resource_files']=[self.filepin(package.parent/'p1_patches'/n)
                                               for n in pre.P1_RESOURCES]
                runtime=self.pin('runtime',self.runtime)
                contract=self.pin('preflight',dict(runtime_sha256=pre.runtime_digest(self.runtime),
                    state_root=self.runtime['state_root'],python=sys.executable,
                    python_sha256=pre.sha(sys.executable),
                    dependencies={n:version(n) for n in pre.MODULES}))
                with patch.object(sys,'argv',['test','--runtime',runtime['path'],'--contract',
                        contract['path'],'--contract-sha256',contract['sha256']]), contextlib.redirect_stdout(io.StringIO()) as stream:
                    kobe_acquisition.main()
                return json.loads(stream.getvalue())
            return k.run_connected(self.runtime)

    def next_week(self):
        self.now+=timedelta(days=7)
        self.a.update(week=self.now.date().isoformat(),valid_from=(self.now-timedelta(hours=1)).isoformat(),
                      valid_until=(self.now+timedelta(hours=1)).isoformat())

    def test_real_parent_cycle_new_same_changed_and_same_week(self):
        before=Path(self.legacy['path']).read_bytes()
        result=self.connected()
        self.assertEqual(result['state'],'private_result_saved')
        self.assertEqual(self.factories[0].index['documents'],{})
        self.assertIn(k.URL,self.factories[-1].index['documents'])
        report=json.loads((self.root/'processing/cycles/2026-11-23/city_report.json').read_text())
        self.assertEqual(report['sources'][0]['saved_observation_age_days'],0)
        self.assertEqual(report['sources'][0]['age_evaluated_at'],self.now.isoformat())
        self.assertTrue((self.root/'processing/state.json').is_file())
        with self.assertRaises(Hold):self.connected()
        self.assertEqual(self.worker_calls,1)
        self.next_week();same=self.connected()
        self.assertEqual(same['private_result']['new_review_count'],0)
        self.assertNotEqual(same['acquisition_audit']['original_retrieved_at'],
                            same['acquisition_audit']['acquisition_observed_at'])
        self.next_week();self.label='changed';changed=self.connected()
        self.assertEqual(changed['private_result']['new_review_count'],1)
        self.assertEqual(Path(self.legacy['path']).read_bytes(),before)

    def test_public_entry_real_preflight_adapters_parent_and_cycle(self):
        result=self.connected(through_entry=True)
        self.assertEqual(result['state'],'private_result_saved')
        self.assertEqual(self.worker_calls,1)
        self.assertTrue((self.root/'processing/cycles/2026-11-23/cycle_result.json').is_file())

    def test_real_cycle_content_hold_keeps_last_good(self):
        self.connected();before=(self.root/'processing/state.json').read_bytes()
        self.next_week();self.label='訂正';result=self.connected()
        self.assertEqual(result['state'],'content_hold')
        self.assertFalse(result['private_result']['state_advanced'])
        self.assertEqual((self.root/'processing/state.json').read_bytes(),before)
        self.assertTrue((self.root/'processing/cycles/2026-11-30/safety_hold.json').is_file())
        with self.assertRaises(Hold):self.connected()

    def test_acquisition_failure_stops_before_cycle(self):
        self.fail=True
        with self.assertRaises(Hold):self.connected()
        self.assertEqual(list((self.root/'processing').iterdir()),[])
        self.assertEqual(len(list((self.root/'series').glob('*/failure.json'))),1)
        with self.assertRaises(Hold):self.connected()
        self.assertEqual(self.worker_calls,1)

    def test_termination_unknown_stops_before_cycle(self):
        self.unknown=True
        with self.assertRaises(Hold):self.connected()
        self.assertEqual(list((self.root/'processing').iterdir()),[])
        self.assertEqual(len(list((self.root/'series').glob('*/reservation.json'))),1)


# Keep fixture inheritance without repeating the already accepted callback suite.
for _name in setup.ConnectionTests.__dict__:
    if _name.startswith('test_') and _name not in AdapterTests.__dict__:
        setattr(AdapterTests,_name,None)


class TerminationTests(unittest.TestCase):
    def test_harmless_child_has_pid_and_observed_exit(self):
        import tempfile,os
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);(root/'single_get_started.json').write_text('{}')
            result=acquire.run_confirmed_worker([sys.executable,'-B','-c','pass'],os.environ.copy(),root)
            evidence=json.loads((root/'termination.json').read_text())
            self.assertEqual(result.returncode,0)
            self.assertTrue(evidence['termination_confirmed'])
            self.assertGreater(evidence['pid'],0)
            self.assertFalse(evidence['timed_out'])

    def test_unknown_exit_is_not_success(self):
        import tempfile,os
        from unittest.mock import MagicMock
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);(root/'single_get_started.json').write_text('{}')
            proc=MagicMock();proc.pid=123;proc.wait.side_effect=subprocess.TimeoutExpired('test',10)
            with patch.object(acquire.subprocess,'Popen',return_value=proc):
                with self.assertRaises(subprocess.TimeoutExpired):
                    acquire.run_confirmed_worker(['synthetic'],os.environ.copy(),root)
            evidence=json.loads((root/'termination.json').read_text())
            self.assertFalse(evidence['termination_confirmed'])
            self.assertEqual([c.kwargs['timeout'] for c in proc.wait.call_args_list],[10,2])


if __name__=='__main__':unittest.main()

