#!/usr/bin/env python3
"""Preserve absolute-coordinate mouse APIs without creating an invalid Mixin.

Accessor mixins must declare only annotated accessor/invoker methods.  Put the
legacy default implementation on an ordinary parent interface, outside every
Mixin package; keep the original accessor type and every caller unchanged.
"""
import hashlib
from pathlib import Path
import re
from northpoint_runtime_mixin_rules import mask_comments, param_rows, ConversionBlock
from northpoint_target_26_3_core import _find_matching_java_brace


def rewrite_mouse_invokers(root: Path) -> list[dict]:
    changes = []
    for path in sorted(root.rglob('*.java')):
        text = path.read_text(encoding='utf-8')
        masked = mask_comments(text)
        imported = bool(re.search(r'import\s+net\.minecraft\.client\.MouseHandler\s*;', masked))
        owner = r'(?:net\.minecraft\.client\.MouseHandler|MouseHandler)' if imported else r'net\.minecraft\.client\.MouseHandler'
        regions = []
        for found in re.finditer(r'@(?:org\.spongepowered\.asm\.mixin\.)?Mixin\s*\(\s*(?:value\s*=\s*)?' + owner + r'\.class\s*\)', masked):
            declaration = re.match(r'\s*(?:public\s+)?interface\s+(\w+)([^{}]*)\{', masked[found.end():])
            if declaration:
                start = found.end() + declaration.end() - 1
                end = _find_matching_java_brace(text, start)
                if end is not None:
                    regions.append((start, end, declaration[1], declaration[2], found.end() + declaration.end(1)))
        pattern = r'@(?:org\.spongepowered\.asm\.mixin\.gen\.)?Invoker\s*\(\s*"onMove"\s*\)\s*(?:public\s+)?void\s+(\w+)\s*\(([^()]*)\)\s*;'
        hits = [(hit, region) for hit in re.finditer(pattern, masked)
                for region in regions if region[0] < hit.start() < region[1]]
        if not hits:
            continue
        if len({region[2] for _, region in hits}) != 1:
            raise ConversionBlock('multiple mouse accessor interfaces in one source need structural handling')
        region = hits[0][1]
        if '<' in region[3] or 'permits' in region[3]:
            raise ConversionBlock('generic/sealed mouse accessor needs structural handling')
        package_match = re.search(r'^\s*package\s+([\w.]+)\s*;', masked, re.M)
        package = package_match[1] if package_match else ''
        source_root = path.parent
        for part in reversed(package.split('.')) if package else []:
            if source_root.name != part:
                raise ConversionBlock('mouse accessor package does not match source path')
            source_root = source_root.parent
        if not source_root.resolve().is_relative_to(root.resolve()):
            raise ConversionBlock('generated mouse bridge would escape conversion root')
        identity = package + '.' + region[2]
        suffix = hashlib.sha256(identity.encode()).hexdigest()[:12]
        helper_name = region[2] + 'AbsoluteMouseBridge_' + suffix
        helper_package = 'northpoint.generated.mouse'
        helper_path = source_root / helper_package.replace('.', '/') / (helper_name + '.java')
        helper_methods = []
        edits = []
        for found, _ in hits:
            params = param_rows(found[2])
            if [kind for kind, _ in params] != ['long', 'double', 'double']:
                continue
            if any(name == 'northpointMouse' for _, name in params):
                raise ConversionBlock('mouse invoker variable collision')
            window, x, y = [name for _, name in params]
            declaration = ', '.join(kind + ' ' + name for kind, name in params)
            raw_name = 'northpoint$absoluteMove$' + suffix + '$' + found[1]
            if raw_name in masked:
                raise ConversionBlock('generated mouse invoker name collision')
            raw_params = 'long window, double x, double y, double dx, double dy'
            helper_methods.append(
                '    void ' + raw_name + '(' + raw_params + ');\n'
                '    default void ' + found[1] + '(' + declaration + ') {\n'
                '        net.minecraft.client.MouseHandler northpointMouse = (net.minecraft.client.MouseHandler)(Object)this;\n'
                '        ' + raw_name + '(' + window + ', ' + x + ', ' + y + ', '
                + x + ' - northpointMouse.xpos(), ' + y + ' - northpointMouse.ypos());\n'
                '    }\n')
            edits.append((found.start(), found.end(),
                          '@org.spongepowered.asm.mixin.gen.Invoker("onMove")\n'
                          '    void ' + raw_name + '(' + raw_params + ');'))
        if not edits:
            continue
        helper = ('package ' + helper_package + ';\n\n'
                  '// Generated ordinary parent interface. Do not register as a Mixin.\n'
                  'public interface ' + helper_name + ' {\n' + '\n'.join(helper_methods) + '}\n')
        if helper_path.exists() and helper_path.read_text(encoding='utf-8') != helper:
            raise ConversionBlock('generated mouse bridge collides with existing source: ' + str(helper_path))
        base = helper_package + '.' + helper_name
        if re.match(r'\s*extends\s+', region[3]):
            position = region[0]
            edits.append((position, position, ', ' + base + ' '))
        elif region[3].strip():
            raise ConversionBlock('unsupported mouse accessor declaration')
        else:
            edits.append((region[4], region[4], ' extends ' + base))
        for start, end, replacement in sorted(edits, reverse=True):
            text = text[:start] + replacement + text[end:]
        helper_path.parent.mkdir(parents=True, exist_ok=True)
        helper_path.write_text(helper, encoding='utf-8')
        path.write_text(text, encoding='utf-8')
        changes.append({'rule': 'minecraft-26.3-mouse-invoker-absolute-bridge',
                        'path': path.relative_to(root).as_posix(), 'count': len(helper_methods),
                        'generated_path': helper_path.relative_to(root).as_posix()})
    return changes
