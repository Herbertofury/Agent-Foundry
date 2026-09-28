#!/usr/bin/env python3
"""Deterministic self-test for the Minecraft 26.3 port intake/scaffold/mapping/Mixin/guard pipeline."""
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import zipfile
import shutil
from pathlib import Path

from mapping_lineage import normalize_file, source_plan
from mapping_bridge import bridge as bridge_mappings
from classfile_symbol_index import build_index, resolve_member
from mixin_target_resolver import resolve_project as resolve_mixins_exact
from access_rule_resolver import resolve_project as resolve_access_exact
from packaged_linkage_audit import audit as audit_packaged_linkage
from port_semantic_planner import plan as semantic_plan
from port_failure_triage import triage as triage_failure
from mixin_surface_audit import audit as audit_mixins
from port_intake import inspect
from content_identity_inventory import inventory as content_inventory
from content_parity_audit import audit as audit_content_parity
from api_reference_migration import audit as audit_api_references
from registration_identity_inventory import inventory as registration_inventory
from registration_parity_audit import audit as audit_registration_parity

HERE = Path(__file__).resolve().parent


def run(*args: str, expect: int = 0) -> subprocess.CompletedProcess[str]:
    cp = subprocess.run([sys.executable, *args], text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if cp.returncode != expect:
        raise AssertionError(f"command expected {expect}, got {cp.returncode}: {' '.join(args)}\nstdout={cp.stdout}\nstderr={cp.stderr}")
    return cp


def write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def scaffold(root: Path, name: str, loader: str = "fabric", mod_id: str = "testmod") -> Path:
    p = root / name
    run(str(HERE / "port_scaffold_26_3.py"), "--loader", loader, "--output", str(p), "--mod-id", mod_id)
    return p


def fixture_old_fabric(root: Path) -> Path:
    p = root / "old-fabric"
    write(p / "fabric.mod.json", json.dumps({
        "schemaVersion": 1, "id": "oldmod", "version": "1.0.0",
        "depends": {"minecraft": "1.20.1", "fabricloader": ">=0.14.0"}
    }))
    write(p / "gradle.properties", "minecraft_version=1.20.1\nloom_version=1.4-SNAPSHOT\nyarn_mappings=1.20.1+build.2\n")
    write(p / "build.gradle", """java { toolchain.languageVersion = JavaLanguageVersion.of(17) }
dependencies { mappings \"net.fabricmc:yarn:1.20.1+build.2:v2\"; modImplementation \"net.fabricmc.fabric-api:fabric-api:0.1\" }
tasks.named(\"remapJar\") {}
""")
    write(p / "src/main/java/example/Old.java", """package example;
import net.fabricmc.fabric.api.registry.FuelRegistry;
import org.lwjgl.glfw.GLFW;
class Old { int key = GLFW.GLFW_KEY_R; Object fuel = FuelRegistry.INSTANCE; Object group = ItemGroupEvents.class; Object trade = TradeOfferHelper.class; }
""")
    write(p / "src/main/java/example/LegacyListEntry.java", """package example;
import net.minecraft.client.gui.components.AbstractSelectionList;
public class LegacyListEntry extends AbstractSelectionList.Entry<LegacyListEntry> {}
""")
    write(p / "src/main/java/example/LegacyScreen.java", """package example;
class LegacyScreen extends Screen {
  void draw() { for (Renderable r : this.renderables) { r.toString(); } }
}
""")
    write(p / "src/main/java/example/Registrations.java", """package example;
class Registrations {
  static final String MOD_ID = "oldmod";
  static final DeferredRegister BLOCKS = DeferredRegister.create(Registries.BLOCK, MOD_ID);
  static final DeferredRegister ENTITIES = DeferredRegister.create(Registries.ENTITY_TYPE, MOD_ID);
  static final Object STONE = BLOCKS.register("stone", () -> null);
  static final Object BEAST = ENTITIES.register("beast", () -> null);
}
""")
    write(p / "src/main/resources/data/oldmod/worldgen/configured_feature/thing.json", "{}")
    return p


def fixture_old_neoforge(root: Path) -> Path:
    p = root / "old-neoforge"
    write(p / "src/main/resources/META-INF/mods.toml", "modLoader=\"javafml\"\n[[mods]]\nmodId=\"oldneo\"\nversion=\"1\"\n")
    write(p / "gradle.properties", "minecraft_version=1.20.1\n")
    write(p / "src/main/java/example/OldNeo.java", "package example; import net.minecraftforge.fml.common.Mod; class OldNeo {}\n")
    return p


def assert_mapping_parsers(root: Path) -> None:
    samples = {
        "tiny.tiny": ("tiny_v2", """tiny\t2\t0\tofficial\tintermediary
c\tnet/minecraft/Foo\tnet/minecraft/class_1
\tf\tI\tvalue\tfield_1
\tm\t()V\ttick\tmethod_1
""", (1, 1, 1)),
        "joined.tsrg": ("tsrg", """a net/minecraft/Foo
\tb field_1
\tc ()V method_1
""", (1, 1, 1)),
        "joined2.tsrg": ("tsrg2", """tsrg2 obfuscated srg official
a net/minecraft/Foo net/minecraft/Foo
\tb field_1 value
\tc ()V method_1 tick
""", (1, 1, 1)),
        "joined.srg": ("srg", """CL: a net/minecraft/Foo
FD: a/b net/minecraft/Foo/field_1
MD: a/c ()V net/minecraft/Foo/method_1 ()V
""", (1, 1, 1)),
        "client.txt": ("proguard", """net.minecraft.Foo -> a:
    int value -> b
    void tick() -> c
""", (1, 1, 1)),
        "methods.csv": ("mcp_csv", """searge,name,side,desc
func_1_a,tick,2,
""", (0, 0, 0)),
    }
    for name, (fmt, text, counts) in samples.items():
        path = root / "mapping-fixtures" / name
        write(path, text)
        result = normalize_file(path, fmt)
        assert result["format"] == fmt
        if fmt == "mcp_csv":
            assert result["counts"]["aliases"] == 1
        else:
            assert (result["counts"]["classes"], result["counts"]["fields"], result["counts"]["methods"]) == counts, (name, result["counts"])
    old_fabric_tiny = normalize_file(root / "mapping-fixtures/tiny.tiny", "tiny_v2", "fabric_intermediary", "1.20.1")
    assert "obfuscated" in old_fabric_tiny["namespaces"] and "official" not in old_fabric_tiny["namespaces"]
    assert old_fabric_tiny["namespace_semantics"]["aliases_applied"] == {"official": "obfuscated"}
    mojang = normalize_file(root / "mapping-fixtures/client.txt", "proguard", "mojang_official", "1.20.1")
    assert "mojang_named" in mojang["namespaces"] and "obfuscated" in mojang["namespaces"]

    # Exact same-version Yarn -> obfuscated -> Mojang bridge with descriptor preservation.
    yarn_path = root / "mapping-fixtures/yarn-bridge.tiny"
    write(yarn_path, """tiny\t2\t0\tofficial\tintermediary\tnamed
c\ta\tnet/minecraft/class_1\tnet/minecraft/FooEntity
\tm\t()V\tc\tmethod_1\ttick
\tm\t(Lb;)Lb;\td\tmethod_2\tmapBar
c\tb\tnet/minecraft/class_2\tnet/minecraft/BarEntity
""")
    moj_path = root / "mapping-fixtures/mojang-bridge.txt"
    write(moj_path, """net.minecraft.Foo -> a:
    void doTick() -> c
    net.minecraft.Bar map(net.minecraft.Bar) -> d
net.minecraft.Bar -> b:
""")
    yarn_ix = normalize_file(yarn_path, "tiny_v2", "fabric_yarn", "1.20.1")
    moj_ix = normalize_file(moj_path, "proguard", "mojang_official", "1.20.1")
    bridged = bridge_mappings([yarn_ix, moj_ix], "yarn_named", "net/minecraft/FooEntity", "tick", "()V")
    assert bridged["status"] == "RESOLVED", bridged
    assert bridged["classes"]["mojang_named"] == "net/minecraft/Foo"
    assert bridged["members"]["mojang_named"] == "doTick"
    bridged_obj = bridge_mappings([yarn_ix, moj_ix], "yarn_named", "net/minecraft/FooEntity", "mapBar", "(Lnet/minecraft/BarEntity;)Lnet/minecraft/BarEntity;")
    assert bridged_obj["status"] == "RESOLVED", bridged_obj
    assert bridged_obj["members"]["mojang_named"] == "map"
    assert bridged_obj["descriptor_by_namespace"]["obfuscated"] == "(Lb;)Lb;"
    assert bridged_obj["descriptor_by_namespace"]["mojang_named"] == "(Lnet/minecraft/Bar;)Lnet/minecraft/Bar;"



def compile_symbol_fixture(root: Path) -> tuple[Path, dict, Path]:
    if not shutil.which("javac"):
        raise AssertionError("javac is required for exact symbol/linkage self-tests")
    src = root / "symbol-src"
    classes = root / "symbol-classes"
    write(src / "net/minecraft/TargetBase.java", """package net.minecraft;
public class TargetBase {
  public int value;
  public void tick() {}
  public void tick(int x) {}
}
""")
    write(src / "net/minecraft/Target.java", """package net.minecraft;
public class Target extends TargetBase {
  public void own() {}
}
""")
    write(src / "net/minecraft/Action.java", """package net.minecraft;
@FunctionalInterface public interface Action { void apply(int x); }
""")
    run_javac = subprocess.run([
        shutil.which("javac"), "-d", str(classes),
        str(src / "net/minecraft/TargetBase.java"), str(src / "net/minecraft/Target.java"), str(src / "net/minecraft/Action.java")
    ], text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if run_javac.returncode:
        raise AssertionError(f"javac target fixture failed: {run_javac.stderr}")
    index = build_index(classes, include_refs=True)
    assert index["class_count"] == 3
    assert resolve_member(index, "net/minecraft/Target", "field", "value", "I")["status"] == "RESOLVED"
    assert resolve_member(index, "net/minecraft/Target", "method", "tick", "()V")["status"] == "RESOLVED"
    assert resolve_member(index, "net/minecraft/Target", "method", "tick", None)["status"] == "AMBIGUOUS"

    # Prove official server-style nested version JAR indexing.
    inner = root / "server-inner.jar"
    subprocess.run(["jar", "cf", str(inner), "-C", str(classes), "."], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    bundler = root / "server-bundler.jar"
    with zipfile.ZipFile(bundler, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("META-INF/versions.list", "fixture\n")
        zf.write(inner, "META-INF/versions/fixture/server-26.3.jar")
    nested = build_index(bundler)
    assert nested["class_count"] == 3
    assert nested["nested_archives"][0]["class_count"] == 3

    # Compile a packaged candidate against the target fixture for exact symbolic linkage tests.
    candidate_src = root / "candidate-src"
    candidate_classes = root / "candidate-classes"
    write(candidate_src / "example/Candidate.java", """package example;
import net.minecraft.Target;
import net.minecraft.Action;
public class Candidate {
  public static int call(Target t) { t.tick(); return t.value; }
  public static Action action(Target t) { return x -> t.tick(x); }
}
""")
    cp = subprocess.run([shutil.which("javac"), "-cp", str(classes), "-d", str(candidate_classes), str(candidate_src / "example/Candidate.java")], text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if cp.returncode:
        raise AssertionError(f"javac candidate fixture failed: {cp.stderr}")
    return classes, index, candidate_classes


def assert_exact_symbol_tools(root: Path) -> None:
    classes, index, candidate_classes = compile_symbol_fixture(root)
    project = root / "mixin-exact"
    write(project / "src/main/java/example/GoodMixin.java", """package example;
import net.minecraft.Target;
@Mixin(Target.class)
class GoodMixin {
  @Inject(method = "tick()V", at = @At("HEAD")) void inject() {}
  @Shadow int value;
}
""")
    good = resolve_mixins_exact(project, index)
    assert not good["blockers"], good
    assert any(x["selector"]["name"] == "tick" for x in good["resolved"])

    write(project / "src/main/java/example/BadMixin.java", """package example;
import net.minecraft.Target;
@Mixin(Target.class)
class BadMixin { @Inject(method = "tick", at = @At("HEAD")) void inject() {} }
""")
    bad = resolve_mixins_exact(project, index)
    assert "mixin-selector-ambiguous" in {x["id"] for x in bad["blockers"]}, bad

    access = root / "access-exact"
    write(access / "src/main/resources/test.classtweaker", """classTweaker v1 official
accessible method net/minecraft/TargetBase tick ()V
accessible field net/minecraft/TargetBase value I
""")
    ar = resolve_access_exact(access, index)
    assert not ar["blockers"], ar
    write(access / "src/main/resources/bad_at/META-INF/accesstransformer.cfg", "public net.minecraft.Target missing()V\n")
    ar_bad = resolve_access_exact(access, index)
    assert "access-member-missing" in {x["id"] for x in ar_bad["blockers"]}

    link = audit_packaged_linkage(candidate_classes, [index])
    assert link["status"] == "PASS", link
    broken = json.loads(json.dumps(index))
    broken["classes"]["net/minecraft/TargetBase"]["methods"] = [m for m in broken["classes"]["net/minecraft/TargetBase"]["methods"] if not (m["name"] == "tick" and m["descriptor"] == "()V")]
    link_bad = audit_packaged_linkage(candidate_classes, [broken])
    assert "unresolved-member-reference" in {x["id"] for x in link_bad["blockers"]}, link_bad

    # invokedynamic/LambdaMetafactory SAM names are validated independently of ordinary refs.
    parsed_candidate = build_index(candidate_classes, include_refs=True)
    candidate_row = parsed_candidate["classes"]["example/Candidate"]
    assert any(x.get("kind") == "lambda_metafactory" and x.get("functional_interface") == "net/minecraft/Action" and x.get("sam_name") == "apply" and x.get("sam_descriptor") == "(I)V" for x in candidate_row.get("invokedynamic_refs") or []), candidate_row.get("invokedynamic_refs")
    broken_sam = json.loads(json.dumps(index))
    broken_sam["classes"]["net/minecraft/Action"]["methods"] = [m for m in broken_sam["classes"]["net/minecraft/Action"]["methods"] if m["name"] != "apply"]
    link_sam_bad = audit_packaged_linkage(candidate_classes, [broken_sam])
    assert "unresolved-indy-sam" in {x["id"] for x in link_sam_bad["blockers"]}, link_sam_bad




def assert_api_reference_migration(root: Path) -> None:
    if not shutil.which("javac"):
        raise AssertionError("javac is required for API reference migration self-test")
    map_dir = root / "api-mapping"
    map_dir.mkdir(parents=True, exist_ok=True)
    yarn_path = map_dir / "yarn.tiny"
    moj_path = map_dir / "mojang.txt"
    write(yarn_path, """tiny\t2\t0\tofficial\tintermediary\tnamed
c\ta\tnet/minecraft/class_1\tnet/minecraft/FooEntity
\tm\t(Lb;)Lb;\td\tmethod_2\tmapBar
c\tb\tnet/minecraft/class_2\tnet/minecraft/BarEntity
""")
    write(moj_path, """net.minecraft.Foo -> a:
    net.minecraft.Bar map(net.minecraft.Bar) -> d
net.minecraft.Bar -> b:
""")
    yarn_ix = normalize_file(yarn_path, "tiny_v2", "fabric_yarn", "1.20.1")
    moj_ix = normalize_file(moj_path, "proguard", "mojang_official", "1.20.1")

    old_src, old_mc, old_mod = root / "old-api-src", root / "old-api-mc", root / "old-api-mod"
    write(old_src / "net/minecraft/FooEntity.java", "package net.minecraft; public class FooEntity { public BarEntity mapBar(BarEntity b){ return b; } }\n")
    write(old_src / "net/minecraft/BarEntity.java", "package net.minecraft; public class BarEntity {}\n")
    cp = subprocess.run([shutil.which("javac"), "-d", str(old_mc), str(old_src / "net/minecraft/FooEntity.java"), str(old_src / "net/minecraft/BarEntity.java")], text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if cp.returncode:
        raise AssertionError(cp.stderr)
    write(old_src / "example/OldMod.java", "package example; import net.minecraft.*; public class OldMod { public BarEntity call(FooEntity f, BarEntity b){ return f.mapBar(b); } }\n")
    cp = subprocess.run([shutil.which("javac"), "-cp", str(old_mc), "-d", str(old_mod), str(old_src / "example/OldMod.java")], text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if cp.returncode:
        raise AssertionError(cp.stderr)

    target_src, target_classes = root / "api-target-src", root / "api-target-classes"
    write(target_src / "net/minecraft/Foo.java", "package net.minecraft; public class Foo { public Bar map(Bar b){ return b; } }\n")
    write(target_src / "net/minecraft/Bar.java", "package net.minecraft; public class Bar {}\n")
    cp = subprocess.run([shutil.which("javac"), "-d", str(target_classes), str(target_src / "net/minecraft/Foo.java"), str(target_src / "net/minecraft/Bar.java")], text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if cp.returncode:
        raise AssertionError(cp.stderr)
    target_index = build_index(target_classes, include_refs=True)
    good = audit_api_references(old_mod, "yarn_named", [yarn_ix, moj_ix], target_index)
    assert good["status"] == "PASS", good
    assert any(x["status"] == "EXACT_26_3" and x["translation"]["target"]["name"] == "map" and x["translation"]["target"]["descriptor"] == "(Lnet/minecraft/Bar;)Lnet/minecraft/Bar;" for x in good["member_references"]), good

    broken = json.loads(json.dumps(target_index))
    broken["classes"]["net/minecraft/Foo"]["methods"] = [m for m in broken["classes"]["net/minecraft/Foo"]["methods"] if m["name"] != "map"]
    bad = audit_api_references(old_mod, "yarn_named", [yarn_ix, moj_ix], broken)
    assert bad["status"] == "FAIL", bad
    assert any(x["status"] == "MEMBER_MISSING" for x in bad["blockers"]), bad

def main() -> int:
    with tempfile.TemporaryDirectory(prefix="mc263-devkit-selftest-") as td:
        root = Path(td)
        old_fabric = fixture_old_fabric(root)
        old_neoforge = fixture_old_neoforge(root)

        fabric_intake = inspect(old_fabric, "fabric")
        fids = {x["id"] for x in fabric_intake["findings"]}
        assert "fabric-fuel-registry-removed" in fids
        assert "glfw-direct-input" in fids
        assert "legacy-java-target" in fids
        assert "old-configured-feature-data-path" in fids
        assert "fabric-yarn-mapping-on-26-3-target" in fids
        assert "fabric" in fabric_intake["detected"]["loaders"]
        assert fabric_intake["source_minecraft_version"] == "1.20.1"
        assert fabric_intake["mapping_hints"]["uses_yarn"] is True
        plan_ids = {x["id"] for x in fabric_intake["mapping_plan"]["sources"]}
        assert {"mojang_official", "fabric_intermediary", "fabric_yarn"} <= plan_ids
        assert "mixin_audit" in fabric_intake

        neo_intake = inspect(old_neoforge, "neoforge")
        nids = {x["id"] for x in neo_intake["findings"]}
        assert "forge-package-on-neoforge-target" in nids
        assert "legacy-forge-mods-toml" in nids

        # Mapping lineage planning: 26.3 is identity/official; historical loaders require bridge artifacts.
        identity = source_plan("26.3", "fabric")
        assert identity["source"]["unobfuscated"] is True
        assert [x["id"] for x in identity["sources"]] == ["source_identity_official"]
        forge_1122 = source_plan("1.12.2", "forge", "snapshot_20171003")
        forge_ids = {x["id"] for x in forge_1122["sources"]}
        assert {"forge_mcpconfig", "forge_mcp_srg_legacy", "forge_mcp_named_legacy"} <= forge_ids
        assert_mapping_parsers(root)
        prewarm_cache = root / "mapping-prewarm"
        run(str(HERE / "prewarm_mc_26_3_mappings.py"), "--cache", str(prewarm_cache), "--plan-only")
        prewarm = json.loads((prewarm_cache / "mapping-prewarm-manifest.json").read_text(encoding="utf-8"))
        assert prewarm["complete"] is True
        assert len(prewarm["profiles"]) >= 10
        assert any(x["profile"]["minecraft"] == "26.3" and x["status"] == "IDENTITY" for x in prewarm["profiles"])

        # Prove JAR/ZIP intake, not just source directories.
        jar_path = root / "old-fabric.jar"
        with zipfile.ZipFile(jar_path, "w", zipfile.ZIP_DEFLATED) as zf:
            zf.write(old_fabric / "fabric.mod.json", "fabric.mod.json")
            zf.write(old_fabric / "src/main/java/example/Old.java", "example/Old.java")
        jar_intake = inspect(jar_path, "fabric")
        assert "fabric" in jar_intake["detected"]["loaders"]
        assert "glfw-direct-input" in {x["id"] for x in jar_intake["findings"]}

        # Clean scaffolds must pass the static guard, and the Fabric scaffold must be official/unobfuscated.
        for loader in ("fabric", "neoforge"):
            target = scaffold(root, f"clean-{loader}", loader)
            guard_json = root / f"guard-{loader}.json"
            run(str(HERE / "port_guard.py"), str(target), "--loader", loader, "--json-out", str(guard_json))
            guard = json.loads(guard_json.read_text(encoding="utf-8"))
            assert guard["status"] == "PASS", guard["blockers"]
            assert guard["target"]["java"] == 25
            if loader == "fabric":
                assert guard["intake"]["mapping_plan"]["source"]["unobfuscated"] is True
                assert "0.161.0+26.3" in (target / "gradle.properties").read_text()

        # Fabric IDs may contain hyphens and must retain exact identity through the target scaffold.
        hyphen_fabric = scaffold(root, "hyphen-fabric", "fabric", "hyphen-mod")
        hyphen_meta = json.loads((hyphen_fabric / "src/main/resources/fabric.mod.json").read_text(encoding="utf-8"))
        assert hyphen_meta["id"] == "hyphen-mod"
        assert "archives_base_name=hyphen-mod" in (hyphen_fabric / "gradle.properties").read_text(encoding="utf-8")
        assert any(x.name == "HyphenModMod.java" for x in (hyphen_fabric / "src/main/java").rglob("*.java"))
        run(
            str(HERE / "port_scaffold_26_3.py"),
            "--loader", "neoforge",
            "--output", str(root / "hyphen-neoforge"),
            "--mod-id", "hyphen-mod",
            expect=1,
        )

        # Regression: stale direct GLFW in an otherwise clean 26.3 Fabric target must fail.
        dirty_glfw = scaffold(root, "dirty-glfw")
        write(dirty_glfw / "src/client/java/example/Dirty.java", "package example; import org.lwjgl.glfw.GLFW; class Dirty { int x=GLFW.GLFW_KEY_X; }\n")
        run(str(HERE / "port_guard.py"), str(dirty_glfw), "--loader", "fabric", expect=3)

        # Stale Yarn declaration on a 26.3 target is a hard failure.
        dirty_yarn = scaffold(root, "dirty-yarn")
        with (dirty_yarn / "build.gradle").open("a", encoding="utf-8") as fh:
            fh.write('\ndependencies { mappings "net.fabricmc:yarn:1.21.1+build.3:v2" }\n')
        y = inspect(dirty_yarn, "fabric")
        assert "fabric-yarn-mapping-on-26-3-target" in {x["id"] for x in y["findings"]}
        run(str(HERE / "port_guard.py"), str(dirty_yarn), "--loader", "fabric", expect=3)

        # Fabric 26.3 class tweakers must be official namespace. Legacy named namespace must fail.
        dirty_tw = scaffold(root, "dirty-tweaker")
        write(dirty_tw / "src/main/resources/testmod.classtweaker", "classTweaker v1 named\naccessible class net/minecraft/Foo\n")
        dirty_audit = audit_mixins(dirty_tw, "26.3", "fabric")
        assert "fabric-26.3-class-tweaker-namespace" in {x["id"] for x in dirty_audit["blockers"]}
        run(str(HERE / "port_guard.py"), str(dirty_tw), "--loader", "fabric", expect=3)

        clean_tw = scaffold(root, "clean-tweaker")
        write(clean_tw / "src/main/resources/testmod.classtweaker", "classTweaker v1 official\naccessible class net/minecraft/Foo\n")
        clean_audit = audit_mixins(clean_tw, "26.3", "fabric")
        assert "fabric-26.3-class-tweaker-namespace" not in {x["id"] for x in clean_audit["blockers"]}
        run(str(HERE / "port_guard.py"), str(clean_tw), "--loader", "fabric")

        # Legacy Mixin selector is blocked; descriptorless official selector is warning-only static evidence.
        dirty_mixin = scaffold(root, "dirty-mixin")
        write(dirty_mixin / "src/main/java/example/BadMixin.java", '@Mixin(Target.class) class BadMixin { @Inject(method = "method_123", at = @At("HEAD")) void x() {} }\n')
        ma = audit_mixins(dirty_mixin, "26.3", "fabric")
        assert "legacy-mixin-selector" in {x["id"] for x in ma["blockers"]}
        run(str(HERE / "port_guard.py"), str(dirty_mixin), "--loader", "fabric", expect=3)

        warn_mixin = scaffold(root, "warn-mixin")
        write(warn_mixin / "src/main/java/example/WarnMixin.java", '@Mixin(Target.class) class WarnMixin { @Inject(method = "tick", at = @At("HEAD")) void x() {} }\n')
        wa = audit_mixins(warn_mixin, "26.3", "fabric")
        assert "descriptorless-mixin-selector" in {x["id"] for x in wa["warnings"]}
        assert not wa["blockers"]
        run(str(HERE / "port_guard.py"), str(warn_mixin), "--loader", "fabric")

        # Port guard can consume an exact target symbol index and fail a structurally wrong Mixin before native launch.
        _, guard_index, _ = compile_symbol_fixture(root / "guard-symbols")
        guard_index_path = root / "guard-target-index.json"
        guard_index_path.write_text(json.dumps(guard_index, indent=2) + "\n", encoding="utf-8")
        exact_guard = scaffold(root, "exact-guard")
        write(exact_guard / "src/main/java/example/ExactMixin.java", """package example;
import net.minecraft.Target;
@Mixin(Target.class) class ExactMixin { @Inject(method = "own()V", at = @At("HEAD")) void x() {} }
""")
        run(str(HERE / "port_guard.py"), str(exact_guard), "--loader", "fabric", "--target-index", str(guard_index_path))
        write(exact_guard / "src/main/java/example/ExactMixin.java", """package example;
import net.minecraft.Target;
@Mixin(Target.class) class ExactMixin { @Inject(method = "missing()V", at = @At("HEAD")) void x() {} }
""")
        run(str(HERE / "port_guard.py"), str(exact_guard), "--loader", "fabric", "--target-index", str(guard_index_path), expect=3)

        # Semantic migration planning catches non-name API/data rewrites, not just stale mappings.
        sem = semantic_plan(old_fabric, "fabric")
        sem_ids = {x["id"] for x in sem["tasks"]}
        assert "fabric-remap-configurations" in sem_ids
        assert "fabric-item-group-events-rename" in sem_ids
        assert "fabric-trade-offer-helper-data-driven" in sem_ids
        assert "legacy-fuel-compost-brewing-registry" in sem_ids
        assert "abstract-selection-list-top-level-entry" in sem_ids
        assert "screen-private-renderables-access" in sem_ids

        # Zero-loss content identity treats known 26.3 path migrations as the same semantic content.
        src_content = content_inventory(old_fabric)
        src_keys = {(x["category"], x.get("subtype"), x["id"]) for x in src_content["entries"]}
        assert ("data-registry", "worldgen/feature", "oldmod:thing") in src_keys
        assert ("mod-id", None, "oldmod:oldmod") in src_keys
        src_regs = registration_inventory(old_fabric)
        reg_keys = {(x["category"], x["id"]) for x in src_regs["entries"]}
        assert ("block", "oldmod:stone") in reg_keys
        assert ("entity_type", "oldmod:beast") in reg_keys
        reg_target = scaffold(root, "registration-target")
        reg_missing = audit_registration_parity(src_regs, reg_target, [])
        assert len(reg_missing["missing"]) == 2, reg_missing
        write(reg_target / "src/main/java/example/Registrations.java", """package example;
class Registrations {
 static final Object STONE = Registry.register(Registries.BLOCK, Identifier.parse("oldmod:stone"), null);
 static final Object BEAST = Registry.register(Registries.ENTITY_TYPE, Identifier.parse("oldmod:beast"), null);
}
""")
        reg_fixed = audit_registration_parity(src_regs, reg_target, [])
        assert not reg_fixed["missing"], reg_fixed

        # Exact class hierarchy/Mixin/access/packaged linkage proof.
        assert_exact_symbol_tools(root)
        # Whole-mod bytecode API references are mapping-bridged and checked against exact 26.3 symbols.
        assert_api_reference_migration(root)

        # Failure triage must prioritize the earliest causal compile failure before later Mixin cascades.
        triaged = triage_failure("""error: cannot find symbol\n  symbol:   class OldApi\norg.spongepowered.asm.mixin.injection.throwables.InjectionError: Critical injection failure\n""")
        assert triaged["earliest_probable_cause"]["id"] == "javac-cannot-find-symbol"
        assert "mixin-injection-failure" in {x["id"] for x in triaged["findings"]}

        # Pipeline should preserve source identity and write dedicated mapping/Mixin evidence.
        workspace = root / "workspace"
        run(str(HERE / "port_26_3_pipeline.py"), str(old_fabric), "--loader", "fabric", "--output", str(workspace), "--mod-id", "oldmod")
        ledger = json.loads((workspace / "porting-ledger.json").read_text(encoding="utf-8"))
        assert ledger["source_manifest"]["identity"]["sha256"] == fabric_intake["input"]["sha256"]
        assert ledger["source_manifest"]["mapping_plan_evidence"] == "devkit-evidence/mapping-plan.json"
        assert ledger["source_manifest"]["mixin_audit_evidence"] == "devkit-evidence/mixin-audit.json"
        assert ledger["source_manifest"]["semantic_port_plan_evidence"] == "devkit-evidence/semantic-port-plan.json"
        assert ledger["source_manifest"]["content_identity_evidence"] == "devkit-evidence/source-content-inventory.json"
        assert ledger["source_manifest"]["content_identity_count"] >= 2
        assert ledger["source_manifest"]["registration_identity_evidence"] == "devkit-evidence/source-registration-inventory.json"
        assert ledger["source_manifest"]["registration_identity_count"] == 2
        assert (workspace / "devkit-evidence/mapping-plan.json").exists()
        assert (workspace / "devkit-evidence/mixin-audit.json").exists()
        assert (workspace / "devkit-evidence/mixin-audit.md").exists()
        assert (workspace / "devkit-evidence/semantic-port-plan.json").exists()
        assert (workspace / "devkit-evidence/semantic-port-plan.md").exists()
        assert (workspace / "devkit-evidence/source-content-inventory.json").exists()
        assert (workspace / "devkit-evidence/source-registration-inventory.json").exists()
        source_content = json.loads((workspace / "devkit-evidence/source-content-inventory.json").read_text(encoding="utf-8"))
        integrated_guard = json.loads(run(str(HERE / "port_guard.py"), str(workspace), "--loader", "fabric", expect=3).stdout)
        integrated_ids = {x["id"] for x in integrated_guard["blockers"]}
        assert "content-parity-loss" in integrated_ids, integrated_ids
        assert "registration-parity-loss" in integrated_ids, integrated_ids
        parity_missing = audit_content_parity(source_content, workspace, [])
        assert any(x.get("id") == "oldmod:thing" and x.get("subtype") == "worldgen/feature" for x in parity_missing["missing"])
        write(workspace / "src/main/resources/data/oldmod/worldgen/feature/thing.json", "{}")
        parity_fixed = audit_content_parity(source_content, workspace, [])
        assert not parity_fixed["missing"], parity_fixed["missing"]
        assert any(i.get("id", "").startswith("semantic:") for i in ledger["items"])
        assert any(i.get("status") == "missing" for i in ledger["items"])
        run(str(HERE / "port_guard.py"), str(workspace), "--loader", "fabric", expect=3)

    print("Minecraft 26.3 Dev Kit port pipeline/mapping/Mixin self-test: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
