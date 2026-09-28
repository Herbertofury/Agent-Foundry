import hashlib, json, subprocess, sys, tempfile, unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]; PKG=ROOT/'tools'/'package_skills.py'; VAL=ROOT/'tools'/'validate_skill_tree.py'
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
class PackageTests(unittest.TestCase):
 def test_deterministic(self):
  with tempfile.TemporaryDirectory() as td:
   t=Path(td); s=t/'skills'/'alpha'; s.mkdir(parents=True); (s/'SKILL.md').write_text('---\nname: alpha\ndescription: test\n---\nhello\n'); (s/'x.txt').write_text('x')
   subprocess.run([sys.executable,str(VAL),str(t/'skills')],check=True)
   out1=t/'o1'; out2=t/'o2'; args=['--skills-root',str(t/'skills'),'--source-url','https://example.invalid/repo','--revision','abc','--built-at','1790467200']
   subprocess.run([sys.executable,str(PKG),'--out',str(out1),*args],check=True,capture_output=True,text=True); subprocess.run([sys.executable,str(PKG),'--out',str(out2),*args],check=True,capture_output=True,text=True)
   self.assertEqual(sha(out1/'alpha'/'skill.zip'),sha(out2/'alpha'/'skill.zip')); r=json.loads((out1/'alpha'/'release-receipt.json').read_text()); self.assertEqual(r['sha256'],sha(out1/'alpha'/'skill.zip')); self.assertEqual(r['sourceRevision'],'abc')
if __name__=='__main__': unittest.main()
