#!/usr/bin/env python3
from __future__ import annotations

import json
import pathlib
import shutil
import subprocess
import tempfile

from access_rule_resolver import resolve_project as resolve_access
from classfile_symbol_index import build_index
from mixin_target_resolver import resolve_project as resolve_mixins
from packaged_linkage_audit import audit as audit_linkage
from reflection_surface_resolver import resolve_project as resolve_reflection


def write(path: pathlib.Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding='utf-8')


def javac(output: pathlib.Path, sources: list[pathlib.Path], classpath: list[pathlib.Path] | None = None) -> None:
    output.mkdir(parents=True, exist_ok=True)
    cmd = [shutil.which('javac') or 'javac']
    if classpath:
        cmd += ['-cp', ':'.join(map(str, classpath))]
    cmd += ['-d', str(output), *map(str, sources)]
    cp = subprocess.run(cmd, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if cp.returncode:
        raise AssertionError(cp.stderr or cp.stdout)


def blocker_ids(report: dict) -> set[str]:
    return {str(row.get('id')) for row in report.get('blockers') or []}


def main() -> int:
    if not shutil.which('javac'):
        raise AssertionError('javac is required')

    with tempfile.TemporaryDirectory(prefix='northpoint-semantic-migration-') as td:
        root = pathlib.Path(td)
        old_api_src, old_api_classes = root / 'old-api-src', root / 'old-api-classes'
        new_public_src, new_public_classes = root / 'new-public-src', root / 'new-public-classes'
        new_runtime_src, new_runtime_classes = root / 'new-runtime-src', root / 'new-runtime-classes'
        old_dep_src, old_dep_classes = root / 'old-dep-src', root / 'old-dep-classes'
        new_dep_src, new_dep_classes = root / 'new-dep-src', root / 'new-dep-classes'
        old_mod_src, old_mod_classes = root / 'old-mod-src', root / 'old-mod-classes'
        repaired_src, repaired_classes = root / 'repaired-src', root / 'repaired-classes'

        write(old_api_src / 'net/minecraft/ApiTarget.java',
              'package net.minecraft; public class ApiTarget { public long compute(int x){ return x; } }\n')
        write(new_public_src / 'net/minecraft/ApiTarget.java',
              'package net.minecraft; public class ApiTarget { public long compute(long x){ return x; } }\n')
        write(new_runtime_src / 'net/minecraft/ApiTarget.java',
              'package net.minecraft; public class ApiTarget { private long compute(long x){ return x; } }\n')
        write(old_dep_src / 'fixturedep/Helper.java',
              'package fixturedep; public class Helper { public static String decorate(int x){ return Integer.toString(x); } }\n')
        write(new_dep_src / 'fixturedep/Helper.java',
              'package fixturedep; public class Helper { public static String decorate(long x){ return Long.toString(x); } }\n')

        javac(old_api_classes, sorted(old_api_src.rglob('*.java')))
        javac(new_public_classes, sorted(new_public_src.rglob('*.java')))
        javac(new_runtime_classes, sorted(new_runtime_src.rglob('*.java')))
        javac(old_dep_classes, sorted(old_dep_src.rglob('*.java')))
        javac(new_dep_classes, sorted(new_dep_src.rglob('*.java')))

        write(old_mod_src / 'example/LegacyPort.java', '''package example;
import net.minecraft.ApiTarget;
import fixturedep.Helper;
public class LegacyPort {
  public static String run(ApiTarget target, int value){ return Helper.decorate((int)target.compute(value)); }
}
''')
        javac(old_mod_classes, sorted(old_mod_src.rglob('*.java')), [old_api_classes, old_dep_classes])

        target_index = build_index(new_runtime_classes, include_refs=True)
        dep_index = build_index(new_dep_classes, include_refs=True)
        broken = audit_linkage(old_mod_classes, [target_index, dep_index], prefixes=('net/minecraft/', 'fixturedep/'))
        broken_ids = blocker_ids(broken)
        assert 'unresolved-member-reference' in broken_ids, broken
        unresolved = broken.get('blockers') or []
        unresolved_text = json.dumps(unresolved)
        assert 'compute' in unresolved_text and 'decorate' in unresolved_text, broken

        write(repaired_src / 'example/LegacyPort.java', '''package example;
import net.minecraft.ApiTarget;
import fixturedep.Helper;
public class LegacyPort {
  public static String run(ApiTarget target, int value){ return Helper.decorate(target.compute((long)value)); }
}
''')
        javac(repaired_classes, sorted(repaired_src.rglob('*.java')), [new_public_classes, new_dep_classes])

        inaccessible = audit_linkage(repaired_classes, [target_index, dep_index], prefixes=('net/minecraft/', 'fixturedep/'))
        assert 'linkage-member-inaccessible' in blocker_ids(inaccessible), inaccessible

        widened = root / 'repaired-widened'
        shutil.copytree(repaired_classes, widened)
        write(widened / 'META-INF/accesstransformer.cfg', 'public net.minecraft.ApiTarget compute(J)J\n')
        linked = audit_linkage(widened, [target_index, dep_index], prefixes=('net/minecraft/', 'fixturedep/'))
        assert linked['status'] == 'PASS', linked

        surfaces = root / 'surfaces'
        write(surfaces / 'src/main/java/example/ApiMixin.java', '''package example;
@Mixin(targets = "net.minecraft.ApiTarget")
class ApiMixin {
  @Inject(method = "compute(J)J", at = @At("HEAD"))
  private void northpoint$compute() {}
}
''')
        write(surfaces / 'src/main/java/example/ReflectionHook.java', '''package example;
import net.minecraft.ApiTarget;
class ReflectionHook {
  void check() throws Exception { ApiTarget.class.getDeclaredMethod("compute", long.class); }
}
''')
        write(surfaces / 'src/main/resources/META-INF/accesstransformer.cfg',
              'public net.minecraft.ApiTarget compute(J)J\n')

        mixin = resolve_mixins(surfaces, target_index)
        access = resolve_access(surfaces, target_index)
        reflection = resolve_reflection(surfaces, target_index)
        assert not mixin.get('blockers'), mixin
        assert not access.get('blockers'), access
        assert not reflection.get('blockers'), reflection

        report = {
            'status': 'PASS',
            'broken_detected': sorted(broken_ids),
            'access_drift_detected': sorted(blocker_ids(inaccessible)),
            'repaired_linkage': linked['status'],
            'mixin_status': mixin['status'],
            'access_status': access['status'],
            'reflection_status': reflection['status'],
            'reflection_warnings': [row.get('id') for row in reflection.get('warnings') or []],
        }
        print(json.dumps(report, indent=2))
    print('Northpoint semantic migration self-test: PASS')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())