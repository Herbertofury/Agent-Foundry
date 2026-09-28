#!/usr/bin/env python3
"""Validate a premium Minecraft mob/boss pack manifest against production gates.

This is a static quality/completeness gate. It does not replace native Minecraft QA.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from pathlib import Path
from typing import Any, Iterable

ART_KEYS = [
    "fantasy",
    "silhouette_language",
    "palette_rules",
    "material_language",
    "texture_density",
    "scale_ladder",
    "variant_rule",
]
QA_KEYS = ["native_client", "dedicated_server", "stress", "visual_showcase"]
ATTACK_KEYS = [
    "id",
    "animation",
    "windup",
    "active",
    "recovery",
    "hitbox",
    "cooldown",
    "vfx",
    "sfx",
    "telegraph",
    "impact_marker",
    "vfx_marker",
    "sfx_marker",
    "purpose",
    "selection",
]


def load_json(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise SystemExit(f"Could not read JSON manifest {path}: {exc}")
    if not isinstance(data, dict):
        raise SystemExit("Manifest root must be a JSON object")
    return data


PLACEHOLDER_RE = ("todo", "tbd", "placeholder", "fixme", "fill this", "example only")

def is_placeholder(value: Any) -> bool:
    return isinstance(value, str) and any(token in value.strip().lower() for token in PLACEHOLDER_RE)

def nonempty(value: Any) -> bool:
    if value is None:
        return False
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, (list, dict, tuple, set)):
        return bool(value)
    return True


def as_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def as_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except Exception:
        return default


def as_float(value: Any, default: float = -1.0) -> float:
    try:
        return float(value)
    except Exception:
        return default


def add(checks: list[dict[str, Any]], level: str, code: str, message: str, entity: str | None = None) -> None:
    checks.append({"level": level, "code": code, "message": message, "entity": entity})


def has_family(names: Iterable[str], terms: Iterable[str]) -> bool:
    lowered = [str(x).lower() for x in names]
    return any(any(term in name for term in terms) for name in lowered)


def count_variants(entities: list[dict[str, Any]]) -> int:
    """Count only alternate variants with >=2 declared meaningful change dimensions."""
    valid = {"silhouette", "attachments", "palette", "materials", "animation_personality", "combat", "audio", "vfx", "environmental_role"}
    total = 0
    for ent in entities:
        for variant in as_list(ent.get("variants")):
            if not isinstance(variant, dict) or str(variant.get("id", "")) in {"", "base"}:
                continue
            changes = {str(x) for x in as_list(variant.get("changes"))} & valid
            if len(changes) >= 2 and not changes <= {"palette", "materials"}:
                total += 1
    return total


def resolve(root: Path | None, ref: str | None) -> Path | None:
    if not root or not ref:
        return None
    p = Path(ref)
    return p if p.is_absolute() else root / p


def validate_attack(ent_id: str, attack: dict[str, Any], animations: set[str], vfx: set[str], sfx: set[str], checks: list[dict[str, Any]]) -> None:
    for key in ATTACK_KEYS:
        if not nonempty(attack.get(key)):
            add(checks, "error", "attack.missing", f"Attack {attack.get('id', '<unnamed>')} is missing {key}", ent_id)
    aid = str(attack.get("id", "<unnamed>"))
    for key in ("hitbox", "telegraph", "interrupt_policy"):
        if is_placeholder(attack.get(key)):
            add(checks, "error", "attack.placeholder", f"Attack {aid} field {key} is still a placeholder", ent_id)
    anim = str(attack.get("animation", ""))
    if anim and anim not in animations:
        add(checks, "error", "attack.animation", f"Attack {aid} references animation {anim!r} not declared by the entity", ent_id)
    for key in ("windup", "active", "recovery"):
        value = as_float(attack.get(key))
        if value <= 0:
            add(checks, "error", "attack.timing", f"Attack {aid} has non-positive {key}: {attack.get(key)!r}", ent_id)
    cooldown = as_float(attack.get("cooldown"))
    if cooldown < 0:
        add(checks, "error", "attack.cooldown", f"Attack {aid} has invalid cooldown: {attack.get('cooldown')!r}", ent_id)
    windup = as_float(attack.get("windup"))
    if windup > 0 and windup < 0.10 and not attack.get("fast_untelegraphed_ok"):
        add(checks, "warning", "attack.telegraph.short", f"Attack {aid} windup is under 0.10s; confirm this is intentionally readable/fair", ent_id)
    if not nonempty(attack.get("hitbox")):
        add(checks, "error", "attack.hitbox", f"Attack {aid} lacks an explicit hitbox/shape contract", ent_id)
    avfx = str(attack.get("vfx", ""))
    asfx = str(attack.get("sfx", ""))
    if avfx and avfx not in vfx:
        add(checks, "error", "attack.vfx_ref", f"Attack {aid} references undeclared VFX {avfx!r}", ent_id)
    if asfx and asfx not in sfx:
        add(checks, "error", "attack.sfx_ref", f"Attack {aid} references undeclared SFX {asfx!r}", ent_id)


def validate_entity(ent: dict[str, Any], root: Path | None, checks: list[dict[str, Any]]) -> None:
    ent_id = str(ent.get("id", "<missing-id>"))
    for key in ("id", "name", "kind", "role", "archetype"):
        if not nonempty(ent.get(key)):
            add(checks, "error", "entity.missing", f"Entity is missing {key}", ent_id)
        elif key in {"name", "role", "archetype"} and is_placeholder(ent.get(key)):
            add(checks, "error", "entity.placeholder", f"Entity {key} is still a placeholder", ent_id)

    kind = str(ent.get("kind", "mob")).lower()
    animations = [str(x) for x in as_list(ent.get("animations")) if nonempty(x)]
    animset = set(animations)
    attacks = [x for x in as_list(ent.get("attacks")) if isinstance(x, dict)]
    vfx = as_list(ent.get("vfx"))
    sfx = as_list(ent.get("sfx"))
    vfxset = {str(x) for x in vfx if nonempty(x)}
    sfxset = {str(x) for x in sfx if nonempty(x)}
    ai = [str(x) for x in as_list(ent.get("ai_features")) if nonempty(x)]

    if len(animations) != len(animset):
        add(checks, "error", "animation.duplicate", "Entity declares duplicate animation names", ent_id)
    if not has_family(animations, ["idle"]):
        add(checks, "error", "animation.state.idle", "Missing idle animation state", ent_id)
    if not has_family(animations, ["walk", "run", "fly", "swim", "crawl", "slither", "hover"]):
        add(checks, "error", "animation.state.locomotion", "Missing locomotion animation state", ent_id)
    if not has_family(animations, ["hurt", "flinch", "stagger", "hit"]):
        add(checks, "error", "animation.state.hurt", "Missing hurt/flinch/stagger state", ent_id)
    if not has_family(animations, ["death", "die"]):
        add(checks, "error", "animation.state.death", "Missing death state", ent_id)
    if attacks and not has_family(animations, ["attack", "slash", "strike", "bite", "shoot", "cast", "slam", "combo", "skill"]):
        add(checks, "warning", "animation.state.attack", "No obvious attack animation name detected; verify attack mapping", ent_id)

    attack_ids: set[str] = set()
    for attack in attacks:
        aid = str(attack.get("id", ""))
        if aid in attack_ids and aid:
            add(checks, "error", "attack.duplicate", f"Duplicate attack id {aid!r}", ent_id)
        attack_ids.add(aid)
        validate_attack(ent_id, attack, animset, vfxset, sfxset, checks)

    if kind in {"boss", "miniboss"}:
        if as_int(ent.get("phases"), 1) < 2 and kind == "boss":
            add(checks, "error", "boss.phases", "Boss needs at least 2 authored phases for premium profile work", ent_id)
        if kind == "boss" and not has_family(animations, ["phase", "transform", "enrage", "transition"]):
            add(checks, "error", "boss.phase_animation", "Boss lacks an explicit phase/transform transition animation", ent_id)
        if len(ai) < 4:
            add(checks, "warning", "boss.ai.depth", "Boss declares fewer than 4 advanced AI/encounter features", ent_id)

    if len(attacks) < (8 if kind == "boss" else 3 if kind in {"mob", "elite", "miniboss"} else 0):
        add(checks, "warning", "combat.attack_breadth", f"Only {len(attacks)} attacks declared for {kind}; verify intended premium combat breadth", ent_id)

    perf = ent.get("performance")
    if not isinstance(perf, dict) or not perf:
        add(checks, "error", "performance.missing", "Missing explicit per-entity performance budget", ent_id)
    else:
        for key in ("bone_budget", "cube_budget", "max_vfx_concurrency"):
            if as_int(perf.get(key), 0) <= 0:
                add(checks, "warning", "performance.budget", f"Performance budget {key} is missing/non-positive", ent_id)

    if not vfx and attacks:
        add(checks, "warning", "vfx.none", "Combat entity has no declared VFX", ent_id)
    if not sfx and attacks:
        add(checks, "warning", "sfx.none", "Combat entity has no declared SFX", ent_id)

    model_ref = ent.get("model_file")
    if root is not None:
        if not nonempty(model_ref):
            add(checks, "error", "asset.model.missing", "Missing model_file for source closure", ent_id)
        else:
            p = resolve(root, str(model_ref))
            if p is None or not p.is_file():
                add(checks, "error", "asset.model.not_found", f"Model file not found: {model_ref}", ent_id)
        if kind in {"boss", "miniboss"} and not nonempty(ent.get("encounter_file")):
            add(checks, "error", "asset.encounter.missing", "Boss/miniboss needs encounter_file for state-graph QA", ent_id)
        for field in ("animation_file", "creature_spec", "encounter_file"):
            ref = ent.get(field)
            if ref:
                p = resolve(root, str(ref))
                if p is None or not p.is_file():
                    add(checks, "error", f"asset.{field}.not_found", f"File not found: {ref}", ent_id)
        if not as_list(ent.get("texture_files")):
            add(checks, "error", "asset.texture.none", "Premium entity needs at least one declared texture_file for source closure", ent_id)
        for field in ("texture_files", "sound_files"):
            for ref in as_list(ent.get(field)):
                p = resolve(root, str(ref))
                if p is None or not p.is_file():
                    add(checks, "error", f"asset.{field}.not_found", f"File not found: {ref}", ent_id)


def profile_checks(data: dict[str, Any], entities: list[dict[str, Any]], checks: list[dict[str, Any]]) -> dict[str, Any]:
    pack = data.get("pack") if isinstance(data.get("pack"), dict) else {}
    profile = str(pack.get("profile", "custom"))
    bosses = [e for e in entities if str(e.get("kind", "")).lower() == "boss"]
    minibosses = [e for e in entities if str(e.get("kind", "")).lower() == "miniboss"]
    standard_mobs = [e for e in entities if str(e.get("kind", "")).lower() in {"mob", "elite"}]
    mounts = [e for e in entities if str(e.get("kind", "")).lower() in {"mount", "pet_mount"}]
    total_animations = sum(len(as_list(e.get("animations"))) for e in entities)
    total_vfx = sum(len(as_list(e.get("vfx"))) for e in entities)
    total_sfx = sum(len(as_list(e.get("sfx"))) for e in entities)
    variants = count_variants(entities)
    roles = {str(e.get("role", "")).strip().lower() for e in entities if nonempty(e.get("role"))}
    archetypes = {str(e.get("archetype", "")).strip().lower() for e in entities if nonempty(e.get("archetype"))}
    sidecars = data.get("sidecars") if isinstance(data.get("sidecars"), dict) else {}
    sidecar_count = sum(len(as_list(sidecars.get(k))) for k in ("equipment", "drops", "props", "items"))

    metrics = {
        "profile": profile,
        "entities": len(entities),
        "standard_mobs": len(standard_mobs),
        "bosses": len(bosses),
        "minibosses": len(minibosses),
        "mounts": len(mounts),
        "variants": variants,
        "roles": len(roles),
        "archetypes": len(archetypes),
        "animations": total_animations,
        "vfx": total_vfx,
        "sfx": total_sfx,
        "sidecars": sidecar_count,
    }

    def require(cond: bool, code: str, message: str) -> None:
        if not cond:
            add(checks, "error", code, message)

    if profile == "boss-mega-2026":
        require(len(bosses) >= 6, "profile.boss_count", f"boss-mega-2026 requires at least 6 bosses; found {len(bosses)}")
        require(total_animations >= 72, "profile.animation_total", f"boss-mega-2026 requires at least 72 total animations; found {total_animations}")
        require(total_vfx >= 60, "profile.vfx_total", f"boss-mega-2026 requires at least 60 VFX; found {total_vfx}")
        require(total_sfx >= 48, "profile.sfx_total", f"boss-mega-2026 requires at least 48 SFX; found {total_sfx}")
        require(len(roles) >= 4, "profile.boss_roles", f"boss-mega-2026 requires at least 4 distinct combat roles; found {len(roles)}")
        require(len(archetypes) >= 4, "profile.boss_archetypes", f"boss-mega-2026 requires at least 4 distinct archetype identities; found {len(archetypes)}")
        for boss in bosses:
            bid = str(boss.get("id", "<boss>"))
            if as_int(boss.get("phases"), 0) < 2:
                add(checks, "error", "profile.boss_phase", "Boss-mega boss must have at least 2 phases", bid)
            if len(as_list(boss.get("attacks"))) < 10:
                add(checks, "error", "profile.boss_attacks", "Boss-mega boss must have at least 10 authored attacks", bid)
            if len(as_list(boss.get("animations"))) < 18:
                add(checks, "error", "profile.boss_animations", "Boss-mega boss must have at least 18 animations", bid)
    elif profile == "mob-mega-2026":
        require(len(standard_mobs) >= 12, "profile.mob_count", f"mob-mega-2026 requires at least 12 standard mobs; found {len(standard_mobs)}")
        require(len(bosses) + len(minibosses) >= 3, "profile.boss_count", f"mob-mega-2026 requires at least 3 bosses/minibosses; found {len(bosses) + len(minibosses)}")
        require(variants >= 6, "profile.variants", f"mob-mega-2026 requires at least 6 meaningful alternate variants; found {variants}")
        require(sidecar_count >= 6, "profile.sidecars", f"mob-mega-2026 requires at least 6 sidecar gameplay assets; found {sidecar_count}")
        require(len(roles) >= 5, "profile.roles", f"mob-mega-2026 requires at least 5 distinct combat/ecology roles; found {len(roles)}")
    elif profile == "supreme-boss-2026":
        require(len(bosses) >= 1, "profile.boss_count", "supreme-boss-2026 requires at least one boss")
        if bosses:
            best = max(bosses, key=lambda b: len(as_list(b.get("animations"))))
            bid = str(best.get("id", "<boss>"))
            if as_int(best.get("phases"), 0) < 2:
                add(checks, "error", "profile.supreme.phases", "Supreme boss requires at least 2 phases", bid)
            if len(as_list(best.get("attacks"))) < 12:
                add(checks, "error", "profile.supreme.attacks", "Supreme boss requires at least 12 authored attacks", bid)
            if len(as_list(best.get("animations"))) < 32:
                add(checks, "error", "profile.supreme.animations", "Supreme boss requires at least 32 animations", bid)
            if len(as_list(best.get("vfx"))) < 10:
                add(checks, "error", "profile.supreme.vfx", "Supreme boss requires at least 10 VFX", bid)
            if len(as_list(best.get("sfx"))) < 8:
                add(checks, "error", "profile.supreme.sfx", "Supreme boss requires at least 8 SFX", bid)
            if len(as_list(best.get("ai_features"))) < 6:
                add(checks, "error", "profile.supreme.ai", "Supreme boss requires at least 6 advanced AI/encounter features", bid)
    elif profile != "custom":
        add(checks, "error", "profile.unknown", f"Unknown profile {profile!r}")

    return metrics


def validate(data: dict[str, Any], root: Path | None) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    checks: list[dict[str, Any]] = []
    if data.get("schema_version") != 1:
        add(checks, "error", "schema.version", "schema_version must be 1")

    pack = data.get("pack") if isinstance(data.get("pack"), dict) else {}
    for key in ("id", "name", "profile", "minecraft", "loader"):
        if not nonempty(pack.get(key)):
            add(checks, "error", "pack.missing", f"Pack is missing {key}")

    art = data.get("art_direction") if isinstance(data.get("art_direction"), dict) else {}
    for key in ART_KEYS:
        if not nonempty(art.get(key)):
            add(checks, "error", "art_direction.missing", f"Art direction is missing {key}")
        elif is_placeholder(art.get(key)):
            add(checks, "error", "art_direction.placeholder", f"Art direction {key} is still a placeholder")

    qa = data.get("qa") if isinstance(data.get("qa"), dict) else {}
    for key in QA_KEYS:
        if not nonempty(qa.get(key)):
            add(checks, "error", "qa.missing", f"QA plan is missing/non-empty {key}")
    stress = qa.get("stress") if isinstance(qa.get("stress"), dict) else {}
    if as_int(stress.get("simultaneous_entities"), 0) <= 0:
        add(checks, "error", "qa.stress", "QA stress plan must set simultaneous_entities > 0")

    controls = data.get("controls") if isinstance(data.get("controls"), dict) else {}
    if not nonempty(controls.get("tuning")):
        add(checks, "error", "controls.tuning", "Pack needs documented/data-driven tuning controls")
    if not nonempty(controls.get("documentation")):
        add(checks, "error", "controls.documentation", "Pack needs installation/developer/admin documentation plan")

    entities = [x for x in as_list(data.get("entities")) if isinstance(x, dict)]
    if not entities:
        add(checks, "error", "entities.empty", "Manifest contains no entities")
    ids: set[str] = set()
    for ent in entities:
        ent_id = str(ent.get("id", ""))
        if ent_id and ent_id in ids:
            add(checks, "error", "entity.duplicate_id", f"Duplicate entity id {ent_id!r}", ent_id)
        ids.add(ent_id)
        validate_entity(ent, root, checks)

    metrics = profile_checks(data, entities, checks)
    return checks, metrics


def markdown_report(manifest: Path, checks: list[dict[str, Any]], metrics: dict[str, Any]) -> str:
    errors = [c for c in checks if c["level"] == "error"]
    warnings = [c for c in checks if c["level"] == "warning"]
    lines = [
        "# Premium Mob Pack Gate",
        "",
        f"- Manifest: `{manifest}`",
        f"- Result: **{'PASS' if not errors else 'FAIL'}**",
        f"- Errors: **{len(errors)}**",
        f"- Warnings: **{len(warnings)}**",
        "",
        "## Benchmark metrics",
        "",
    ]
    for key, value in metrics.items():
        lines.append(f"- {key}: **{value}**")
    lines.extend(["", "## Findings", ""])
    if not checks:
        lines.append("- No static findings.")
    else:
        for c in checks:
            ent = f" [{c['entity']}]" if c.get("entity") else ""
            lines.append(f"- **{c['level'].upper()}** `{c['code']}`{ent}: {c['message']}")
    lines.extend([
        "",
        "## Interpretation",
        "",
        "This gate checks declared production completeness and public-benchmark-equivalent scope. It does **not** prove visual artistry, animation feel, balance, audio quality, server performance, or native runtime behavior. Those still require real visual/runtime QA.",
    ])
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("manifest", type=Path)
    parser.add_argument("--root", type=Path, default=None, help="Optional project/source root for referenced file closure")
    parser.add_argument("--json", type=Path, dest="json_out")
    parser.add_argument("--markdown", type=Path, dest="md_out")
    args = parser.parse_args()

    data = load_json(args.manifest)
    root = args.root.resolve() if args.root else None
    checks, metrics = validate(data, root)
    errors = [c for c in checks if c["level"] == "error"]
    payload = {
        "manifest": str(args.manifest),
        "manifest_sha256": hashlib.sha256(args.manifest.read_bytes()).hexdigest(),
        "result": "pass" if not errors else "fail",
        "errors": len(errors),
        "warnings": sum(1 for c in checks if c["level"] == "warning"),
        "metrics": metrics,
        "findings": checks,
    }
    report = markdown_report(args.manifest, checks, metrics)
    if args.json_out:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    if args.md_out:
        args.md_out.parent.mkdir(parents=True, exist_ok=True)
        args.md_out.write_text(report, encoding="utf-8")
    if not args.md_out:
        sys.stdout.write(report)
    return 0 if not errors else 2


if __name__ == "__main__":
    raise SystemExit(main())
