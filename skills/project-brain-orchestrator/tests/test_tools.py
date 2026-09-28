from __future__ import annotations
import contextlib, importlib.util, io, json, os, subprocess, sys, tempfile, traceback, unittest, zipfile
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
SCRIPTS=ROOT/'scripts'
_TEST_ROOT=Path(tempfile.mkdtemp(prefix='agents-enforcer-tests-'))
_TEST_ENV=os.environ.copy()
_TEST_ENV['AGENTS_MEMORY_HOME']=str(_TEST_ROOT/'memory')
Path(_TEST_ENV['AGENTS_MEMORY_HOME']).mkdir(parents=True,exist_ok=True)
_MODULE_CACHE={}

def _load_script(path):
    path=Path(path).resolve()
    key=str(path)
    if key not in _MODULE_CACHE:
        spec=importlib.util.spec_from_file_location(f'_agents_test_{path.stem}_{abs(hash(key))}',path)
        module=importlib.util.module_from_spec(spec)
        assert spec.loader is not None
        spec.loader.exec_module(module)
        _MODULE_CACHE[key]=module
    return _MODULE_CACHE[key]

def run(*args,cwd=None):
    """Invoke the real script main() in-process to remove repeated Python startup cost."""
    script=Path(args[0]).resolve(); argv=[str(script),*map(str,args[1:])]
    module=_load_script(script); out=io.StringIO(); err=io.StringIO(); old_cwd=Path.cwd()
    code=0
    try:
        if cwd is not None: os.chdir(cwd)
        with patch.object(sys,'argv',argv), patch.dict(os.environ,_TEST_ENV,clear=True), contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            try:
                result=module.main()
                code=0 if result is None else int(result)
            except SystemExit as exc:
                code=exc.code if isinstance(exc.code,int) else (0 if exc.code is None else 1)
            except Exception:
                traceback.print_exc(file=err); code=1
    finally:
        os.chdir(old_cwd)
    return SimpleNamespace(returncode=code,stdout=out.getvalue(),stderr=err.getvalue())

