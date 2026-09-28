# ItemsAdder / Oraxen / Nexo custom-content semantics

Research snapshot: **2026-09-06**. These ecosystems change with Minecraft resource-pack and DataComponent formats; re-check current docs for the exact source server version before generating target code.

## Why this matters

A generated resource pack proves what the client renders. The plugin config often owns everything else: item identity, components, furniture placement, seat offsets, collision, storage, drops, interaction actions, sounds, cooldowns, connection variants, and version-specific item-model selection. Preserve both.

Run `scripts/content_plugin_ir.py` on authorized config roots/bundles before writing mod registries.

## Nexo

Nexo is a file-configured custom content system for items, blocks, armor, and furniture with resource-pack generation.

Important source concepts:

- `Pack` and/or `ItemModel` determine rendered item model/texture behavior.
- Minecraft 1.21.4+ ItemModels are a distinct layer from model JSON and texture files. Nexo exposes model-tree types such as Reference/Model, Select, Condition, RangeDispatch, Composite, Empty, and Special. Preserve that decision tree; do not collapse it into one model.
- `Components` maps modern Minecraft item DataComponents such as consumable/tool/equippable/glider/item-model/custom-model-data/repair/death-protection/etc. These are version-sensitive and must be translated against the target Minecraft version rather than copied blindly.
- Furniture can include seat offsets, barrier or interaction hitboxes, shulker/ghast collision strategies on supported versions, storage, waterlogging, block-locker/protection integration, custom drops, block sounds, and connectable-furniture visual states.
- Connectable furniture has semantic variants such as DEFAULT, LEFT, RIGHT, STRAIGHT, INNER, OUTER. Keep the connection-state machine even when backporting its resource-pack representation.
- Nexo custom item mechanics can model Event -> Conditions -> Actions. Translate that to explicit mod events/predicates/actions, not command strings when a native equivalent is available.

Current public docs:
- `https://docs.nexomc.com/configuration/items-advanced/itemmodel-builder`
- `https://docs.nexomc.com/configuration/items-advanced/components`
- `https://docs.nexomc.com/mechanics/furniture-mechanic`
- `https://docs.nexomc.com/mechanics/custom-mechanic`

## Oraxen

Oraxen combines generated/custom resource-pack assets with item/block/furniture mechanics.

Important source concepts:

- item ID / material / generated-or-supplied model and texture identity;
- custom block/furniture placement and break/interact event identity;
- storage contents/persistence for storage-enabled furniture/blocks;
- `clickActions` with condition expressions and console/player/message/actionbar/sound actions;
- optional integrations such as Skript/MMOItems can add behavior not visible in the Oraxen item file itself. Detect references and flag external behavior dependencies instead of assuming the Oraxen config is complete.

For a native mod, prefer typed event handlers and capability/state over invoking text commands to emulate Oraxen actions when a direct implementation exists.

Current public docs:
- `https://docs.oraxen.com/creating-content/items/abilities/clickaction`
- `https://docs.oraxen.com/developers/api`
- `https://docs.oraxen.com/compatibility/skript`

## ItemsAdder

ItemsAdder uses namespaced content configs plus generated/supplied resource-pack assets. Preserve the `info.namespace` identity because it often scopes item IDs and pack paths.

Important source concepts include:

- `items` definitions with display name/permission/material/resource data;
- `resource.generate` and `resource.model_path` / textures;
- item events and event cooldown settings;
- behaviors/mechanics for content families;
- animated Java item models may be implemented as multiple model/texture animation resources, so inspect generated model closure and `.mcmeta` rather than expecting a skeletal animation track;
- external integrations (Citizens/custom entity systems/etc.) can drive animation/model state outside the item config.

Current public docs:
- `https://itemsadder.devs.beer/`

## Normalized conversion fields

Regardless of source plugin, normalize each item/content entry to:

```text
source_plugin
namespace + item_id
material/base vanilla identity
name/lore/permission
pack model/texture/item-model references
modern item components
mechanics/behaviours/events
furniture:
  seats
  hitboxes/collision type
  storage
  drops
  sounds
  connection variants
  click/action graph
external integration references
unclassified source keys
```

Keep the original raw config alongside the IR. Unknown keys are not junk: they are evidence that the adapter may need another semantic handler.

## Mod translation priorities

1. Register stable native IDs first; keep source IDs as migration aliases/provenance where useful.
2. Recreate item DataComponents/attributes/tool/food/equipment semantics in the target version.
3. Recreate static models and texture closure.
4. Translate ItemModel/CMD condition trees into the target version's renderer/model system without dropping branches.
5. For furniture choose block, block entity, decorative entity, or multipart entity based on persistence/interaction/collision/state—not solely on how the server plugin rendered it.
6. Convert seats to passenger anchors; collision definitions to voxel/multipart/entity shapes; storage to persistent inventories; drops to loot logic; sounds to registered sound events; connection states to block/entity state.
7. Translate conditions/actions/event hooks to native code and test authority/synchronization.
8. Preserve unsupported integrations as explicit blockers/dependencies until their source is ingested.
