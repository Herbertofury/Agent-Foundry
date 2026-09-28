#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_REGISTRY = ROOT / "assets/memory/FEATURE-FOUNDRY-LIVING-ECOLOGY.seed.json"
DEFAULT_OUTPUT = ROOT / "references/FEATURE-FOUNDRY-LIVING-ECOLOGY.md"


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def is_https(value: str) -> bool:
    try:
        parsed = urlparse(value)
        return parsed.scheme == "https" and bool(parsed.netloc)
    except Exception:
        return False


def validate(data: dict) -> list[str]:
    errors: list[str] = []
    if data.get("schema_version") != 1:
        errors.append("living ecology schema_version must be 1")
    if data.get("project_id") != "feature-foundry":
        errors.append("living ecology project_id must be feature-foundry")

    required_sections = (
        "northpoint",
        "intent_aware_anticipation",
        "ecology_director",
        "transition_depth_ladder",
        "transition_selection",
        "persistent_world_memory",
        "semantic_material_intelligence",
        "spatial_micro_audio",
        "relationship_and_social_physics",
        "theme_native_ai_presence",
        "environmental_data_embodiment",
        "living_time_and_microclimates",
        "causal_undo_replay_and_inspection",
        "object_behavior_genome",
        "ecology_authoring_studio",
        "cross_device_embodiment",
        "performance_capability_ladder",
        "acceptance_tests",
        "official_sources",
    )
    for section in required_sections:
        if not data.get(section):
            errors.append(f"missing required section: {section}")

    northpoint = data.get("northpoint") or {}
    for field in ("id", "title", "statement", "non_negotiables"):
        if not northpoint.get(field):
            errors.append(f"northpoint missing {field}")

    anticipation = data.get("intent_aware_anticipation") or {}
    if len(anticipation.get("signals") or []) < 7:
        errors.append("intent-aware anticipation requires at least seven signal families")
    bands = anticipation.get("confidence_bands") or []
    if [band.get("id") for band in bands] != ["observe", "hint", "prepare", "strong-prepare"]:
        errors.append("anticipation confidence bands must be observe, hint, prepare, strong-prepare")

    director = data.get("ecology_director") or {}
    if len(director.get("world_modes") or []) < 6:
        errors.append("ecology director requires at least six world modes")
    if len(director.get("decision_order") or []) < 8:
        errors.append("ecology director decision order is incomplete")
    budgets = director.get("budgets") or {}
    for budget in ("motion", "brightness", "particles", "audio", "physics", "causal_depth"):
        if not budgets.get(budget):
            errors.append(f"ecology director missing {budget} budget")

    levels = data.get("transition_depth_ladder") or []
    if [item.get("level") for item in levels] != list(range(6)):
        errors.append("transition depth ladder must contain ordered levels 0 through 5")
    if any(item.get("interruptible") is not True for item in levels):
        errors.append("every transition depth level must be interruptible")
    if len({item.get("id") for item in levels}) != len(levels):
        errors.append("duplicate transition depth IDs")

    memory = data.get("persistent_world_memory") or {}
    channel_ids = [item.get("id") for item in memory.get("channels") or []]
    expected_channels = ["chronological-patina", "interaction-patina", "authored-memory"]
    if channel_ids != expected_channels:
        errors.append("world memory channels must separate chronological, interaction and authored memory")

    genome = data.get("object_behavior_genome") or {}
    if len(genome.get("fields") or []) < 14:
        errors.append("object behavior genome is not sufficiently developed")

    studio = data.get("ecology_authoring_studio") or {}
    families = studio.get("tool_families") or []
    if len(families) < 10:
        errors.append("ecology authoring studio requires at least ten tool families")
    if len({item.get("id") for item in families}) != len(families):
        errors.append("duplicate ecology authoring tool-family IDs")

    ladder = data.get("performance_capability_ladder") or {}
    tiers = ladder.get("tiers") or []
    expected_tiers = ["efficient", "balanced", "high", "ultra", "cinematic-lab"]
    if [item.get("id") for item in tiers] != expected_tiers:
        errors.append("performance tiers must be efficient, balanced, high, ultra, cinematic-lab")
    guardrail_corpus = " ".join(ladder.get("hard_guardrails") or []).lower()
    for phrase in ("viewport culling", "quantity caps", "remove features", "task-result correctness", "all objects remain selectable"):
        if phrase not in guardrail_corpus:
            errors.append(f"performance ladder missing guardrail concept: {phrase}")

    tests = data.get("acceptance_tests") or []
    if len(tests) < 18:
        errors.append("living ecology requires at least eighteen acceptance tests")
    test_ids = [item.get("id") for item in tests]
    if len(test_ids) != len(set(test_ids)):
        errors.append("duplicate living ecology acceptance-test IDs")
    for test in tests:
        if not test.get("id") or len(str(test.get("test", ""))) < 24:
            errors.append(f"weak acceptance test: {test.get('id', '?')}")

    sources = data.get("official_sources") or []
    if len(sources) < 8:
        errors.append("living ecology requires at least eight official sources")
    source_ids = []
    for source in sources:
        source_ids.append(source.get("id"))
        if not is_https(str(source.get("url", ""))):
            errors.append(f"source {source.get('id', '?')} must use an HTTPS URL")
        if not source.get("applies_to"):
            errors.append(f"source {source.get('id', '?')} missing applies_to")
    if len(source_ids) != len(set(source_ids)):
        errors.append("duplicate living ecology source IDs")

    corpus = json.dumps(data, ensure_ascii=False).lower().replace("_", " ").replace("-", " ")
    required_concepts = (
        "intent aware",
        "predicted pointer",
        "grass waves",
        "full world traversal",
        "spatial micro",
        "relationship",
        "theme native ai",
        "environmental data",
        "microclimate",
        "causal undo",
        "behavior genome",
        "authoring capability must continuously expand",
        "cross device",
        "webgpu",
        "potato",
        "chronological patina",
        "interaction patina",
        "user input always wins",
    )
    for phrase in required_concepts:
        if phrase not in corpus:
            errors.append(f"living ecology missing required concept: {phrase}")
    return errors


