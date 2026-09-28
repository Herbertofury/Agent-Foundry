#!/usr/bin/env python3
"""Production-JAR native Fabric 26.3 world/sync/save-reopen verification, not mocked QA."""
from __future__ import annotations
import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import re
import shutil
import sys
import tempfile
from urllib.request import Request, urlopen
from devkit_dependencies import jar_inventory, resolve
from devkit_toolchains import ensure_jdk, get_json, safe_extract, secure_url, USER_AGENT
from northpoint_execution import atomic_json, new_run_id, run_logged, sha256_file, workspace_lock

GRADLE = '''
// DEVKIT_NATIVE_PROBE_V8 -- independent of the original mod source.
fabricApi {
  configureTests {
    createSourceSet = true
    modId = "devkit-runtime-probe"
    enableGameTests = false
    enableClientGameTests = true
    eula = true
  }
}
tasks.register("devkitProbeJar", Jar) {
  archiveClassifier = "gametest"
  from sourceSets.gametest.output
}
dependencies {
  productionRuntimeMods files("candidate.jar")
  productionRuntimeMods fabricApi.module("fabric-client-gametest-api-v1", project.fabric_api_version)
  productionRuntimeMods fileTree("verified-dependencies") { include "*.jar" }
}
tasks.register("devkitNativeTest", net.fabricmc.loom.task.prod.ClientProductionRunTask) {
  mods.from(tasks.named("devkitProbeJar"))
  runDir = file("run/devkit-native")
  jvmArgs.add("-Dfabric.client.gametest")
  jvmArgs.add("--enable-native-access=ALL-UNNAMED")
  useXVFB = System.getProperty("os.name").toLowerCase().contains("linux") && System.getenv("DISPLAY") == null
}
'''

JAVA = '''package devkit;
import java.nio.file.Files;
import java.nio.file.Path;
import java.security.MessageDigest;
import java.util.HexFormat;
import java.util.concurrent.atomic.AtomicReference;
import net.fabricmc.loader.api.FabricLoader;
import net.fabricmc.fabric.api.client.gametest.v1.FabricClientGameTest;
import net.fabricmc.fabric.api.client.gametest.v1.context.ClientGameTestContext;
import net.fabricmc.fabric.api.client.gametest.v1.context.TestSingleplayerContext;
import net.fabricmc.fabric.api.client.gametest.v1.world.TestWorldSave;
import net.minecraft.core.BlockPos;
import net.minecraft.world.level.block.Blocks;
public final class RuntimeProbe implements FabricClientGameTest {
  public void runTest(ClientGameTestContext context) {
    try {
      var mod = FabricLoader.getInstance().getModContainer("EXPECTED_MOD").orElseThrow();
      boolean exact = false;
      for (Path origin : mod.getOrigin().getPaths()) {
        if (Files.isRegularFile(origin)) {
          String hash = HexFormat.of().formatHex(MessageDigest.getInstance("SHA-256").digest(Files.readAllBytes(origin)));
          if (hash.equals("EXPECTED_SHA")) exact = true;
        }
      }
      if (!exact) throw new AssertionError("runtime did not load the exact candidate SHA-256");
      AtomicReference<BlockPos> marker = new AtomicReference<>();
      TestWorldSave save;
      try (TestSingleplayerContext world = context.worldBuilder().create()) {
        world.getConnection().waitForChunksRender();
        world.getServer().runOnServer(server -> {
          BlockPos pos = world.getConnection().getServerPlayer().blockPosition().offset(2, 0, 2);
          marker.set(pos);
          world.getConnection().getServerLevel().setBlock(pos, Blocks.GOLD_BLOCK.defaultBlockState(), 3);
        });
        context.waitTick();
        world.getConnection().waitForClientboundPackets();
        context.runOnClient(client -> {
          if (client.player == null || client.level == null) throw new AssertionError("no live client player/level");
          if (!client.level.getBlockState(marker.get()).is(Blocks.GOLD_BLOCK)) throw new AssertionError("server block did not synchronize");
        });
        context.takeScreenshot("devkit-EXPECTED_MOD-integrated-world");
        save = world.getWorldSave();
        System.out.println("DEVKIT_NATIVE_WORLD_READY:EXPECTED_MOD");
      }
      System.out.println("DEVKIT_NATIVE_WORLD_CLOSED:EXPECTED_MOD");
      try (TestSingleplayerContext reopened = save.open()) {
        reopened.getConnection().waitForChunksRender();
        reopened.getServer().runOnServer(server -> {
          if (!reopened.getConnection().getServerLevel().getBlockState(marker.get()).is(Blocks.GOLD_BLOCK))
            throw new AssertionError("saved marker did not persist on the authoritative server");
        });
        context.runOnClient(client -> {
          if (!client.level.getBlockState(marker.get()).is(Blocks.GOLD_BLOCK)) throw new AssertionError("reopened client lost marker");
        });
        context.takeScreenshot("devkit-EXPECTED_MOD-reopened-world");
        System.out.println("DEVKIT_NATIVE_WORLD_REOPENED:EXPECTED_MOD");
      }
      Files.writeString(Path.of("devkit-runtime-proof.json"), "{\\"state\\":\\"runtime-smoke-verified\\",\\"artifact_sha256\\":\\"EXPECTED_SHA\\",\\"modid\\":\\"EXPECTED_MOD\\",\\"world_reopened\\":true,\\"client_server_sync\\":true}");
      System.out.println("DEVKIT_NATIVE_PROOF_COMPLETE:EXPECTED_MOD");
    } catch (Exception error) { throw new RuntimeException(error); }
  }
}
'''


