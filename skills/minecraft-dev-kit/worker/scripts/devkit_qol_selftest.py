#!/usr/bin/env python3
"""Exercise setup, dependency closure, provider verification and hostile archive cases."""
from __future__ import annotations
import hashlib
import io
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tarfile
import tempfile
import unittest
from unittest.mock import patch
import zipfile
import devkit_dependencies as dep
import devkit_toolchains as tc


def jar_bytes(modid, version='1.0.0', *, depends=None, nested=None, **extra):
    stream=io.BytesIO()
    metadata={'schemaVersion':1,'id':modid,'version':version,'depends':depends or {},**extra}
    if nested: metadata['jars']=[{'file':'META-INF/jars/child.jar'}]
    with zipfile.ZipFile(stream,'w') as z:
        z.writestr('fabric.mod.json',json.dumps(metadata))
        if nested:z.writestr('META-INF/jars/child.jar',nested)
    return stream.getvalue()


class QoL(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(prefix='devkit-qol-')
        self.root=Path(self.temp.name)
    def tearDown(self):self.temp.cleanup()
    def jar(self,name,data):
        p=self.root/name;p.write_bytes(data);return p
    def test_release_envelopes(self):
        for mc,jdk in {'1.12.2':8,'1.17.1':16,'1.18.2':17,'1.20.1':17,'1.20.4':17,'1.20.5':21,'1.21.1':21,'26.3':25}.items():
            self.assertEqual(tc.target_java(mc),jdk)
    def test_real_installed_jdk_offline(self):
        pair=tc.java_pair(Path(shutil.which('java')))
        self.assertTrue(pair)
        with patch.object(tc,'get_json',side_effect=AssertionError('offline used network')):
            result=tc.ensure_jdk(pair['java'],offline=True)
        self.assertEqual(result['java'],pair['java'])
        with self.assertRaises(ValueError):tc.ensure_jdk(pair['java']+1,explicit=Path(pair['java_path']))
    def test_private_jdk_cache_path_containment(self):
        with patch.object(tc,'get_json',side_effect=AssertionError('offline used network')):
            with self.assertRaises(RuntimeError):tc.ensure_jdk(25,root=self.root,offline=True,managed_only=True)
    def test_archive_zip_slip(self):
        for name in ['../escape','/absolute','C:/drive','folder\\escape','safe/file:ads']:
            p=self.root/'evil.zip'
            entry = zipfile.ZipInfo('placeholder')
            entry.filename = entry.orig_filename = name
            with zipfile.ZipFile(p,'w') as z:z.writestr(entry,'bad')
            with zipfile.ZipFile(p) as z:self.assertEqual(z.infolist()[0].orig_filename, name)
            with self.assertRaises(ValueError):tc.safe_extract(p,self.root/'out')
        self.assertFalse((self.root/'escape').exists())
    def test_archive_tar_link(self):
        p=self.root/'evil.tar'
        with tarfile.open(p,'w') as z:
            link=tarfile.TarInfo('link');link.type=tarfile.SYMTYPE;link.linkname='../../escape';z.addfile(link)
        with self.assertRaises(ValueError):tc.safe_extract(p,self.root/'out')
    def test_verified_download_reuse_and_corruption(self):
        data=b'exact provider bytes';checksum=hashlib.sha256(data).hexdigest();p=self.root/'cached.zip'
        p.write_bytes(data)
        with patch.object(tc,'urlopen',side_effect=AssertionError('cached bytes redownloaded')):
            self.assertEqual(tc.download_verified('https://example.test/a',p,checksum),p)
        class Response(io.BytesIO):url='https://example.test/a'
        p.write_bytes(b'prior bytes')
        with patch.object(tc,'urlopen',return_value=Response(b'bad')):
            with self.assertRaises(ValueError):tc.download_verified('https://example.test/a',p,checksum)
        self.assertEqual(p.read_bytes(),b'prior bytes')
        with patch.object(tc,'urlopen',return_value=Response(data)):
            tc.download_verified('https://example.test/a',p,checksum)
        self.assertEqual(p.read_bytes(),data)
        self.assertEqual(list(self.root.glob('*.partial')),[])
    def test_versions(self):
        cases=[('26.3','~26.3',True),('26.2','~26.3',False),('1.2.0','>=1.0 <2.0',True),
               ('1.2.0','1.x',True),('0.2.5','^0.2.1',True),('0.3.0','^0.2.1',True),
               ('2.0.0',['<1','>=2'],True),('1.0.0-beta.2','>=1.0.0',False),
               ('1.0.0-beta.11','>1.0.0-beta.2',True),('1.0.0','>=not-semver',None)]
        cases += [('26.3','~26.3-',True),('26.3-rc.1','~26.3-',True),
                  ('26.4-alpha','~26.3-',False),('1.9','~1',False)]
        for version,rule,result in cases:self.assertIs(dep.satisfies(version,rule),result,(version,rule))
    def test_native_fixture_and_wizard(self):
        import devkit
        import devkit_native
        self.assertIn('world.getConnection().waitForChunksRender()', devkit_native.JAVA)
        self.assertIn('save.open()', devkit_native.JAVA)
        self.assertNotIn('world.getClientLevel().waitForChunksRender()', devkit_native.JAVA)
        with patch('builtins.input', side_effect=EOFError):
            self.assertEqual(devkit.main(['wizard']), 130)
        with patch('builtins.input', return_value='4'):
            self.assertEqual(devkit.main(['wizard']), 0)
    def test_nested_mismatch_and_immutable_sources(self):
        child=jar_bytes('nested',depends={'minecraft':'~26.2'})
        p=self.jar('original.jar',jar_bytes('parent',depends={'fabric-api':'*'},nested=child))
        before=p.read_bytes()
        report=dep.audit([p],minecraft='26.3',java=25,loader_version='0.19.5')
        self.assertEqual(report['mod_count'],2);self.assertEqual(len(report['issues']),2)
        out=dep.resolve([p],self.root/'deps',minecraft='26.3',java=25,loader_version='0.19.5',offline=True)
        self.assertEqual(out['state'],'unresolved');self.assertEqual(before,p.read_bytes())
    def test_invalid_metadata_and_empty_inventory(self):
        for modid in ('../escape','a/b','with space'):
            p=self.jar('bad.jar',jar_bytes(modid))
            with self.assertRaises(ValueError):dep.jar_inventory(p)
        with self.assertRaises(ValueError):dep.audit([],minecraft='26.3',java=25)
        p=self.root/'plain.jar'
        with zipfile.ZipFile(p,'w') as z:z.writestr('empty','')
        with self.assertRaises(ValueError):dep.audit([p],minecraft='26.3',java=25)
    def test_transitive_resolve_and_offline_lock_reuse(self):
        p=self.jar('parent.jar',jar_bytes('parent',depends={'first':'>=2 <3'}))
        first=jar_bytes('first','2.0.0',depends={'second':'^1.0.0','minecraft':'~26.3'})
        second=jar_bytes('second',depends={'minecraft':'~26.3'})
        blobs={'first':first,'second':second}
        def provider(url):
            modid=url.split('/project/')[1].split('/')[0]
            data=blobs[modid]
            return [{'id':modid+'-version','project_id':modid,'version_type':'release','date_published':'2026-09-23',
              'game_versions':['26.3'],'loaders':['fabric'],'files':[{'url':'https://example.test/'+modid,
              'size':len(data),'primary':True,'hashes':{'sha512':hashlib.sha512(data).hexdigest()}}]}]
        def download(url,dest,expected,**kwargs):
            data=blobs[url.rsplit('/',1)[1]]
            self.assertEqual(hashlib.sha512(data).hexdigest(),expected)
            dest.write_bytes(data);return dest
        with patch.object(dep,'get_json',side_effect=provider),patch.object(dep,'download_verified',side_effect=download):
            result=dep.resolve([p],self.root/'deps',minecraft='26.3',java=25,loader_version='0.19.5')
        self.assertEqual(result['state'],'complete');self.assertEqual(len(result['downloads']),2)
        with patch.object(dep,'get_json',side_effect=AssertionError('offline network')):
            result=dep.resolve([p],self.root/'deps',minecraft='26.3',java=25,loader_version='0.19.5',offline=True)
        self.assertEqual(result['state'],'complete')
    def test_provider_compatibility_overrides_broad_nested_claim(self):
        old=jar_bytes('nested','1.0.0',depends={'minecraft':'>=26.2'})
        p=self.jar('parent.jar',jar_bytes('parent',nested=old))
        new=jar_bytes('nested','2.0.0',depends={'minecraft':'~26.3'})
        def provider(url):
            if '/version_file/' in url:return {'project_id':'nested','game_versions':['26.2']}
            return [{'id':'target','project_id':'nested','game_versions':['26.3'],'loaders':['fabric'],
                     'files':[{'primary':True,'url':'https://example.test/new','hashes':{'sha512':hashlib.sha512(new).hexdigest()}}]}]
        def download(url,dest,expected,**kwargs):dest.write_bytes(new);return dest
        before=hashlib.sha256(p.read_bytes()).hexdigest()
        with patch.object(dep,'get_json',side_effect=provider),patch.object(dep,'download_verified',side_effect=download):
            result=dep.resolve([p],self.root/'deps',minecraft='26.3',java=25,loader_version='0.19.5')
        self.assertEqual(result['state'],'complete');self.assertEqual(result['downloads'][0]['version'],'2.0.0')
        self.assertEqual(hashlib.sha256(p.read_bytes()).hexdigest(),before)

if __name__=='__main__':unittest.main(verbosity=2)