def bullets(items: list[str]) -> list[str]:
    return [f"- {item}" for item in items]


def render(data: dict) -> str:
    out: list[str] = [
        "# Feature Foundry Living UI Ecology",
        "",
        f"**Registry version:** {data.get('registry_version', '')}",
        f"**Verified:** {data.get('verified_at_utc', '')}",
        f"**Review due:** {data.get('review_due', '')}",
        "",
        "This document is generated from the machine-readable living-ecology registry. It is a product contract and authoring specification, not a claim that the current application already implements every behavior.",
        "",
        "## Northpoint",
        "",
        f"### {data['northpoint']['title']}",
        data["northpoint"]["statement"],
        "",
        "#### Non-negotiables",
        "",
        *bullets(data["northpoint"]["non_negotiables"]),
        "",
        "## Intent-aware anticipation",
        "",
        data["intent_aware_anticipation"]["purpose"],
        "",
        "### Signals",
        "",
        *bullets(data["intent_aware_anticipation"]["signals"]),
        "",
        "### Confidence bands",
        "",
        "| Band | Range | Allowed behavior |",
        "|---|---|---|",
    ]
    for band in data["intent_aware_anticipation"]["confidence_bands"]:
        out.append(f"| `{band['id']}` | {band['range']} | {band['behavior']} |")
    out += ["", "### Anticipation rules", "", *bullets(data["intent_aware_anticipation"]["rules"])]

    director = data["ecology_director"]
    out += [
        "",
        "## Ecology Director",
        "",
        director["purpose"],
        "",
        "### World modes",
        "",
        *bullets(director["world_modes"]),
        "",
        "### Authoritative decision order",
        "",
    ]
    for index, item in enumerate(director["decision_order"], 1):
        out.append(f"{index}. {item}")
    out += ["", "### Sensory and simulation budgets", ""]
    for name, value in director["budgets"].items():
        out.append(f"- **{name.replace('_', ' ').title()}:** {value}")

    out += [
        "",
        "## Transition depth ladder",
        "",
        "| Level | Mode | Purpose | Representative use |",
        "|---:|---|---|---|",
    ]
    for level in data["transition_depth_ladder"]:
        out.append(f"| {level['level']} | **{level['title']}** | {level['description']} | {level['example']} |")
    out += ["", "### Transition selection and adaptation", "", *bullets(data["transition_selection"]["controls"]), "", *bullets(data["transition_selection"]["adaptive_rules"])]

    out += ["", "## Persistent world and material memory", ""]
    for channel in data["persistent_world_memory"]["channels"]:
        out += [f"### {channel['title']}", f"**Source:** {channel['source']}", "", *bullets(channel["examples"]), ""]
    out += ["### Memory controls", "", *bullets(data["persistent_world_memory"]["controls"]), "", "### Memory guardrails", "", *bullets(data["persistent_world_memory"]["guardrails"])]

    out += ["", "## Semantic material intelligence", "", "### Material properties", "", *bullets(data["semantic_material_intelligence"]["properties"]), "", "### Material rules", "", *bullets(data["semantic_material_intelligence"]["rules"])]

    audio = data["spatial_micro_audio"]
    out += ["", "## Spatial micro-audio", "", audio["purpose"], "", "### Features", "", *bullets(audio["features"]), "", "### Guardrails", "", *bullets(audio["guardrails"])]

    relationships = data["relationship_and_social_physics"]
    out += ["", "## Object relationships and social physics", "", "### Relationship edge types", "", *bullets(relationships["edge_types"]), "", "### Authoring", "", *bullets(relationships["authoring"]), "", "### Guardrails", "", *bullets(relationships["guardrails"])]

    ai = data["theme_native_ai_presence"]
    out += ["", "## Theme-native AI presence", "", ai["purpose"], "", "### Embodiments", "", *bullets(ai["embodiments"]), "", "### Truthfulness", "", *bullets(ai["truthfulness"])]

    embodiment = data["environmental_data_embodiment"]
    out += ["", "## Environmental data embodiment", "", "### Examples", "", *bullets(embodiment["examples"]), "", "### Rules", "", *bullets(embodiment["rules"])]

    climate = data["living_time_and_microclimates"]
    out += ["", "## Living time and microclimates", "", "### Systems", "", *bullets(climate["systems"]), "", "### Controls", "", *bullets(climate["controls"]), "", "### Guardrails", "", *bullets(climate["guardrails"])]

    undo = data["causal_undo_replay_and_inspection"]
    out += ["", "## Causal undo, replay, and inspection", "", "### Architecture", "", *bullets(undo["architecture"]), "", "### Tools", "", *bullets(undo["tools"]), "", "### Guardrails", "", *bullets(undo["guardrails"])]

    genome = data["object_behavior_genome"]
    out += ["", "## Object behavior genome", "", "### Fields", "", *bullets(genome["fields"]), "", "### Generation rules", "", *bullets(genome["generation_rules"])]

    studio = data["ecology_authoring_studio"]
    out += ["", "## Ecology Authoring Studio", "", studio["northpoint"], ""]
    for family in studio["tool_families"]:
        out += [f"### {family['id'].replace('-', ' ').title()}", "", *bullets(family["tools"]), ""]
    out += ["### AI-assisted authoring", "", *bullets(studio["ai_assistance"])]

    device = data["cross_device_embodiment"]
    out += ["", "## Cross-device embodiment", "", "### Capabilities", "", *bullets(device["capabilities"]), "", "### Rules", "", *bullets(device["rules"])]

    perf = data["performance_capability_ladder"]
    out += ["", "## Performance capability ladder", "", perf["selection"], "", "| Tier | Target | Behavior | GPU path |", "|---|---|---|---|"]
    for tier in perf["tiers"]:
        out.append(f"| **{tier['display_name']}** | {tier['target']} | {tier['behavior']} | {tier['gpu']} |")
    out += ["", "### Adaptive controller", "", *bullets(perf["adaptive_controller"]), "", "### Implementation patterns", "", *bullets(perf["implementation_patterns"]), "", "### Hard performance guardrails", "", *bullets(perf["hard_guardrails"])]

    out += ["", "## Acceptance tests", ""]
    for item in data["acceptance_tests"]:
        out.append(f"- **`{item['id']}`:** {item['test']}")

    out += ["", "## Official technical sources", ""]
    for source in data["official_sources"]:
        out.append(f"- **{source['id']}** — {source['url']} — {', '.join(source['applies_to'])}")
    return "\n".join(out) + "\n"


def command_validate(args: argparse.Namespace) -> int:
    data = load(args.registry)
    errors = validate(data)
    if errors:
        print("\n".join(errors))
        return 1
    print(
        "Living ecology valid: "
        f"{len(data['transition_depth_ladder'])} transition levels, "
        f"{len(data['ecology_authoring_studio']['tool_families'])} authoring tool families, "
        f"{len(data['performance_capability_ladder']['tiers'])} performance tiers, "
        f"{len(data['acceptance_tests'])} acceptance tests"
    )
    return 0


def command_render(args: argparse.Namespace) -> int:
    data = load(args.registry)
    errors = validate(data)
    if errors:
        print("\n".join(errors))
        return 1
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(render(data), encoding="utf-8")
    print(args.output)
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    for name, fn in (("validate", command_validate), ("render", command_render)):
        command = sub.add_parser(name)
        command.add_argument("--registry", type=Path, default=DEFAULT_REGISTRY)
        if name == "render":
            command.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
        command.set_defaults(fn=fn)
    args = parser.parse_args()
    return args.fn(args)


if __name__ == "__main__":
    raise SystemExit(main())