from devkit_native_restart import extend_probe, run_phases, valid_restart
JAVA, GRADLE = extend_probe(JAVA, GRADLE)


def _download_template(root: Path) -> Path:
    metadata=get_json('https://api.github.com/repos/FabricMC/fabric-example-mod/commits/26.3')
    sha=metadata['sha']
    if not re.fullmatch(r'[0-9a-f]{40}',sha):raise ValueError('invalid template commit')
    archive=root/'template.zip'
    url='https://api.github.com/repos/FabricMC/fabric-example-mod/zipball/'+sha
    with urlopen(Request(url,headers={'User-Agent':USER_AGENT}),timeout=60) as response,archive.open('wb') as stream:
        secure_url(response.url);shutil.copyfileobj(response,stream)
    safe_extract(archive,root/'template-source')
    candidates=list((root/'template-source').glob('*/build.gradle'))
    if len(candidates)!=1:raise ValueError('template source did not contain one unambiguous build')
    atomic_json(root/'template-origin.json',{'repository':'FabricMC/fabric-example-mod','commit':sha,
                'archive_sha256':sha256_file(archive),'url':url})
    return candidates[0].parent


def prepare(template: Path, artifact: Path, root: Path, dependencies: dict, dependencies_root: Path) -> Path:
    original_hash=sha256_file(artifact)
    inventory=jar_inventory(artifact)
    primary=next(row for row in inventory if not row['nested'])
    probe=root/'probe'
    if probe.exists():raise ValueError('native probe workspace already exists')
    shutil.copytree(template,probe,ignore=shutil.ignore_patterns('.git','.gradle','build','run'))
    properties=(probe/'gradle.properties').read_text()
    if not re.search(r'^minecraft_version\s*=\s*26\.3\s*$',properties,re.M):
        raise ValueError('native template must target exactly Minecraft 26.3')
    shutil.copyfile(artifact,probe/'candidate.jar')
    depsdir=probe/'verified-dependencies';depsdir.mkdir()
    for row in dependencies['downloads']:
        source=(dependencies_root/'mods'/row['file']).resolve()
        if not source.is_relative_to(dependencies_root.resolve()) or sha256_file(source)!=row['sha256']:
            raise ValueError('dependency lock bytes changed: '+row['file'])
        shutil.copyfile(source,depsdir/row['file'])
    with (probe/'build.gradle').open('a',encoding='utf-8') as f:f.write(GRADLE)
    path=probe/'src/gametest/java/devkit/RuntimeProbe.java';path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(JAVA.replace('EXPECTED_MOD',primary['id']).replace('EXPECTED_SHA',original_hash),encoding='utf-8')
    meta=probe/'src/gametest/resources/fabric.mod.json';meta.parent.mkdir(parents=True,exist_ok=True)
    atomic_json(meta,{'schemaVersion':1,'id':'devkit-runtime-probe','version':'1.0.0','environment':'client',
                     'entrypoints':{'fabric-client-gametest':['devkit.RuntimeProbe']},
                     'depends':{'fabric-client-gametest-api-v1':'*'}})
    return probe


