#!/usr/bin/env python3
"""Audit reconstructed/original asset packs for family-level premium consistency.

The audit looks for accidental drift and fake variety, not sameness. Per-asset catalog
flags decide which assets must be visually distinct and which share a material family.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
from typing import Any

import numpy as np
from PIL import Image
from skimage.color import rgb2lab, deltaE_ciede2000


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()


def resolve(root: Path, value: str) -> Path:
    p = Path(value)
    return p if p.is_absolute() else (root / p).resolve()


def spec_metrics(spec: dict[str, Any]) -> dict[str, Any]:
    mins, maxs, volumes, surface = [], [], [], 0.0
    for cube in spec.get('cubes', []):
        if not isinstance(cube, dict):
            continue
        try:
            o = np.asarray(cube['origin'], dtype=float); s = np.abs(np.asarray(cube['size'], dtype=float))
            if o.shape != (3,) or s.shape != (3,):
                continue
        except Exception:
            continue
        mins.append(o); maxs.append(o + s); volumes.append(float(np.prod(s)))
        surface += float(2.0 * (s[0] * s[1] + s[0] * s[2] + s[1] * s[2]))
    if mins:
        lo = np.min(np.stack(mins), axis=0); hi = np.max(np.stack(maxs), axis=0); ext = np.maximum(1e-6, hi - lo)
    else:
        lo = np.zeros(3); hi = np.zeros(3); ext = np.ones(3)
    norm_ext = ext / max(1e-6, float(ext.max()))
    vol = sorted(volumes, reverse=True)
    total_vol = max(1e-9, sum(vol)); profile = [v / total_vol for v in vol[:12]] + [0.0] * max(0, 12 - len(vol))
    signature = [*norm_ext.tolist(), min(1.0, len(volumes) / 32.0), *profile[:12]]
    anim_lengths = []
    for anim in spec.get('animations', []):
        if isinstance(anim, dict) and isinstance(anim.get('length'), (int, float)):
            anim_lengths.append(float(anim['length']))
    return {
        'bounds_min': [round(float(x), 5) for x in lo], 'bounds_max': [round(float(x), 5) for x in hi],
        'extents': [round(float(x), 5) for x in ext], 'cube_count': len(volumes), 'surface_area': surface,
        'shape_signature': signature, 'animation_lengths': anim_lengths,
    }


def texture_metrics(path: Path, palette_n: int = 24) -> dict[str, Any]:
    im = Image.open(path).convert('RGBA'); arr = np.asarray(im, dtype=np.uint8); mask = arr[:, :, 3] > 0
    pix = arr[:, :, :3][mask]
    if len(pix) == 0:
        pix = arr[:, :, :3].reshape(-1, 3)
    # Deterministic bounded sample.
    if len(pix) > 150000:
        idx = np.linspace(0, len(pix) - 1, 150000, dtype=np.int64); pix = pix[idx]
    q = Image.fromarray(pix.reshape(1, -1, 3), 'RGB').quantize(colors=max(2, palette_n), method=Image.Quantize.MEDIANCUT).convert('RGB')
    colors = q.getcolors(q.width * q.height) or []; colors.sort(reverse=True); total = max(1, q.width * q.height)
    pal = [{'rgb': list(rgb), 'fraction': n / total} for n, rgb in colors[:palette_n]]
    unique = len(np.unique(pix, axis=0)) if len(pix) <= 250000 else None
    return {
        'path': str(path), 'sha256': sha256(path), 'width': im.width, 'height': im.height,
        'alpha_fraction': round(float(mask.mean()), 6), 'unique_colors': unique, 'palette': pal,
    }


def palette_distance(a: list[dict], b: list[dict]) -> float:
    if not a or not b:
        return 100.0
    ar = np.asarray([x['rgb'] for x in a[:12]], dtype=np.float64) / 255.0
    br = np.asarray([x['rgb'] for x in b[:12]], dtype=np.float64) / 255.0
    al = rgb2lab(ar.reshape(-1, 1, 3)).reshape(-1, 3); bl = rgb2lab(br.reshape(-1, 1, 3)).reshape(-1, 3)
    d = np.zeros((len(al), len(bl)), dtype=np.float64)
    for i in range(len(al)):
        for j in range(len(bl)):
            d[i, j] = float(deltaE_ciede2000(al[i].reshape(1, 1, 3), bl[j].reshape(1, 1, 3))[0, 0])
    aw = np.asarray([x['fraction'] for x in a[:12]], dtype=float); aw /= max(1e-9, aw.sum())
    bw = np.asarray([x['fraction'] for x in b[:12]], dtype=float); bw /= max(1e-9, bw.sum())
    return 0.5 * float(np.sum(np.min(d, axis=1) * aw)) + 0.5 * float(np.sum(np.min(d, axis=0) * bw))


def shape_distance(a: list[float], b: list[float]) -> float:
    x, y = np.asarray(a, dtype=float), np.asarray(b, dtype=float)
    n = max(len(x), len(y)); x = np.pad(x, (0, n - len(x))); y = np.pad(y, (0, n - len(y)))
    return float(np.linalg.norm(x - y) / math.sqrt(max(1, n)))


def main() -> int:
    ap = argparse.ArgumentParser(); ap.add_argument('catalog', type=Path); ap.add_argument('--output', type=Path, required=True); ap.add_argument('--markdown', type=Path); ap.add_argument('--strict', action='store_true'); args = ap.parse_args()
    cfg = json.loads(args.catalog.read_text(encoding='utf-8')); root = args.catalog.parent
    assets_raw = cfg.get('assets', []); style = cfg.get('style_contract', {}) if isinstance(cfg.get('style_contract'), dict) else {}
    if not isinstance(assets_raw, list) or len(assets_raw) < 2:
        print('catalog.assets needs at least two assets'); return 2
    density_ratio_warn = float(style.get('density_ratio_warn', 2.5)); clone_distance = float(style.get('clone_shape_distance', 0.025)); palette_warn = float(style.get('shared_palette_delta_e_warn', 35.0)); texel_unit = int(style.get('texture_unit', 16)); max_palette = style.get('max_unique_colors_warn')
    assets=[]; findings=[]
    for row in assets_raw:
        if not isinstance(row, dict) or not row.get('id') or not row.get('spec'):
            findings.append({'level':'error','code':'catalog.asset','message':f'Invalid asset entry {row!r}'}); continue
        sp=resolve(root,str(row['spec'])); spec=json.loads(sp.read_text(encoding='utf-8')); sm=spec_metrics(spec); tm=None
        if row.get('texture'):
            tp=resolve(root,str(row['texture'])); tm=texture_metrics(tp,int(style.get('palette_sample',24)))
            if tm['width'] % texel_unit or tm['height'] % texel_unit:
                findings.append({'level':'warning','asset':row['id'],'code':'texture.unit','message':f"texture {tm['width']}x{tm['height']} is not aligned to {texel_unit}px material-grid discipline"})
            if max_palette is not None and tm['unique_colors'] is not None and tm['unique_colors'] > int(max_palette):
                findings.append({'level':'warning','asset':row['id'],'code':'texture.palette_sprawl','message':f"{tm['unique_colors']} unique colors exceeds style warning {int(max_palette)}"})
        density=None
        if tm and sm['surface_area']>0:
            density=math.sqrt((tm['width']*tm['height']*tm['alpha_fraction'])/sm['surface_area'])
        assets.append({'id':str(row['id']),'class':str(row.get('class',spec.get('asset_class','unknown'))),'family':str(row.get('family','default')),'palette_family':str(row.get('palette_family',row.get('family','default'))),'must_be_distinct':bool(row.get('must_be_distinct',False)),'spec':str(sp),'texture':tm,'model':sm,'texel_density':density,'motifs':sorted(str(x) for x in row.get('motifs',[]) if isinstance(x,(str,int,float)))})
    # Family density consistency.
    families={}
    for a in assets: families.setdefault(a['family'],[]).append(a)
    for family,rows in families.items():
        ds=[x['texel_density'] for x in rows if x['texel_density'] and x['texel_density']>0]
        if len(ds)>=2:
            ratio=max(ds)/max(1e-9,min(ds))
            if ratio>density_ratio_warn: findings.append({'level':'warning','family':family,'code':'style.texel_density','message':f'texel-density ratio {ratio:.3f} exceeds {density_ratio_warn:.3f}'})
    # Pairwise fake-variety and material-family checks.
    pairs=[]
    for i,a in enumerate(assets):
        for b in assets[i+1:]:
            sd=shape_distance(a['model']['shape_signature'],b['model']['shape_signature']); pd=None
            if a['texture'] and b['texture']: pd=palette_distance(a['texture']['palette'],b['texture']['palette'])
            duplicate_tex=bool(a['texture'] and b['texture'] and a['texture']['sha256']==b['texture']['sha256'])
            same_family=a['family']==b['family']; same_palette=a['palette_family']==b['palette_family']
            pair={'a':a['id'],'b':b['id'],'same_family':same_family,'shape_distance':round(sd,6),'palette_delta_e':round(pd,4) if pd is not None else None,'duplicate_texture':duplicate_tex};pairs.append(pair)
            if same_family and (a['must_be_distinct'] or b['must_be_distinct']) and sd<clone_distance:
                findings.append({'level':'error','assets':[a['id'],b['id']],'code':'variety.shape_clone','message':f'distinct assets have near-clone shape signature {sd:.5f} < {clone_distance:.5f}'})
            if same_family and (a['must_be_distinct'] or b['must_be_distinct']) and duplicate_tex:
                findings.append({'level':'error','assets':[a['id'],b['id']],'code':'variety.texture_clone','message':'distinct assets use byte-identical textures'})
            if same_palette and pd is not None and pd>palette_warn:
                findings.append({'level':'warning','assets':[a['id'],b['id']],'code':'style.palette_drift','message':f'shared material family palette distance {pd:.2f} exceeds {palette_warn:.2f}'})
    errors=sum(1 for x in findings if x['level']=='error'); warnings=sum(1 for x in findings if x['level']=='warning'); passed=errors==0 and (not args.strict or warnings==0)
    report={'schema_version':1,'result':'pass' if passed else 'fail','asset_count':len(assets),'family_count':len(families),'style_contract':style,'errors':errors,'warnings':warnings,'assets':assets,'pairs':pairs,'findings':findings,'note':'Consistency means coherent production language, not identical assets. must_be_distinct is the explicit anti-recolor/clone gate.'}
    args.output.parent.mkdir(parents=True,exist_ok=True);args.output.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    if args.markdown:
        lines=['# Pack Consistency Audit','',f"Result: **{report['result'].upper()}**",'',f"Assets: **{len(assets)}**  ",f"Errors: **{errors}**  ",f"Warnings: **{warnings}**",'','## Findings','']
        if findings:
            for f in findings: lines.append(f"- **{f['level'].upper()}** `{f['code']}` — {f['message']}")
        else: lines.append('- None.')
        lines+=['','## Asset metrics','']
        for a in assets: lines.append(f"- `{a['id']}` ({a['class']}, family `{a['family']}`): cubes={a['model']['cube_count']}, extents={a['model']['extents']}, texel_density={None if a['texel_density'] is None else round(a['texel_density'],4)}")
        args.markdown.write_text('\n'.join(lines)+'\n',encoding='utf-8')
    print(json.dumps({'result':report['result'],'assets':len(assets),'errors':errors,'warnings':warnings,'output':str(args.output)},indent=2));return 0 if passed else 2
if __name__=='__main__':raise SystemExit(main())
