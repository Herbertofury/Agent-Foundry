#!/usr/bin/env python3
"""Inventory an authorized Minecraft server/resource-pack asset bundle for mod conversion."""
from __future__ import annotations
import argparse, hashlib, json, re, zipfile
from collections import Counter
from pathlib import Path, PurePosixPath

TEXT_EXTS = {'.json','.mcmeta','.yml','.yaml','.toml','.properties','.txt','.cfg','.conf','.bbmodel','.ajmodel','.jem','.jpm'}
SPECIAL_EXTS = {'.bbmodel','.ajmodel','.fmmodel','.jem','.jpm','.geo.json','.png','.mcmeta','.json','.yml','.yaml','.ogg'}
MAX_SNIFF = 524288
REGISTRY = Path(__file__).resolve().parent.parent / 'references' / 'server-plugin-registry.json'

class Bundle:
    def __init__(self, root: Path):
        self.root = root
        self.is_zip = root.is_file() and zipfile.is_zipfile(root)
        self.zf = zipfile.ZipFile(root) if self.is_zip else None
        if not self.is_zip and not root.is_dir():
            raise SystemExit(f"input is neither a directory nor a ZIP: {root}")
    def names(self):
        if self.is_zip:
            return [n for n in self.zf.namelist() if not n.endswith('/')]
        return [p.relative_to(self.root).as_posix() for p in self.root.rglob('*') if p.is_file()]
    def read(self, name: str, limit: int | None = None) -> bytes:
        if self.is_zip:
            with self.zf.open(name) as f:
                return f.read() if limit is None else f.read(limit)
        p = self.root / PurePosixPath(name)
        with p.open('rb') as f:
            return f.read() if limit is None else f.read(limit)
    def size(self, name: str) -> int:
        if self.is_zip:
            return self.zf.getinfo(name).file_size
        return (self.root / PurePosixPath(name)).stat().st_size
    def close(self):
        if self.zf:
            self.zf.close()

def suffix_key(name: str) -> str:
    low = name.lower()
    if low.endswith('.geo.json'): return '.geo.json'
    if low.endswith('.png.mcmeta'): return '.png.mcmeta'
    return Path(low).suffix or '<none>'

def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()

def safe_text(data: bytes) -> str:
    try:
        return data.decode('utf-8', errors='ignore')
    except Exception:
        return ''

