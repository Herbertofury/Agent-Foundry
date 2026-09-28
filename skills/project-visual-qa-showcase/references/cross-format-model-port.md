# Cross-format model and animation port method

A visual format conversion should be treated as a transform-composition problem, not an eyeballing exercise.

## 1. Write down both coordinate systems

Determine, from authoritative source code/specification when possible:

- axis orientation and handedness
- origin/pivot conventions
- whether positions are local or absolute
- rotation units and Euler order
- cube-origin convention
- texture UV convention and mirror semantics
- whether target runtime uses Y-up or Y-down model coordinates

## 2. Compose the transforms

If a known editor/importer converts Source -> Internal and a known exporter converts Internal -> Target, compose both mappings. A sign flip in the importer may be cancelled by the exporter. Never carry one half of the conversion into custom code and assume it is the final mapping.

Do this independently for:

- bind-pose pivot/offset
- bind-pose rotation
- cube origin
- animated translation
- animated rotation
- animated scale

## 3. Preserve hierarchy before animation

Build the exact parent tree and bind pose first. Render static multi-angle views. Only after the static model matches should animation be added. This isolates hierarchy/pivot errors from animation errors.

## 4. Port animation channel semantics

For every animated bone, record:

- source channel name
- target part name
- source interpolation
- source expression/keyframes
- conversion applied
- whether target animation is additive or replacing bind pose

For expression-driven channels, translate the expression itself. Do not replace a meaningful authored expression with a generic approximation unless the user accepts approximation.

## 5. Audit numerically and visually

Create an automated equivalence audit that can compare the source and generated target representation. Then create multi-angle/checkpoint renders that make visual errors obvious. Numerical audit catches hidden data regressions; render QA catches incorrect assumptions in the audit itself.

## 6. Preserve semantics over source-format adapters

A source model/config may exist only to compensate for limitations of the original format. If it represents a standard target primitive, preserve the authored visual/behavioral result rather than blindly copying the adapter. For reskinned vanilla content, use the target version's vanilla model/behavior as an oracle and deterministically map the source art onto it. Keep the original adapter in the provenance mirror for auditability.

## 7. Repair the cause, not the symptom

A protruding cube, tail, ear, or limb often means:

- wrong rotation sign
- double conversion
- local/absolute pivot confusion
- reset/additive animation mistake
- wrong parent
- mirror/inflate mishandling

Do not delete or hide the part unless the source proves it should not exist.
