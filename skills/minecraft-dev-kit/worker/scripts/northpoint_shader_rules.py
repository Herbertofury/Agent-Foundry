#!/usr/bin/env python3
"""Source-linked explicit shader interfaces for Minecraft 26.3 RenderPearl.

Authority: NeoForged 26.2 -> 26.3 shader primer and actual Shaderc failure.
Only proven single-vertex POSITION_TEX factory families are adapted. Preserve
all shader math, uniform blocks, identifiers and original files in the source.
"""
from __future__ import annotations
from pathlib import Path
import re
from northpoint_runtime_mixin_rules import mask_comments, ConversionBlock
from northpoint_target_26_3_core import _find_matching_java_brace


DECL = re.compile(r'(?m)^[ \t]*(?:(layout\s*\(\s*location\s*=\s*(\d+)\s*\))\s*)?((?:(?:flat|smooth|noperspective|centroid)\s+)*)(in|out)\s+(float|int|uint|[biu]?vec[234])\s+(\w+)\s*;')


def declarations(text: str, path: Path) -> list:
    masked = mask_comments(text)
    # Conditional or included declarations require an actual preprocessor/linker,
    # never number whichever branch happens to be visible in source text.
    if re.search(r'^\s*#\s*(?:if|ifdef|ifndef|include|moj_import)\b', masked, re.M):
        raise ConversionBlock('shader interface needs preprocessor-aware linkage: ' + str(path))
    found = list(DECL.finditer(masked))
    remainder = DECL.sub('', masked)
    if re.search(r'^\s*(?:layout\([^\n]*\)\s*)?(?:flat\s+)?(?:in|out)\b', remainder, re.M):
        raise ConversionBlock('complex shader interface needs an explicit layout: ' + str(path))
    if len({(m[4], m[6]) for m in found}) != len(found):
        raise ConversionBlock('duplicate shader interface symbol: ' + str(path))
    return found


def rewrite_stage(text: str, rows: list, locations: dict, path: Path) -> str:
    edits = []
    for row in rows:
        expected = locations.get((row[4], row[6]))
        if expected is None:
            raise ConversionBlock('unlinked shader interface: ' + str(path) + ':' + row[6])
        if row[2] is not None:
            if int(row[2]) != expected:
                raise ConversionBlock('existing shader location conflicts with the source pipeline: ' + str(path))
        else:
            # Keep the complete original declaration including indentation/qualifiers.
            offset = row.start()
            while text[offset] in ' \t': offset += 1
            edits.append((offset, 'layout(location = ' + str(expected) + ') '))
    if not edits:
        return text
    for offset, addition in reversed(edits): text = text[:offset] + addition + text[offset:]
    version = re.search(r'^\s*#version\s+(\d+)[^\n]*\n', text, re.M)
    if version is None:
        raise ConversionBlock('shader GLSL version is missing: ' + str(path))
    if int(version[1]) < 410 and not re.search(r'^\s*#extension\s+GL_ARB_separate_shader_objects\s*:\s*(?:require|enable)\b', text, re.M):
        text = text[:version.end()] + '#extension GL_ARB_separate_shader_objects : require\n' + text[version.end():]
    return text



# Official 26.3 DynamicGpuData.Transform.write(ByteBuffer): Mat4, Mat4, Vec4, Vec3.
# Old inline copies read ColorModulator from the texture matrix (alpha becomes 0).
TRANSFORM_FIELDS = [('mat4', 'ModelViewMat'), ('vec4', 'ColorModulator'),
                    ('vec3', 'ModelOffset'), ('mat4', 'TextureMat')]
TARGET_TRANSFORM_FIELDS = [TRANSFORM_FIELDS[i] for i in (0, 3, 1, 2)]


def rewrite_dynamic_transforms(text: str, path: Path) -> str:
    """Reorder only the complete known vanilla block, preserving declarations/math."""
    masked = mask_comments(text)
    pattern = re.compile(r'layout\s*\(\s*std140\s*\)\s*uniform\s+DynamicTransforms\s*\{([^{}]*)\}\s*;')
    blocks = list(pattern.finditer(masked))
    if not blocks:
        if re.search(r'\buniform\s+DynamicTransforms\b', masked):
            raise ConversionBlock('custom DynamicTransforms layout needs explicit adaptation: ' + str(path))
        return text
    if len(blocks) != 1:
        raise ConversionBlock('duplicate DynamicTransforms block: ' + str(path))
    block = blocks[0]
    members = list(re.finditer(r'\b(mat4|vec[34])\s+(\w+)\s*;', block[1]))
    remainder = re.sub(r'\b(mat4|vec[34])\s+(\w+)\s*;', '', block[1])
    signature = [(m[1], m[2]) for m in members]
    if remainder.strip() or signature not in (TRANSFORM_FIELDS, TARGET_TRANSFORM_FIELDS):
        raise ConversionBlock('unrecognized DynamicTransforms payload; no fields may be dropped: ' + str(path))
    if signature == TARGET_TRANSFORM_FIELDS:
        return text
    original = text[block.start(1):block.end(1)]
    chunks, end = {}, 0
    for member in members:
        chunks[(member[1], member[2])] = original[end:member.end()]
        end = member.end()
    body = ''.join(chunks[field] for field in TARGET_TRANSFORM_FIELDS) + original[end:]
    return text[:block.start(1)] + body + text[block.end(1):]


