#!/usr/bin/env python3
"""Retain exact packet hook semantics and all source bytes across the 26.3 move."""
from pathlib import Path
import tempfile
import northpoint_target_26_3 as engine

SOURCE = '''import net.minecraft.client.player.LocalPlayer;
@Mixin(LocalPlayer.class)
class Test {
@Inject(method = "tick", at = @At(value = "INVOKE", target = "Lnet/minecraft/client/multiplayer/ClientPacketListener;send(Lnet/minecraft/network/protocol/Packet;)V", ordinal = 0))
private void before(CallbackInfo ci) { event.pre(); }
@Inject(method = "tick", at = @At(value = "INVOKE", target = "Lnet/minecraft/client/multiplayer/ClientPacketListener;send(Lnet/minecraft/network/protocol/Packet;)V", ordinal = 1, shift = At.Shift.AFTER))
private void after(CallbackInfo ci) { event.post(); }
@Inject(method = "tick", at = @At("HEAD"))
private void unrelated(CallbackInfo ci) { event.tick(); }
}
'''

def main():
    from devkit_shader_selftest import main as shader_tests
    assert shader_tests()==0
    from devkit_chunk_packet_selftest import main as chunk_tests
    assert chunk_tests()==0
    with tempfile.TemporaryDirectory(prefix='mixin-target-test-') as td:
        root=Path(td);p=root/'Test.java';p.write_text(SOURCE)
        rows=engine.rewrite_network_tick_mixins(root)
        assert rows[0]['count']==2
        updated=p.read_text()
        assert updated==SOURCE.replace('method = "tick", at = @At(value = "INVOKE"','method = "sendChanges", at = @At(value = "INVOKE"')
        assert not engine.rewrite_network_tick_mixins(root)
        p.write_text(SOURCE.replace('net.minecraft.client.player.LocalPlayer','example.LocalPlayer'))
        assert not engine.rewrite_network_tick_mixins(root)
        other=SOURCE.split('@Mixin',1)[1].replace('(LocalPlayer.class)','(Other.class)').replace('class Test','class OtherMixin')
        p.write_text(SOURCE+'@Mixin'+other)
        assert engine.rewrite_network_tick_mixins(root)[0]['count']==2
        assert p.read_text().endswith('@Mixin'+other)
        for invalid in [SOURCE.replace('(CallbackInfo ci)','(CallbackInfo ci, int captured)'),SOURCE.replace('method = "tick",','locals = LocalCapture.CAPTURE_FAILHARD, method = "tick",')]:
            p.write_text(invalid)
            try:engine.rewrite_network_tick_mixins(root)
            except engine.ConversionBlock:pass
            else:raise AssertionError('unsafe local capture was silently rewritten')
        large=root/'large-source.bin';large.write_bytes(b'x'*(21*1024*1024));original=engine.tree_digest(root)
        with large.open('r+b') as stream:stream.seek(-1,2);stream.write(b'y')
        assert engine.tree_digest(root)!=original
    from devkit_mouse_bridge_selftest import main as mouse_bridge_tests
    assert mouse_bridge_tests() == 0
    from devkit_runtime_mixin_selftest import main as runtime_mixin_tests
    assert runtime_mixin_tests() == 0
    print('Mixin exact owner/class/method scope, preserved body/ordinal/shift, local-capture guard, idempotence and large-source integrity: PASS')
    return 0
if __name__=='__main__':raise SystemExit(main())
