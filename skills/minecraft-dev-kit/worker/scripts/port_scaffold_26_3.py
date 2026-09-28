#!/usr/bin/env python3
"""Create a loader-native Minecraft 26.3 Fabric or NeoForge port scaffold without touching the source mod."""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

FABRIC = {
    "minecraft": "26.3",
    "java": 25,
    "loader": "0.19.5",
    "loom": "1.17-SNAPSHOT",
    "fabric_api": "0.161.0+26.3",
    "gradle": "9.6.0",
}
NEOFORGE = {
    "minecraft": "26.3",
    "java": 25,
    "neoforge": "26.3.0.7-beta",
    "moddevgradle": "2.0.147",
    "gradle": "9.2.1",
    "foojay": "1.0.0",
}
SNAPSHOT_DATE = "2026-09-22"


def valid_mod_id(value: str) -> str:
    if not re.fullmatch(r"[a-z][a-z0-9_-]{1,63}", value):
        raise argparse.ArgumentTypeError("Fabric-compatible mod id must match [a-z][a-z0-9_-]{1,63}")
    return value


def require_neoforge_mod_id(value: str) -> str:
    if not re.fullmatch(r"[a-z][a-z0-9_]{1,63}", value):
        raise ValueError("NeoForge mod id must match [a-z][a-z0-9_]{1,63}")
    return value


def package_path(group: str, mod_id: str) -> Path:
    pkg = f"{group}.{mod_id}".replace("-", "_")
    if not re.fullmatch(r"[A-Za-z_$][\w$]*(\.[A-Za-z_$][\w$]*)+", pkg):
        raise ValueError(f"invalid Java package derived from group/mod id: {pkg}")
    return Path(*pkg.split("."))


def write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip() + "\n", encoding="utf-8")


def wrapper_properties(version: str) -> str:
    return f"""distributionBase=GRADLE_USER_HOME
distributionPath=wrapper/dists
distributionUrl=https\\://services.gradle.org/distributions/gradle-{version}-bin.zip
networkTimeout=10000
validateDistributionUrl=true
zipStoreBase=GRADLE_USER_HOME
zipStorePath=wrapper/dists
"""


def common_files(out: Path, loader: str, mod_id: str, mod_name: str, group: str, version: str, profile: dict) -> None:
    write(out / ".gitignore", ".gradle/\nbuild/\nout/\nrun/\n.idea/\n*.iml\n")
    write(out / "settings.gradle", "")
    ledger = {
        "schema_version": 1,
        "target": {"minecraft": "26.3", "loader": loader, "java": 25},
        "source_manifest": None,
        "phase_a": {"future_vanilla_parity_enabled": False},
        "items": [],
        "status_values": ["carried", "regenerated", "superseded", "intentionally_excluded", "missing"],
        "note": "Populate from the intake inventory before declaring the port complete. Every source-owned item/surface needs an explicit status.",
    }
    write(out / "porting-ledger.json", json.dumps(ledger, indent=2))
    lock = {
        "schema_version": 1,
        "snapshot_date": SNAPSHOT_DATE,
        "target": {"minecraft": "26.3", "loader": loader, "java": 25},
        "profile": profile,
        "revalidate_before_new_port": True,
        "mod": {"id": mod_id, "name": mod_name, "group": group, "version": version},
    }
    write(out / "devkit-26.3-lock.json", json.dumps(lock, indent=2))
    write(out / "PORTING.md", f"""# {mod_name} — Minecraft 26.3 {loader.title()} port scaffold

Generated from the Minecraft Dev Kit 26.3 profile snapshot dated {SNAPSHOT_DATE}.

This directory is a **target scaffold**, not evidence that the source mod has been fully ported. Keep the original source untouched. Attach `port-intake.json`, populate `porting-ledger.json`, then migrate behavior and run `port_guard.py` before runtime QA.

Target: Minecraft 26.3 / {loader} / Java 25.

The Gradle wrapper properties are pinned, but this scaffold intentionally does not fabricate `gradle-wrapper.jar`. Use the Dev Kit's verified Gradle distribution (or a trusted local Gradle) once to run `gradle wrapper --gradle-version {profile['gradle']}`, then hash/cache the resulting wrapper files.
""")
    write(out / "gradle/wrapper/gradle-wrapper.properties", wrapper_properties(profile["gradle"]))


