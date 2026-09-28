#!/usr/bin/env python3
"""26.3 ClientChunkCache packet payload migration, proven by real Mixin APPLY.

Retain return-value chunk events. Only collapse unused legacy packet arguments;
consumed buffers/heightmaps/block-entity consumers require an explicit bridge.
"""
from pathlib import Path
import re
from northpoint_runtime_mixin_rules import handlers, mask_comments, signature_replace, require_no_locals, ConversionBlock

OLD = 'replaceWithPacketData(IILnet/minecraft/network/FriendlyByteBuf;Ljava/util/Map;Ljava/util/function/Consumer;)Lnet/minecraft/world/level/chunk/LevelChunk;'
NEW = 'replaceWithPacketData(IILnet/minecraft/network/protocol/game/ClientboundLevelChunkPacketData;)Lnet/minecraft/world/level/chunk/LevelChunk;'
PARAMETERS = re.compile(r'\s*int\s+(\w+)\s*,\s*int\s+(\w+)\s*,\s*(?:net\.minecraft\.network\.)?FriendlyByteBuf\s+(\w+)\s*,\s*(?:java\.util\.)?Map\s*<\s*(?:net\.minecraft\.world\.level\.levelgen\.)?Heightmap\.Types\s*,\s*long\s*\[\s*\]\s*>\s+(\w+)\s*,\s*(?:java\.util\.function\.)?Consumer\s*<\s*(?:net\.minecraft\.network\.protocol\.game\.)?ClientboundLevelChunkPacketData\.BlockEntityTagOutput\s*>\s+(\w+)\s*,\s*((?:org\.spongepowered\.asm\.mixin\.injection\.callback\.)?CallbackInfoReturnable\s*<\s*(?:net\.minecraft\.world\.level\.chunk\.)?LevelChunk\s*>)\s+(\w+)\s*')


def rewrite_chunk_packet_mixins(root: Path) -> list[dict]:
    result = []
    staged = []
    for path in sorted(root.rglob('*.java')):
        text = path.read_text(encoding='utf-8')
        edits = []
        for handler in handlers(text, 'net.minecraft.client.multiplayer.ClientChunkCache'):
            if handler['kind'] != 'Inject': continue
            annotation = handler['annotation']
            if not re.search(r'\bmethod\s*=\s*"(?:replaceWithPacketData|'+re.escape(OLD)+')"', annotation): continue
            match = PARAMETERS.fullmatch(handler['params'])
            if not match: continue
            require_no_locals(handler)
            masked = mask_comments(text)
            for short, owner in [('FriendlyByteBuf','net.minecraft.network.FriendlyByteBuf'),('Heightmap','net.minecraft.world.level.levelgen.Heightmap'),('ClientboundLevelChunkPacketData','net.minecraft.network.protocol.game.ClientboundLevelChunkPacketData'),('LevelChunk','net.minecraft.world.level.chunk.LevelChunk')]:
                if re.search(r'(?<![\w.])'+short+r'\b', handler['params']) and not re.search(r'import\s+'+re.escape(owner)+r'\s*;',masked):
                    break
            else:
                body = mask_comments(handler['body'])
                if any(re.search(r'\b'+re.escape(match[i])+r'\b',body) for i in [3,4,5]):
                    raise ConversionBlock('chunk packet callback consumes old payload; semantic bridge required: '+str(path))
                if 'northpointChunkData' in handler['full']:
                    raise ConversionBlock('chunk packet callback variable collision: '+str(path))
                parameters = 'int '+match[1]+', int '+match[2]+', net.minecraft.network.protocol.game.ClientboundLevelChunkPacketData northpointChunkData, '+match[6]+' '+match[7]
                replacement = signature_replace(handler, annotation.replace(OLD,NEW), parameters)
                edits.append((handler['start'],handler['end'],replacement))
        for start,end,replacement in sorted(edits,reverse=True):text=text[:start]+replacement+text[end:]
        if edits:staged.append((path,text,len(edits)))
    for path,text,count in staged:
        path.write_text(text,encoding='utf-8')
        result.append({'rule':'minecraft-26.3-chunk-packet-data-callback','path':path.relative_to(root).as_posix(),'count':count})
    return result
