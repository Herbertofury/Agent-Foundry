#!/usr/bin/env python3
import tempfile,unittest
from pathlib import Path
from PIL import Image, PngImagePlugin
from reference_catalog import build_catalog,select_target,verify_catalog,digest
class CatalogTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name)
  for name in ('primary/a.png','rejected/a.png','states/a.png'):
   p=self.root/name;p.parent.mkdir(exist_ok=True);Image.new('RGBA',(2,2),(5,10,15,255)).save(p)
  self.policy={'rules':[{'prefix':'primary','role':'primary'},{'prefix':'rejected','role':'rejected'},{'prefix':'states','role':'state'}], 'overrides':{'primary/a.png':{'variant':'a','expected_sha256':digest(self.root/'primary/a.png')}}}
 def tearDown(self):self.tmp.cleanup()
 def test_pinned_selection_and_no_deletion(self):
  cat=build_catalog(self.root,self.policy);self.assertEqual(select_target(cat,'a')['path'],'primary/a.png');self.assertEqual(len(cat['assets']),3);self.assertEqual(len(cat['duplicate_groups']),1);self.assertEqual(len(list(self.root.rglob('*.png'))),3)
 def test_metadata_only_difference_is_pixel_duplicate(self):
  p=self.root/'states/a.png';meta=PngImagePlugin.PngInfo();meta.add_text('source','alternate export')
  Image.new('RGBA',(2,2),(5,10,15,255)).save(p,pnginfo=meta)
  cat=build_catalog(self.root,self.policy)
  self.assertEqual(len(cat['pixel_duplicate_groups']),1)
  self.assertEqual(len(cat['pixel_duplicate_groups'][0]['paths']),3)
  self.assertNotEqual(digest(p),digest(self.root/'primary/a.png'))
 def test_unpinned_is_not_approved(self):
  self.policy['overrides']['primary/a.png'].pop('expected_sha256')
  with self.assertRaises(ValueError):select_target(build_catalog(self.root,self.policy),'a')
 def test_rejected_is_not_target(self):
  self.policy['overrides']['primary/a.png']['role']='rejected'
  with self.assertRaises(ValueError):select_target(build_catalog(self.root,self.policy),'a')
 def test_hash_drift_fails(self):
  (self.root/'primary/a.png').write_bytes(b'changed')
  with self.assertRaises(ValueError):build_catalog(self.root,self.policy)
 def test_verify_detects_later_drift(self):
  cat=build_catalog(self.root,self.policy);(self.root/'states/a.png').write_bytes(b'changed')
  with self.assertRaises(ValueError):verify_catalog(self.root,cat)
 def test_ambiguous_targets_fail(self):
  self.policy['overrides']['states/a.png']={'variant':'a','expected_sha256':digest(self.root/'states/a.png')}
  with self.assertRaises(ValueError):select_target(build_catalog(self.root,self.policy),'a')
 def test_path_escape_fails(self):
  self.policy['overrides']['../outside.png']={'role':'primary'}
  with self.assertRaises(ValueError):build_catalog(self.root,self.policy)
 def test_missing_override_fails(self):
  self.policy['overrides']['primary/missing.png']={'role':'primary'}
  with self.assertRaises(ValueError):build_catalog(self.root,self.policy)
 def test_symlink_escape_fails(self):
  with tempfile.TemporaryDirectory() as other:
   p=Path(other)/'image.png';p.write_bytes(b'outside');(self.root/'primary/link.png').symlink_to(p)
   with self.assertRaises(ValueError):build_catalog(self.root,self.policy)
if __name__=='__main__':unittest.main()
