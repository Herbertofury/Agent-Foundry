#!/usr/bin/env python3
"""Linked shader preservation and negative controls; native Shaderc is separate."""
from pathlib import Path
import tempfile
from northpoint_shader_rules import rewrite_shader_interfaces, ConversionBlock

JAVA='''import net.minecraft.resources.Identifier;
import com.mojang.blaze3d.vertex.DefaultVertexFormat;
class Pipelines {
 private static Identifier shader(String name) { return Identifier.fromNamespaceAndPath("example", "effect_" + name); }
 private static RenderPipeline pipeline(String id) { return RenderPipelines.register(RenderPipeline.builder().withVertexShader(shader("")).withFragmentShader(shader(id)).withVertexBinding(0, DefaultVertexFormat.POSITION_TEX).build()); }
}'''
VERT='''#version 330
in vec3 Position;
in vec2 UV0;
out vec2 uv;
void main() { gl_Position=vec4(Position,1);uv=UV0; }
'''
FRAG='''#version 330
in vec2 uv;
out vec4 color;
void main() { color=vec4(uv,0,1); }
'''

def uniform_layout_tests():
 import struct
 from northpoint_shader_rules import rewrite_dynamic_transforms
 block = """layout(std140) uniform DynamicTransforms {
    mat4 ModelViewMat; // original transform
    vec4 ColorModulator;
    vec3 ModelOffset;
    mat4 TextureMat;
};
"""
 expected = [('mat4', 'ModelViewMat'), ('mat4', 'TextureMat'), ('vec4', 'ColorModulator'), ('vec3', 'ModelOffset')]
 import re
 changed = rewrite_dynamic_transforms(block, Path('inline.fsh'))
 assert re.findall(r'(mat4|vec[34])\s+(\w+)\s*;', changed) == expected
 assert '// original transform' in changed
 assert rewrite_dynamic_transforms(changed, Path('inline.fsh')) == changed
 identity = [1.0 if i % 5 == 0 else 0.0 for i in range(16)]
 gpu = struct.pack('<40f', *(identity + identity + [1.0]*4 + [0.0]*4))
 assert struct.unpack_from('<4f', gpu, 64)[3] == 0.0, 'original invisible-alpha reproducer changed'
 assert struct.unpack_from('<4f', gpu, 128) == (1.0, 1.0, 1.0, 1.0)
 with tempfile.TemporaryDirectory() as td:
  root=Path(td); (root/'Pipelines.java').write_text(JAVA.replace('.withVertexBinding', '.withUniform("DynamicTransforms", UniformType.UNIFORM_BUFFER).withVertexBinding'))
  shaders=root/'src/main/resources/assets/example/shaders';shaders.mkdir(parents=True)
  vertex=shaders/'effect_.vsh'; fragment=shaders/'effect_gradient.fsh'
  vertex.write_text(VERT.replace('in vec3 Position;',block+'in vec3 Position;'))
  fragment.write_text(FRAG.replace('in vec2 uv;',block+'in vec2 uv;'))
  rows=rewrite_shader_interfaces(root)
  assert sum(r['rule']=='minecraft-26.3-dynamic-transform-uniform-layout' for r in rows)==2
  assert VERT[VERT.index('void main'):]==vertex.read_text()[vertex.read_text().index('void main'):]
  assert FRAG[FRAG.index('void main'):]==fragment.read_text()[fragment.read_text().index('void main'):]
  assert not rewrite_shader_interfaces(root)
  for invalid in [block.replace('mat4 TextureMat;', 'mat4 TextureMat; float Extra;'), block.replace('vec3 ModelOffset;', 'vec4 ModelOffset;'),block.replace('std140','std430')]:
   oldvert=VERT.replace('in vec3 Position;',block+'in vec3 Position;')
   oldfrag=FRAG.replace('in vec2 uv;',invalid+'in vec2 uv;')
   vertex.write_text(oldvert);fragment.write_text(oldfrag)
   try:rewrite_shader_interfaces(root)
   except ConversionBlock:pass
   else:raise AssertionError('unknown uniform payload accepted')
   assert vertex.read_text()==oldvert and fragment.read_text()==oldfrag
  foreign=block.replace('DynamicTransforms','PrivateTransforms')
  assert rewrite_dynamic_transforms(foreign,Path('private.fsh'))==foreign
 print('Uniform ABI: transparent-alpha reproducer, complete field order, math/comment retention, atomic negatives and idempotence PASS')


def main():
 uniform_layout_tests()
 with tempfile.TemporaryDirectory() as td:
  root=Path(td);(root/'Pipelines.java').write_text(JAVA)
  shaders=root/'src/main/resources/assets/example/shaders';shaders.mkdir(parents=True)
  vertex=shaders/'effect_.vsh';fragment=shaders/'effect_gradient.fsh'
  vertex.write_text(VERT);fragment.write_text(FRAG)
  untouched=shaders/'other.fsh';untouched.write_text(FRAG)
  changes=rewrite_shader_interfaces(root);assert len(changes)==2
  assert 'layout(location = 0) in vec3 Position;' in vertex.read_text()
  assert 'layout(location = 1) in vec2 UV0;' in vertex.read_text()
  assert 'layout(location = 0) out vec2 uv;' in vertex.read_text()
  assert 'layout(location = 0) in vec2 uv;' in fragment.read_text()
  assert 'layout(location = 0) out vec4 color;' in fragment.read_text()
  assert '#extension GL_ARB_separate_shader_objects : require' in vertex.read_text()
  assert VERT[VERT.index('void main'):]==vertex.read_text()[vertex.read_text().index('void main'):]
  assert FRAG[FRAG.index('void main'):]==fragment.read_text()[fragment.read_text().index('void main'):]
  assert untouched.read_text()==FRAG
  assert not rewrite_shader_interfaces(root)
  for invalid in [FRAG.replace('vec2 uv','vec3 uv'),FRAG.replace('in vec2','layout(location=7) in vec2'),FRAG.replace('in vec2 uv;','in vec2 uv[2];'),FRAG.replace('in vec2 uv;','#if CONDITIONAL\nin vec2 uv;\n#endif')]:
   vertex.write_text(VERT);fragment.write_text(invalid)
   try:rewrite_shader_interfaces(root)
   except ConversionBlock:pass
   else:raise AssertionError('unsafe linked shader was changed')
   assert vertex.read_text()==VERT and fragment.read_text()==invalid
  fragment.write_text(FRAG)
  (root/'Pipelines.java').write_text(JAVA.replace('com.mojang.blaze3d.vertex.DefaultVertexFormat','foreign.DefaultVertexFormat'))
  assert not rewrite_shader_interfaces(root)
 print('Shader linkage, explicit locations, extension, body preservation, atomic negatives, foreign owner and idempotence PASS')
 return 0

if __name__=='__main__':raise SystemExit(main())
