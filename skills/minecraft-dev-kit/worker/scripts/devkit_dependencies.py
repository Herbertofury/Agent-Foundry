#!/usr/bin/env python3
"""Read nested Fabric JAR requirements and install a verified, target-correct dependency closure."""
from __future__ import annotations
import hashlib
import io
import json
from pathlib import Path
import re
from urllib.parse import quote, urlencode
from urllib.error import HTTPError
import zipfile
from devkit_toolchains import get_json, download_verified
from northpoint_execution import atomic_json, sha256_file, workspace_lock


def _version(value: str):
    match = re.fullmatch(r'(\d+(?:\.\d+)*)(?:-([0-9A-Za-z.-]*))?(?:\+[0-9A-Za-z.-]+)?', value)
    if not match: return None
    main = tuple(map(int, match[1].split('.')))
    return main, match[2]


def _compare(left: str, right: str):
    a, b = _version(left), _version(right)
    if a is None or b is None: return None
    size = max(len(a[0]), len(b[0]), 3)
    x, y = a[0] + (0,)*(size-len(a[0])), b[0] + (0,)*(size-len(b[0]))
    if x != y: return (x > y) - (x < y)
    if a[1] == b[1]: return 0
    if a[1] is None: return 1
    if b[1] is None: return -1
    if a[1] == '': return -1
    if b[1] == '': return 1
    x, y = a[1].split('.'), b[1].split('.')
    for p, q in zip(x, y):
        if p == q: continue
        if p.isdigit() and q.isdigit(): return (int(p)>int(q))-(int(p)<int(q))
        if p.isdigit() != q.isdigit(): return -1 if p.isdigit() else 1
        return (p>q)-(p<q)
    return (len(x)>len(y))-(len(x)<len(y))


def satisfies(version: str, requirement) -> bool | None:
    """Three-state evaluation: unsupported constraints are unresolved, never accepted."""
    if isinstance(requirement, list):
        results = [satisfies(version, part) for part in requirement]
        return True if True in results else None if None in results else False
    if not isinstance(requirement, str): return None
    requirement = requirement.strip()
    if requirement in {'', '*'}: return True
    if '||' in requirement: return satisfies(version, requirement.split('||'))
    parts = requirement.split()
    if len(parts) > 1:
        results = [satisfies(version, part) for part in parts]
        return False if False in results else None if None in results else True
    match = re.fullmatch(r'(>=|<=|!=|>|<|=|~|\^)?([0-9A-Za-z.*+_-]+)', requirement)
    if not match: return None
    op, wanted = match[1] or '=', match[2]
    if '*' in wanted or re.search(r'(?:^|\.)[xX](?:\.|$)', wanted):
        prefix = re.split(r'(?:\*|[xX])', wanted)[0].rstrip('.')
        if op != '=' or not re.fullmatch(r'\d+(?:\.\d+)*', prefix): return None
        current = _version(version)
        return current[0][:len(prefix.split('.'))] == tuple(map(int,prefix.split('.'))) if current else None
    if op == '=' and version == wanted: return True
    comparison = _compare(version, wanted)
    if comparison is None: return False if op == '=' else None
    if op == '=': return comparison == 0
    if op == '!=': return comparison != 0
    if op == '>=': return comparison >= 0
    if op == '<=': return comparison <= 0
    if op == '>': return comparison > 0
    if op == '<': return comparison < 0
    # Fabric operators are same-major (^), same-major/minor (~), not npm's
    # special handling of zero-major versions. Empty prerelease is a lower bound.
    actual, base = _version(version)[0], _version(wanted)[0]
    actual += (0,) * max(0, 2-len(actual))
    base += (0,) * max(0, 2-len(base))
    return comparison >= 0 and actual[:2 if op == '~' else 1] == base[:2 if op == '~' else 1]



def jar_inventory(path: Path) -> list[dict]:
    rows, active = [], set()
    def visit(data: bytes, location: str, depth: int):
        digest = hashlib.sha256(data).hexdigest()
        if digest in active: raise ValueError('cyclic nested JAR: ' + location)
        if depth > 64: raise ValueError('nested JAR safety boundary exceeded; inventory remains incomplete')
        active.add(digest)
        try:
            with zipfile.ZipFile(io.BytesIO(data)) as archive:
                if 'fabric.mod.json' not in archive.namelist(): return
                metadata = json.loads(archive.read('fabric.mod.json'))
                if not isinstance(metadata, dict) or not isinstance(metadata.get('id'), str):
                    raise ValueError('invalid Fabric metadata: ' + location)
                if not re.fullmatch(r'[a-z][a-z0-9_-]{1,63}', metadata['id']):
                    raise ValueError('unsafe mod id: ' + str(metadata['id']))
                rows.append({'id': metadata['id'], 'version': str(metadata.get('version','')), 'path': location,
                             'sha256': digest, 'sha512': hashlib.sha512(data).hexdigest(), 'nested': depth > 0, 'metadata': metadata})
                for entry in metadata.get('jars', []):
                    name = entry.get('file','')
                    if not name or name.startswith('/') or '..' in Path(name).parts or '\\' in name or ':' in name:
                        raise ValueError('unsafe nested JAR path: ' + name)
                    visit(archive.read(name), location + '!/' + name, depth+1)
        finally: active.remove(digest)
    visit(path.read_bytes(), str(path.resolve()), 0)
    return rows


