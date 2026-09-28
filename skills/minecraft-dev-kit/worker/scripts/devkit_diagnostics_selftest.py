#!/usr/bin/env python3
"""Regress actual offline-profile noise masking a later chunk Mixin failure."""
from pathlib import Path
import tempfile
from devkit_diagnostics import diagnose,native_failure


def main():
    noise='Caused by: MinecraftClientHttpException[type=HTTP_ERROR, status=401]\n[Render thread/INFO]: Loading game\n'
    actual='Caused by: org.spongepowered.asm.mixin.injection.throwables.InvalidInjectionException: Invalid descriptor on aoba.mixins.json:ClientChunkCacheMixin\n'
    timeout='java.lang.AssertionError: Timeout loading world\n'
    report=diagnose(noise+actual+timeout)
    assert report['family']=='mixin' and 'ClientChunkCacheMixin' in report['summary']
    assert diagnose(noise+'ShaderCompileException: Could not parse GLSL\n')['family']=='shader'
    assert diagnose(noise+'java.lang.NoSuchMethodError: exact.owner.method\n')['family']=='linkage'
    assert diagnose(timeout)['family']=='assertion'
    assert diagnose('')['family']=='unclassified'
    with tempfile.TemporaryDirectory() as raw:
        root=Path(raw);log=root/'run/game/logs/latest.log';log.parent.mkdir(parents=True);log.write_text(noise+actual)
        result=native_failure(root,timeout,'');assert result['family']=='mixin' and result['source']==str(log)
        assert log.read_text()==noise+actual
    print('Native failure ranking, exact Mixin root, shader/linkage, preserved full logs and empty-output controls PASS')
    return 0
if __name__=='__main__':raise SystemExit(main())
