#!/usr/bin/env python3
"""Regression for the observed Mixin PREPARE subtype crash, plus API parity."""
from pathlib import Path
import subprocess
import tempfile
from northpoint_target_26_3 import rewrite_mouse_invokers, ConversionBlock


def main():
    source = 'import net.minecraft.client.MouseHandler; @Mixin(MouseHandler.class) public interface Bridge { @Invoker("onMove") void move(long window, double x, double y); }'
    with tempfile.TemporaryDirectory() as td:
        root = Path(td); path = root / 'Bridge.java'; path.write_text(source)
        changes = rewrite_mouse_invokers(root)
        assert changes[0]['count'] == 1
        helper_path = root / changes[0]['generated_path']
        helper = helper_path.read_text()
        assert 'default void move(long window, double x, double y)' in helper
        assert 'x - northpointMouse.xpos(), y - northpointMouse.ypos()' in helper
        assert 'default ' not in path.read_text(), 'default method changes accessor subtype to invalid interface Mixin'
        assert '@org.spongepowered.asm.mixin.gen.Invoker("onMove")' in path.read_text()
        assert 'extends northpoint.generated.mouse.' in path.read_text()
        assert not rewrite_mouse_invokers(root)
        # Exercise retained default API with a real Java compiler and VM. This
        # fixture is not a substitute for the independent native Minecraft gate.
        stub = root / 'net/minecraft/client/MouseHandler.java'; stub.parent.mkdir(parents=True)
        stub.write_text('package net.minecraft.client; public class MouseHandler { public double xpos(){return 4;} public double ypos(){return 8;} }')
        annotations = root / 'Annotations.java'
        annotations.write_text('@interface Mixin {Class<?> value();} @interface Invoker {String value();}')
        invoker = root / 'org/spongepowered/asm/mixin/gen/Invoker.java'; invoker.parent.mkdir(parents=True)
        invoker.write_text('package org.spongepowered.asm.mixin.gen; public @interface Invoker {String value();}')
        raw_name = helper.split('void ')[1].split('(')[0]
        (root / 'Proof.java').write_text('public class Proof extends net.minecraft.client.MouseHandler implements Bridge { public void ' + raw_name + '(long w,double x,double y,double dx,double dy){ if(w!=7 || x!=14 || y!=5 || dx!=10 || dy!=-3) throw new AssertionError(); } public static void main(String[] args){Bridge bridge=new Proof(); bridge.move(7,14,5); System.out.println("API_PARITY_PASS");} }')
        subprocess.run(['javac', '-d', str(root / 'classes'), *map(str, root.rglob('*.java'))], check=True, capture_output=True)
        cp = subprocess.run(['java', '-cp', str(root / 'classes'), 'Proof'], check=True, capture_output=True, text=True)
        assert 'API_PARITY_PASS' in cp.stdout
        for unchanged in [source.replace('net.minecraft.client.MouseHandler', 'foreign.MouseHandler'), '/* ' + source + ' */']:
            path.write_text(unchanged); assert not rewrite_mouse_invokers(root); assert path.read_text() == unchanged
        path.write_text(source.replace('double x', 'double northpointMouse'))
        try: rewrite_mouse_invokers(root)
        except ConversionBlock: pass
        else: raise AssertionError('unsafe local collision')
        path.write_text(source.replace('interface Bridge {', 'interface Bridge extends Other {'))
        rewrite_mouse_invokers(root)
        assert 'extends Other , northpoint.generated.mouse.' in path.read_text()
        path.write_text(source)
        helper_path.write_text('user owned source')
        try: rewrite_mouse_invokers(root)
        except ConversionBlock: pass
        else: raise AssertionError('overwrote pre-existing helper')
        assert path.read_text() == source
    print('Mouse invoker bridge: accessor-only subtype, retained API JVM proof, inheritance, idempotence, scope and collision controls PASS')
    return 0

if __name__ == '__main__': raise SystemExit(main())