def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('input', type=Path)
    ap.add_argument('--json-out', type=Path)
    ap.add_argument('--md-out', type=Path)
    ap.add_argument('--hash-limit-mib', type=int, default=32, help='hash files no larger than this many MiB')
    args = ap.parse_args()

    bundle = Bundle(args.input)
    try:
        names = sorted(bundle.names())
        exts = Counter(suffix_key(n) for n in names)
        namespaces = sorted({parts[1] for n in names for parts in [PurePosixPath(n).parts] if len(parts) >= 3 and parts[0] == 'assets'})
        pack_meta = None
        if 'pack.mcmeta' in names:
            try: pack_meta = json.loads(bundle.read('pack.mcmeta').decode('utf-8'))
            except Exception as exc: pack_meta = {'parse_error': str(exc)}

        text_parts = []
        config_files = []
        notable = []
        aj_blueprints = []
        hash_cap = args.hash_limit_mib * 1024 * 1024
        for n in names:
            low = n.lower()
            size = bundle.size(n)
            if low.endswith(('.yml','.yaml','.json','.toml','.properties','.cfg','.conf','.bbmodel','.ajmodel')):
                config_files.append(n)
            if any(low.endswith(x) for x in ('.bbmodel','.ajmodel','.fmmodel','.jem','.jpm','.geo.json','.png','.png.mcmeta','.ogg')):
                entry = {'path': n, 'size': size}
                if size <= hash_cap:
                    entry['sha256'] = sha256_bytes(bundle.read(n))
                notable.append(entry)
            if Path(low).suffix in TEXT_EXTS or low.endswith(('.geo.json','.png.mcmeta')):
                raw = bundle.read(n, min(size, MAX_SNIFF))
                txt = safe_text(raw)
                text_parts.append((n, txt))
                if low.endswith('.json') and size <= MAX_SNIFF:
                    try:
                        jd = json.loads(txt)
                        if isinstance(jd, dict) and 'format_version' in jd and isinstance(jd.get('settings'), dict) and jd['settings'].get('id') and isinstance(jd.get('nodes'), dict) and isinstance(jd.get('animations'), dict):
                            node_types={str(v.get('type')) for v in jd.get('nodes',{}).values() if isinstance(v,dict) and v.get('type')}
                            if node_types & {'bone','item_display','block_display','text_display','structure','camera','locator'}:
                                aj_blueprints.append(n)
                    except Exception:
                        pass

        all_paths = '\n'.join(names).lower()
        all_text = '\n'.join(t for _, t in text_parts).lower()
        detections = {}
        def detect(name, score, evidence):
            if score > 0: detections[name] = {'confidence': 'high' if score >= 3 else 'medium' if score == 2 else 'low', 'evidence': evidence}

        bb_count = exts.get('.bbmodel', 0)
        aj_count = exts.get('.ajmodel', 0)
        geo_count = exts.get('.geo.json', 0)
        jem_count = exts.get('.jem', 0) + exts.get('.jpm', 0)
        detect('ModelEngine', int('modelengine' in all_paths) + int('blueprints/' in all_paths and bb_count) + int('modelengine' in all_text or 'model{' in all_text), ['path/config markers', f'{bb_count} .bbmodel'])
        detect('MythicMobs', int('mythicmobs' in all_paths) + int('~on' in all_text and 'skills:' in all_text) + int('mythicmob' in all_text), ['mob/skill config markers'])
        detect('MythicCrucible', int('crucible' in all_paths) + int('mythiccrucible' in all_text) + int('furniture' in all_text and 'crucible' in all_text), ['item/furniture config markers'])
        detect('ItemsAdder', int('itemsadder' in all_paths) + int('itemsadder' in all_text) + int('behaviours:' in all_text and 'namespace:' in all_text), ['namespace/behaviour markers'])
        detect('Oraxen', int('oraxen' in all_paths) + int('oraxen' in all_text) + int('mechanics:' in all_text and 'pack:' in all_text), ['pack/mechanics markers'])
        detect('Nexo', int('/nexo/' in '/' + all_paths or all_paths.startswith('nexo/')) + int('nexo' in all_text) + int('item_model' in all_text and 'mechanics:' in all_text), ['item-model/mechanics markers'])
        detect('CraftEngine', int('craftengine' in all_paths or 'craft-engine' in all_paths) + int('craftengine' in all_text or 'craft-engine' in all_text), ['path/config markers'])
        detect('ExecutableItems', int('executableitems' in all_paths) + int('executableitems' in all_text), ['path/config markers'])
        detect('ExecutableBlocks', int('executableblocks' in all_paths) + int('executableblocks' in all_text), ['path/config markers'])
        detect('MMOItems', int('mmoitems' in all_paths) + int('mmoitems' in all_text), ['path/config markers'])
        detect('EcoItems', int('ecoitems' in all_paths) + int('ecoitems' in all_text), ['path/config markers'])
        detect('HMCCosmetics', int('hmccosmetics' in all_paths) + int('hmccosmetics' in all_text), ['path/config markers'])
        detect('HMCWraps', int('hmcwraps' in all_paths) + int('hmcwraps' in all_text), ['path/config markers'])
        detect('BetterModel', int('bettermodel' in all_paths) + int('bettermodel' in all_text), ['path/config markers', f'{bb_count} .bbmodel'])
        detect('FreeMinecraftModels', int('freeminecraftmodels' in all_paths) + int(exts.get('.fmmodel', 0) > 0) + int('freeminecraftmodels' in all_text), ['FMM markers'])
        detect('Animated Java', int(aj_count > 0) + int(bool(aj_blueprints)) + int('animated_java' in all_text or 'animated-java' in all_text), [f'{aj_count} .ajmodel', f'{len(aj_blueprints)} Plugin Blueprint JSON'])
        detect('OptiFine CEM / EMF-compatible', int('/optifine/cem/' in '/' + all_paths) + int(jem_count > 0), [f'{jem_count} .jem/.jpm'])
        detect('GeckoLib-style resources', int(geo_count > 0) + int('/animations/' in '/' + all_paths and '.json' in all_paths), [f'{geo_count} .geo.json'])

        # Broaden ecosystem recognition from the canonical server-plugin registry.
        # Detailed first-class detections above keep their stronger evidence; registry matches fill the long tail.
        registry_snapshot = None
        registry_entries = 0
        try:
            reg = json.loads(REGISTRY.read_text(encoding='utf-8'))
            registry_snapshot = reg.get('snapshot_date')
            registry_entries = len(reg.get('entries') or [])
            normalized_paths = re.sub(r'[^a-z0-9]+', '', all_paths)
            normalized_text = re.sub(r'[^a-z0-9]+', '', all_text)
            for ent in reg.get('entries') or []:
                name = ent.get('name')
                if not name or name in detections:
                    continue
                markers = []
                for raw in [name, *(ent.get('aliases') or []), *(ent.get('markers') or [])]:
                    m = re.sub(r'[^a-z0-9]+', '', str(raw).lower())
                    if len(m) >= 5:
                        markers.append(m)
                path_hits = sorted({m for m in markers if m in normalized_paths})
                text_hits = sorted({m for m in markers if m in normalized_text})
                score = 2 if path_hits else 1 if text_hits else 0
                if score:
                    detect(name, score, [f'registry {ent.get("adapter","unknown")} / {ent.get("impact","unknown")}', *(path_hits[:3] or text_hits[:3])])
        except Exception:
            registry_snapshot = None
            registry_entries = 0

        model_jsons = [n for n in names if re.match(r'^assets/[^/]+/models/.+\.json$', n)]
        item_defs = [n for n in names if re.match(r'^assets/[^/]+/items/.+\.json$', n)]
        blockstates = [n for n in names if re.match(r'^assets/[^/]+/blockstates/.+\.json$', n)]
        textures = [n for n in names if re.match(r'^assets/[^/]+/textures/.+\.png$', n)]
        anim_tex = [n for n in names if n.lower().endswith('.png.mcmeta')]
        sounds = [n for n in names if re.match(r'^assets/[^/]+/sounds/.+\.ogg$', n)]

        source_score = 0
        if bb_count or aj_count or aj_blueprints or jem_count: source_score += 3
        if textures: source_score += 1
        if any(n.lower().endswith(('.yml','.yaml')) for n in names): source_score += 1
        if 'pack.mcmeta' in names: source_score += 1
        fidelity = 'A - authoring source + behavior/config evidence' if source_score >= 5 else 'B - strong visual source, behavior may be incomplete' if source_score >= 3 else 'C - generated/runtime resource pack; reconstructable visuals, missing authoring semantics likely' if textures or model_jsons else 'D - sparse/unknown bundle'

        report = {
            'input': str(args.input), 'input_kind': 'zip' if bundle.is_zip else 'directory',
            'plugin_registry': {'snapshot_date': registry_snapshot, 'entries': registry_entries},
            'file_count': len(names), 'total_bytes': sum(bundle.size(n) for n in names),
            'extensions': dict(exts.most_common()), 'resource_pack': {'pack_mcmeta': pack_meta, 'namespaces': namespaces},
            'asset_counts': {'bbmodel': bb_count, 'ajmodel': aj_count, 'animated_java_plugin_blueprints': len(aj_blueprints), 'fmmodel': exts.get('.fmmodel',0), 'geo_json': geo_count, 'cem_jem_jpm': jem_count, 'java_models': len(model_jsons), 'item_definitions_1_21_4_plus': len(item_defs), 'blockstates': len(blockstates), 'textures_png': len(textures), 'animated_texture_mcmeta': len(anim_tex), 'sounds_ogg': len(sounds), 'config_like_files': len(config_files)},
            'detected_ecosystems': detections, 'animated_java_plugin_blueprints': aj_blueprints, 'conversion_fidelity': fidelity,
            'notable_files': notable[:1000],
            'warnings': [
                'Use only assets/configs you own or are authorized to convert.',
                'A client-downloaded/generated resource pack usually does not contain complete server AI, skill graphs, hidden animation state logic, hitbox rules, drops, or permissions.',
                'Do not treat obfuscation, encryption, or pack protection as permission to bypass it; obtain authorized source instead.'
            ]
        }
        text = json.dumps(report, indent=2)
        if args.json_out:
            args.json_out.parent.mkdir(parents=True, exist_ok=True); args.json_out.write_text(text+'\n', encoding='utf-8')
        if args.md_out:
            args.md_out.parent.mkdir(parents=True, exist_ok=True)
            lines = [f"# Server Asset Probe: {args.input.name}", '', f"- Files: **{len(names)}**", f"- Bytes: **{report['total_bytes']}**", f"- Fidelity: **{fidelity}**", f"- Namespaces: {', '.join(namespaces) or '(none)'}", '', '## Asset counts']
            for k,v in report['asset_counts'].items(): lines.append(f'- {k}: {v}')
            lines += ['', '## Detected ecosystems']
            for k,v in detections.items(): lines.append(f"- {k}: {v['confidence']} ({'; '.join(v['evidence'])})")
            lines += ['', '## Safety / provenance'] + [f'- {w}' for w in report['warnings']]
            args.md_out.write_text('\n'.join(lines)+'\n', encoding='utf-8')
        print(text)
    finally:
        bundle.close()

if __name__ == '__main__': main()
