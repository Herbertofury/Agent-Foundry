#!/usr/bin/env python3
"""Exact 26.3 input/render Mixin migrations established from official bytecode.

No missing-injector suppression: retain handlers and register split target mixins.
"""
from __future__ import annotations
import json
from pathlib import Path
import re
from northpoint_target_26_3_core import ConversionBlock, _find_matching_java_brace


def mask_comments(text: str) -> str:
    token = re.compile(r'"(?:\\.|[^"\\])*"|\'(?:\\.|[^\'\\])*\'|//[^\n]*|/\*[\s\S]*?\*/')
    return token.sub(lambda m: re.sub(r'[^\n]', ' ', m[0]) if m[0].startswith(('/',)) else m[0], text)


def closing(text: str, start: int) -> int:
    depth = 0; quote = None; escaped = False
    for pos in range(start, len(text)):
        char = text[pos]
        if quote:
            if escaped: escaped = False
            elif char == '\\': escaped = True
            elif char == quote: quote = None
        elif char in '\"\'': quote = char
        elif char == '(': depth += 1
        elif char == ')':
            depth -= 1
            if depth == 0: return pos + 1
    raise ConversionBlock('unterminated runtime Mixin annotation')


def owner_regions(text: str, fqcn: str):
    masked = mask_comments(text)
    short = fqcn.rsplit('.', 1)[1]
    simple = bool(re.search(r'import\s+' + re.escape(fqcn) + r'\s*;', masked))
    owner = '(?:' + re.escape(fqcn) + ('|' + re.escape(short) if simple else '') + ')'
    regions = []
    for match in re.finditer(r'@(?:org\.spongepowered\.asm\.mixin\.)?Mixin\s*\(\s*(?:value\s*=\s*)?' + owner + r'\.class\s*\)', masked):
        declaration = re.search(r'\bclass\s+(\w+)[^{}]*\{', masked[match.end():])
        if declaration:
            start = match.end() + declaration.end() - 1
            end = _find_matching_java_brace(text, start)
            if end is not None: regions.append((start, end, declaration[1]))
    return regions


def handlers(text: str, fqcn: str):
    masked = mask_comments(text)
    regions = owner_regions(text, fqcn)
    for match in re.finditer(r'@(?:org\.spongepowered\.asm\.mixin\.injection\.)?(Inject|Redirect)\s*\(', masked):
        region = next((row for row in regions if row[0] < match.start() < row[1]), None)
        if not region: continue
        end = closing(masked, match.end()-1)
        signature = re.match(r'\s*(?:private|protected|public)\s+(?:(?:static|final)\s+)*(void|float)\s+(\w+)\s*\(([^()]*)\)\s*\{', masked[end:])
        if not signature: continue
        body_start = end + signature.end() - 1
        body_end = _find_matching_java_brace(text, body_start)
        if body_end is None: raise ConversionBlock('unterminated Mixin handler')
        yield {'start':match.start(), 'annotation_end':end, 'end':body_end+1,
               'annotation':text[match.start():end], 'kind':match[1], 'params':signature[3],
               'return':signature[1], 'name':signature[2], 'class':region[2],
               'body':text[body_start+1:body_end], 'full':text[match.start():body_end+1]}


def param_rows(text: str):
    rows=[]
    for p in text.split(','):
        match=re.fullmatch(r'\s*([\w.$]+)\s+(\w+)\s*',p)
        if not match: raise ConversionBlock('annotated or complex Mixin parameters need semantic handling')
        rows.append((match[1],match[2]))
    return rows


def signature_replace(handler, annotation, parameters, body=None):
    full=handler['full']; old_end=handler['annotation_end']-handler['start']
    tail=full[old_end:]
    tail=re.sub(r'(\b'+re.escape(handler['name'])+r'\s*\()[^()]*(\))',lambda m:m[1]+parameters+m[2],tail,count=1)
    if body is not None: tail=tail[:tail.index('{')+1]+body+'}'
    return annotation+tail


def require_no_locals(handler):
    if re.search(r'\b(?:locals|slice)\s*=',mask_comments(handler['annotation'])):
        raise ConversionBlock('runtime Mixin migration cannot discard local-capture or slice semantics')


