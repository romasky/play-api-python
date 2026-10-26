"""Offline step-coverage check — run BEFORE hitting the live API.

`pytest --co` collects scenarios but pytest-bdd 8 resolves step definitions only at *runtime*,
so an undefined or ambiguous step surfaces one scenario at a time, after real HTTP calls.
This script renders every scenario (outline rows included) and matches each step against the
registered definitions, honouring pytest-bdd's keyword typing (`@step` matches any keyword).
Definitions no feature uses are listed as UNUSED (informational — dead-code candidates). A feature file
without an `@allure.label.epic:` tag is fatal: the CI matrix selects by epic, so it would never run.

    uv run python tools/check_steps.py            # exit 1 on a missing / ambiguous step or an epic-less feature
"""

from __future__ import annotations

import glob
import importlib
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path[:0] = [str(ROOT / "src"), str(ROOT)]

from pytest_bdd.parser import FeatureParser  # noqa: E402
from tests.conftest import pytest_plugins  # noqa: E402  # the authoritative list of step modules


def load_step_definitions():
    defs = []
    for module_name in pytest_plugins:
        module = importlib.import_module(module_name)
        for attr in dir(module):
            context = getattr(getattr(module, attr), "_pytest_bdd_step_context", None)
            if context is not None:
                defs.append((f"{module_name}.{attr}", context))
    return defs


def main() -> int:
    defs = load_step_definitions()
    missing: list[str] = []
    ambiguous: dict[str, list[str]] = {}
    used: set[str] = set()
    scenarios = steps = 0

    no_epic: list[str] = []
    for feature_file in sorted(glob.glob(str(ROOT / "features" / "**" / "*.feature"), recursive=True)):
        feature = FeatureParser(str(ROOT), feature_file).parse()
        if not any(tag.startswith("allure.label.epic:") for tag in feature.tags):
            no_epic.append(str(Path(feature_file).relative_to(ROOT)))
        for template in feature.scenarios.values():
            contexts = [c for examples in template.examples for c in examples.as_contexts()] or [{}]
            for context in contexts:
                scenarios += 1
                for step in template.render(context).steps:
                    steps += 1
                    hits = [
                        name
                        for name, sc in defs
                        if (sc.type is None or sc.type == step.type) and sc.parser.is_matching(step.name)
                    ]
                    used.update(hits)
                    if not hits:
                        missing.append(
                            f"{Path(feature_file).relative_to(ROOT)}:{step.line_number} [{step.type}] {step.name}"
                        )
                    elif len(hits) > 1:
                        ambiguous.setdefault(step.name, hits)

    print(f"{len(defs)} step definitions, {scenarios} scenarios, {steps} steps")
    for line in missing:
        print("MISSING  ", line)
    for name, hits in ambiguous.items():
        print("AMBIGUOUS", name, "->", hits)
    for name in no_epic:
        print("NO EPIC  ", name, "(CI selects by epic — this feature would never run there)")
    unused = sorted(name for name, _ in defs if name not in used)
    for name in unused:
        print("UNUSED   ", name)
    ok = not missing and not ambiguous and not no_epic  # unused definitions are reported, not fatal
    problems = f"{len(missing)} missing, {len(ambiguous)} ambiguous, {len(no_epic)} without an epic"
    print(("OK" if ok else problems) + f" ({len(unused)} unused)")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
