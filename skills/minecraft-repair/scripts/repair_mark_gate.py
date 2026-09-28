#!/usr/bin/env python3
"""Fail closeout when a repaired Minecraft JAR lacks Repair Mark v2 integration."""
from __future__ import annotations
import argparse, json, sys
from pathlib import Path

VALID_INTEGRATIONS = {"embedded", "sidecar", "sidecar/launcher-mapping", "launcher-mapping"}


def _sha(value) -> bool:
    return isinstance(value, str) and len(value) == 64 and all(c in "0123456789abcdefABCDEF" for c in value)


def validate(record: dict) -> list[str]:
    errors: list[str] = []
    artifacts = record.get("artifacts") or []
    repaired_jars = [a for a in artifacts if str(a.get("filename", "")).lower().endswith(".jar") and any(k in str(a.get("role", "")).lower() for k in ("repair", "replacement", "fixed", "patched", "active"))]
    if not repaired_jars:
        # If the record itself is clearly a repair and has any JAR, treat it as shippable.
        repaired_jars = [a for a in artifacts if str(a.get("filename", "")).lower().endswith(".jar")]
    if not repaired_jars:
        return errors

    visual = record.get("visual_identity") or record.get("storefront_identity")
    if not isinstance(visual, dict):
        return ["missing visual_identity/storefront_identity for shippable repaired JAR"]

    if visual.get("policy") != "repair-mark-v2":
        errors.append("visual identity policy must be repair-mark-v2")
    integration = str(visual.get("integration", "")).strip().lower()
    if integration not in VALID_INTEGRATIONS:
        errors.append(f"invalid or missing integration state: {integration!r}; expected embedded or sidecar/launcher-mapping")
    if any(word in integration for word in ("defer", "pending", "skip")):
        errors.append("deferred/pending/skipped visual integration is not a valid closeout state")
    if not _sha(visual.get("normalized_art_sha256")):
        errors.append("missing/invalid normalized_art_sha256")
    if not _sha(visual.get("marked_art_sha256")):
        errors.append("missing/invalid marked_art_sha256")
    if not visual.get("official_source"):
        errors.append("missing official_source provenance")
    if "PASS" not in str(visual.get("marker_only_diff", "")).upper():
        errors.append("marker_only_diff must explicitly PASS")

    if integration == "embedded":
        if not visual.get("embedded_icon_entry"):
            errors.append("embedded integration requires embedded_icon_entry")
    else:
        pngs = [a for a in artifacts if str(a.get("filename", "")).lower().endswith(".png") and any(k in str(a.get("role", "")).lower() for k in ("repair mark", "sidecar", "badge"))]
        if not pngs:
            errors.append("sidecar integration requires a PNG Repair Mark/sidecar artifact in artifacts[]")
        mappings = [a for a in artifacts if str(a.get("filename", "")).lower().endswith(".json") and any(k in str(a.get("role", "")).lower() for k in ("badge", "launcher", "mapping", "registry"))]
        if not mappings:
            errors.append("sidecar/launcher integration requires a badge/launcher mapping JSON artifact")
        if visual.get("embedded_icon_entry") not in (None, ""):
            errors.append("sidecar integration should not claim an embedded_icon_entry")

    for jar in repaired_jars:
        if not _sha(jar.get("sha256")):
            errors.append(f"repaired JAR missing valid sha256: {jar.get('filename')}")
    return errors


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("record", type=Path, help="Repair Brain JSON record")
    args = ap.parse_args()
    try:
        record = json.loads(args.record.read_text(encoding="utf-8"))
    except Exception as exc:
        print(f"FAIL: cannot read repair record: {exc}", file=sys.stderr)
        return 2
    errors = validate(record)
    if errors:
        print("REPAIR MARK GATE: FAIL", file=sys.stderr)
        for e in errors:
            print(f"- {e}", file=sys.stderr)
        return 1
    print("REPAIR MARK GATE: PASS")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
