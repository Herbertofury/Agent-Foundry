import json, subprocess, sys, tempfile, unittest
from pathlib import Path
SCRIPT=Path(__file__).resolve().parents[1]/'tools'/'foundry_sync.py'
class SyncTests(unittest.TestCase):
 def run_cmd(self,*args,code=0):
  p=subprocess.run([sys.executable,str(SCRIPT),*map(str,args)],text=True,capture_output=True); self.assertEqual(p.returncode,code,(p.stdout,p.stderr)); return p
 def mk_skill(self,path,name,body='v1'):
  path.mkdir(parents=True); (path/'SKILL.md').write_text(f'---\nname: {name}\ndescription: test\n---\n{body}\n'); (path/'data.txt').write_text(body)
 def cfg(self,repo,target):
  p=repo/'config.json'; p.write_text(json.dumps({'schemaVersion':1,'targets':[target],'skills':[{'name':'alpha','source':'skills/alpha','targets':[target['name']]}]})); return p
 def test_symlink_copy_drift_and_no_clobber(self):
  with tempfile.TemporaryDirectory() as td:
   root=Path(td); repo=root/'repo'; self.mk_skill(repo/'skills'/'alpha','alpha'); state=root/'s.json'
   cfg=self.cfg(repo,{'name':'codex','root':str(root/'codex'),'mode':'symlink'})
   self.assertIn('CREATE',self.run_cmd('plan','--repo',repo,'--config',cfg,'--state',state).stdout)
   self.run_cmd('apply','--repo',repo,'--config',cfg,'--state',state); self.assertTrue((root/'codex'/'alpha').is_symlink()); self.run_cmd('status','--repo',repo,'--config',cfg,'--state',state)
   (repo/'skills'/'alpha'/'data.txt').write_text('v2'); self.run_cmd('status','--repo',repo,'--config',cfg,'--state',state)
   state2=root/'s2.json'; cfg2=self.cfg(repo,{'name':'claude','root':str(root/'copy'),'mode':'copy'}); self.run_cmd('apply','--repo',repo,'--config',cfg2,'--state',state2)
   (repo/'skills'/'alpha'/'data.txt').write_text('v3'); self.run_cmd('status','--repo',repo,'--config',cfg2,'--state',state2,code=2); self.run_cmd('apply','--repo',repo,'--config',cfg2,'--state',state2); self.assertEqual((root/'copy'/'alpha'/'data.txt').read_text(),'v3')
   (root/'copy'/'alpha'/'data.txt').write_text('customized'); before_state=state2.read_bytes()
   self.run_cmd('plan','--repo',repo,'--config',cfg2,'--state',state2,code=2)
   self.run_cmd('apply','--repo',repo,'--config',cfg2,'--state',state2,code=3)
   self.assertEqual((root/'copy'/'alpha'/'data.txt').read_text(),'customized'); self.assertEqual(state2.read_bytes(),before_state)
   bad=root/'bad'; (bad/'alpha').mkdir(parents=True); (bad/'alpha'/'keep.txt').write_text('mine'); cfg3=self.cfg(repo,{'name':'cursor','root':str(bad),'mode':'copy'})
   self.run_cmd('plan','--repo',repo,'--config',cfg3,'--state',root/'s3.json',code=2); self.run_cmd('apply','--repo',repo,'--config',cfg3,'--state',root/'s3.json',code=3); self.assertEqual((bad/'alpha'/'keep.txt').read_text(),'mine')
if __name__=='__main__': unittest.main()