def audit(jars: list[Path], *, minecraft: str, java: int, loader_version: str | None = None) -> dict:
    if not jars: raise ValueError('no candidate JARs were supplied')
    inventories = [jar_inventory(jar) for jar in jars]
    if any(not rows for rows in inventories):
        raise ValueError('a supplied JAR has no Fabric metadata; choose its actual loader')
    rows = [row for inventory in inventories for row in inventory]
    groups = {}
    for row in rows: groups.setdefault(row['id'], []).append(row)
    chosen = {}
    for modid, candidates in groups.items():
        external = [row for row in candidates if not row['nested']]
        if len({row['sha256'] for row in external}) > 1:
            raise ValueError('conflicting top-level versions: ' + modid)
        pool = external or candidates
        selected = pool[0]
        for row in pool[1:]:
            comparison = _compare(row['version'], selected['version'])
            if comparison is None and row['version'] != selected['version']:
                raise ValueError('ambiguous nested versions: ' + modid)
            if comparison is not None and comparison > 0: selected = row
        chosen[modid] = selected
    available = {modid: row['version'] for modid,row in chosen.items()}
    available.update(minecraft=minecraft, java=str(java))
    if loader_version: available['fabricloader'] = loader_version
    for row in chosen.values():
        for alias in row['metadata'].get('provides', []): available[alias] = row['version']
    issues, optional = [], []
    for row in chosen.values():
        meta = row['metadata']
        for modid, constraint in meta.get('depends', {}).items():
            current = available.get(modid)
            result = satisfies(current,constraint) if current else None
            if result is not True:
                issues.append({'owner':row['id'],'dependency':modid,'constraint':constraint,'installed':current,
                               'kind':'missing' if current is None else 'incompatible' if result is False else 'unresolved-constraint',
                               'source':row['path']})
        for modid, constraint in meta.get('breaks', {}).items():
            if modid in available and satisfies(available[modid],constraint) is not False:
                issues.append({'owner':row['id'],'dependency':modid,'constraint':constraint,'installed':available[modid],
                               'kind':'conflict','source':row['path']})
        for relation in ('recommends','suggests'):
            for modid,constraint in meta.get(relation,{}).items():
                if modid not in available: optional.append({'owner':row['id'],'dependency':modid,'constraint':constraint,'relation':relation})
    return {'schema_version':1,'minecraft':minecraft,'java':java,'loader':'fabric','loader_version':loader_version,
            'state':'complete' if not issues else 'unresolved','jar_count':len(jars),'mod_count':len(chosen),
            'mods':rows,'selected':{key:row['path'] for key,row in chosen.items()},'issues':issues,'optional':optional}