def split_item_activation(root: Path, path: Path, text: str, handler):
    require_no_locals(handler)
    body=mask_comments(handler['body'])
    fields=re.findall(r'@Shadow\s+(?:@\w+\s+)*(?:private|protected|public)\s+[\w.<>]+\s+(\w+)\s*;',mask_comments(text))
    if re.search(r'\b(?:this|super)\b',body) or any(re.search(r'\b'+re.escape(name)+r'\b',body) for name in fields):
        raise ConversionBlock('item-activation hook consumes the old owner state; preserve it with a typed bridge')
    local_calls=re.findall(r'(?<![\w.$])([a-zA-Z_]\w*)\s*\(',body)
    if any(name not in {'if','switch','while','for','catch','synchronized'} for name in local_calls):
        raise ConversionBlock('item-activation hook calls an owner-local helper; explicit bridge required')
    package=re.search(r'\bpackage\s+([\w.]+)\s*;',mask_comments(text))
    if not package:raise ConversionBlock('split Mixin requires a named package')
    generated=handler['class']+'NorthpointItemActivation'
    fqcn=package[1]+'.'+generated;oldfqcn=package[1]+'.'+handler['class']
    configs=[]
    for config in root.rglob('*.json'):
        if 'build' in config.parts:continue
        try:value=json.loads(config.read_text())
        except (ValueError,UnicodeError):continue
        if not isinstance(value,dict) or not isinstance(value.get('package'),str):continue
        changed=False
        for key in ('client','mixins','server'):
            entries=value.get(key)
            if not isinstance(entries,list):continue
            for name in list(entries):
                if value['package']+'.'+str(name)==oldfqcn:
                    if not fqcn.startswith(value['package']+'.'):raise ConversionBlock('split Mixin package mismatch')
                    relative=fqcn[len(value['package'])+1:]
                    if relative not in entries:entries.append(relative);changed=True
        if changed:configs.append((config,value))
    if not configs:raise ConversionBlock('source hook was not found in a Mixin configuration; refuse an unregistered split')
    imports='\n'.join(re.findall(r'^import\s+[^;]+;',text,re.M))
    content=text[:package.end()]+'\n'+imports+'\n@Mixin(net.minecraft.client.player.LocalPlayer.class)\npublic abstract class '+generated+' {\n'+handler['full']+'\n}\n'
    target=path.with_name(generated+'.java')
    if target.exists() and target.read_text()!=content:raise ConversionBlock('generated Mixin collision: '+str(target))
    target.write_text(content)
    for config,value in configs:config.write_text(json.dumps(value,indent=2)+'\n')
    return target


