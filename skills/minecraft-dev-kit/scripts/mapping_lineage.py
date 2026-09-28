#!/usr/bin/env python3
"""Plan, fetch, normalize, and query mapping lineage for Minecraft ports into unobfuscated 26.3.

The target (26.1+) is unobfuscated, so this tool is intentionally source-lineage focused:
it recovers historical Mojang/Yarn/Intermediary/SRG/MCP names and exact descriptors without
inventing a fake mapping namespace for 26.3.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path
from typing import Iterable

ROOT = Path(__file__).resolve().parent.parent
CATALOG_PATH = ROOT / "references" / "minecraft-mapping-sources.json"
USER_AGENT = "Minecraft-Dev-Kit/26.3 mapping-lineage"


def load_catalog() -> dict:
    return json.loads(CATALOG_PATH.read_text(encoding="utf-8"))


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def version_tuple(value: str) -> tuple[int, ...]:
    # Release versions only for ordering decisions. Snapshot/pre/rc suffixes are ignored deliberately.
    nums = [int(x) for x in re.findall(r"\d+", value.split("-")[0])]
    return tuple(nums or [0])


def at_least(version: str, floor: str) -> bool:
    a, b = version_tuple(version), version_tuple(floor)
    n = max(len(a), len(b))
    return a + (0,) * (n - len(a)) >= b + (0,) * (n - len(b))


def at_most(version: str, ceiling: str) -> bool:
    a, b = version_tuple(version), version_tuple(ceiling)
    n = max(len(a), len(b))
    return a + (0,) * (n - len(a)) <= b + (0,) * (n - len(b))


def source_plan(source_version: str, loader: str, mapping_hint: str | None = None) -> dict:
    loader = loader.lower()
    if loader not in {"forge", "neoforge", "fabric", "quilt", "unknown"}:
        raise ValueError(f"unsupported loader {loader!r}")
    sources: list[dict] = []
    unobfuscated_source = at_least(source_version, "26.1")
    if unobfuscated_source:
        sources.append({
            "id": "source_identity_official",
            "required": True,
            "status": "identity",
            "reason": f"Minecraft {source_version} is in the unobfuscated 26.1+ era; shipped names are official names.",
        })
    else:
        if at_least(source_version, "1.14"):
            sources.append({
                "id": "mojang_official", "required": True, "status": "fetch",
                "reason": "Join source obfuscated names to Mojang official names and descriptors.",
            })
        if loader in {"fabric", "quilt"}:
            sources.append({
                "id": "fabric_intermediary", "required": True, "status": "fetch",
                "reason": "Resolve production intermediary class_/method_/field_ names used by historical Fabric mods and refmaps.",
            })
            if not at_least(source_version, "26.1"):
                sources.append({
                    "id": "fabric_yarn", "required": True, "status": "fetch-latest-for-version",
                    "reason": "Resolve historical Yarn named source identifiers before migration to official 26.3 names.",
                })
        if loader in {"forge", "neoforge"}:
            if at_most(source_version, "1.16.5"):
                sources.append({
                    "id": "forge_mcpconfig", "required": True, "status": "fetch",
                    "reason": "Resolve obfuscated <-> SRG/TSRG owners and exact descriptors.",
                })
            if at_most(source_version, "1.12.2"):
                sources.append({
                    "id": "forge_mcp_srg_legacy", "required": True, "status": "fetch",
                    "reason": "Preserve legacy SRG structural mappings used by ForgeGradle 2.x-era projects.",
                })
                sources.append({
                    "id": "forge_mcp_named_legacy",
                    "required": bool(mapping_hint),
                    "status": "derive-from-source" if mapping_hint else "needs-source-mapping-hint",
                    "mapping_hint": mapping_hint,
                    "reason": "Recover MCP human method/field names used by legacy source; exact stable/snapshot must come from the source build when possible.",
                })
    return {
        "schema_version": 1,
        "target": {"minecraft": "26.3", "namespace": "official", "obfuscated": False},
        "source": {"minecraft": source_version, "loader": loader, "mapping_hint": mapping_hint, "unobfuscated": unobfuscated_source},
        "sources": sources,
        "mixin_rule": "Names alone are never sufficient for Mixins: preserve owner + member + JVM descriptor + injector/ordinal/slice/local semantics and validate in a real target runtime.",
    }


def request_bytes(url: str, timeout: int = 45) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=timeout) as response:
        return response.read()


def fetch_to(url: str, dest: Path) -> dict:
    data = request_bytes(url)
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(data)
    return {"url": url, "path": str(dest), "size": len(data), "sha256": sha256_bytes(data)}


def _catalog_by_id() -> dict[str, dict]:
    return {x["id"]: x for x in load_catalog()["sources"]}


def _mojang_version_json(version: str) -> tuple[dict, dict]:
    catalog = _catalog_by_id()["mojang_official"]
    manifest_url = catalog["manifest_url"]
    manifest_bytes = request_bytes(manifest_url)
    manifest = json.loads(manifest_bytes)
    entry = next((x for x in manifest.get("versions", []) if x.get("id") == version), None)
    if not entry:
        raise RuntimeError(f"Minecraft version {version!r} is absent from Mojang version manifest")
    version_bytes = request_bytes(entry["url"])
    return json.loads(version_bytes), {
        "manifest_url": manifest_url,
        "manifest_sha256": sha256_bytes(manifest_bytes),
        "version_url": entry["url"],
        "version_json_sha256": sha256_bytes(version_bytes),
    }


def fetch_mojang(version: str, out: Path) -> list[dict]:
    version_json, meta = _mojang_version_json(version)
    results: list[dict] = [{"id": "mojang_metadata", **meta}]
    downloads = version_json.get("downloads") or {}
    found = False
    for key in ("client_mappings", "server_mappings"):
        item = downloads.get(key)
        if not item:
            continue
        found = True
        dest = out / f"mojang-{version}-{key}.txt"
        rec = fetch_to(item["url"], dest)
        rec.update({"id": f"mojang_{key}", "declared_sha1": item.get("sha1"), "declared_size": item.get("size")})
        results.append(rec)
    if not found:
        results.append({
            "id": "mojang_mappings_absent",
            "status": "expected-for-unobfuscated" if at_least(version, "26.1") else "missing",
            "message": "No client/server mapping downloads are published in this version JSON.",
        })
    return results


def _extract_mapping_jar(jar_path: Path, dest: Path, preferred: str = "mappings/mappings.tiny") -> dict:
    with zipfile.ZipFile(jar_path) as zf:
        names = zf.namelist()
        name = preferred if preferred in names else next((n for n in names if n.endswith(".tiny")), None)
        if not name:
            raise RuntimeError(f"no Tiny mapping entry found in {jar_path}")
        data = zf.read(name)
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(data)
    return {"archive": str(jar_path), "entry": name, "path": str(dest), "size": len(data), "sha256": sha256_bytes(data)}


def fetch_intermediary(version: str, out: Path) -> list[dict]:
    src = _catalog_by_id()["fabric_intermediary"]
    url = src["url_template"].format(minecraft=version)
    jar = out / f"fabric-intermediary-{version}-v2.jar"
    rec = fetch_to(url, jar)
    tiny = _extract_mapping_jar(jar, out / f"fabric-intermediary-{version}.tiny", src["jar_entry"])
    return [{"id": "fabric_intermediary_jar", **rec}, {"id": "fabric_intermediary_tiny", **tiny}]


def _latest_yarn_coordinate(version: str) -> tuple[str, dict]:
    src = _catalog_by_id()["fabric_yarn"]
    raw = request_bytes(src["metadata_url"])
    root = ET.fromstring(raw)
    versions = [e.text for e in root.findall("./versioning/versions/version") if e.text]
    prefix = version + "+build."
    candidates = [x for x in versions if x.startswith(prefix)]
    if not candidates:
        # Some versions use a non-build suffix. Keep exact-version-prefixed candidates as a fallback.
        candidates = [x for x in versions if x.startswith(version + "+") or x == version]
    if not candidates:
        raise RuntimeError(f"no Yarn coordinate found for Minecraft {version}")

    def sort_key(value: str) -> tuple:
        m = re.search(r"\+build\.(\d+)", value)
        return (int(m.group(1)) if m else -1, value)

    chosen = sorted(candidates, key=sort_key)[-1]
    return chosen, {"metadata_url": src["metadata_url"], "metadata_sha256": sha256_bytes(raw), "candidate_count": len(candidates)}


def fetch_yarn(version: str, out: Path) -> list[dict]:
    src = _catalog_by_id()["fabric_yarn"]
    coord, meta = _latest_yarn_coordinate(version)
    encoded = urllib.parse.quote(coord, safe="+.-_")
    url = src["artifact_url_template"].format(coordinate=encoded)
    jar = out / f"fabric-yarn-{coord}-v2.jar"
    rec = fetch_to(url, jar)
    tiny = _extract_mapping_jar(jar, out / f"fabric-yarn-{coord}.tiny", src["jar_entry"])
    return [
        {"id": "fabric_yarn_metadata", "coordinate": coord, **meta},
        {"id": "fabric_yarn_jar", "coordinate": coord, **rec},
        {"id": "fabric_yarn_tiny", "coordinate": coord, **tiny},
    ]


def fetch_mcpconfig(version: str, out: Path) -> list[dict]:
    src = _catalog_by_id()["forge_mcpconfig"]
    url = src["url_template"].format(minecraft=version)
    rec = fetch_to(url, out / f"mcpconfig-{version}-joined.tsrg")
    return [{"id": "forge_mcpconfig", **rec}]


def _extract_zip_suffixes(zip_path: Path, out: Path, suffixes: tuple[str, ...], prefix: str) -> list[dict]:
    extracted = []
    with zipfile.ZipFile(zip_path) as zf:
        for name in zf.namelist():
            low = name.lower()
            if not any(low.endswith(s) for s in suffixes):
                continue
            data = zf.read(name)
            dest = out / f"{prefix}-{Path(name).name}"
            dest.write_bytes(data)
            extracted.append({"archive": str(zip_path), "entry": name, "path": str(dest), "size": len(data), "sha256": sha256_bytes(data)})
    return extracted


def fetch_legacy_srg(version: str, out: Path) -> list[dict]:
    src = _catalog_by_id()["forge_mcp_srg_legacy"]
    url = src["url_template"].format(minecraft=version)
    zip_path = out / f"mcp-{version}-srg.zip"
    rec = fetch_to(url, zip_path)
    records = [{"id": "forge_mcp_srg_legacy", **rec}]
    try:
        for ext in _extract_zip_suffixes(zip_path, out, ("joined.srg", "joined.tsrg"), f"mcp-{version}"):
            records.append({"id": "forge_mcp_srg_legacy_extracted", **ext})
    except zipfile.BadZipFile:
        raise
    return records


def parse_mapping_hint(hint: str | None, source_version: str) -> dict | None:
    if not hint:
        return None
    hint = hint.strip().strip("'\"")
    # ForgeGradle 2 forms: snapshot_20171003 / stable_39. Newer channel/version forms are normalized too.
    m = re.search(r"\b(snapshot|stable)[_:\-]?([0-9.]+)\b", hint, re.I)
    if not m:
        return {"raw": hint, "resolved": False}
    channel, value = m.group(1).lower(), m.group(2)
    parts = source_version.split(".")
    # FG2-era MCP named zips commonly key 1.12.2 to the 1.12 mapping line. Preserve a conservative default.
    base = ".".join(parts[:2]) if source_version.startswith(("1.10.", "1.11.", "1.12.")) else source_version
    artifact = "mcp_snapshot" if channel == "snapshot" else "mcp_stable"
    coord = f"{value}-{base}"
    return {
        "raw": hint,
        "resolved": True,
        "channel": channel,
        "value": value,
        "minecraft_base": base,
        "coordinate": coord,
        "url": f"https://maven.minecraftforge.net/de/oceanlabs/mcp/{artifact}/{coord}/{artifact}-{coord}.zip",
    }


def fetch_legacy_named(source_version: str, hint: str | None, out: Path) -> list[dict]:
    resolved = parse_mapping_hint(hint, source_version)
    if not resolved or not resolved.get("resolved"):
        return [{"id": "forge_mcp_named_legacy", "status": "not-fetched", "reason": "exact source MCP stable/snapshot mapping declaration was not resolved", "hint": hint}]
    dest = out / f"{resolved['coordinate']}-{resolved['channel']}-mcp.zip"
    rec = fetch_to(resolved["url"], dest)
    records = [{"id": "forge_mcp_named_legacy", **resolved, **rec}]
    for ext in _extract_zip_suffixes(dest, out, ("fields.csv", "methods.csv", "params.csv"), resolved["coordinate"]):
        records.append({"id": "forge_mcp_named_legacy_extracted", **resolved, **ext})
    return records


def harvest(source_version: str, loader: str, cache: Path, mapping_hint: str | None = None, include_optional: bool = False) -> dict:
    cache = cache.resolve()
    cache.mkdir(parents=True, exist_ok=True)
    plan = source_plan(source_version, loader, mapping_hint)
    records: list[dict] = []
    for source in plan["sources"]:
        sid = source["id"]
        try:
            if sid == "source_identity_official":
                records.append({"id": sid, "status": "identity", "minecraft": source_version})
            elif sid == "mojang_official":
                records.extend(fetch_mojang(source_version, cache))
            elif sid == "fabric_intermediary":
                records.extend(fetch_intermediary(source_version, cache))
            elif sid == "fabric_yarn":
                records.extend(fetch_yarn(source_version, cache))
            elif sid == "forge_mcpconfig":
                records.extend(fetch_mcpconfig(source_version, cache))
            elif sid == "forge_mcp_srg_legacy":
                records.extend(fetch_legacy_srg(source_version, cache))
            elif sid == "forge_mcp_named_legacy":
                records.extend(fetch_legacy_named(source_version, mapping_hint, cache))
        except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, RuntimeError, zipfile.BadZipFile) as exc:
            records.append({"id": sid, "status": "fetch-failed", "error": f"{type(exc).__name__}: {exc}"})
    # Normalize every directly parseable mapping artifact now so downstream conversion code can
    # query deterministic JSON indexes instead of reparsing mapping formats ad hoc.
    source_id_for_record = {
        "mojang_client_mappings": "mojang_official",
        "mojang_server_mappings": "mojang_official",
        "fabric_intermediary_tiny": "fabric_intermediary",
        "fabric_yarn_tiny": "fabric_yarn",
        "forge_mcpconfig": "forge_mcpconfig",
        "forge_mcp_srg_legacy_extracted": "forge_mcp_srg_legacy",
        "forge_mcp_named_legacy_extracted": "forge_mcp_named_legacy",
    }
    for rec in records:
        path_value = rec.get("path")
        source_id = source_id_for_record.get(rec.get("id"))
        if not path_value or not source_id:
            continue
        path = Path(path_value)
        if path.suffix.lower() not in {".txt", ".tiny", ".tsrg", ".srg", ".csv"}:
            continue
        try:
            normalized = normalize_file(path, "auto", source_id, source_version)
            index_path = path.with_suffix(path.suffix + ".normalized.json")
            write_json(index_path, normalized)
            rec["normalized_index"] = str(index_path)
            rec["normalized_sha256"] = sha256_file(index_path)
            rec["normalized_counts"] = normalized["counts"]
        except Exception as exc:
            rec["normalize_error"] = f"{type(exc).__name__}: {exc}"

    result = {
        "schema_version": 2,
        "plan": plan,
        "cache": str(cache),
        "records": records,
        "complete": all(r.get("status") != "fetch-failed" and not r.get("normalize_error") for r in records),
    }
    write_json(cache / "mapping-harvest.json", result)
    return result


# ------------------------ normalization ------------------------

def detect_format(path: Path, text: str | None = None) -> str:
    low = path.name.lower()
    if low.endswith(".tiny"):
        return "tiny_v2"
    if low.endswith(".srg"):
        return "srg"
    if low.endswith(".tsrg"):
        if text is None:
            text = path.read_text(encoding="utf-8", errors="replace")
        return "tsrg2" if text.lstrip().startswith("tsrg2 ") else "tsrg"
    if low.endswith(".csv"):
        return "mcp_csv"
    if text is None:
        text = path.read_text(encoding="utf-8", errors="replace")
    first = next((x.strip() for x in text.splitlines() if x.strip()), "")
    if first.startswith("tiny\t2\t"):
        return "tiny_v2"
    if first.startswith("tsrg2 "):
        return "tsrg2"
    if first.startswith(("CL: ", "FD: ", "MD: ")):
        return "srg"
    if " -> " in first and first.endswith(":"):
        return "proguard"
    raise ValueError(f"unable to detect mapping format for {path}")


def parse_tiny_v2(text: str) -> dict:
    lines = text.splitlines()
    if not lines or not lines[0].startswith("tiny\t2\t"):
        raise ValueError("not Tiny v2")
    header = lines[0].split("\t")
    namespaces = header[3:]
    classes, fields, methods = [], [], []
    owner_names: dict[str, str] | None = None
    for raw in lines[1:]:
        if not raw or raw.startswith("#"):
            continue
        depth = len(raw) - len(raw.lstrip("\t"))
        parts = raw.lstrip("\t").split("\t")
        if depth == 0 and parts[0] == "c":
            names = dict(zip(namespaces, parts[1:1 + len(namespaces)]))
            owner_names = names
            classes.append({"names": names})
        elif depth == 1 and owner_names and parts[0] in {"m", "f"}:
            desc = parts[1]
            names = dict(zip(namespaces, parts[2:2 + len(namespaces)]))
            row = {"owner": owner_names.copy(), "descriptor": desc, "descriptor_namespace": namespaces[0], "names": names}
            (methods if parts[0] == "m" else fields).append(row)
    return {"format": "tiny_v2", "namespaces": namespaces, "classes": classes, "fields": fields, "methods": methods}


def parse_tsrg(text: str, force_v2: bool | None = None) -> dict:
    lines = [x.rstrip() for x in text.splitlines() if x.strip()]
    is_v2 = bool(lines and lines[0].startswith("tsrg2 ")) if force_v2 is None else force_v2
    namespaces = lines[0].split()[1:] if is_v2 else ["obfuscated", "srg"]
    body = lines[1:] if is_v2 else lines
    classes, fields, methods = [], [], []
    owner: dict[str, str] | None = None
    for raw in body:
        depth = len(raw) - len(raw.lstrip("\t"))
        if depth >= 2:
            continue
        parts = raw.strip().split()
        if depth == 0:
            if len(parts) < 2:
                continue
            names = dict(zip(namespaces, parts[:len(namespaces)]))
            owner = names
            classes.append({"names": names})
            continue
        if not owner or len(parts) < 2:
            continue
        # TSRG methods carry a JVM descriptor as the second token; fields generally do not.
        if len(parts) >= 3 and parts[1].startswith("("):
            src_name, desc = parts[0], parts[1]
            target_names = [src_name] + parts[2:2 + max(1, len(namespaces) - 1)]
            names = dict(zip(namespaces, target_names))
            methods.append({"owner": owner.copy(), "descriptor": desc, "descriptor_namespace": namespaces[0], "names": names})
        else:
            target_names = parts[:len(namespaces)]
            names = dict(zip(namespaces, target_names))
            fields.append({"owner": owner.copy(), "descriptor": None, "names": names})
    return {"format": "tsrg2" if is_v2 else "tsrg", "namespaces": namespaces, "classes": classes, "fields": fields, "methods": methods}


def parse_srg(text: str) -> dict:
    namespaces = ["obfuscated", "srg"]
    classes, fields, methods = [], [], []
    for raw in text.splitlines():
        parts = raw.split()
        if not parts:
            continue
        if parts[0] == "CL:" and len(parts) >= 3:
            classes.append({"names": {"obfuscated": parts[1], "srg": parts[2]}})
        elif parts[0] == "FD:" and len(parts) >= 3:
            so, sn = parts[1].rsplit("/", 1)
            to, tn = parts[2].rsplit("/", 1)
            fields.append({"owner": {"obfuscated": so, "srg": to}, "descriptor": None, "names": {"obfuscated": sn, "srg": tn}})
        elif parts[0] == "MD:" and len(parts) >= 5:
            so, sn = parts[1].rsplit("/", 1)
            to, tn = parts[3].rsplit("/", 1)
            methods.append({"owner": {"obfuscated": so, "srg": to}, "descriptor": parts[2], "descriptor_namespace": "obfuscated", "target_descriptor": parts[4], "target_descriptor_namespace": "srg", "names": {"obfuscated": sn, "srg": tn}})
    return {"format": "srg", "namespaces": namespaces, "classes": classes, "fields": fields, "methods": methods}


_PRIMITIVES = {
    "void": "V", "boolean": "Z", "byte": "B", "char": "C", "short": "S", "int": "I",
    "long": "J", "float": "F", "double": "D",
}


def _erase_generics(value: str) -> str:
    out, depth = [], 0
    for ch in value:
        if ch == "<":
            depth += 1
        elif ch == ">":
            depth = max(0, depth - 1)
        elif depth == 0:
            out.append(ch)
    return "".join(out)


def java_type_descriptor(value: str, class_to_obf: dict[str, str]) -> str:
    value = _erase_generics(value.strip())
    dims = 0
    while value.endswith("[]"):
        dims += 1
        value = value[:-2]
    if value.endswith("..."):
        dims += 1
        value = value[:-3]
    base = _PRIMITIVES.get(value)
    if not base:
        internal = class_to_obf.get(value, value.replace(".", "/"))
        base = f"L{internal};"
    return "[" * dims + base


def parse_proguard(text: str) -> dict:
    # Mojang mapping files are official -> obfuscated ProGuard mappings.
    class_map: dict[str, str] = {}
    for raw in text.splitlines():
        if raw.startswith(" "):
            continue
        m = re.match(r"^(.+?) -> ([^:]+):$", raw.strip())
        if m:
            class_map[m.group(1)] = m.group(2).replace(".", "/")
    classes = [{"names": {"mojang_named": k.replace(".", "/"), "obfuscated": v}} for k, v in class_map.items()]
    fields, methods = [], []
    current_official: str | None = None
    current_obf: str | None = None
    for raw in text.splitlines():
        if not raw.startswith(" "):
            m = re.match(r"^(.+?) -> ([^:]+):$", raw.strip())
            if m:
                current_official, current_obf = m.group(1), m.group(2).replace(".", "/")
            continue
        if not current_official or not current_obf:
            continue
        line = raw.strip()
        # Strip optional ProGuard line number prefixes/suffixes.
        line = re.sub(r"^\d+:\d+:", "", line)
        line = re.sub(r":\d+:\d+(?= -> )", "", line)
        if " -> " not in line:
            continue
        left, obf_name = line.rsplit(" -> ", 1)
        owner = {"mojang_named": current_official.replace(".", "/"), "obfuscated": current_obf}
        mm = re.match(r"^(.+?)\s+([^\s(]+)\((.*)\)$", left)
        if mm:
            ret, name, args = mm.groups()
            arg_types = [] if not args.strip() else [x.strip() for x in args.split(",")]
            desc = "(" + "".join(java_type_descriptor(x, class_map) for x in arg_types) + ")" + java_type_descriptor(ret, class_map)
            methods.append({"owner": owner, "descriptor": desc, "descriptor_namespace": "obfuscated", "names": {"mojang_named": name, "obfuscated": obf_name}})
            continue
        fm = re.match(r"^(.+?)\s+([^\s]+)$", left)
        if fm:
            typ, name = fm.groups()
            fields.append({"owner": owner, "descriptor": java_type_descriptor(typ, class_map), "descriptor_namespace": "obfuscated", "names": {"mojang_named": name, "obfuscated": obf_name}})
    return {"format": "proguard", "namespaces": ["mojang_named", "obfuscated"], "classes": classes, "fields": fields, "methods": methods}


def parse_mcp_csv(text: str) -> dict:
    rows = list(csv.DictReader(io.StringIO(text)))
    aliases = []
    for row in rows:
        srg = row.get("searge") or row.get("srg") or row.get("param")
        name = row.get("name")
        if srg and name:
            aliases.append({"srg": srg, "mcp_named": name, "side": row.get("side"), "desc": row.get("desc")})
    return {"format": "mcp_csv", "namespaces": ["srg", "mcp_named"], "aliases": aliases, "classes": [], "fields": [], "methods": []}


def _rename_namespace(result: dict, old: str, new: str) -> None:
    if old == new or old not in result.get("namespaces", []):
        return
    result["namespaces"] = [new if x == old else x for x in result.get("namespaces", [])]
    for section in ("classes", "fields", "methods"):
        for row in result.get(section, []):
            for key in ("names", "owner"):
                values = row.get(key)
                if isinstance(values, dict) and old in values:
                    values[new] = values.pop(old)
            if row.get("descriptor_namespace") == old:
                row["descriptor_namespace"] = new
            if row.get("target_descriptor_namespace") == old:
                row["target_descriptor_namespace"] = new


def canonicalize_namespaces(result: dict, source_id: str | None = None, source_version: str | None = None) -> dict:
    """Disambiguate mapping-system namespace labels without erasing their historical meaning."""
    aliases = {}
    if source_id == "fabric_intermediary":
        if source_version and not at_least(source_version, "26.1"):
            aliases["official"] = "obfuscated"
    elif source_id == "fabric_yarn":
        aliases["named"] = "yarn_named"
        if source_version and not at_least(source_version, "26.1"):
            aliases["official"] = "obfuscated"
    for old, new in aliases.items():
        _rename_namespace(result, old, new)
    result["namespace_semantics"] = {
        "source_id": source_id,
        "source_version": source_version,
        "aliases_applied": aliases,
        "note": "Do not equate historical Fabric 'official' on obfuscated releases with unobfuscated 26.3 target names. Mojang readable ProGuard names are normalized as mojang_named."
    }
    return result


def normalize_file(path: Path, fmt: str = "auto", source_id: str | None = None, source_version: str | None = None) -> dict:
    text = path.read_text(encoding="utf-8", errors="replace")
    fmt = detect_format(path, text) if fmt == "auto" else fmt
    if fmt == "tiny_v2":
        result = parse_tiny_v2(text)
    elif fmt in {"tsrg", "tsrg2"}:
        result = parse_tsrg(text, fmt == "tsrg2")
    elif fmt == "srg":
        result = parse_srg(text)
    elif fmt == "proguard":
        result = parse_proguard(text)
    elif fmt == "mcp_csv":
        result = parse_mcp_csv(text)
    else:
        raise ValueError(f"unsupported mapping format {fmt}")
    canonicalize_namespaces(result, source_id, source_version)
    result.update({
        "schema_version": 1,
        "source_path": str(path.resolve()),
        "source_sha256": sha256_file(path),
        "counts": {k: len(result.get(k, [])) for k in ("classes", "fields", "methods", "aliases")},
    })
    return result


def query_index(index: dict, namespace: str, class_name: str, member: str | None = None, descriptor: str | None = None) -> list[dict]:
    class_name = class_name.replace(".", "/")
    results = []
    if member is None:
        for row in index.get("classes", []):
            if row.get("names", {}).get(namespace) == class_name:
                results.append(row)
        return results
    for kind in ("fields", "methods"):
        for row in index.get(kind, []):
            if row.get("owner", {}).get(namespace) != class_name:
                continue
            if row.get("names", {}).get(namespace) != member:
                continue
            if descriptor and row.get("descriptor") != descriptor:
                continue
            results.append({"kind": kind[:-1], **row})
    return results


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("plan", help="emit the historical mapping artifacts needed for a source version")
    p.add_argument("--source-version", required=True)
    p.add_argument("--loader", required=True, choices=["forge", "neoforge", "fabric", "quilt", "unknown"])
    p.add_argument("--mapping-hint")
    p.add_argument("--json-out", type=Path)

    h = sub.add_parser("harvest", help="download authoritative mapping artifacts into a checksum cache")
    h.add_argument("--source-version", required=True)
    h.add_argument("--loader", required=True, choices=["forge", "neoforge", "fabric", "quilt", "unknown"])
    h.add_argument("--mapping-hint")
    h.add_argument("--cache", required=True, type=Path)

    n = sub.add_parser("normalize", help="normalize a Tiny/TSRG/SRG/ProGuard/MCP CSV mapping file to JSON")
    n.add_argument("input", type=Path)
    n.add_argument("--format", default="auto", choices=["auto", "tiny_v2", "tsrg", "tsrg2", "srg", "proguard", "mcp_csv"])
    n.add_argument("--json-out", type=Path, required=True)
    n.add_argument("--source-id", choices=["mojang_official", "fabric_intermediary", "fabric_yarn", "forge_mcpconfig", "forge_mcp_srg_legacy", "forge_mcp_named_legacy"])
    n.add_argument("--source-version")

    q = sub.add_parser("query", help="query a normalized mapping JSON by exact owner/member/descriptor")
    q.add_argument("index", type=Path)
    q.add_argument("--namespace", required=True)
    q.add_argument("--class", dest="class_name", required=True)
    q.add_argument("--member")
    q.add_argument("--descriptor")

    args = ap.parse_args()
    if args.cmd == "plan":
        result = source_plan(args.source_version, args.loader, args.mapping_hint)
        if args.json_out:
            write_json(args.json_out, result)
        else:
            print(json.dumps(result, indent=2, sort_keys=True))
        return 0
    if args.cmd == "harvest":
        result = harvest(args.source_version, args.loader, args.cache, args.mapping_hint)
        print(json.dumps(result, indent=2, sort_keys=True))
        return 0 if result["complete"] else 4
    if args.cmd == "normalize":
        result = normalize_file(args.input, args.format, args.source_id, args.source_version)
        write_json(args.json_out, result)
        print(json.dumps({"status": "normalized", "format": result["format"], "counts": result["counts"], "output": str(args.json_out)}, indent=2))
        return 0
    if args.cmd == "query":
        index = json.loads(args.index.read_text(encoding="utf-8"))
        print(json.dumps(query_index(index, args.namespace, args.class_name, args.member, args.descriptor), indent=2, sort_keys=True))
        return 0
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
