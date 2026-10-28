---
name: ub-mode
description: >
  Follow the reduced principles when writing or changing code. Every change
  follows First Make it Work, then Then Make it Right, then Follow Practice.
  Use when the user runs /ub-mode or asks for the reduced principles.
---

<!-- Upstream: https://github.com/unclebob/ub-mode @ 57a8bdd (SKILL.md verbatim down to "Commit and Push").
     "In this repo" at the end maps every rule onto play-api-python — it wins where they differ. -->

# ub-mode

Every time you are asked to make a change follow:
* First Make it Work.
* Then Make it Right.
* Follow Practice

# First Make it Work

## Laziness Protocol

* One decision lives in one place.
* Ship the smallest edit that solves the problem.

## Foundational Thinking

* Get the data shape right before you write the logic.
* Do first whatever helps every later phase.
* If a concurrent writer would matter, do not share state.

## TDD

* Write the failing test before you change the code.
* See it fail for the reason you expect.
* Make the smallest change that makes it pass.
* If an honest test is impractical, do not write a bad one.

## Redesign From First Principles

* Do not bolt a new requirement onto the old design.
* Ask what you would have built if it had been there from the start, think that through, and deliver it in pieces.

## Attack the Premise

* When two fixes that share one premise fail the same gate, write that premise in one sentence and count which actors hold the imbalance.
* Remove the assignment.
* Do not start another fix until you have done that.

## Subtract Before You Add

* Take complexity out before you add anything.

## Outcome-Oriented Execution

* Aim at the end state you can check.
* A break in the middle is allowed when you planned it and can undo it.

## Build the Lever

* If the work is not obvious at a glance, build the tool that does it.
* Do one unit by hand, then make the tool match that unit.

## Architecture

### Model the Domain

* Put the domain in a structure that makes the illegal states impossible.
* Maintain a glossary of domain terms.
* If the code is already clear and local, leave it.

### Boundary Discipline

* Check the data where it enters.
* Inside, trust it.
* Keep the business logic in a pure function.

### Type System Discipline

* Make the illegal value impossible to write.
* Parse outside data once, where it comes in.
* Do not silence the compiler.

### Make Operations Idempotent

* Running it twice, or running it after a crash halfway through, ends in the same state.

### Separate Before Serializing Shared State

* If they do not need the same mutable thing, give each its own.
* If they do, allow one writer, and enforce that in the structure.

# Then Make it Right

## Fix Root Causes

* Reproduce it.
* Fix the cause.
* A guard that only hides the crash is not a fix.

## Sequence work into verifiable units

* Finish one small unit and check it.
* Then start the next.

## Test Behavior, Not Implementation

* The test calls the code the way its user does and checks the result that user would see.
* If the test would still pass when every function returned nothing, throw it out.

## Crapper

* Use the crapper tool
* Reduce each function under  CRAP 10 by splitting it, by testing it, or both.
* Consider whether case statements are worth reducing.

## Dryer

* Use the dryer tool to eliminate duplication that rank 0.8 or above.

## Mutator

* Use the mutator tool
* Cover the uncovered.
* Kill the survivors.
* Delete dead code.

## Refactoring

* Pin what the code does.
* Change the structure.
* Prove the behavior did not change.

# Practice

## Keep a Log

* Keep a log of every action you take and the reason you took it.
* Report that log upon completion.

## Guard the Context Window

* Keep the main thread small.
* Send the bulk elsewhere, and keep the summary.

## Worktree Cleanup

* Find what is safe to remove, confirm nothing still in use needs it, then reclaim the disk.
* Uncommitted work waits for a decision.

## Commit and Push

* Commit often, in small ordered commits.
* Each commit says why, what changed, and how you proved it.
* Push to the main line at the end.

# In this repo (play-api-python)

Read `CLAUDE.md` first; its conventions (§6) are non-negotiable and come before any rule above.

## Two kinds of failing test

| Change | The failing test you write first | How you see it fail |
|---|---|---|
| API behaviour (a scenario, a step, a service, a contract) | a Gherkin scenario in `features/play_qa_api/*.feature` phrased like its neighbours | `uv run python tools/check_steps.py` (offline: MISSING step) → then `uv run pytest --epic <Epic> -k <name>` (live, one epic only) |
| Framework logic in `src/play_api` or `tools/` (parsing, pacing, context, assertions, client plumbing) | a unit test in `tests/unit/test_<module>.py` | `uv run python tools/ub_gates.py unit` (offline, < 1 s) |

Unit tests never touch the network: HTTP through `httpx.MockTransport` (patch `play_api.api.client`'s
transport/client), time through `monkeypatch`. Live runs are rate-limited and shared — run the one epic you changed,
never the whole suite to "see it fail".

## The gates (all offline, `uv run --group ub …`)

```bash
uv run --group ub python tools/ub_gates.py unit              # unit tests
uv run --group ub python tools/ub_gates.py crap              # coverage from tests/unit → crapper, every function CRAP < 10
uv run --group ub python tools/ub_gates.py dry               # dryer, no pair ≥ 0.8 (src + tools)
uv run --group ub python tools/ub_gates.py mutate <path>...  # mutator on the files you touched (differential after the first run)
uv run --group ub python tools/ub_gates.py fast              # unit + crap + dry — quick loop, NOT the full gate
uv run --group ub python tools/ub_gates.py all [path...]     # the full gate: fast + mutator (paths, or git-changed sources)
```

Plus the CLAUDE.md lint gate: `uv run ruff check . && uv run ruff format --check . && uv run mypy && uv run python tools/check_steps.py`.
Never call `crapper`/`mutator` bare: by default they run plain `pytest` = the live suite.
Mutator runs every site (`--no-coverage`): "cover the uncovered" shows up as a survivor, so `all` fails on it.

## Mapping

- **Boundary Discipline** — the boundary is `play_api.api.client.request()` (strict pydantic contracts, `ContractViolation`).
  Steps and services trust what it returns; never re-validate a 2xx body inside a step.
- **Model the Domain** — the glossary is `docs/API_REFERENCE.md` + CLAUDE.md §8; request bodies are pydantic models,
  never dicts built in steps.
- **Make Operations Idempotent** — every created server-side resource goes through `save_created` / `ctx.defer`, so an
  interrupted scenario still cleans up.
- **Separate Before Serializing Shared State** — `ScenarioContext` is single-threaded by design (no xdist); rate-limit
  buckets have exactly one writer, `play_api.pacing`.
- **Mutator → delete dead code** — `tools/check_steps.py` lists UNUSED step definitions; delete them, don't keep them.
- **Guard the Context Window** — delegate to the project agents: `ub-implementer` (Make it Work),
  `ub-gatekeeper` (Make it Right: gates + fixes), `ub-reviewer` (read-only review).
- **Commit and Push** — per CLAUDE.md: never `;` after a gate before `git commit`; branch first when on `main`;
  push only when the user asks.