def resolve(jars: list[Path], output: Path, *, minecraft: str, java: int,
            loader_version: str, offline: bool = False, projects: dict | None = None, refresh_nested: bool = True) -> dict:
    """Fetch required mods only; verify the downloaded mod ID and all target requirements.

    Files are installed into a separate managed directory. Originals, embedded JARs,
    optional providers and user instances are never deleted or edited.
    """
    projects = projects or {}
    output = output.resolve(); output.mkdir(parents=True,exist_ok=True)
    with workspace_lock(output):
        managed = output / 'mods'; managed.mkdir(exist_ok=True)
        lockpath = output / 'dependency-lock.json'
        prior = json.loads(lockpath.read_text()) if lockpath.is_file() else {}
        resolved = {}
        for row in prior.get('downloads',[]):
            path = (managed / row['file']).resolve()
            if path.is_relative_to(managed.resolve()) and path.is_file() and sha256_file(path) == row['sha256']:
                resolved[row['id']] = dict(row, path=path)
        attempted = set()
        catalog_path = output / 'provider-compatibility.json'
        catalog = json.loads(catalog_path.read_text()) if catalog_path.is_file() else {}
        refresh = {}
        if refresh_nested:
            for jar in jars:
                for row in jar_inventory(jar):
                    if not row['nested']: continue
                    key = row['sha512']
                    record = catalog.get(key)
                    if record is None and not offline:
                        try:
                            record = get_json('https://api.modrinth.com/v2/version_file/' + key + '?algorithm=sha512')
                        except HTTPError as exc:
                            if exc.code != 404: raise
                            record = {'state':'unresolved-provider', 'id':row['id']}
                        catalog[key] = record
                        atomic_json(catalog_path, catalog)
                    if record and record.get('game_versions') and minecraft not in record['game_versions']:
                        refresh[row['id']] = {'owner':row['id'], 'dependency':row['id'], 'constraint':'*',
                            'source':row['path'], 'kind':'provider-target-mismatch', 'source_versions':record['game_versions']}
                        projects.setdefault(row['id'], record['project_id'])
        while True:
            report = audit(jars + [row['path'] for row in resolved.values()],minecraft=minecraft,java=java,loader_version=loader_version)
            needed = [issue for issue in report['issues'] if issue['dependency'] not in {'minecraft','java','fabricloader'} and issue['kind'] in {'missing','incompatible'}]
            needed.extend(issue for key,issue in refresh.items() if key not in resolved)
            constraints = {}
            for row in report['mods']:
                if report['selected'].get(row['id']) != row['path']: continue
                for modid,constraint in row['metadata'].get('depends',{}).items():
                    constraints.setdefault(modid, []).append(constraint)
            # A top-level, compatible newer mod can supersede an incompatible nested candidate.
            for issue in report['issues']:
                if issue['dependency'] == 'minecraft' and '!/' in issue['source']:
                    needed.append(dict(issue, dependency=issue['owner'], constraint='*'))
            progress = False
            for issue in needed:
                modid = issue['dependency']
                if not re.fullmatch(r'[a-z][a-z0-9_-]{1,63}', modid):
                    raise ValueError('unsafe dependency mod id: ' + modid)
                # Never replace a user's explicit top-level mod behind their back.
                if any(row['id'] == modid and not row['nested'] and row['path'] in {str(j.resolve()) for j in jars} for row in report['mods']):
                    continue
                required = constraints.get(modid, [issue['constraint']])
                key = (modid, json.dumps(required,sort_keys=True))
                if key in attempted or offline: continue
                attempted.add(key)
                project = projects.get(modid, modid.replace('_','-'))
                query = urlencode({'loaders':json.dumps(['fabric']),'game_versions':json.dumps([minecraft])})
                try:
                    versions = get_json('https://api.modrinth.com/v2/project/' + quote(project,safe='') + '/version?' + query)
                except HTTPError as exc:
                    if exc.code == 404:
                        issue['resolution_error'] = 'provider project unresolved; supply projects mapping';continue
                    raise
                if not isinstance(versions,list): raise ValueError('invalid Modrinth version response')
                versions.sort(key=lambda v:(v.get('version_type')=='release',v.get('date_published','')),reverse=True)
                for version in versions:
                    if minecraft not in version.get('game_versions',[]) or 'fabric' not in version.get('loaders',[]):continue
                    files = version.get('files',[])
                    file = next((f for f in files if f.get('primary')), files[0] if len(files)==1 else None)
                    if not file: continue
                    hashes = file.get('hashes',{})
                    algorithm = 'sha512' if hashes.get('sha512') else 'sha256'
                    checksum = hashes.get(algorithm)
                    if not checksum: continue
                    path = managed / (modid + '-' + checksum[:16] + '.jar')
                    download_verified(file['url'],path,checksum,algorithm=algorithm,size=file.get('size'))
                    inventory = jar_inventory(path)
                    entry = next((row for row in inventory if not row['nested'] and (row['id']==modid or modid in row['metadata'].get('provides',[]))),None)
                    if not entry or not all(satisfies(entry['version'],constraint) is True for constraint in required): continue
                    if satisfies(minecraft,entry['metadata'].get('depends',{}).get('minecraft','*')) is not True:continue
                    resolved[modid] = {'id':modid,'file':path.name,'path':path,'version':entry['version'],
                                       'sha256':sha256_file(path),'project_id':version['project_id'],'version_id':version['id'],'url':file['url']}
                    progress = True;break
            if not progress:
                report['issues'].extend(issue for key,issue in refresh.items() if key not in resolved)
                if report['issues']: report['state'] = 'unresolved'
                break
        report['downloads'] = [{k:str(v) if isinstance(v,Path) else v for k,v in row.items() if k!='path'} for row in resolved.values()]
        report['input_sha256'] = {str(jar.resolve()):sha256_file(jar) for jar in jars}
        atomic_json(lockpath,report)
        return report
