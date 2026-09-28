#!/usr/bin/env python3
"""Real compiler/runner proof promotion with an explicitly simulated native receipt.
Native Minecraft itself is exercised separately by devkit-native-ci.yml.
"""
from __future__ import annotations
import contextlib
import io
import json
import os
from pathlib import Path
import platform
import shutil
import tempfile
from unittest.mock import patch
import zipfile
import devkit
import devkit_native as native
from devkit_toolchains import java_pair
from northpoint_execution import atomic_json, sha256_file
from northpoint_production_driver_selftest import fixture


def main() -> int:
    from devkit_native_restart_selftest import main as restart_tests
    assert restart_tests()==0
    from devkit_diagnostics_selftest import main as diagnostic_tests
    assert diagnostic_tests()==0
    root=Path(tempfile.mkdtemp(prefix='devkit-resume-',dir=os.environ.get('RUNNER_TEMP'))).resolve()
    project=root/'project';fixture(project)
    cfg=json.loads((project/'northpoint.project.json').read_text());cfg['runtime']={'required':True}
    atomic_json(project/'northpoint.project.json',cfg)
    workspace=root/'session';workspace.mkdir()
    java=Path(shutil.which('java')).resolve();pair=java_pair(java)
    cell={'id':'mc-26.3-fabric','minecraft':'26.3','loader':'fabric','java':pair['java'],'java_path':str(java),'primary':True}
    atomic_json(workspace/'manifest.json',{'schema_version':1,'project_root':str(project),'primary_cell':cell['id'],'cells':[cell],
                                        'config':{'zero_loss':True},'native_verify':True})
    calls=[]
    def simulated(artifact, directory, **kwargs):
        calls.append(sha256_file(artifact));directory.mkdir(parents=True,exist_ok=True)
        atomic_json(directory/'dependencies/dependency-lock.json',{'downloads':[]})
        shots=[]
        for name in ['first.png','reopened.png','restarted.png']:
            image=directory/name;image.write_bytes(b'UNIT-TEST-NOT-A-REAL-SCREENSHOT')
            shots.append({'path':str(image),'sha256':sha256_file(image)})
        proof={'state':'runtime-smoke-verified','artifact_sha256':sha256_file(artifact),'world_reopened':True,'client_server_sync':True,'process_restart':True,'first_process_id':101,'restart_process_id':202}
        proof_file=directory/'devkit-runtime-proof.json';atomic_json(proof_file,proof)
        result={'proof':proof,'evidence_files':[{'path':str(proof_file),'sha256':sha256_file(proof_file)}],'state':'runtime-smoke-verified','artifact_sha256':sha256_file(artifact),
                'verifier_sha256':native.verifier_fingerprint(),'platform':[platform.system(),platform.machine()],
                'jdk':pair,'dependency_lock_sha256':sha256_file(directory/'dependencies/dependency-lock.json'),
                'screenshots':shots,'coverage':['SIMULATED-RECEIPT-ORCHESTRATION-ONLY'],
                'not_proven':['MINECRAFT-NOT-RUN-IN-THIS-UNIT-TEST']}
        atomic_json(directory/'native-result.json',result);return result
    with contextlib.redirect_stdout(io.StringIO()):
        code=devkit.run_workspace(workspace,90,offline=True)
        assert code in {2,3},code
        before=devkit.status(workspace);assert not before['all_passed']
        assert before['cells'][0]['state']=='runtime-unverified',before
        assert before['cells'][0]['attempts']==1
        with patch.object(native,'verify',side_effect=simulated):
            assert devkit.verify_workspace(workspace,90,offline=True)==0
            after=devkit.status(workspace);assert after['all_passed']
            assert after['cells'][0]['attempts']==1 and after['last_run']['built']==[]
            assert devkit.main(['resume','--workspace',str(workspace),'--offline','--timeout','90'])==0
            assert len(calls)==1,'unchanged valid proof reran native verification'
            (workspace/'native/first.png').write_bytes(b'changed')
            assert not devkit.status(workspace)['all_passed'],'tampered proof advertised success'
            assert devkit.main(['resume','--workspace',str(workspace),'--offline','--timeout','90'])==0
            assert len(calls)==2,'tampered native evidence was reused'
            (workspace/'native/devkit-runtime-proof.json').write_text('{}')
            assert not devkit.status(workspace)['all_passed'],'modified proof file advertised success'
            assert devkit.main(['resume','--workspace',str(workspace),'--offline','--timeout','90'])==0
            assert len(calls)==3,'modified proof file was reused'
        package=root/'candidate-and-evidence.zip';devkit.package(workspace,package)
        with zipfile.ZipFile(package) as archive:
            assert archive.testzip() is None
            assert json.loads(archive.read('VERIFICATION.json'))['all_passed']
            assert 'native/dependencies/dependency-lock.json' in archive.namelist()
            assert 'runtime-proofs.json' in archive.namelist()
        artifact=Path(devkit.status(workspace)['cells'][0]['artifact']['path'])
        assert 'productionRuntimeMods fabricApi.module("fabric-client-gametest-api-v1", project.fabric_api_version)' in native.GRADLE
        template=root/'template';template.mkdir()
        (template/'gradle.properties').write_text('minecraft_version=26.3\n')
        (template/'build.gradle').write_text('// fixture\n')
        probe=native.prepare(template,artifact,root/'probe-check',{'downloads':[]},root/'dependencies')
        metadata=json.loads((probe/'src/gametest/resources/fabric.mod.json').read_text())
        assert metadata['depends']['fabric-client-gametest-api-v1']=='*'
        artifact.write_bytes(artifact.read_bytes()+b'corrupt')
        assert not devkit.status(workspace)['all_passed']
    print(json.dumps({'status':'PASS','workspace':str(root),'native_scope':'SIMULATED-RECEIPT-ONLY',
                      'actual_javac_and_runner':True,'native_reuse_calls':len(calls),
                      'cases':['runtime-unverified-not-complete','sha-bound-promotion-without-rebuild',
                               'automatic-resume','proof-reuse','tampered-evidence-reverify','package','candidate-corruption',
                               'production-test-executor-required']},indent=2))
    return 0
if __name__=='__main__':raise SystemExit(main())
