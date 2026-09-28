#!/usr/bin/env python3
"""Verified, per-user JDK provisioning. No administrator rights or global PATH edits."""
from __future__ import annotations
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import platform
import re
import shutil
import stat
import subprocess
import tarfile
import tempfile
import time
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, urlsplit
from urllib.request import Request, urlopen
import zipfile

from northpoint_execution import atomic_json, sha256_file, workspace_lock, new_run_id

USER_AGENT = 'Enderloom-Minecraft-Dev-Kit/8 (managed developer tooling)'


def cache_home() -> Path:
    return Path(os.environ.get('DEVKIT_CACHE', str(Path.home() / '.minecraft-dev-kit' / 'cache'))).expanduser().resolve()


def secure_url(url: str) -> str:
    parts = urlsplit(url)
    if parts.scheme != 'https' or not parts.hostname or parts.username or parts.password:
        raise ValueError('downloads require an HTTPS URL without embedded credentials')
    return url


def get_json(url: str, *, timeout: float = 30):
    with urlopen(Request(secure_url(url), headers={'User-Agent': USER_AGENT, 'Accept': 'application/json'}), timeout=timeout) as response:
        secure_url(response.url)
        return json.load(response)


def download_verified(url: str, destination: Path, expected: str, *, algorithm: str = 'sha256', size: int | None = None) -> Path:
    """Preserve an existing file until new complete bytes pass provider checksum and size."""
    secure_url(url)
    if algorithm not in {'sha256', 'sha512'} or not re.fullmatch(r'[a-fA-F0-9]{%d}' % (64 if algorithm == 'sha256' else 128), expected):
        raise ValueError('a complete SHA-256 or SHA-512 checksum is required')
    expected = expected.lower()
    def valid(path):
        if not path.is_file() or (size is not None and path.stat().st_size != size):
            return False
        h = hashlib.new(algorithm)
        with path.open('rb') as stream:
            for chunk in iter(lambda: stream.read(1024 * 1024), b''):
                h.update(chunk)
        return h.hexdigest() == expected
    destination.parent.mkdir(parents=True, exist_ok=True)
    if valid(destination):
        return destination
    fd, name = tempfile.mkstemp(prefix=destination.name + '.', suffix='.partial', dir=destination.parent)
    os.close(fd)
    partial = Path(name)
    try:
        for attempt in range(3):
            try:
                with urlopen(Request(url, headers={'User-Agent': USER_AGENT}), timeout=45) as response, partial.open('wb') as stream:
                    secure_url(response.url)
                    for chunk in iter(lambda: response.read(1024 * 1024), b''):
                        stream.write(chunk)
                    stream.flush(); os.fsync(stream.fileno())
                if not valid(partial):
                    raise ValueError('download checksum or size mismatch: ' + destination.name)
                os.replace(partial, destination)
                return destination
            except HTTPError as exc:
                if exc.code not in {408, 429, 500, 502, 503, 504} or attempt == 2:
                    raise
                time.sleep(min(float(exc.headers.get('Retry-After', '2')) if exc.headers.get('Retry-After', '2').isdigit() else 2, 30))
            except (URLError, TimeoutError, ConnectionError):
                if attempt == 2:
                    raise
                time.sleep(attempt + 1)
        raise RuntimeError('download did not complete')
    finally:
        partial.unlink(missing_ok=True)


def safe_extract(archive: Path, destination: Path) -> None:
    """Preflight every member; never follow archive links outside the private staging tree."""
    destination.mkdir(parents=True, exist_ok=True)
    def check(name):
        p = PurePosixPath(name)
        if '\x00' in name or '\\' in name or p.is_absolute() or '..' in p.parts or any(':' in part for part in p.parts):
            raise ValueError('unsafe archive member: ' + name)
        target = (destination / name).resolve()
        if not target.is_relative_to(destination.resolve()):
            raise ValueError('archive path escapes staging directory')
        return target
    if zipfile.is_zipfile(archive):
        with zipfile.ZipFile(archive) as source:
            for item in source.infolist():
                check(item.orig_filename)
                check(item.filename)
                if stat.S_ISLNK(item.external_attr >> 16):
                    raise ValueError('ZIP symbolic links are not accepted')
            source.extractall(destination)
            if os.name != 'nt':
                for item in source.infolist():
                    if not item.is_dir() and item.external_attr >> 16:
                        (destination / item.filename).chmod((item.external_attr >> 16) & 0o777)
    else:
        with tarfile.open(archive, 'r:*') as source:
            for item in source.getmembers():
                target = check(item.name)
                if item.isdev() or item.isfifo():
                    raise ValueError('archive contains special device')
                if item.issym() or item.islnk():
                    link = Path(item.linkname)
                    linked = (target.parent / link if item.issym() else destination / link).resolve()
                    if link.is_absolute() or not linked.is_relative_to(destination.resolve()):
                        raise ValueError('archive link escapes staging directory')
            source.extractall(destination, filter='data')