class GovernanceToolsTests(unittest.TestCase):
    def test_compile_and_doctor(self):
        self.assertEqual(run(SCRIPTS/'compile_policy.py','--skill-root',ROOT,'--check').returncode,0)
        r=run(SCRIPTS/'agents_doctor.py','--skill-root',ROOT)
        self.assertEqual(r.returncode,0,r.stderr)

    def test_no_fixture_pitfall_in_production(self):
        data=json.loads((ROOT/'references/pitfalls-approved.json').read_text(encoding='utf-8'))
        joined=json.dumps(data).lower()
        for marker in ('test candidate','test only','test evidence'):
            self.assertNotIn(marker,joined)

    def test_task_state_and_receipt(self):
        with tempfile.TemporaryDirectory() as td:
            td=Path(td); state=td/'ACTIVE-TASK.json'; receipt=td/'CLOSEOUT.json'
            self.assertEqual(run(SCRIPTS/'task_state.py','--path',state,'init','--request','fix x','--target','repo').returncode,0)
            self.assertEqual(run(SCRIPTS/'task_state.py','--path',state,'add-requirement','--id','R-1','--text','works','--proof','runtime').returncode,0)
            self.assertEqual(run(SCRIPTS/'task_state.py','--path',state,'evidence','--id','R-1','--implementation','src/a','--verification','test','--observed','passed').returncode,0)
            self.assertEqual(run(SCRIPTS/'task_state.py','--path',state,'validate').returncode,0)
            self.assertEqual(run(SCRIPTS/'closeout_receipt.py','--path',receipt,'init','--target','repo','--build-id','abc').returncode,0)
            self.assertNotEqual(run(SCRIPTS/'closeout_receipt.py','--path',receipt,'validate').returncode,0)
            self.assertEqual(run(SCRIPTS/'closeout_receipt.py','--path',receipt,'build','--artifact','dist/app.zip','--verification-command','smoke','--exit-code','0','--observation','fresh copy launched','--status','verified','--fresh-copy').returncode,0)
            self.assertEqual(run(SCRIPTS/'closeout_receipt.py','--path',receipt,'add','--id','R-1','--implementation','src/a','--verification-command','test','--exit-code','0','--observation','passed','--status','verified').returncode,0)
            self.assertEqual(run(SCRIPTS/'closeout_receipt.py','--path',receipt,'validate').returncode,0)

    def test_static_ui_audit_detects_dead_control(self):
        with tempfile.TemporaryDirectory() as td:
            td=Path(td); (td/'index.html').write_text('<a href="#">Open</a>',encoding='utf-8'); out=td/'audit.json'
            r=run(SCRIPTS/'ui_audit.py',td,'--output',out)
            self.assertEqual(r.returncode,1)
            report=json.loads(out.read_text(encoding='utf-8'))
            self.assertTrue(any(x['kind']=='dead_href' for x in report['static_findings']))

    def test_project_probe_and_export(self):
        with tempfile.TemporaryDirectory() as td:
            td=Path(td); repo=td/'repo'; repo.mkdir(); (repo/'package.json').write_text('{"scripts":{"test":"echo ok"}}',encoding='utf-8')
            r=run(SCRIPTS/'project_probe.py',repo)
            self.assertEqual(r.returncode,0,r.stderr)
            self.assertTrue((repo/'.agents/PROJECT-PROBE.json').is_file())
            out=td/'out'; r=run(SCRIPTS/'export_bundle.py','--skill-root',ROOT,'--output-dir',out)
            self.assertEqual(r.returncode,0,r.stderr)
            z=out/'AGENTS-workflow-bundle.zip'; self.assertTrue(z.is_file())
            with zipfile.ZipFile(z) as f:
                names=set(f.namelist())
                self.assertIn('agents-workflow/AGENTS.md',names)
                self.assertIn('agents-workflow/.agents/VERIFICATION.md',names)
                self.assertIn('agents-workflow/.agents/MEMORY-CONTINUITY.md',names)
                self.assertIn('agents-workflow/tools/agents_doctor.py',names)
                self.assertIn('agents-workflow/tools/project_memory.py',names)
                self.assertIn('agents-workflow/tools/project_catalog.py',names)
                self.assertIn('agents-workflow/tools/research_memory.py',names)
                self.assertIn('agents-workflow/tools/library_manager.py',names)
                self.assertIn('agents-workflow/tools/project_compass.py',names)
                self.assertIn('agents-workflow/tools/asset_intelligence.py',names)
                self.assertIn('agents-workflow/memory/FEATURE-FOUNDRY-SOURCE-HUBS.seed.json',names)
                self.assertIn('agents-workflow/memory/FEATURE-FOUNDRY-OBJECT-INTELLIGENCE.seed.json',names)
                self.assertIn('agents-workflow/.agents/LIBRARY-STORAGE.md',names)
                self.assertIn('agents-workflow/library/README.md',names)
                self.assertIn('agents-workflow/library/quota-profiles.json',names)
                self.assertIn('agents-workflow/memory/USER-PROJECTS-DATABASE.seed.md',names)
                self.assertIn('agents-workflow/memory/README.md',names)


    def test_library_manager_organizes_warns_quarantines_restores_and_exports(self):
        with tempfile.TemporaryDirectory() as td:
            td=Path(td); vault=td/'library'; source=td/'source'; source.mkdir()
            (source/'alpha.txt').write_text('same payload',encoding='utf-8')
            (source/'beta.txt').write_text('same payload',encoding='utf-8')
            v1=source/'v1'; v2=source/'v2'; v1.mkdir(); v2.mkdir()
            (v1/'reference.html').write_text('<h1>Version 1</h1>',encoding='utf-8')
            (v2/'reference.html').write_text('<h1>Version 2</h1>',encoding='utf-8')
            lm=SCRIPTS/'library_manager.py'
            self.assertEqual(run(lm,'--vault',vault,'init').returncode,0)
            r=run(lm,'--vault',vault,'ingest',source/'alpha.txt',source/'beta.txt','--project-id','PRJ-001','--project-name','Agent','--kind','current','--status','current')
            self.assertEqual(r.returncode,0,r.stderr)
            self.assertEqual(run(lm,'--vault',vault,'ingest',v1/'reference.html','--project-id','PRJ-001','--project-name','Agent','--kind','version','--version','v1','--status','archived').returncode,0)
            self.assertEqual(run(lm,'--vault',vault,'ingest',v2/'reference.html','--project-id','PRJ-001','--project-name','Agent','--kind','version','--version','v2','--status','current','--protected').returncode,0)
            external=td/'external.json'
            external.write_text(json.dumps({'items':[{'name':'alpha-copy.txt','project_id':'PRJ-001','kind':'current','source_type':'chatgpt-library','source_id':'file-123','sha256':__import__('hashlib').sha256(b'same payload').hexdigest(),'bytes':12,'status':'observed'}]}),encoding='utf-8')
            self.assertEqual(run(lm,'--vault',vault,'import-manifest',external).returncode,0)
            r=run(lm,'--vault',vault,'record-usage','--plan','free','--used-bytes',450000000)
            self.assertEqual(r.returncode,0,r.stderr)
            self.assertEqual(json.loads(run(lm,'--vault',vault,'status').stdout)['severity'],'high')
            plan=json.loads(run(lm,'--vault',vault,'plan-cleanup').stdout)
            self.assertTrue(any(a['action']=='quarantine-local' for a in plan['actions']))
            self.assertTrue(any(a['action']=='manual-delete-external' for a in plan['actions']))
            self.assertTrue(any(x.get('reason','').startswith('same filename') for x in plan['review']))
            plan_path=vault/'cleanup-plans'/f"{plan['plan_id']}.json"
            denied=run(lm,'--vault',vault,'apply-cleanup',plan_path,'--confirm','WRONG')
            self.assertNotEqual(denied.returncode,0)
            applied=json.loads(run(lm,'--vault',vault,'apply-cleanup',plan_path,'--confirm',plan['confirm_token']).stdout)
            self.assertEqual(len(applied['moved']),1)
            moved=applied['moved'][0]
            self.assertTrue((vault/'90-Quarantine').exists())
            self.assertEqual(run(lm,'--vault',vault,'restore',moved).returncode,0)
            self.assertEqual(run(lm,'--vault',vault,'doctor').returncode,0)
            project_bundle=td/'project.zip'
            self.assertEqual(run(lm,'--vault',vault,'bundle-project','PRJ-001','--output',project_bundle).returncode,0)
            with zipfile.ZipFile(project_bundle) as zf:
                self.assertIn('project-library/MANIFEST.json',zf.namelist())
                self.assertTrue(any(name.endswith('/reference.html') for name in zf.namelist()))
            catalog_bundle=td/'library-catalog.zip'
            self.assertEqual(run(lm,'--vault',vault,'export','--output',catalog_bundle).returncode,0)
            with zipfile.ZipFile(catalog_bundle) as zf:
                self.assertIn('library-catalog/library-catalog.json',zf.namelist())
                self.assertIn('library-catalog/LIBRARY-DATABASE.md',zf.namelist())
            db=(vault/'LIBRARY-DATABASE.md').read_text(encoding='utf-8')
            self.assertIn('10-Projects/<project-id-name>/',db)
            self.assertIn('Same-name files with different content are versions',db)


    def test_project_catalog_bootstrap_reconcile_latest_gate_and_export(self):
        with tempfile.TemporaryDirectory() as td:
            td=Path(td); vault=td/'vault'; out=td/'catalog.zip'
            pc=SCRIPTS/'project_catalog.py'
            seed=ROOT/'assets/memory/USER-PROJECTS-DATABASE.seed.md'
            r=run(pc,'bootstrap','--vault',vault,'--seed',seed)
            self.assertEqual(r.returncode,0,r.stderr)
            rows=json.loads(run(pc,'list','--vault',vault,'--json').stdout)
            self.assertEqual(len(rows),24)
            manifest=td/'update.json'
            manifest.write_text(json.dumps({'projects':[{'project_id':'PRJ-002','status':'ACTIVE','confidence':'High','next_action':'Verify V12 in the canonical runtime','version':{'label':'V12','artifact':'feature-foundry-v12.html','status':'verified','confidence':'high','observed_at_utc':'2026-08-02T12:00:00Z','source':'file-library','source_id':'ff-v12','sha256':'a'*64,'is_latest':True},'artifact':{'name':'feature-foundry-v12.html','version':'V12','sha256':'a'*64,'source':'file-library','source_id':'ff-v12','status':'verified'}}]}),encoding='utf-8')
            r=run(pc,'reconcile','--vault',vault,'--input',manifest)
            self.assertEqual(r.returncode,0,r.stderr)
            project=json.loads(run(pc,'show','--vault',vault,'--project-id','PRJ-002').stdout)
            self.assertEqual(project['latest_version_or_artifact'],'V12')
            self.assertTrue(any(v.get('label')=='V12' and v.get('is_latest') for v in project['versions']))
            self.assertTrue(any('V11' in v.get('label','') for v in project['versions']))
            candidate=td/'candidate.json'
            candidate.write_text(json.dumps({'projects':[{'project_id':'PRJ-002','latest_version_or_artifact':'V99 timestamp-only candidate'}]}),encoding='utf-8')
            self.assertEqual(run(pc,'reconcile','--vault',vault,'--input',candidate).returncode,0)
            project=json.loads(run(pc,'show','--vault',vault,'--project-id','PRJ-002').stdout)
            self.assertEqual(project['latest_version_or_artifact'],'V12')
            self.assertEqual(run(pc,'doctor','--vault',vault).returncode,0)
            self.assertEqual(run(pc,'export','--vault',vault,'--output',out).returncode,0)
            with zipfile.ZipFile(out) as zf:
                self.assertIn('project-catalog/project-catalog.json',zf.namelist())
                self.assertIn('project-catalog/USER-PROJECTS-DATABASE.md',zf.namelist())
                self.assertIn('project-catalog/project-catalog-events.jsonl',zf.namelist())

    def test_project_memory_duplicate_prevention_resume_and_export(self):
        with tempfile.TemporaryDirectory() as td:
            td=Path(td); vault=td/'vault'; repo1=td/'repo-one'; repo2=td/'repo-two'; repo1.mkdir(); repo2.mkdir()
            for repo in (repo1,repo2):
                subprocess.run(['git','init','-q'],cwd=repo,check=True)
                subprocess.run(['git','remote','add','origin','https://example.invalid/org/explorer.git'],cwd=repo,check=True)
                (repo/'package.json').write_text('{"name":"explorer"}',encoding='utf-8')
            pm=SCRIPTS/'project_memory.py'
            r=run(pm,'init',repo1,'--name','Explorer','--purpose','Long-running project','--vault',vault)
            self.assertEqual(r.returncode,0,r.stderr)
            project1=json.loads((repo1/'.agents-memory/PROJECT.json').read_text(encoding='utf-8'))
            r=run(pm,'checkpoint',repo1,'--summary','Baseline captured','--goal','Continue existing work','--next-step','Verify runtime','--vault',vault)
            self.assertEqual(r.returncode,0,r.stderr)
            r=run(pm,'init',repo2,'--name','Explorer','--vault',vault)
            self.assertEqual(r.returncode,3,'duplicate project should be blocked')
            r=run(pm,'init',repo2,'--name','Explorer','--adopt-existing','--vault',vault)
            self.assertEqual(r.returncode,0,r.stderr)
            project2=json.loads((repo2/'.agents-memory/PROJECT.json').read_text(encoding='utf-8'))
            self.assertEqual(project1['project_id'],project2['project_id'])
            self.assertEqual(project2['canonical_root'],str(repo1.resolve()))
            r=run(pm,'resume','--query','Explorer','--vault',vault,'--json')
            self.assertEqual(r.returncode,0,r.stderr)
            resumed=json.loads(r.stdout)
            self.assertEqual(resumed['project']['project_id'],project1['project_id'])
            out=td/'memory.zip'; r=run(pm,'export',repo1,'--output',out)
            self.assertEqual(r.returncode,0,r.stderr); self.assertTrue(out.is_file())
            with zipfile.ZipFile(out) as zf:
                self.assertIn('project-memory/PROJECT.json',zf.namelist())
                self.assertIn('project-memory/HANDOFF.md',zf.namelist())

    def test_cross_chat_artifact_reconciliation_preserves_same_name_versions(self):
        with tempfile.TemporaryDirectory() as td:
            td=Path(td); repo=td/'repo'; vault=td/'vault'; repo.mkdir()
            pm=SCRIPTS/'project_memory.py'
            self.assertEqual(run(pm,'init',repo,'--name','Feature Foundry','--vault',vault).returncode,0)
            v3=td/'v3.json'; v4=td/'v4.json'
            v3.write_text(json.dumps({'artifacts':[{
                'name':'feature-foundry-living-world-prototype-standalone.html',
                'source_type':'file-library','source_id':'file-v3','created_at_utc':'2026-08-02T06:47:54Z',
                'explicit_version':'v3','content_signature':'sig-v3','status':'verified'
            }]}),encoding='utf-8')
            v4.write_text(json.dumps({'artifacts':[{
                'name':'feature-foundry-living-world-prototype-standalone.html',
                'source_type':'file-library','source_id':'file-v4','created_at_utc':'2026-08-02T07:01:36Z',
                'explicit_version':'v4','content_signature':'sig-v4','status':'verified'
            }]}),encoding='utf-8')
            r=run(pm,'reconcile-artifacts',repo,'--input',v3,'--vault',vault)
            self.assertEqual(r.returncode,0,r.stderr)
            first=json.loads(r.stdout)['added'][0]
            r=run(pm,'reconcile-artifacts',repo,'--input',v4,'--vault',vault)
            self.assertEqual(r.returncode,0,r.stderr)
            second=json.loads(r.stdout)['added'][0]
            self.assertTrue(second['lineage']['same_name_new_content'])
            self.assertEqual(second['lineage']['supersedes'],[first['id']])
            artifacts=json.loads(run(pm,'list-artifacts',repo,'--json').stdout)
            self.assertEqual(len(artifacts),2)
            self.assertEqual(artifacts[0]['explicit_version'],'v4')
            handoff=(repo/'.agents-memory/HANDOFF.md').read_text(encoding='utf-8')
            self.assertIn('(v4)',handoff)
            r=run(pm,'reconcile-artifacts',repo,'--input',v4,'--vault',vault)
            self.assertEqual(r.returncode,0,r.stderr)
            self.assertEqual(len(json.loads(r.stdout)['added']),0)
            self.assertEqual(len(json.loads(run(pm,'list-artifacts',repo,'--json').stdout)),2)
            self.assertEqual(run(pm,'doctor',repo,'--vault',vault).returncode,0)
            library_catalog=json.loads((vault/'library/library-catalog.json').read_text(encoding='utf-8'))
            library_items=list(library_catalog['items'].values())
            self.assertEqual(len(library_items),2)
            self.assertEqual({item.get('version') for item in library_items},{'v3','v4'})
            self.assertIn('feature-foundry-living-world-prototype-standalone.html',(vault/'library/LIBRARY-DATABASE.md').read_text(encoding='utf-8'))

    def test_research_memory_provenance_search_and_staleness(self):
        with tempfile.TemporaryDirectory() as td:
            td=Path(td); repo=td/'repo'; vault=td/'vault'; repo.mkdir()
            pm=SCRIPTS/'project_memory.py'; rm=SCRIPTS/'research_memory.py'
            self.assertEqual(run(pm,'init',repo,'--name','Research Project','--vault',vault).returncode,0)
            bad=run(rm,'add',repo,'--query','best parser','--claim','Tool A is best','--applies-to','parser','--decision','Use A','--why','fast','--status','verified')
            self.assertNotEqual(bad.returncode,0)
            good=run(rm,'add',repo,'--query','best parser','--claim','Tool A fits the current constraints','--source-url','https://example.com/tool-a','--source-title','Tool A docs','--publisher','Example','--source-version','2.0','--applies-to','parser on current platform','--decision','Use Tool A','--why','Verified compatibility','--evidence','Docs and runtime test','--status','verified','--review-after','2999-01-01T00:00:00+00:00')
            self.assertEqual(good.returncode,0,good.stderr)
            rid=good.stdout.strip(); self.assertTrue(rid.startswith('res-'))
            found=run(rm,'search',repo,'parser')
            self.assertEqual(found.returncode,0,found.stderr)
            self.assertEqual(json.loads(found.stdout)[0]['research_id'],rid)
            self.assertEqual(run(rm,'doctor',repo).returncode,0)
            digest=td/'digest.md'; self.assertEqual(run(rm,'digest',repo,'--output',digest).returncode,0)
            self.assertIn('Tool A fits',digest.read_text(encoding='utf-8'))

    def test_repository_doctor_validates_project_memory(self):
        with tempfile.TemporaryDirectory() as td:
            td=Path(td); repo=td/'repo'; vault=td/'vault'; repo.mkdir()
            (repo/'AGENTS.md').write_text('# AGENTS.md\n',encoding='utf-8')
            pm=SCRIPTS/'project_memory.py'
            self.assertEqual(run(pm,'init',repo,'--name','Doctor Project','--vault',vault).returncode,0)
            r=run(SCRIPTS/'agents_doctor.py','--repository',repo)
            self.assertEqual(r.returncode,0,r.stderr)

if __name__=='__main__': unittest.main()
