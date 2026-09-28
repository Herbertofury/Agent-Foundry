#!/usr/bin/env python3
"""Rank model/animation runtime routes using a dated compatibility snapshot plus requested semantics."""
from __future__ import annotations
import argparse,json

SNAPSHOT='2026-09-06'

def norm(x):return (x or '').strip().lower()
def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--minecraft',required=True);ap.add_argument('--loader',required=True)
    ap.add_argument('--source',choices=['static','bbmodel','fmmodel','animated-java','cem','geckolib','bedrock','player','unknown'],default='unknown')
    ap.add_argument('--features',default='',help='comma list: animation,molang,locators,variants,player,hitboxes,mounts,root-motion,effects,billboards,flipbook,text-displays')
    args=ap.parse_args();mc=args.minecraft;loader=norm(args.loader);src=args.source;features={norm(x) for x in args.features.split(',') if x.strip()}
    if src=='player':features.add('player')
    candidates=[]
    def add(name,supported,score,reasons,blockers=None,kind='runtime'):
        candidates.append({'name':name,'kind':kind,'snapshot_supported':supported,'score':score,'reasons':reasons,'blockers':blockers or []})
    # Native is always an implementation option, but cost rises with semantic complexity.
    complexf={'animation','molang','locators','variants','player','root-motion','effects','billboards','flipbook','text-displays'} & features
    add('Native Minecraft APIs',True,88 if src=='static' and not complexf else 50,['No extra runtime dependency','Best for simple/static assets']+(['High custom implementation burden for requested advanced semantics'] if complexf else []))
    # Current snapshot routes relevant to the user and common modern targets.
    gecko_support=(mc=='1.20.1' and loader in {'forge','fabric'}) or (mc=='1.21.1' and loader in {'forge','neoforge','fabric'}) or mc.startswith('26.')
    gecko_score=90 if src in {'geckolib','bedrock','fmmodel','unknown'} or 'animation' in features else 75
    add('GeckoLib',gecko_support,gecko_score,['Strong general skeletal animation/render route','Current Forge 1.20.1 release 4.8.4 in this snapshot'] if mc=='1.20.1' else ['Strong general skeletal animation/render route'],[] if gecko_support else ['Exact target build must be reverified or a different route used'])
    bblib_support=(mc=='1.21.1' and loader=='neoforge') or (mc=='1.18.2' and loader=='forge')
    bblib_score=98 if src=='bbmodel' else 68 if src=='fmmodel' else 82
    add('BlockbenchLib / BBLib',bblib_support,bblib_score,(['Direct Generic .bbmodel loading minimizes exporter loss','Supports controllers/Molang, locators, billboards, flipbook textures and hitbox data in current releases'] if src!='fmmodel' else ['FMM .fmmodel is Blockbench-derived JSON but may be stripped; do not assume direct BBLib compatibility','Use as parser/port reference unless normalized back to a proven supported source']),[] if bblib_support else ['No published build for this exact target in the snapshot; treat as reference/port candidate'])
    emf_support=src=='cem' and ((mc=='1.20.1' and loader in {'forge','neoforge'}) or mc.startswith('1.21') or mc.startswith('26.'))
    add('Entity Model Features (EMF)',emf_support,99 if src=='cem' else 25,['Best semantic oracle/runtime for OptiFine CEM/JEM/JPM source'],[] if emf_support else ['Only appropriate for CEM-origin assets and supported targets'])
    pal_support=('player' in features) and ((mc=='1.21.1' and loader in {'fabric','neoforge'}) or (mc.startswith('1.21.') and loader in {'fabric','neoforge'} and mc not in {'1.21.2','1.21.3','1.21.4','1.21.5','1.21.6'}) or mc.startswith('26.'))
    add('Player Animation Library (PAL)',pal_support,98 if 'player' in features else 20,['Modern conflict-aware player animation route','Molang/effect keyframes/custom pivots'],[] if pal_support else ['Snapshot does not provide a drop-in Forge 1.20.1 lane'])
    legacy_player=('player' in features and mc=='1.20.1' and loader=='forge')
    add('KosmX PlayerAnimator',legacy_player,85 if legacy_player else 20,['Established Forge 1.20.1 player-animation compatibility lane'],[] if legacy_player else ['Legacy route; prefer PAL on supported modern targets'])
    bil_support=(src in {'bbmodel','animated-java'} and (mc.startswith('26.') or (mc.startswith('1.21.') and loader in {'fabric','quilt','neoforge'})))
    add('blockbench-import-library',bil_support,96 if src=='animated-java' else 93 if src=='bbmodel' else 40,['Direct Generic/Animated Java import','Variants, locators, effect keyframes, Molang/display-entity semantics'],[] if bil_support else ['Use as parser/semantic reference unless an exact target build is verified or ported'])
    # Penalize known semantic mismatches.
    for c in candidates:
        if not c['snapshot_supported']:c['score']-=35
        if src=='animated-java' and c['name']=='GeckoLib':c['score']-=10;c['reasons'].append('May require explicit translation of AJ variants/locators/effect/display semantics')
        if 'player' in features and c['name'] not in {'Player Animation Library (PAL)','KosmX PlayerAnimator','Native Minecraft APIs'}:c['score']-=20
        if src in {'bbmodel','fmmodel'} and c['name']=='Native Minecraft APIs':c['score']-=10
    candidates.sort(key=lambda x:x['score'],reverse=True)
    report={'snapshot':SNAPSHOT,'target':{'minecraft':mc,'loader':args.loader},'source':src,'features':sorted(features),'ranking':candidates,'decision_rule':'Reverify exact current version support before dependency mutation; choose least semantic loss among genuinely supported candidates.'}
    print(json.dumps(report,indent=2))
if __name__=='__main__':main()
