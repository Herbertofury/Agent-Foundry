#!/usr/bin/env python3
"""Positive and negative controls for structural 26.3 runtime migrations."""
from pathlib import Path
import json
import tempfile
from northpoint_runtime_mixin_rules import rewrite_runtime_mixins, ConversionBlock

MOUSE='''package fixture;
import net.minecraft.client.MouseHandler;
@Mixin(MouseHandler.class) class MouseMixin {
@Inject(method={"onMove(JDD)V"},at=@At("HEAD"),cancellable=true)
private void cursor(long window,double x,double y,CallbackInfo ci) { events.fire(x,y); if(cancelled) ci.cancel(); }
}
'''
RENDER='''package fixture;
import net.minecraft.client.renderer.GameRenderer;
import org.spongepowered.asm.mixin.Mixin;
import net.minecraft.world.item.ItemStack;
import org.spongepowered.asm.mixin.injection.Inject;
import org.spongepowered.asm.mixin.injection.Redirect;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfo;
@Mixin(GameRenderer.class) class RenderMixin {
@Shadow private Camera camera;
@Inject(method="displayItemActivation",at=@At("HEAD"),cancellable=true)
private void activate(ItemStack item,CallbackInfo ci) { if(Options.hide(item)) ci.cancel(); }
@Redirect(method={"renderLevel(Lnet/minecraft/client/DeltaTracker;)V"},at=@At(value="INVOKE",target="Lnet/minecraft/util/Mth;lerp(FFF)F",ordinal=0))
private float nausea(float tick,float first,float last) { if(Options.hidden()) return 0; return Mth.lerp(tick,first,last); }
}
'''
LEVEL='''package fixture;
import net.minecraft.client.renderer.LevelRenderer;
@Mixin(LevelRenderer.class) class WorldMixin {
@Inject(method="render(Lcom/mojang/blaze3d/resource/GraphicsResourceAllocator;Lnet/minecraft/client/DeltaTracker;ZLnet/minecraft/client/renderer/state/level/CameraRenderState;Lorg/joml/Matrix4fc;Lcom/mojang/blaze3d/buffers/GpuBufferSlice;Lorg/joml/Vector4f;Z)V",at=@At("TAIL"))
private void render(GraphicsResourceAllocator allocator,DeltaTracker ticks,boolean outline,CameraRenderState camera,Matrix4fc view,GpuBufferSlice fog,Vector4f color,boolean sky,CallbackInfo ci) { Renderer.render(ticks,camera); }
}
'''

def overlay_tests():
    water = '''import net.minecraft.client.renderer.ScreenEffectRenderer;
import net.minecraft.client.Minecraft;
@Mixin(ScreenEffectRenderer.class) class Overlay {
@Inject(method="submitWater",at=@At("HEAD"),cancellable=true)
private static void water(Minecraft client, PoseStack poses, SubmitNodeCollector nodes, CallbackInfo ci) { if(Config.noWater()) ci.cancel(); }
@Inject(method="submitFire",at=@At("HEAD"),cancellable=true)
private static void fire(PoseStack poses, SubmitNodeCollector nodes, TextureAtlasSprite sprite, CallbackInfo ci) { if(Config.noFire()) ci.cancel(); }
}'''
    with tempfile.TemporaryDirectory() as raw:
        root=Path(raw); path=root/'Overlay.java';path.write_text(water)
        rows=rewrite_runtime_mixins(root);assert len(rows)==1 and rows[0]['rule']=='minecraft-26.3-water-overlay-render-state'
        expected=water.replace('Minecraft client','net.minecraft.client.renderer.state.level.PlayerRenderState.WaterOverlay client')
        # Only parameter type/spacing changes; staticness, fire, cancellation and body survive.
        assert path.read_text()==expected
        assert not rewrite_runtime_mixins(root)
        for negative in [water.replace('net.minecraft.client.Minecraft','foreign.Minecraft'),
                         water.replace('net.minecraft.client.renderer.ScreenEffectRenderer','foreign.ScreenEffectRenderer'),
                         '/* '+water+' */']:
            path.write_text(negative);assert not rewrite_runtime_mixins(root);assert path.read_text()==negative
        path.write_text(water.replace('if(Config.noWater())','if(client.isPaused())'))
        try:rewrite_runtime_mixins(root)
        except ConversionBlock:pass
        else:raise AssertionError('consumed old overlay state was dropped')
        assert 'Minecraft client' in path.read_text()
        path.write_text(water.replace('method="submitWater"','locals=LocalCapture.CAPTURE_FAILHARD,method="submitWater"'))
        try:rewrite_runtime_mixins(root)
        except ConversionBlock:pass
        else:raise AssertionError('overlay local capture was discarded')
    print('Water overlay exact owner/type, static handler, body/cancellation/fire preservation and unsafe-state controls PASS')