def fabric_scaffold(out: Path, mod_id: str, mod_name: str, group: str, version: str, profile: dict) -> None:
    common_files(out, "fabric", mod_id, mod_name, group, version, profile)
    write(out / "settings.gradle", """pluginManagement {
    repositories {
        maven { name = 'Fabric'; url = 'https://maven.fabricmc.net/' }
        gradlePluginPortal()
    }
}
rootProject.name = 'mc263-fabric-port'
""")
    write(out / "gradle.properties", f"""org.gradle.jvmargs=-Xmx2G
org.gradle.parallel=true
org.gradle.configuration-cache=false

minecraft_version={profile['minecraft']}
loader_version={profile['loader']}
loom_version={profile['loom']}
fabric_api_version={profile['fabric_api']}

mod_version={version}
maven_group={group}
archives_base_name={mod_id}
""")
    write(out / "build.gradle", """plugins {
    id 'net.fabricmc.fabric-loom' version "${loom_version}"
    id 'maven-publish'
}

version = project.mod_version
group = project.maven_group
base { archivesName = project.archives_base_name }

repositories { }

loom {
    splitEnvironmentSourceSets()
    mods {
        "${project.archives_base_name}" {
            sourceSet sourceSets.main
            sourceSet sourceSets.client
        }
    }
}

dependencies {
    minecraft "com.mojang:minecraft:${project.minecraft_version}"
    implementation "net.fabricmc:fabric-loader:${project.loader_version}"
    implementation "net.fabricmc.fabric-api:fabric-api:${project.fabric_api_version}"
}

processResources {
    inputs.property "version", project.version
    filesMatching("fabric.mod.json") { expand "version": project.version }
}

tasks.withType(JavaCompile).configureEach { options.release = 25 }
java {
    withSourcesJar()
    sourceCompatibility = JavaVersion.VERSION_25
    targetCompatibility = JavaVersion.VERSION_25
}
""")
    pkg = f"{group}.{mod_id}".replace("-", "_")
    rel = package_path(group, mod_id)
    main_class = "".join(part.capitalize() for part in re.split(r"[_-]+", mod_id)) + "Mod"
    client_class = main_class + "Client"
    write(out / "src/main/java" / rel / f"{main_class}.java", f"""package {pkg};

import net.fabricmc.api.ModInitializer;

public final class {main_class} implements ModInitializer {{
    public static final String MOD_ID = "{mod_id}";

    @Override
    public void onInitialize() {{
        // Port source behavior here; keep loader-specific registrations on the Fabric side.
    }}
}}
""")
    write(out / "src/client/java" / rel / f"{client_class}.java", f"""package {pkg};

import net.fabricmc.api.ClientModInitializer;

public final class {client_class} implements ClientModInitializer {{
    @Override
    public void onInitializeClient() {{
        // Port client/render/input behavior here and avoid direct GLFW use on 26.3.
    }}
}}
""")
    mod_json = {
        "schemaVersion": 1,
        "id": mod_id,
        "version": "${version}",
        "name": mod_name,
        "environment": "*",
        "entrypoints": {
            "main": [f"{pkg}.{main_class}"],
            "client": [f"{pkg}.{client_class}"],
        },
        "depends": {"fabricloader": f">={profile['loader']}", "minecraft": "~26.3", "java": ">=25", "fabric-api": "*"},
    }
    write(out / "src/main/resources/fabric.mod.json", json.dumps(mod_json, indent=2))


