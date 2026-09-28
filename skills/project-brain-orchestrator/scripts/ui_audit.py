#!/usr/bin/env python3
"""Audit UI source and optionally inventory/click-test safe controls in a running app."""
from __future__ import annotations
import argparse, json, os, re, sys
from pathlib import Path

EXTS={'.html','.htm','.js','.jsx','.ts','.tsx','.vue','.svelte'}
SKIP={'.git','node_modules','dist','build','.next','.output','vendor','coverage'}
PATTERNS={
 'placeholder':re.compile(r'coming soon|not implemented|TODO|FIXME',re.I),
 'dead_href':re.compile(r'href\s*=\s*["\'](?:#|javascript:void\(0\))["\']',re.I),
 'console_only':re.compile(r'(?:onClick|onclick)\s*=.*console\.(?:log|warn|info)',re.I),
 'fake_success':re.compile(r'(?:success|completed|published|saved).{0,80}(?:setTimeout|hardcoded|mock)',re.I),
 'empty_handler':re.compile(r'(?:onClick|onclick)\s*=\s*\{?\s*\(?.*?\)?\s*=>\s*\{?\s*\}?\s*\}?',re.I),
}
DESTRUCTIVE=re.compile(r'delete|remove|destroy|purchase|pay|publish|deploy|send|submit|logout|reset|wipe',re.I)

def static_scan(root:Path):
    findings=[]
    for base,dirs,files in os.walk(root):
        dirs[:]=[d for d in dirs if d not in SKIP]
        for f in files:
            p=Path(base)/f
            if p.suffix.lower() not in EXTS: continue
            try: lines=p.read_text(encoding='utf-8',errors='replace').splitlines()
            except OSError: continue
            for i,line in enumerate(lines,1):
                for kind,pat in PATTERNS.items():
                    if pat.search(line): findings.append({'kind':kind,'file':p.relative_to(root).as_posix(),'line':i,'excerpt':line.strip()[:240]})
    return findings

def runtime_audit(url:str,click_safe:bool,allow:str|None,headless:bool):
    try:
        from playwright.sync_api import sync_playwright
    except Exception as exc:
        raise RuntimeError('Playwright is required for runtime audit; install it and its browser runtime') from exc
    records=[]; allow_re=re.compile(allow,re.I) if allow else None
    with sync_playwright() as pw:
        browser=pw.chromium.launch(headless=headless); page=browser.new_page(); errors=[]
        page.on('console',lambda m: errors.append({'type':'console','level':m.type,'text':m.text}) if m.type=='error' else None)
        page.on('pageerror',lambda e: errors.append({'type':'pageerror','text':str(e)}))
        page.goto(url,wait_until='networkidle')
        controls=page.locator('button, a[href], [role="button"], input[type="submit"], input[type="button"]')
        count=min(controls.count(),250)
        for idx in range(count):
            c=controls.nth(idx)
            try:
                label=(c.inner_text(timeout=500) or c.get_attribute('aria-label') or c.get_attribute('title') or '').strip()
                href=c.get_attribute('href'); disabled=c.is_disabled(); visible=c.is_visible()
                rec={'index':idx,'label':label[:160],'tag':c.evaluate('(e)=>e.tagName.toLowerCase()'),'href':href,'visible':visible,'disabled':disabled,'clicked':False,'before_url':page.url,'after_url':page.url,'changed':False}
                if click_safe and visible and not disabled and not DESTRUCTIVE.search(label or '') and (allow_re is None or allow_re.search(label or href or '')):
                    before=page.url; before_sig=page.locator('body').inner_text(timeout=1000)[:4000]
                    try:
                        c.click(timeout=1500); page.wait_for_timeout(250)
                        after=page.url; after_sig=page.locator('body').inner_text(timeout=1000)[:4000]
                        rec.update({'clicked':True,'after_url':after,'changed':before!=after or before_sig!=after_sig})
                        if before!=after: page.go_back(wait_until='domcontentloaded'); page.wait_for_timeout(150)
                    except Exception as exc: rec['click_error']=str(exc)
                records.append(rec)
            except Exception as exc: records.append({'index':idx,'inventory_error':str(exc)})
        browser.close()
    return {'url':url,'controls':records,'errors':errors}

def main():
    ap=argparse.ArgumentParser(description=__doc__); ap.add_argument('source',type=Path,nargs='?',default=Path('.')); ap.add_argument('--url'); ap.add_argument('--click-safe',action='store_true'); ap.add_argument('--allow'); ap.add_argument('--headed',action='store_true'); ap.add_argument('--output',type=Path,default=Path('ui-audit.json'))
    args=ap.parse_args(); root=args.source.resolve(); report={'schema_version':1,'source':str(root),'static_findings':static_scan(root)}
    if args.url:
        try: report['runtime']=runtime_audit(args.url,args.click_safe,args.allow,not args.headed)
        except Exception as exc: report['runtime_error']=str(exc)
    args.output.parent.mkdir(parents=True,exist_ok=True); args.output.write_text(json.dumps(report,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
    dead=[x for x in report['static_findings'] if x['kind'] in ('dead_href','console_only','empty_handler','fake_success')]
    if report.get('runtime'):
        for c in report['runtime']['controls']:
            if c.get('clicked') and not c.get('changed'): dead.append({'kind':'runtime_no_observable_change','control':c})
    print(args.output); print(f'static_findings={len(report["static_findings"])} suspicious_controls={len(dead)}')
    return 1 if dead else 0
if __name__=='__main__': raise SystemExit(main())
