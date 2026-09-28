import json, subprocess, sys, tempfile, unittest
from pathlib import Path
SCRIPT=Path(__file__).resolve().parents[1]/"scripts/project_compass.py"
class CompassTests(unittest.TestCase):
 def cmd(self,*a,ok=True):
  r=subprocess.run([sys.executable,str(SCRIPT),*map(str,a)],text=True,capture_output=True)
  if ok and r.returncode: self.fail(r.stderr+r.stdout)
  return r
 def test_lifecycle(self):
  with tempfile.TemporaryDirectory() as td:
   root=Path(td); self.cmd('init',root,'--project-id','demo')
   self.cmd('add',root,'northpoints','--id','alive','--title','Alive UI','--statement','Make it alive','--priority','foundational','--verify','real runtime reacts')
   self.cmd('validate',root)
   d=json.loads((root/'.agents-memory/COMPASS.json').read_text())
   self.assertEqual(d['northpoints'][0]['id'],'alive')
   self.assertTrue((root/'.agents-memory/PROJECT-COMPASS.md').is_file())
   self.assertNotEqual(self.cmd('add',root,'northpoints','--id','alive','--statement','duplicate',ok=False).returncode,0)
   self.cmd('supersede',root,'northpoints','alive','--by','alive-v2','--reason','expanded')
   self.assertEqual(json.loads((root/'.agents-memory/COMPASS.json').read_text())['northpoints'][0]['status'],'superseded')

 def test_foundational_items_require_provenance_and_proof(self):
  with tempfile.TemporaryDirectory() as td:
   root=Path(td); self.cmd('init',root,'--project-id','demo')
   self.cmd('add',root,'northpoints','--id','weak','--title','Weak foundation','--statement','Missing proof','--priority','foundational','--source','')
   invalid=self.cmd('validate',root,ok=False)
   self.assertNotEqual(invalid.returncode,0)
   self.assertIn('foundational item missing source',invalid.stdout)
   self.assertIn('foundational item missing verification',invalid.stdout)

 def test_feature_foundry_seed_has_theme_native_interaction_ecology(self):
  seed=Path(__file__).resolve().parents[1]/'assets/memory/FEATURE-FOUNDRY-COMPASS.seed.json'
  d=json.loads(seed.read_text(encoding='utf-8'))
  ids={kind:{item['id'] for item in d[kind]} for kind in ('goals','feature_pillars','principles','wants','guardrails','acceptance_signals')}
  self.assertIn('goal-theme-native-interaction-ecology',ids['goals'])
  self.assertIn('pillar-cross-element-causality',ids['feature_pillars'])
  self.assertIn('pillar-interruptible-world-physics',ids['feature_pillars'])
  self.assertIn('principle-input-sovereignty',ids['principles'])
  self.assertIn('principle-subtle-unmistakable',ids['principles'])
  self.assertIn('want-frutiger-gel-button',ids['wants'])
  self.assertIn('want-liminal-soft-uncanny-input',ids['wants'])
  self.assertIn('want-graffiti-input-placement',ids['wants'])
  self.assertIn('guardrail-interaction-never-blocks',ids['guardrails'])
  self.assertIn('signal-live-interruption-test',ids['acceptance_signals'])
  corpus=json.dumps(d,ensure_ascii=False).lower()
  for phrase in ('frutiger aero','liminal','jet set','subtle but unmistakable','user input always wins','yank','continuous causal world','reversible derivation graph','truthful representation ladder','source adapter','noai','quality lanes'):
   self.assertIn(phrase,corpus)
  for iid in ('goal-continuous-causal-world-model','goal-alive-on-any-hardware','goal-authoring-capability-continuously-expands','pillar-causal-field-router','pillar-material-memory-and-recovery','pillar-attention-governor','pillar-intent-aware-anticipation','pillar-ecology-director','pillar-transition-depth-ladder','pillar-spatial-micro-audio','pillar-relationship-social-physics','pillar-theme-native-ai-presence','pillar-environmental-data-embodiment','pillar-living-time-microclimates','pillar-causal-undo-replay','pillar-ecology-authoring-studio','pillar-cross-device-embodiment','pillar-adaptive-capability-ladder','pillar-age-and-usage-patina','pillar-representation-ladder','pillar-reversible-derivation-graph','pillar-isolated-blend-processing','guardrail-license-and-noai','guardrail-no-performance-feature-loss','guardrail-no-viewport-content-culling','guardrail-gpu-is-optional','signal-source-adapter-contract','signal-transition-depth-matrix','signal-potato-feature-parity','signal-authoring-roundtrip'):
   self.assertTrue(any(iid==x['id'] for section in ('goals','feature_pillars','principles','wants','guardrails','acceptance_signals') for x in d[section]),iid)
  for phrase in ('intent-aware anticipation','full world traversal','chronological patina','interaction patina','potato','cinematic','viewport content culling','authoring capability continuously expands with the ecology'):
   self.assertIn(phrase,corpus)

 def test_publish_requires_matching_size(self):
  with tempfile.TemporaryDirectory() as td:
   root=Path(td); self.cmd('init',root,'--project-id','demo')
   bad=self.cmd('publish-record',root,'--provider','drive','--remote-id','x','--remote-url','u','--name','a','--local-size','1','--remote-size','2','--sha256','0'*64,ok=False)
   self.assertNotEqual(bad.returncode,0)
   self.cmd('publish-record',root,'--provider','drive','--remote-id','x','--remote-url','u','--name','a','--local-size','2','--remote-size','2','--sha256','0'*64)
   self.assertTrue((root/'.agents-memory/publications.jsonl').is_file())
if __name__=='__main__': unittest.main()