def neoforge_scaffold(out: Path, mod_id: str, mod_name: str, group: str, version: str, profile: dict) -> None:
    common_files(out, "neoforge", mod_id, mod_name, group, version, profile)
    write(out / "settings.gradle", f"""pluginManagement {{ repositories {{ gradlePluginPortal(); maven {{ url = 'https://maven.neoforged.net/releases' }} }} }}
plugins {{ id 'org.gradle.toolchains.foojay-resolver-convention' version '{profile['foojay']}' }}
rootProject.name = 'mc263-neoforge-port'
""")
    write(out / "gradle.properties", f"""org.gradle.jvmargs=-Xmx2G
org.gradle.daemon=true
org.gradle.parallel=true
org.gradle.caching=true
org.gradle.configuration-cache=true

minecraft_version={profile['minecraft']}
minecraft_version_range=[26.3]
neo_version={profile['neoforge']}
mod_id={mod_id}
mod_name={mod_name}
mod_license=All Rights Reserved
mod_version={version}
mod_group_id={group}
""")
    write(out / "build.gradle", f"""plugins {{
    id 'java-library'
    id 'maven-publish'
    id 'net.neoforged.moddev' version '{profile['moddevgradle']}'
    id 'idea'
}}

version = mod_version
group = mod_group_id
base {{ archivesName = mod_id }}
java.toolchain.languageVersion = JavaLanguageVersion.of(25)

sourceSets.main.resources {{
    srcDir('src/generated/resources')
    exclude("**/*.bbmodel")
    exclude("src/generated/**/.cache")
}}

neoForge {{
    version = project.neo_version
    runs {{
        client {{ client(); systemProperty 'neoforge.enabledGameTestNamespaces', project.mod_id }}
        server {{ server(); programArgument '--nogui'; systemProperty 'neoforge.enabledGameTestNamespaces', project.mod_id }}
        gameTestServer {{ type = 'gameTestServer'; systemProperty 'neoforge.enabledGameTestNamespaces', project.mod_id }}
        data {{
            clientData()
            programArguments.addAll '--mod', project.mod_id, '--all', '--output', file('src/generated/resources/').getAbsolutePath(), '--existing', file('src/main/resources/').getAbsolutePath()
        }}
    }}
    mods {{ "${{mod_id}}" {{ sourceSet(sourceSets.main) }} }}
}}

configurations {{ runtimeClasspath.extendsFrom localRuntime }}

def generateModMetadata = tasks.register("generateModMetadata", ProcessResources) {{
    def replaceProperties = [minecraft_version:minecraft_version, minecraft_version_range:minecraft_version_range, neo_version:neo_version, mod_id:mod_id, mod_name:mod_name, mod_license:mod_license, mod_version:mod_version]
    inputs.properties replaceProperties
    expand replaceProperties
    from "src/main/templates"
    into "build/generated/sources/modMetadata"
}}
sourceSets.main.resources.srcDir generateModMetadata
neoForge.ideSyncTask generateModMetadata

tasks.withType(JavaCompile).configureEach {{ options.encoding = 'UTF-8'; options.release = 25 }}
""")
    pkg = f"{group}.{mod_id}".replace("-", "_")
    rel = package_path(group, mod_id)
    main_class = "".join(part.capitalize() for part in re.split(r"[_-]+", mod_id)) + "Mod"
    write(out / "src/main/java" / rel / f"{main_class}.java", f"""package {pkg};

import net.neoforged.fml.common.Mod;

@Mod({main_class}.MOD_ID)
public final class {main_class} {{
    public static final String MOD_ID = "{mod_id}";

    public {main_class}() {{
        // Port source behavior here using NeoForge 26.3 APIs.
    }}
}}
""")
    write(out / "src/main/templates/META-INF/neoforge.mods.toml", f"""license="${{mod_license}}"

[[mods]]
modId="${{mod_id}}"
version="${{mod_version}}"
displayName="${{mod_name}}"
description='''Minecraft 26.3 port scaffold generated by the Minecraft Dev Kit.'''

[[dependencies.${{mod_id}}]]
modId="neoforge"
type="required"
versionRange="[${{neo_version}},)"
ordering="NONE"
side="BOTH"

[[dependencies.${{mod_id}}]]
modId="minecraft"
type="required"
versionRange="${{minecraft_version_range}}"
ordering="NONE"
side="BOTH"
""")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--loader", required=True, choices=["fabric", "neoforge"])
    ap.add_argument("--output", required=True, type=Path)
    ap.add_argument("--mod-id", required=True, type=valid_mod_id)
    ap.add_argument("--mod-name")
    ap.add_argument("--group", default="com.example")
    ap.add_argument("--mod-version", default="1.0.0")
    ap.add_argument("--force", action="store_true", help="allow writing into an existing empty/nonempty output directory")
    args = ap.parse_args()
    out = args.output.resolve()
    if out.exists() and any(out.iterdir()) and not args.force:
        raise SystemExit(f"refusing to write into non-empty directory without --force: {out}")
    out.mkdir(parents=True, exist_ok=True)
    mod_name = args.mod_name or re.sub(r"[_-]+", " ", args.mod_id).title()
    if args.loader == "neoforge":
        require_neoforge_mod_id(args.mod_id)
    if args.loader == "fabric":
        fabric_scaffold(out, args.mod_id, mod_name, args.group, args.mod_version, dict(FABRIC))
    else:
        neoforge_scaffold(out, args.mod_id, mod_name, args.group, args.mod_version, dict(NEOFORGE))
    print(json.dumps({"status": "ok", "output": str(out), "loader": args.loader, "minecraft": "26.3", "java": 25}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