def rewrite_shader_interfaces(root: Path) -> list[dict]:
    families = set()
    transform_families = set()
    for path in sorted(root.rglob('*.java')):
        text = mask_comments(path.read_text(encoding='utf-8'))
        if not re.search(r'import\s+com\.mojang\.blaze3d\.vertex\.DefaultVertexFormat\s*;', text): continue
        if not re.search(r'import\s+net\.minecraft\.resources\.Identifier\s*;', text): continue
        helpers = {}
        pattern = r'(?:private|public|protected)\s+static\s+Identifier\s+(\w+)\s*\(\s*String\s+(\w+)\s*\)\s*\{\s*return\s+Identifier\.fromNamespaceAndPath\(\s*"([a-z0-9_.-]+)"\s*,\s*"([a-z0-9_/.-]*)"\s*\+\s*\2\s*\)\s*;\s*\}'
        for helper in re.finditer(pattern, text): helpers[helper[1]] = (helper[3], helper[4])
        for method in re.finditer(r'(?:private|public|protected)\s+static\s+RenderPipeline\s+\w+\s*\(\s*String\s+(\w+)\s*\)\s*\{', text):
            end = _find_matching_java_brace(text, method.end()-1)
            if end is None: continue
            body = text[method.end():end]
            calls = list(re.finditer(r'\.withVertexShader\(\s*(\w+)\(\s*"([a-z0-9_/.-]*)"\s*\)\s*\)\s*\.withFragmentShader\(\s*\1\(\s*'+re.escape(method[1])+r'\s*\)\s*\)', body))
            if len(calls) != 1 or calls[0][1] not in helpers: continue
            if len(re.findall(r'\bRenderPipeline\.builder\(\s*\)',body)) != 1: continue
            bindings = re.findall(r'\.withVertexBinding\(\s*(\d+)\s*,\s*DefaultVertexFormat\.(\w+)\s*\)',body)
            if bindings != [('0','POSITION_TEX')]: continue
            namespace, prefix = helpers[calls[0][1]]
            families.add((namespace, prefix, prefix+calls[0][2]))
            if re.search(r'\.withUniform\(\s*"DynamicTransforms"\s*,\s*UniformType\.UNIFORM_BUFFER\s*\)', body):
                transform_families.add((namespace, prefix, prefix+calls[0][2]))
    staged = {}
    for namespace, prefix, vertex_id in sorted(families):
        vertices = list(root.glob('**/resources/assets/'+namespace+'/shaders/'+vertex_id+'.vsh'))
        if len(vertices) != 1:
            raise ConversionBlock('source shader family has no unambiguous vertex resource: '+namespace+':'+vertex_id)
        vertex = vertices[0]; base = next(p for p in vertex.parents if p.name == 'shaders')
        fragments = sorted(p for p in base.rglob('*.fsh') if p.relative_to(base).as_posix().startswith(prefix))
        if not fragments: raise ConversionBlock('shader family has no fragment source: '+str(vertex))
        vtext = vertex.read_text(encoding='utf-8'); vr = declarations(vtext, vertex)
        inputs = {m[6]:m[5] for m in vr if m[4]=='in'}
        if inputs != {'Position':'vec3','UV0':'vec2'}:
            raise ConversionBlock('shader inputs do not match verified POSITION_TEX binding: '+str(vertex))
        outputs = [(m[6],m[5]) for m in vr if m[4]=='out']
        vlocations = {('in','Position'):0, ('in','UV0'):1}
        vlocations.update({('out',name):i for i,(name,kind) in enumerate(outputs)})
        stages = [(vertex,vtext,rewrite_stage(vtext,vr,vlocations,vertex))]
        for fragment in fragments:
            ftext = fragment.read_text(encoding='utf-8'); fr = declarations(ftext,fragment)
            fin = {m[6]:m[5] for m in fr if m[4]=='in'}
            if fin != dict(outputs):
                raise ConversionBlock('fragment does not link to the verified vertex interface: '+str(fragment))
            fout = [m for m in fr if m[4]=='out']
            if len(fout)!=1 or fout[0][5]!='vec4':
                raise ConversionBlock('fragment targets need explicit attachment mapping: '+str(fragment))
            flocations = {('in',name):i for i,(name,kind) in enumerate(outputs)}
            flocations[('out',fout[0][6])] = 0
            stages.append((fragment,ftext,rewrite_stage(ftext,fr,flocations,fragment)))
        for path,old,new in stages:
            rules = ['minecraft-26.3-linked-shader-interface-locations'] if old != new else []
            if (namespace, prefix, vertex_id) in transform_families:
                transformed = rewrite_dynamic_transforms(new, path)
                if transformed != new:
                    rules.append('minecraft-26.3-dynamic-transform-uniform-layout')
                    new = transformed
            if path in staged and staged[path][1]!=new:
                raise ConversionBlock('shared shader has contradictory pipeline layouts: '+str(path))
            staged[path] = (old,new,rules)
    changes=[]
    # No file changes occur until every linked stage passed the complete audit.
    for path,(old,new,rules) in sorted(staged.items()):
        if old!=new:
            path.write_text(new,encoding='utf-8')
            for rule in rules:
                changes.append({'rule':rule, 'path':path.relative_to(root).as_posix(),'count':1})
    return changes
