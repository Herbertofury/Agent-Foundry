#!/usr/bin/env python3
"""Select actionable native failure context without discarding the full logs.

An early expected offline-profile 401 must not hide a later Mixin/linkage error.
Priorities choose an excerpt only; complete command and game logs stay on disk.
"""
from __future__ import annotations
from pathlib import Path
import re

PATTERNS = [
    ('mixin', r'InvalidInjectionException:|InvalidMixinException:|Critical injection failure|@Shadow .* was not located|InvalidAccessorException:'),
    ('linkage', r'(?:NoSuchMethodError|NoSuchFieldError|AbstractMethodError|IllegalAccessError|IncompatibleClassChangeError|NoClassDefFoundError):'),
    ('shader', r'ShaderCompileException:|SPIR-V requires|ERROR: .*GLSL|Couldn.t compile pipeline'),
    ('dependency', r'Incompatible mods found|ModResolutionException:|requires version .*which is missing'),
    ('assertion', r'(?:java\.lang\.)?AssertionError:|Client gametests failed with an exception'),
    ('compiler', r'\.java:\d+: error:|Compilation failed|Could not resolve all files for configuration'),
    ('runtime', r'(?:Caused by:|Exception in thread|\* What went wrong:)'),
]


def diagnose(text: str) -> dict:
    lines = re.sub(r'\x1b\[[0-9;]*[A-Za-z]', '', text).splitlines()
    for family, pattern in PATTERNS:
        match = next((index for index,line in enumerate(lines) if re.search(pattern,line)), None)
        if match is not None:
            return {'family':family, 'summary':lines[match].strip(), 'line':match+1,
                    'context':'\n'.join(lines[max(0,match-2):match+34])}
    return {'family':'unclassified', 'summary':lines[-1] if lines else 'process returned no diagnostic output',
            'line':max(1,len(lines)), 'context':'\n'.join(lines[-40:])}


def native_failure(probe: Path, stdout: str, stderr: str) -> dict:
    sources = [('command-output', stdout+'\n'+stderr)]
    for name in ['latest.log', 'debug.log']:
        for path in sorted((probe/'run').rglob(name)):
            sources.append((str(path), path.read_text(encoding='utf-8',errors='replace')))
    for path in sorted((probe/'run').rglob('crash-*.txt')):
        sources.append((str(path),path.read_text(encoding='utf-8',errors='replace')))
    rank={family:index for index,(family,_) in enumerate(PATTERNS)}
    rows=[dict(diagnose(text),source=source) for source,text in sources]
    return min(rows,key=lambda row:rank.get(row['family'],len(rank)))
