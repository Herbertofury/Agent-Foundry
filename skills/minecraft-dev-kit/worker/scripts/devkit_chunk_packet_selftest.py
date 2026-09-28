#!/usr/bin/env python3
from pathlib import Path
import tempfile
from northpoint_chunk_packet_rules import rewrite_chunk_packet_mixins, ConversionBlock, OLD, NEW

SOURCE='''import net.minecraft.client.multiplayer.ClientChunkCache;
import net.minecraft.network.FriendlyByteBuf;
import net.minecraft.network.protocol.game.ClientboundLevelChunkPacketData;
import net.minecraft.world.level.chunk.LevelChunk;
import net.minecraft.world.level.levelgen.Heightmap;
@Mixin(ClientChunkCache.class) class ChunkHook {
@Inject(method="replaceWithPacketData",at=@At("RETURN"))
private void loaded(int x,int z,FriendlyByteBuf buffer,Map<Heightmap.Types, long[]> heights,Consumer<ClientboundLevelChunkPacketData.BlockEntityTagOutput> tags,CallbackInfoReturnable<LevelChunk> ci) { LevelChunk chunk=ci.getReturnValue(); if(chunk!=null) Events.loaded(chunk); }
@Inject(method="drop",at=@At("HEAD")) private void unload(ChunkPos pos,CallbackInfo ci) { Events.unload(pos); }
}'''

def main():
    with tempfile.TemporaryDirectory() as td:
        root=Path(td);p=root/'Hook.java';p.write_text(SOURCE)
        assert len(rewrite_chunk_packet_mixins(root))==1
        assert 'ClientboundLevelChunkPacketData northpointChunkData' in p.read_text()
        assert '{ LevelChunk chunk=ci.getReturnValue(); if(chunk!=null) Events.loaded(chunk); }' in p.read_text()
        assert '@Inject(method="drop",at=@At("HEAD")) private void unload(ChunkPos pos,CallbackInfo ci) { Events.unload(pos); }' in p.read_text()
        assert not rewrite_chunk_packet_mixins(root)
        p.write_text(SOURCE.replace('method="replaceWithPacketData"','method="'+OLD+'"'))
        rewrite_chunk_packet_mixins(root);assert NEW in p.read_text()
        for wrong in [SOURCE.replace('net.minecraft.client.multiplayer.ClientChunkCache','foreign.ClientChunkCache'),SOURCE.replace('net.minecraft.network.FriendlyByteBuf','foreign.FriendlyByteBuf'),'/* '+SOURCE+' */']:
            p.write_text(wrong);assert not rewrite_chunk_packet_mixins(root);assert p.read_text()==wrong
        for wrong in [SOURCE.replace('Events.loaded(chunk)','Events.loaded(buffer)'),SOURCE.replace('at=@At("RETURN")','at=@At("RETURN"),locals=LocalCapture.CAPTURE_FAILHARD')]:
            p.write_text(wrong)
            try:rewrite_chunk_packet_mixins(root)
            except ConversionBlock:pass
            else:raise AssertionError('unsafe packet payload or locals discarded')
            assert p.read_text()==wrong
    print('Chunk packet Mixin: retained loaded/unloaded event bodies, descriptors, owner guards, atomic negatives and idempotence PASS')
    return 0
if __name__=='__main__':raise SystemExit(main())