def java_pair(java: Path, major: int | None = None) -> dict | None:
    java = java.resolve()
    compiler = java.with_name('javac.exe' if os.name == 'nt' else 'javac')
    if not java.is_file() or not compiler.is_file():
        return None
    versions = []
    for binary in [java, compiler]:
        try:
            cp = subprocess.run([str(binary), '-version'], capture_output=True, text=True, timeout=15)
            match = re.search(r'(?:version\s+"?|javac\s+|openjdk\s+)(\d+)(?:\.(\d+))?', cp.stdout + '\n' + cp.stderr)
            value = int(match[2]) if match and match[1] == '1' and match[2] else int(match[1]) if match else 0
            if cp.returncode or value == 0:
                return None
            versions.append(value)
        except (OSError, subprocess.SubprocessError):
            return None
    if len(set(versions)) != 1 or (major is not None and versions[0] != major):
        return None
    return {'java_path': str(java), 'javac_path': str(compiler), 'java': versions[0],
            'java_sha256': sha256_file(java), 'javac_sha256': sha256_file(compiler)}


def target_java(minecraft: str) -> int:
    """Known release envelopes; unknown targets require authoritative metadata, not guesses."""
    parts = re.fullmatch(r'(\d+)\.(\d+)(?:\.(\d+))?', minecraft)
    if parts:
        major, minor, patch = (int(x or 0) for x in parts.groups())
        if major == 26 and 1 <= minor <= 3:
            return 25
        if major == 1:
            if minor < 17: return 8
            if minor == 17: return 16
            if minor < 20 or (minor == 20 and patch < 5): return 17
            if minor <= 21: return 21
    manifest = get_json('https://piston-meta.mojang.com/mc/game/version_manifest_v2.json')
    version = next((v for v in manifest['versions'] if v['id'] == minecraft), None)
    if version is None:
        raise ValueError('unknown Minecraft target: ' + minecraft)
    return int(get_json(version['url'])['javaVersion']['majorVersion'])


def ensure_jdk(major: int, *, root: Path | None = None, explicit: Path | None = None,
               offline: bool = False, managed_only: bool = False, refresh: bool = False) -> dict:
    if major < 8 or major > 100:
        raise ValueError('invalid Java major')
    if explicit:
        pair = java_pair(explicit, major)
        if not pair:
            raise ValueError(f'explicit JDK is missing or not Java {major}: {explicit}')
        return dict(pair, source='explicit')
    if not managed_only:
        candidates = []
        for key in (f'JAVA_HOME_{major}_X64', 'JAVA_HOME'):
            if os.environ.get(key): candidates.append(Path(os.environ[key]) / 'bin' / ('java.exe' if os.name == 'nt' else 'java'))
        if shutil.which('java'): candidates.append(Path(shutil.which('java')))
        for candidate in candidates:
            pair = java_pair(candidate, major)
            if pair: return dict(pair, source='installed')
    root = (root or cache_home()) / 'jdks'
    system = {'Windows':'windows', 'Darwin':'mac', 'Linux':'linux'}.get(platform.system())
    architecture = {'x86_64':'x64','AMD64':'x64','aarch64':'aarch64','arm64':'aarch64'}.get(platform.machine())
    if not system or not architecture:
        raise ValueError('no supported managed JDK for this OS/architecture')
    target = root / f'java-{major}-{system}-{architecture}'
    with workspace_lock(root / 'locks' / target.name):
        receipt_path = target / 'install.json'
        if receipt_path.is_file() and not refresh:
            receipt = json.loads(receipt_path.read_text(encoding='utf-8'))
            binary = (target / receipt['relative_java']).resolve()
            if not binary.is_relative_to(target.resolve()):
                raise ValueError('invalid managed JDK receipt path')
            pair = java_pair(binary, major)
            if pair and pair['java_sha256'] == receipt['java_sha256'] and pair['javac_sha256'] == receipt['javac_sha256']:
                return dict(pair, source='managed-cache', package=receipt['package'])
        if offline:
            raise RuntimeError(f'Java {major} is not cached; run setup once while online')
        query = urlencode({'architecture':architecture,'image_type':'jdk','os':system,'vendor':'eclipse','release_type':'ga'})
        assets = get_json(f'https://api.adoptium.net/v3/assets/latest/{major}/hotspot?{query}')
        if not isinstance(assets, list) or not assets:
            raise RuntimeError(f'Adoptium returned no supported Java {major} JDK')
        release = next((row for row in assets if row.get('binary',{}).get('image_type') == 'jdk'), None)
        if not release: raise RuntimeError('provider metadata contains no JDK image')
        package = release['binary']['package']
        archive = root / 'downloads' / (package['checksum'] + ('.zip' if system == 'windows' else '.tar.gz'))
        print(f'Provisioning Java {major}: {release.get("release_name", package["name"])}', flush=True)
        download_verified(package['link'], archive, package['checksum'], size=package.get('size'))
        staging = Path(tempfile.mkdtemp(prefix=target.name + '.', dir=root))
        try:
            safe_extract(archive, staging)
            binaries = list(staging.rglob('java.exe' if system == 'windows' else 'java'))
            valid = [(p, java_pair(p, major)) for p in binaries if p.parent.name == 'bin']
            valid = [(p, info) for p, info in valid if info]
            if len(valid) != 1:
                raise RuntimeError('extracted JDK did not pass java and javac version verification')
            binary, pair = valid[0]
            rel = binary.relative_to(staging).as_posix()
            atomic_json(staging / 'install.json', dict(pair, schema_version=1, relative_java=rel,
                        package={k:package[k] for k in ('name','link','checksum','size') if k in package}, release=release.get('release_name')))
            if target.exists():
                target.rename(root / (target.name + '.previous-' + new_run_id()))
            staging.rename(target)
            final = java_pair(target / rel, major)
            if not final: raise RuntimeError('installed JDK failed final validation')
            return dict(final, source='managed-install', package=package)
        finally:
            if staging.exists(): shutil.rmtree(staging)