def verifier_fingerprint() -> str:
    digest=hashlib.sha256()
    for name in ['devkit_native.py','devkit_native_restart.py','devkit_diagnostics.py','devkit_dependencies.py','devkit_toolchains.py','northpoint_execution.py']:
        path=Path(__file__).with_name(name)
        digest.update(name.encode());digest.update(path.read_bytes().replace(b'\r\n',b'\n'))
    return digest.hexdigest()


def reusable_proof(workspace: Path, artifact: Path, java_path: Path) -> dict | None:
    path=workspace/'native-result.json'
    if not path.is_file():return None
    try:
        result=json.loads(path.read_text())
        if result.get('state')!='runtime-smoke-verified' or result.get('artifact_sha256')!=sha256_file(artifact):return None
        if result.get('verifier_sha256')!=verifier_fingerprint() or result.get('platform')!=[platform.system(),platform.machine()]:return None
        if result.get('jdk',{}).get('java_sha256')!=sha256_file(java_path):return None
        lock=workspace/'dependencies/dependency-lock.json'
        if sha256_file(lock)!=result.get('dependency_lock_sha256'):return None
        for row in json.loads(lock.read_text()).get('downloads',[]):
            dependency=(workspace/'dependencies/mods'/row['file']).resolve()
            if not dependency.is_relative_to((workspace/'dependencies/mods').resolve()) or sha256_file(dependency)!=row['sha256']:return None
        if not valid_restart(result.get('proof', {}), result['artifact_sha256']):return None
        if len(result.get('screenshots',[]))<3:return None
        evidence=result.get('evidence_files',[])
        if not evidence or not any(Path(row['path']).name=='devkit-runtime-proof.json' for row in evidence):return None
        for row in evidence:
            item=Path(row['path']).resolve()
            if not item.is_relative_to(workspace.resolve()) or sha256_file(item)!=row['sha256']:return None
            if item.name=='devkit-runtime-proof.json' and json.loads(item.read_text())!=result['proof']:return None
        for row in result['screenshots']:
            image=Path(row['path']).resolve()
            if not image.is_relative_to(workspace.resolve()) or sha256_file(image)!=row['sha256']:return None
        return result
    except (OSError,ValueError,KeyError):return None


