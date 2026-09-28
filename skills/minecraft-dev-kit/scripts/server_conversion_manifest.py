#!/usr/bin/env python3
"""Combine server conversion evidence into an actionable full-asset migration manifest."""
from __future__ import annotations
import argparse, json
from pathlib import Path

def load(p): return json.loads(p.read_text(encoding='utf-8')) if p else {}
def loads(paths): return [load(p) for p in (paths or [])]
def status(ok, partial=False): return 'present' if ok else 'partial' if partial else 'missing/unknown'

def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--probe',type=Path,required=True); ap.add_argument('--closure',type=Path); ap.add_argument('--semantics',type=Path)
    ap.add_argument('--mythic-ir',type=Path); ap.add_argument('--content-ir',type=Path); ap.add_argument('--adjacent-ir',type=Path); ap.add_argument('--family-ir',type=Path); ap.add_argument('--plugin-inventory',type=Path); ap.add_argument('--plugin-coverage',type=Path); ap.add_argument('--unknown-triage',type=Path); ap.add_argument('--aj-ir',type=Path,action='append'); ap.add_argument('--cem-ir',type=Path); ap.add_argument('--link-audit',type=Path); ap.add_argument('--renderer',type=Path)
    ap.add_argument('--target-version'); ap.add_argument('--loader'); ap.add_argument('--json-out',type=Path); ap.add_argument('--md-out',type=Path); args=ap.parse_args()
    p=load(args.probe); c=load(args.closure); s=load(args.semantics); m=load(args.mythic_ir); ci=load(args.content_ir); adj=load(args.adjacent_ir); fam=load(args.family_ir); pinv=load(args.plugin_inventory); pcov=load(args.plugin_coverage); utri=load(args.unknown_triage); ajs=loads(args.aj_ir); cem=load(args.cem_ir); link=load(args.link_audit); renderer=load(args.renderer)
    ac=p.get('asset_counts') or {}
    bb=ac.get('bbmodel',0); aj=ac.get('ajmodel',0); ajbp=ac.get('animated_java_plugin_blueprints',0); cem_count=ac.get('cem_jem_jpm',0); java=ac.get('java_models',0); tex=ac.get('textures_png',0)
    server_anim=len(s.get('animations') or []); aj_anim=sum(x.get('counts',{}).get('animations',0) for x in ajs); cem_anim=(cem.get('counts') or {}).get('animation_assignments',0)
    special=len(s.get('special_bones') or []) + sum((x.get('node_types') or {}).get('locator',0) for x in ajs) + (cem.get('counts') or {}).get('attachments',0)
    mechanics=s.get('mechanics') or {}; triggers=s.get('triggers') or {}; targeters=s.get('targeters') or {}; mythic_lines=m.get('skill_line_count',0)
    content_entries=(ci.get('semantic_counts') or {}).get('entries',0)
    plugin_jars=len(pinv.get('plugin_jars') or []); plugin_folders=len(pinv.get('plugin_config_folders') or [])
    plugin_unknown=len(pcov.get('unknown_conversion_risk_families') or pcov.get('unknown_conversion_risk') or []); plugin_review=len(pcov.get('recognized_needing_semantic_review') or []); triaged_unknown=len(utri.get('records') or [])
    adjacent_plugins=len(adj.get('plugins') or {}); adjacent_files=adj.get('files_scanned',0) or 0
    family_plugins=len(fam.get('plugin_summaries') or {}); family_records=len(fam.get('entries') or []); family_unmatched=sum((x.get('unmatched_key_paths') or 0) for x in (fam.get('plugin_summaries') or {}).values())
    unresolved=c.get('unresolved_references') or []; itemdefs=c.get('item_definitions_1_21_4_plus',0) or 0; cmd=len(c.get('custom_model_data_overrides') or [])
    structured=bb or aj or ajbp or cem_count
    ledger={
        'structured_model_source':status(structured), 'generated_java_model_evidence':status(java), 'textures':status(tex),
        'animation_or_expression_source':status(server_anim or aj_anim or cem_anim, partial=bool(java and not (server_anim or aj_anim or cem_anim))),
        'attachment_locator_hitbox_semantics':status(special), 'gameplay_skill_semantics':status(mechanics or triggers or targeters or mythic_lines),
        'custom_content_semantics':status(content_entries), 'resource_pack_dependency_closure':'blocked' if unresolved else ('present' if c else 'not analyzed'),
        'cross_file_link_integrity':('present' if link.get('pass') is True else 'blocked' if link else 'not analyzed'),
        'renderer_route':status(renderer.get('ranking')), 'legacy_custom_model_data':status(cmd), 'new_item_model_schema':status(itemdefs),
        'server_plugin_inventory':status(plugin_jars or plugin_folders, partial=bool(pinv)), 'plugin_registry_classification':('review' if plugin_unknown else ('present' if pcov else 'not analyzed')),
        'unknown_plugin_semantic_triage':status(triaged_unknown, partial=bool(utri)),
        'adjacent_plugin_semantic_inventory':status(adjacent_plugins, partial=bool(adj)),
        'plugin_family_semantic_ir':status(family_plugins, partial=bool(fam)),
    }
    actions=[]; unknowns=[]
    if bb: actions.append('Use .bbmodel as the visual/rig/animation source of truth; preserve UUID hierarchy and run per-model IR/lint.')
    if aj or ajbp: actions.append('Preserve Animated Java authoring/Plugin Blueprint semantics: locators/display nodes, palettes, Molang, events, easing/interpolation and loop/blend timing.')
    if cem_count: actions.append('Preserve CEM attach/replace, baseId/JPM hierarchy, UV/axis/mirror/attachments and expression-driven animation; compare against EMF/OptiFine oracle.')
    if not structured and java:
        actions.append('No structured authoring source detected: inverse-inspect generated Java models for geometry/UV/texture evidence; reconstruct hierarchy/pivots cautiously.')
        unknowns += ['Original bone hierarchy/pivots may be unrecoverable from generated Java models alone.','Original animation tracks/interpolation are unknown unless present elsewhere.']
    if not structured and not java: unknowns.append('No structured model source detected.')
    if unresolved: actions.append(f'Resolve {len(unresolved)} non-vanilla resource-pack reference(s) before conversion.')
    if mechanics or triggers or targeters or mythic_lines: actions.append('Translate gameplay mechanics/triggers/targeters/meta-skill graph into native authoritative mod logic with ordering/cooldown/selection regression tests.')
    else: unknowns.append('No gameplay skill/AI semantics detected; resource-pack visuals alone cannot prove server behavior.')
    if content_entries: actions.append('Translate custom-content item/components/events/furniture semantics into registered native item/block/entity behavior; review every unclassified key.')
    if plugin_unknown:
        unknowns.append(f'{plugin_unknown} supplied plugin JAR/config identity(ies) are not yet classified by the registry; inspect before claiming full-server parity.')
        if triaged_unknown: actions.append(f'Use unknown-plugin semantic triage for {triaged_unknown} identity(ies) to verify vendor/schema and deliberately promote a registry candidate; never auto-trust the scaffold.')
    if plugin_review: actions.append(f'Review/translate {plugin_review} recognized conversion-impact plugin family/families that are detect-only; extend dedicated adapters where their behavior affects parity.')
    if adjacent_plugins: actions.append(f'Use adjacent-plugin IR for {adjacent_plugins} recognized plugin family/families as a semantic checklist; vendor-specific behavior still requires exact translation where applicable.')
    if family_plugins: actions.append(f'Use category-aware family IR for {family_plugins} plugin family/families; review {family_unmatched} unmatched key-path evidence item(s) before declaring vendor-specific parity.')
    if special: actions.append('Map special bones/locators/attachments to native seats, hitboxes, held items, leashes, nameplates or effect/event origins before flattening hierarchy.')
    if link and link.get('pass') is False: actions.append('Fix cross-file model/state linkage blockers before implementation; do not invent missing clips or silently retarget IDs.')
    if itemdefs and args.target_version and args.target_version.startswith('1.20'): actions.append('Back-translate 1.21.4+ item-model definitions to 1.20.x-compatible model/renderer logic without dropping source states.')
    if cmd: actions.append('Replace server CustomModelData ownership with registered mod item/model identity where practical; retain mappings as parity evidence.')
    renderer_notes=['Prefer native APIs for static/simple assets; avoid unnecessary animation dependencies.','For animated assets choose the highest-ranked genuinely supported route with the least semantic loss; reverify exact target support before dependency mutation.']
    if renderer.get('ranking'):
        top=renderer['ranking'][0]; renderer_notes.append(f"Selector top route: {top.get('name')} (snapshot_supported={top.get('snapshot_supported')}, score={top.get('score')}).")
    elif args.target_version == '1.21.1' and (args.loader or '').lower() == 'neoforge': renderer_notes.append('BBLib is a direct-.bbmodel candidate for 1.21.1 NeoForge; still benchmark/QA before adoption.')
    elif args.target_version == '1.18.2' and (args.loader or '').lower() == 'forge': renderer_notes.append('BBLib is a direct-.bbmodel candidate for 1.18.2 Forge; still benchmark/QA before adoption.')
    else: renderer_notes.append('Do not assume current BBLib supports this target; use it as architecture/reference unless a compatible build is verified or deliberately ported.')
    release_gate=['All applicable ledger rows implemented, explicitly not-applicable, or truthfully marked missing-source.','No unresolved non-vanilla asset dependencies or failed cross-file model/state references.','Deterministic multi-view/multi-time visual and state parity evidence.','Native client/server proof of converted behavior and persistence.','Rights/provenance and untouched source hashes preserved with the artifact.']
    report={'source':p.get('input'),'target':{'minecraft':args.target_version,'loader':args.loader},'detected_ecosystems':p.get('detected_ecosystems') or {},'fidelity':p.get('conversion_fidelity'),'evidence_summary':{'bbmodel':bb,'ajmodel':aj,'animated_java_plugin_blueprints':ajbp,'cem_jem_jpm':cem_count,'generated_java_models':java,'server_animation_entries':server_anim,'animated_java_animations':aj_anim,'cem_animation_assignments':cem_anim,'mythic_skill_lines':mythic_lines,'custom_content_entries':content_entries,'plugin_jars':plugin_jars,'plugin_config_folders':plugin_folders,'plugin_registry_unknowns':plugin_unknown,'plugin_unknowns_semantically_triaged':triaged_unknown,'plugin_detect_only_review':plugin_review,'adjacent_plugin_families':adjacent_plugins,'adjacent_plugin_files':adjacent_files,'category_family_plugins':family_plugins,'category_family_records':family_records,'category_family_unmatched_key_paths':family_unmatched},'unknown_plugin_triage':{'count':triaged_unknown,'records':utri.get('records') or []},'plugin_coverage':{'registry_snapshot':pcov.get('registry_snapshot'),'registry_entries':pcov.get('registry_entries'),'counts':pcov.get('counts') or {},'unknown_conversion_risk':pcov.get('unknown_conversion_risk') or [],'unknown_conversion_risk_families':pcov.get('unknown_conversion_risk_families') or []},'ledger':ledger,'actions':actions,'unknowns':unknowns,'renderer_notes':renderer_notes,'release_gate':release_gate}
    text=json.dumps(report,indent=2)
    if args.json_out: args.json_out.parent.mkdir(parents=True,exist_ok=True);args.json_out.write_text(text+'\n',encoding='utf-8')
    if args.md_out:
        lines=['# Server Asset -> Mod Conversion Manifest','',f"- Source: `{report['source']}`",f"- Target: `{args.target_version or 'unspecified'}` / `{args.loader or 'unspecified'}`",f"- Source fidelity: **{report['fidelity']}**",'', '## Completeness ledger']
        lines += [f'- {k}: **{v}**' for k,v in ledger.items()]
        lines += ['', '## Required next actions']+[f'{i}. {x}' for i,x in enumerate(actions,1)]
        lines += (['', '## Unknown / missing evidence']+[f'- {x}' for x in unknowns]) if unknowns else ['', '## Unknown / missing evidence','- None detected by the supplied reports.']
        lines += ['', '## Renderer notes']+[f'- {x}' for x in renderer_notes]+['', '## Release gate']+[f'- {x}' for x in release_gate]
        args.md_out.parent.mkdir(parents=True,exist_ok=True);args.md_out.write_text('\n'.join(lines)+'\n',encoding='utf-8')
    print(text)
if __name__=='__main__':main()
