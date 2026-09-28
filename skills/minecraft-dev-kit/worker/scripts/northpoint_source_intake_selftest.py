#!/usr/bin/env python3
import json, pathlib, subprocess, sys, tempfile

SCRIPT = pathlib.Path(__file__).with_name('northpoint_source_intake.py')

def write(root, rel, text):
    p=root/rel; p.parent.mkdir(parents=True, exist_ok=True); p.write_text(text, encoding='utf-8')

def run(project):
    cp=subprocess.run([sys.executable,str(SCRIPT),'--project',str(project)],text=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
    assert cp.returncode == 0, (cp.stdout,cp.stderr)
    return json.loads([x for x in cp.stdout.splitlines() if x.strip()][-1])

with tempfile.TemporaryDirectory(prefix='northpoint-intake-') as td:
    root=pathlib.Path(td)/'fabricmod'; root.mkdir()
    write(root,'gradle.properties','minecraft_version=1.21.1\nloader_version=0.16.10\n')
    write(root,'build.gradle','plugins { id "fabric-loom" }\ntasks.withType(JavaCompile).configureEach { it.options.release = 21 }\n')
    write(root,'gradlew','#!/bin/sh\n')
    write(root,'src/main/resources/fabric.mod.json',json.dumps({'schemaVersion':1,'id':'intakeproof','version':'1.0.0','environment':'*','entrypoints':{'main':['x.Main']}}))
    write(root,'src/main/resources/intakeproof.mixins.json','{"required":true,"package":"x.mixin","mixins":["ProofMixin"]}\n')
    write(root,'src/main/java/x/Main.java','package x; public class Main {}\n')
    got=run(root)
    assert got['build']['mode']=='gradle', got
    assert got['loader']=='fabric' and got['mod_id']=='intakeproof', got
    assert got['minecraft']=='1.21.1' and got['java']==21, got
    assert got['source_counts']['java']==1 and got['source_counts']['mixins']>=1, got
    assert got['proposed_config']['build']['mode']=='gradle', got
    assert got['proposed_config']['runtime']['required'] is True, got
    assert got['runtime_scope']=='both', got
    assert got['proposed_config']['runtime']['scope']=='both', got
    assert got['source_sha256'], got

    forge=pathlib.Path(td)/'forgemod'; forge.mkdir()
    write(forge,'gradle.properties','minecraft_version=1.20.1\n')
    write(forge,'build.gradle','java { toolchain.languageVersion = JavaLanguageVersion.of(17) }\n')
    write(forge,'src/main/resources/META-INF/mods.toml','modLoader="javafml"\n[[mods]]\nmodId="forgeproof"\n')
    write(forge,'src/main/java/x/Main.java','package x; public class Main {}\n')
    got=run(forge)
    assert got['loader']=='forge' and got['mod_id']=='forgeproof', got
    assert got['minecraft']=='1.20.1' and got['java']==17, got
    assert got['runtime_scope']=='unknown', got
    write(forge,'northpoint.project.json',json.dumps({'schema_version':1,'runtime':{'required':True,'scope':'both'}}))
    got=run(forge)
    assert got['runtime_scope']=='both', got
    assert got['proposed_config']['runtime']['scope']=='both', got

    neo=pathlib.Path(td)/'neomod'; neo.mkdir()
    write(neo,'gradle.properties','minecraft_version=26.3\nmod_id=examplemod\nneo_version=26.3.0.7-beta\n')
    write(neo,'build.gradle','java.toolchain.languageVersion = JavaLanguageVersion.of(25)\n')
    write(neo,'gradlew','#!/bin/sh\n')
    write(neo,'src/main/templates/META-INF/neoforge.mods.toml','[[mods]]\nmodId="${mod_id}"\n')
    write(neo,'src/main/java/com/example/ExampleMod.java','package com.example; public class ExampleMod {}\n')
    got=run(neo)
    assert got['loader']=='neoforge', got
    assert got['mod_id']=='examplemod', got
    assert got['minecraft']=='26.3' and got['java']==25, got
    assert got['proposed_config']['mod_id']=='examplemod', got
    assert any('template placeholder' in warning for warning in got['warnings']), got

    client=pathlib.Path(td)/'clientmod'; client.mkdir()
    write(client,'gradle.properties','minecraft_version=1.21.1\n')
    write(client,'build.gradle','tasks.withType(JavaCompile).configureEach { it.options.release = 21 }\n')
    write(client,'src/main/resources/fabric.mod.json',json.dumps({'schemaVersion':1,'id':'clientproof','version':'1.0.0','environment':'client'}))
    write(client,'src/main/java/x/Client.java','package x; public class Client {}\n')
    got=run(client)
    assert got['runtime_scope']=='client', got
    assert got['proposed_config']['runtime']['scope']=='client', got

print('Northpoint source intake self-test: PASS')