def verify(artifact: Path, workspace: Path, *, template: Path | None=None, timeout: int=900,
           offline: bool=False, java_path: Path | None=None) -> dict:
    artifact=artifact.resolve();workspace=workspace.resolve()
    with workspace_lock(workspace):
        run=workspace/'runs'/new_run_id();run.mkdir(parents=True)
        result={'schema_version':1,'state':'running','artifact_sha256':sha256_file(artifact),'artifact_path':str(artifact),
                'minecraft':'26.3','loader':'fabric','run':str(run),
                'verifier_sha256':verifier_fingerprint(),'platform':[platform.system(),platform.machine()],
                'coverage':[], 'required_coverage':['exact-production-JAR','client-render','integrated-server','block-network-sync','world-save-reopen','independent-JVM-restart'],
                'not_proven':['exhaustive-mod-gameplay','online-multiplayer','hardware-GPU-performance']}
        atomic_json(workspace/'native-result.json',result)
        try:
            jdk=ensure_jdk(25,explicit=java_path,offline=offline)
            if template is None:
                if offline:raise RuntimeError('offline native verification needs --template with a cached source template')
                template=_download_template(run)
            properties=(template/'gradle.properties').read_text()
            match=re.search(r'^loader_version\s*=\s*(\S+)',properties,re.M)
            if not match:raise ValueError('template loader version is missing')
            dependencies=resolve([artifact],workspace/'dependencies',minecraft='26.3',java=25,
                                 loader_version=match[1],offline=offline)
            if dependencies['state']!='complete':
                raise RuntimeError('dependency closure unresolved: ' + json.dumps(dependencies['issues']) + '; see dependencies/dependency-lock.json')
            probe=prepare(template,artifact,run,dependencies,workspace/'dependencies')
            env=dict(os.environ,JAVA_HOME=str(Path(jdk['java_path']).parent.parent))
            env['PATH']=str(Path(jdk['java_path']).parent)+os.pathsep+env.get('PATH','')
            if os.name!='nt' and not env.get('DISPLAY'):
                env.setdefault('LIBGL_ALWAYS_SOFTWARE','1');env.setdefault('ALSOFT_DRIVERS','null')
            wrapper=probe/('gradlew.bat' if os.name=='nt' else 'gradlew')
            if os.name!='nt':wrapper.chmod(wrapper.stat().st_mode|0o111)
            cmd=[str(wrapper),'--no-daemon','devkitNativeTest']
            if offline:cmd.append('--offline')
            cp=run_phases(cmd,run=run,probe=probe,env=env,timeout=timeout)
            proof_path=probe/'run/devkit-native/devkit-runtime-proof.json'
            if cp.returncode:
                from devkit_diagnostics import native_failure
                diagnosis=native_failure(probe, cp.stdout, cp.stderr)
                result['diagnosis']=diagnosis
                detail=diagnosis['family']+': '+diagnosis['summary']+'\n'+diagnosis['context']
                raise RuntimeError('native process failed: '+str(cp.returncode)+'; full logs: '+str(run/'commands')+'\n'+detail)
            proof=json.loads(proof_path.read_text())
            if not valid_restart(proof, result['artifact_sha256']):
                raise ValueError('runtime proof does not match the candidate or required world gates')
            if sha256_file(artifact)!=result['artifact_sha256']:raise ValueError('candidate changed during native verification')
            screenshots=list((probe/'run').rglob('*devkit-*.png'))
            if len(screenshots)<3:raise ValueError('expected initial, reopened and restarted native world screenshots')
            evidence=[proof_path, probe/'run/devkit-native/devkit-restart.properties', run/'phase.json']
            evidence.extend(p for directory in [run/'phase-evidence',run/'commands'] for p in directory.rglob('*') if p.is_file())
            result.update(state='runtime-smoke-verified',proof=proof,coverage=result['required_coverage'],
                          evidence_files=[{'path':str(p),'sha256':sha256_file(p)} for p in evidence],
                          screenshots=[{'path':str(p),'sha256':sha256_file(p)} for p in screenshots],jdk=jdk,
                          dependency_lock_sha256=sha256_file(workspace/'dependencies/dependency-lock.json'))
        except Exception as error:
            result.update(state='failed',error=str(error))
        atomic_json(workspace/'native-result.json',result)
        return result


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--jar',type=Path,required=True);p.add_argument('--workspace',type=Path,required=True)
    p.add_argument('--template',type=Path);p.add_argument('--java-path',type=Path)
    p.add_argument('--timeout',type=int,default=900);p.add_argument('--offline',action='store_true')
    a=p.parse_args();result=verify(a.jar,a.workspace,template=a.template,timeout=a.timeout,offline=a.offline,java_path=a.java_path)
    print(json.dumps(result,indent=2));return 0 if result['state']=='runtime-smoke-verified' else 2
if __name__=='__main__':raise SystemExit(main())
