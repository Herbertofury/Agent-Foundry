#!/usr/bin/env python3
"""Dependency-free structural checker for site-adapter manifests."""
from __future__ import annotations
import argparse, json, re, sys
from pathlib import Path

ALLOWED_AUTH = {"none", "oauth2", "device-code", "api-token", "browser-session"}
ALLOWED_TRANSPORTS = {"official-api", "public-endpoint", "structured-endpoint", "embedded-structured-data", "html", "authorized-browser-session"}
ALLOWED_PAGINATION = {"none", "page", "offset", "cursor", "next-link", "infinite-scroll"}
REQUIRED = {"id", "name", "version", "base_urls", "capabilities", "auth", "transports", "pagination", "health"}
ID_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")

def fail(errors):
    for error in errors:
        print(f"ERROR: {error}")
    return 1

def check(data):
    errors=[]
    missing=sorted(REQUIRED-set(data))
    if missing: errors.append("missing required keys: " + ", ".join(missing))
    ident=data.get("id")
    if not isinstance(ident,str) or not ID_RE.fullmatch(ident): errors.append("id must be lowercase kebab-case")
    for key in ("name","version"):
        if not isinstance(data.get(key),str) or not data.get(key).strip(): errors.append(f"{key} must be a non-empty string")
    urls=data.get("base_urls")
    if not isinstance(urls,list) or not urls or not all(isinstance(x,str) and x for x in urls): errors.append("base_urls must be a non-empty string list")
    caps=data.get("capabilities")
    if not isinstance(caps,list) or not all(isinstance(x,str) and x for x in caps): errors.append("capabilities must be a string list")
    elif len(caps)!=len(set(caps)): errors.append("capabilities must be unique")
    auth=data.get("auth")
    if not isinstance(auth,dict): errors.append("auth must be an object")
    else:
        methods=auth.get("methods")
        req=auth.get("required_for")
        if not isinstance(methods,list) or not methods or not set(methods)<=ALLOWED_AUTH: errors.append("auth.methods contains unsupported values or is empty")
        if not isinstance(req,list) or not all(isinstance(x,str) for x in req): errors.append("auth.required_for must be a string list")
        elif isinstance(caps,list) and not set(req)<=set(caps): errors.append("auth.required_for must reference declared capabilities")
        if isinstance(req,list) and req and isinstance(methods,list) and set(methods)=={"none"}: errors.append("authenticated capabilities cannot use only auth method 'none'")
    transports=data.get("transports")
    if not isinstance(transports,list) or not transports or not set(transports)<=ALLOWED_TRANSPORTS: errors.append("transports contains unsupported values or is empty")
    pagination=data.get("pagination")
    modes=pagination.get("modes") if isinstance(pagination,dict) else None
    if not isinstance(modes,list) or not modes or not set(modes)<=ALLOWED_PAGINATION: errors.append("pagination.modes contains unsupported values or is empty")
    health=data.get("health")
    if not isinstance(health,dict) or not isinstance(health.get("supported"),bool): errors.append("health.supported must be boolean")
    return errors

def main():
    p=argparse.ArgumentParser()
    p.add_argument("manifest")
    args=p.parse_args()
    path=Path(args.manifest)
    try: data=json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc: return fail([f"cannot read/parse manifest: {exc}"])
    if not isinstance(data,dict): return fail(["manifest root must be an object"])
    errors=check(data)
    if errors: return fail(errors)
    print(f"PASS: site adapter manifest {data['id']} v{data['version']}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