def main():
    overlay_tests()
    with tempfile.TemporaryDirectory(prefix='runtime-mixin-regression-') as raw:
        root=Path(raw);(root/'MouseMixin.java').write_text(MOUSE)
        (root/'RenderMixin.java').write_text(RENDER);(root/'WorldMixin.java').write_text(LEVEL)
        config=root/'test.mixins.json';config.write_text(json.dumps({'package':'fixture','client':['MouseMixin','RenderMixin','WorldMixin']}))
        rows=rewrite_runtime_mixins(root);assert len(rows)==4
        mouse=(root/'MouseMixin.java').read_text()
        assert 'onMove(JDDDD)V' in mouse and 'double northpointDX, double northpointDY' in mouse
        assert '{ events.fire(x,y); if(cancelled) ci.cancel(); }' in mouse
        generated=(root/'RenderMixinNorthpointItemActivation.java').read_text()
        assert '@Mixin(net.minecraft.client.player.LocalPlayer.class)' in generated
        assert '{ if(Options.hide(item)) ci.cancel(); }' in generated
        assert json.loads(config.read_text())['client']==['MouseMixin','RenderMixin','WorldMixin','RenderMixinNorthpointItemActivation']
        render=(root/'RenderMixin.java').read_text()
        assert 'nauseaEffectIntensity:F' in render and 'value="FIELD"' in render
        assert 'if(Options.hidden()) return 0; return northpointPlayerState.nauseaEffectIntensity;' in render
        level=(root/'WorldMixin.java').read_text()
        assert 'getDeltaTracker()' in level and 'Renderer.render(ticks,camera)' in level
        assert 'Lcom/mojang/renderpearl/api/buffers/GpuBufferSlice;' in level
        assert not rewrite_runtime_mixins(root),'migration is not idempotent'
        (root/'MouseMixin.java').write_text(MOUSE.replace('events.fire(x,y)', 'events.fire(x - this.xpos,y - this.ypos)'))
        assert len(rewrite_runtime_mixins(root)) == 1
        updated=(root/'MouseMixin.java').read_text()
        assert 'isMouseGrabbed() ? northpointDX : x - this.xpos' in updated
        assert 'isMouseGrabbed() ? northpointDY : y - this.ypos' in updated
        (root/'Foreign.java').write_text(MOUSE.replace('net.minecraft.client.MouseHandler','unrelated.MouseHandler'))
        (root/'Comment.java').write_text('/* '+MOUSE+' */')
        assert not rewrite_runtime_mixins(root),'rewrote a comment or unrelated owner'
        bad=root/'Bad.java'
        for text in [MOUSE.replace('method={','locals=LocalCapture.CAPTURE_FAILHARD, method={'),
                     LEVEL.replace('Renderer.render(ticks,camera)','Renderer.render(ticks,view)'),
                     RENDER.replace('Options.hide(item)','camera.hidden()')]:
            bad.write_text(text)
            try:rewrite_runtime_mixins(root)
            except ConversionBlock:pass
            else:raise AssertionError('unsafe owner/local/render payload was silently changed')
            bad.unlink()
        (root/'RenderMixin.java').write_text(RENDER)
        config.write_text(json.dumps({'package':'other','client':['Unrelated']}))
        try:rewrite_runtime_mixins(root)
        except ConversionBlock:pass
        else:raise AssertionError('unregistered generated Mixin was accepted')
    print('Runtime input/render migrations: four positive cases, owner/body/config preservation, idempotence and negative controls PASS')
    return 0
if __name__=='__main__':raise SystemExit(main())
