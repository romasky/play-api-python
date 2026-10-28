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
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path[:0] = [str(ROOT / "src"), str(ROOT)]

from pytest_bdd.parser import FeatureParser, Step  # noqa: E402
from pytest_bdd.steps import StepFunctionContext  # noqa: E402
from tests.conftest import pytest_plugins  # noqa: E402  # the authoritative list of step modules

Definitions = list[tuple[str, StepFunctionContext]]


def load_step_definitions() -> Definitions:
    defs: Definitions = []
    for module_name in pytest_plugins:
        module = importlib.import_module(module_name)
        for attr in dir(module):
            context = getattr(getattr(module, attr), "_pytest_bdd_step_context", None)
            if context is not None:
                defs.append((f"{module_name}.{attr}", context))
    return defs


def _matches(context: StepFunctionContext, step: Step) -> bool:
    """pytest-bdd's rule: the keyword must fit (`@step` has no type and fits any) and the parser accepts the text."""
    return (context.type is None or context.type == step.type) and context.parser.is_matching(step.name)


@dataclass
class Scan:
    """What one pass over the feature files found, step by step."""

    root: Path
    defs: Definitions
    scenarios: int = 0
    steps: int = 0
    missing: list[str] = field(default_factory=list)
    ambiguous: dict[str, list[str]] = field(default_factory=dict)
    used: set[str] = field(default_factory=set)
    no_epic: list[str] = field(default_factory=list)

    def feature(self, feature_file: str) -> None:
        """Every scenario of one feature file, outline rows rendered."""
        feature = FeatureParser(str(self.root), feature_file).parse()
        where = Path(feature_file).relative_to(self.root)
        if not any(tag.startswith("allure.label.epic:") for tag in feature.tags):
            self.no_epic.append(str(where))
        for template in feature.scenarios.values():
            contexts = [c for examples in template.examples for c in examples.as_contexts()] or [{}]
            for context in contexts:
                self.scenarios += 1
                for step in template.render(context).steps:
                    self.step(where, step)

    def step(self, where: Path, step: Step) -> None:
        """Match one rendered step against every definition, honouring keyword typing."""
        self.steps += 1
        hits = [name for name, context in self.defs if _matches(context, step)]
        self.used.update(hits)
        if not hits:
            self.missing.append(f"{where}:{step.line_number} [{step.type}] {step.name}")
        elif len(hits) > 1:
            self.ambiguous.setdefault(step.name, hits)

    @property
    def unused(self) -> list[str]:
        return sorted(name for name, _ in self.defs if name not in self.used)

    @property
    def ok(self) -> bool:
        return not self.missing and not self.ambiguous and not self.no_epic  # unused definitions are not fatal


def scan(root: Path, defs: Definitions) -> Scan:
    result = Scan(root, defs)
    for feature_file in sorted(glob.glob(str(root / "features" / "**" / "*.feature"), recursive=True)):
        result.feature(feature_file)
    return result


def report(result: Scan) -> int:
    """Print the summary, every problem and every unused definition; the exit code."""
    print(f"{len(result.defs)} step definitions, {result.scenarios} scenarios, {result.steps} steps")
    for line in result.missing:
        print("MISSING  ", line)
    for name, hits in result.ambiguous.items():
        print("AMBIGUOUS", name, "->", hits)
    for name in result.no_epic:
        print("NO EPIC  ", name, "(CI selects by epic — this feature would never run there)")
    unused = result.unused
    for name in unused:
        print("UNUSED   ", name)
    problems = (
        f"{len(result.missing)} missing, {len(result.ambiguous)} ambiguous, {len(result.no_epic)} without an epic"
    )
    print(("OK" if result.ok else problems) + f" ({len(unused)} unused)")
    return 0 if result.ok else 1


def main(root: Path = ROOT) -> int:
    return report(scan(root, load_step_definitions()))


if __name__ == "__main__":
    sys.exit(main())
