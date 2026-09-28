import json, subprocess, sys, tempfile, unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
SCRIPT=ROOT/'scripts/asset_intelligence.py'
HUBS=ROOT/'assets/memory/FEATURE-FOUNDRY-SOURCE-HUBS.seed.json'
OBJECTS=ROOT/'assets/memory/FEATURE-FOUNDRY-OBJECT-INTELLIGENCE.seed.json'
class AssetIntelligenceTests(unittest.TestCase):
 def cmd(self,*args,ok=True):
  r=subprocess.run([sys.executable,str(SCRIPT),*map(str,args)],text=True,capture_output=True)
  if ok and r.returncode: self.fail(r.stdout+r.stderr)
  return r
 def test_catalogs_validate_and_render(self):
  self.cmd('validate')
  with tempfile.TemporaryDirectory() as td:
   out=Path(td)/'asset-intelligence.md'; self.cmd('render','--output',out)
   text=out.read_text(encoding='utf-8')
   for phrase in ('Source capability matrix','Reversible derivation graph','GIPHY','Blender 4.5 LTS','simplest truthful representation'):
    self.assertIn(phrase,text)
 def test_hub_matrix_truthfully_distinguishes_access_modes(self):
  d=json.loads(HUBS.read_text(encoding='utf-8')); hubs={x['id']:x for x in d['hubs']}
  self.assertEqual(hubs['openverse']['preferred_mode'],'public_api')
  self.assertEqual(hubs['pinterest']['preferred_mode'],'browser_clipper')
  self.assertEqual(hubs['artstation']['status'],'clipper_only')
  self.assertEqual(hubs['tenor']['status'],'legacy_existing_clients')
  self.assertEqual(hubs['giphy']['preferred_mode'],'official_api')
  self.assertIn('oembed',hubs['bluesky']['adapter_modes'])
  for h in d['hubs']:
   self.assertTrue(h['rights_policy']); self.assertTrue(h['fallback']); self.assertTrue(h['review_due'])
 def test_object_pipeline_is_reversible_and_progressive(self):
  d=json.loads(OBJECTS.read_text(encoding='utf-8'))
  self.assertEqual([x['id'] for x in d['quality_lanes']],['instant-preview','interactive-draft','high-fidelity'])
  self.assertGreaterEqual(len(d['derivation_pipeline']),15)
  self.assertTrue(all(x['reversible'] for x in d['derivation_pipeline']))
  ids={x['id'] for x in d['derivation_pipeline']}
  for iid in ('preserve-original','representation-selection','part-affordance-graph','theme-behavior-genome','publish-lineage'):
   self.assertIn(iid,ids)
  tools={x['id'] for x in d['tools']}
  for iid in ('grounded-sam2','depth-anything-v2','spar3d','trellis2','blender-4-5-lts','meshoptimizer-gltfpack','coacd','rapier'):
   self.assertIn(iid,tools)
 def test_validator_rejects_fake_api_claim(self):
  with tempfile.TemporaryDirectory() as td:
   bad=json.loads(HUBS.read_text(encoding='utf-8'))
   bad['hubs'][0]['status']='clipper_only'
   p=Path(td)/'bad.json'; p.write_text(json.dumps(bad),encoding='utf-8')
   r=self.cmd('validate','--hubs',p,ok=False)
   self.assertNotEqual(r.returncode,0); self.assertIn('cannot claim an API',r.stdout)
if __name__=='__main__': unittest.main()