def rewrite_runtime_mixins(root: Path) -> list[dict]:
    changes=[]
    for path in sorted(root.rglob('*.java')):
        text=path.read_text(encoding='utf-8');edits=[]
        for handler in handlers(text,'net.minecraft.client.MouseHandler'):
            annotation=handler['annotation']
            if handler['kind']!='Inject' or '"onMove(JDD)V"' not in annotation:continue
            require_no_locals(handler);params=param_rows(handler['params'])
            if [p[0].rsplit('.',1)[-1] for p in params]!=['long','double','double','CallbackInfo']:
                raise ConversionBlock('unexpected legacy mouse move hook signature: '+str(path))
            if re.search(r'\bnorthpoint(?:DX|DY)\b',handler['full']):raise ConversionBlock('mouse callback parameter collision')
            parameters=', '.join(t+' '+n for t,n in params[:-1])+', double northpointDX, double northpointDY, '+params[-1][0]+' '+params[-1][1]
            body=handler['body']
            # Match vanilla: grabbed-pointer motion uses SDL's relative deltas;
            # ungrabbed motion retains the original absolute coordinate difference.
            for parameter, field, delta in [(params[1][1],'xpos','northpointDX'),(params[2][1],'ypos','northpointDY')]:
                pattern=r'\b'+re.escape(parameter)+r'\s*-\s*this\.'+field+r'\b'
                body=re.sub(pattern,lambda m:'(net.minecraft.client.Minecraft.getInstance().mouseHandler.isMouseGrabbed() ? '+delta+' : '+m[0]+')',body)
            replacement=signature_replace(handler,annotation.replace('"onMove(JDD)V"','"onMove(JDDDD)V"'),parameters,body)
            edits.append((handler['start'],handler['end'],replacement,'minecraft-26.3-mouse-move-relative-deltas'))
        for handler in handlers(text,'net.minecraft.client.renderer.GameRenderer'):
            annotation=handler['annotation'];body=handler['body']
            if handler['kind']=='Inject' and re.search(r'\bmethod\s*=\s*"displayItemActivation(?:\(Lnet/minecraft/world/item/ItemStack;\)V)?"',annotation):
                params=param_rows(handler['params'])
                if [p[0].rsplit('.',1)[-1] for p in params]!=['ItemStack','CallbackInfo']:
                    raise ConversionBlock('unexpected item activation callback signature')
                split_item_activation(root,path,text,handler)
                edits.append((handler['start'],handler['end'],'','minecraft-26.3-item-activation-mixin-owner'))
            elif handler['kind']=='Redirect' and 'renderLevel(Lnet/minecraft/client/DeltaTracker;)V' in annotation and 'Lnet/minecraft/util/Mth;lerp(FFF)F' in annotation:
                require_no_locals(handler);params=param_rows(handler['params'])
                if len(params)!=3 or any(t!='float' for t,n in params):raise ConversionBlock('complex nausea redirect needs explicit adaptation')
                expected=r'(?:Mth|net\.minecraft\.util\.Mth)\s*\.\s*lerp\s*\(\s*'+r'\s*,\s*'.join(re.escape(n) for t,n in params)+r'\s*\)'
                matches=list(re.finditer(expected,body))
                if len(matches)!=1 or any(re.search(r'\b'+re.escape(n)+r'\b',mask_comments(re.sub(expected,'',body))) for t,n in params):
                    raise ConversionBlock('nausea redirect consumes uninterpolated values; cannot replace by render-state field')
                if not re.search(r'\bordinal\s*=\s*0\b',annotation):raise ConversionBlock('unproven nausea interpolation ordinal')
                newbody=re.sub(expected,'northpointPlayerState.nauseaEffectIntensity',body)
                updated=annotation.replace('renderLevel(Lnet/minecraft/client/DeltaTracker;)V','renderLevel()V').replace('"INVOKE"','"FIELD"').replace('Lnet/minecraft/util/Mth;lerp(FFF)F','Lnet/minecraft/client/renderer/state/level/PlayerRenderState;nauseaEffectIntensity:F')
                replacement=signature_replace(handler,updated,'net.minecraft.client.renderer.state.level.PlayerRenderState northpointPlayerState',newbody)
                edits.append((handler['start'],handler['end'],replacement,'minecraft-26.3-nausea-render-state-redirect'))
        # Exact 26.3 ScreenEffectRenderer.submitWater descriptor from official
        # bytecode. Fire keeps its existing signature and is deliberately untouched.
        for handler in handlers(text,'net.minecraft.client.renderer.ScreenEffectRenderer'):
            annotation=handler['annotation']
            old='submitWater(Lnet/minecraft/client/Minecraft;Lcom/mojang/blaze3d/vertex/PoseStack;Lnet/minecraft/client/renderer/SubmitNodeCollector;)V'
            if handler['kind']!='Inject' or not re.search(r'\bmethod\s*=\s*"(?:submitWater|'+re.escape(old)+')"',annotation):continue
            params=param_rows(handler['params'])
            types=[t.rsplit('.',1)[-1] for t,n in params]
            if types!=['Minecraft','PoseStack','SubmitNodeCollector','CallbackInfo']:continue
            if params[0][0]=='Minecraft' and not re.search(r'import\s+net\.minecraft\.client\.Minecraft\s*;',mask_comments(text)):continue
            if params[0][0] not in {'Minecraft','net.minecraft.client.Minecraft'}:continue
            require_no_locals(handler)
            if re.search(r'\b'+re.escape(params[0][1])+r'\b',mask_comments(handler['body'])):
                raise ConversionBlock('water overlay callback consumes the old client parameter; explicit state bridge required')
            selected=[('net.minecraft.client.renderer.state.level.PlayerRenderState.WaterOverlay',params[0][1])]+params[1:]
            updated=annotation.replace(old,old.replace('Lnet/minecraft/client/Minecraft;','Lnet/minecraft/client/renderer/state/level/PlayerRenderState$WaterOverlay;'))
            replacement=signature_replace(handler,updated,', '.join(t+' '+n for t,n in selected))
            edits.append((handler['start'],handler['end'],replacement,'minecraft-26.3-water-overlay-render-state'))
        for handler in handlers(text,'net.minecraft.client.renderer.LevelRenderer'):
            annotation=handler['annotation']
            old='render(Lcom/mojang/blaze3d/resource/GraphicsResourceAllocator;Lnet/minecraft/client/DeltaTracker;ZLnet/minecraft/client/renderer/state/level/CameraRenderState;Lorg/joml/Matrix4fc;Lcom/mojang/blaze3d/buffers/GpuBufferSlice;Lorg/joml/Vector4f;Z)V'
            if handler['kind']!='Inject' or old not in annotation:continue
            require_no_locals(handler);params=param_rows(handler['params'])
            types=[t.rsplit('.',1)[-1] for t,n in params]
            if types!=['GraphicsResourceAllocator','DeltaTracker','boolean','CameraRenderState','Matrix4fc','GpuBufferSlice','Vector4f','boolean','CallbackInfo']:
                raise ConversionBlock('unexpected LevelRenderer callback signature')
            if re.search(r'\b'+re.escape(params[4][1])+r'\b',mask_comments(handler['body'])):
                raise ConversionBlock('LevelRenderer callback consumes removed model-view matrix; a measured camera-state bridge is required')
            selected=[params[i] for i in [0,2,3,5,6,7]]+[('boolean','northpointConsistentDepth'),params[8]]
            if re.search(r'\bnorthpointConsistentDepth\b',handler['body']):raise ConversionBlock('render callback parameter collision')
            new='render(Lcom/mojang/blaze3d/resource/GraphicsResourceAllocator;ZLnet/minecraft/client/renderer/state/level/CameraRenderState;Lcom/mojang/renderpearl/api/buffers/GpuBufferSlice;Lorg/joml/Vector4f;ZZ)V'
            body='\n        net.minecraft.client.DeltaTracker '+params[1][1]+' = net.minecraft.client.Minecraft.getInstance().getDeltaTracker();'+handler['body']
            replacement=signature_replace(handler,annotation.replace(old,new),', '.join(t+' '+n for t,n in selected),body)
            edits.append((handler['start'],handler['end'],replacement,'minecraft-26.3-level-render-mixin-state-signature'))
        for start,end,replacement,rule in sorted(edits,reverse=True):
            text=text[:start]+replacement+text[end:]
            changes.append({'rule':rule,'path':path.relative_to(root).as_posix(),'count':1})
        if edits:path.write_text(text,encoding='utf-8')
    return changes
