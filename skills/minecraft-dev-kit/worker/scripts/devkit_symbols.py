#!/usr/bin/env python3
"""Export exact cached Minecraft bytecode signatures for runtime failure repair."""
from __future__ import annotations
import argparse
import hashlib
import shutil
from urllib.request import Request, urlopen
import json
from pathlib import Path
import re
import subprocess
import zipfile
from devkit_toolchains import ensure_jdk, get_json, secure_url, USER_AGENT
from northpoint_execution import atomic_json, sha256_file


def capture(workspace: Path, minecraft: str, output: Path, download: bool = False) -> dict:
    output.mkdir(parents=True, exist_ok=True)
    roots = set()
    for path in workspace.rglob('*.txt'):
        if 'commands' not in path.parts: continue
        text = path.read_text(encoding='utf-8', errors='replace')
        roots.update(re.findall(r'Mixin transformation of ([A-Za-z0-9_.$]+) failed', text))
    roots.update({'net.minecraft.client.player.LocalPlayer','net.minecraft.client.multiplayer.ClientPacketListener'})
    owners_file = Path(__file__).resolve().parents[1]/'references/native-mixin-owners-26.3.json'
    if owners_file.is_file():
        roots.update(json.loads(owners_file.read_text())['owners'])
    jdk = ensure_jdk(25)
    javap = Path(jdk['java_path']).with_name('javap.exe' if Path(jdk['java_path']).suffix == '.exe' else 'javap')
    cache = Path.home()/'.gradle/caches/fabric-loom'
    candidates = []
    if download:
        manifest = get_json('https://piston-meta.mojang.com/mc/game/version_manifest_v2.json')
        version = next((row for row in manifest['versions'] if row['id'] == minecraft), None)
        if not version: raise ValueError('Minecraft version was not found: ' + minecraft)
        metadata = get_json(version['url']); client = metadata['downloads']['client']
        target = output / 'official-client.jar'
        with urlopen(Request(secure_url(client['url']), headers={'User-Agent': USER_AGENT}), timeout=60) as response, target.open('wb') as stream:
            secure_url(response.url); shutil.copyfileobj(response, stream)
        digest = hashlib.sha1(target.read_bytes()).hexdigest()
        if digest != client['sha1'] or target.stat().st_size != client['size']:
            raise ValueError('official client did not match Mojang metadata')
        candidates.append(target)
    for path in cache.rglob('*.jar'):
        try:
            with zipfile.ZipFile(path) as jar:
                if 'version.json' not in jar.namelist(): continue
                metadata=json.loads(jar.read('version.json'))
                if metadata.get('id') != minecraft: continue
                entries=set(jar.namelist())
                if any(owner.replace('.','/')+'.class' in entries for owner in roots): candidates.append(path)
        except (OSError,zipfile.BadZipFile,ValueError): continue
    report={'minecraft':minecraft,'classes':[], 'missing':[]}
    for owner in sorted(roots):
        entry=owner.replace('.','/')+'.class'
        found=None
        for path in candidates:
            with zipfile.ZipFile(path) as jar:
                if entry not in jar.namelist(): continue
                data=jar.read(entry);target=output/'classes'/entry;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(data)
                cp=subprocess.run([str(javap),'-p','-c','-s','-classpath',str(output/'classes'),owner],text=True,capture_output=True,timeout=30)
                textfile=output/(owner+'.javap.txt');textfile.write_text(cp.stdout+'\n'+cp.stderr,encoding='utf-8')
                found={'owner':owner,'minecraft_jar_sha256':sha256_file(path),'class_sha256':sha256_file(target),'javap_exit':cp.returncode,'text':textfile.name}
                target.unlink()
                break
        if found:report['classes'].append(found)
        else:report['missing'].append(owner)
    if download: (output/'official-client.jar').unlink(missing_ok=True)
    atomic_json(output/'symbols.json',report)
    return report

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--workspace',type=Path,required=True);p.add_argument('--minecraft',default='26.3');p.add_argument('--output',type=Path,required=True);p.add_argument('--download',action='store_true')
    a=p.parse_args();result=capture(a.workspace,a.minecraft,a.output,a.download);print(json.dumps(result,indent=2))
    raise SystemExit(1 if result['missing'] or any(row['javap_exit'] for row in result['classes']) else 0)
