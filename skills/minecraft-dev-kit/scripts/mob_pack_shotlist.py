#!/usr/bin/env python3
"""Generate deterministic visual/runtime QA shot requirements from a mob-pack manifest."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


def as_list(v: Any) -> list[Any]:
    return v if isinstance(v, list) else []


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("manifest", type=Path)
    ap.add_argument("--output", type=Path, required=True)
    args = ap.parse_args()
    data = json.loads(args.manifest.read_text(encoding="utf-8"))
    pack = data.get("pack") if isinstance(data.get("pack"), dict) else {}
    lines = [
        f"# Premium Mob Pack QA Shot List - {pack.get('name', 'Unnamed Pack')}",
        "",
        "Use the real model/runtime. Keep camera, FOV, lighting and scale deterministic within each comparison set.",
        "",
        "## Pack lineup",
        "",
        "- [ ] all-entity scale lineup, front",
        "- [ ] all-entity scale lineup, three-quarter",
        "- [ ] silhouette/grayscale comparison",
        "- [ ] bright environment texture/material check",
        "- [ ] dark environment emissive/readability check",
        "",
    ]
    for ent in as_list(data.get("entities")):
        if not isinstance(ent, dict):
            continue
        eid = ent.get("id", "entity")
        name = ent.get("name", eid)
        kind = str(ent.get("kind", "mob")).lower()
        lines += [f"## {name} (`{eid}`)", "", "### Static/model", ""]
        for view in ("front", "three-quarter", "side", "back"):
            lines.append(f"- [ ] {view} bind/neutral")
        lines += ["- [ ] UV/texture seam close-up", "- [ ] eye/face attention close-up", "- [ ] collision/ground-contact view", "", "### Motion", ""]
        for anim in as_list(ent.get("animations")):
            lines.append(f"- [ ] `{anim}` representative non-zero frame/loop scrub")
        lines += ["", "### Combat timing", ""]
        for attack in as_list(ent.get("attacks")):
            if not isinstance(attack, dict):
                continue
            aid = attack.get("id", "attack")
            lines += [
                f"- [ ] `{aid}` 25% windup",
                f"- [ ] `{aid}` one tick/frame before impact",
                f"- [ ] `{aid}` impact: pose + hitbox + VFX + SFX",
                f"- [ ] `{aid}` one tick/frame after impact",
                f"- [ ] `{aid}` mid recovery",
            ]
        if kind == "boss":
            lines += ["", "### Boss state", "", "- [ ] prebattle/intro", "- [ ] every phase transition", "- [ ] low-health/high-pressure state", "- [ ] interrupted/canceled skill cleanup", "- [ ] multiplayer target-switch behavior"]
        lines += ["", "### Runtime/performance", "", "- [ ] native client live render", "- [ ] dedicated/integrated server authoritative state", "- [ ] low/high FPS animation check", "- [ ] stress scene with configured simultaneous-entity target", ""]
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
