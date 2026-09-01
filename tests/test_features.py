"""Binds every feature file under features/ to pytest (bdd_features_base_dir in pyproject.toml).
One file is enough — steps live in tests/steps/* and are registered via conftest.pytest_plugins."""

from pytest_bdd import scenarios

scenarios("play_qa_api")
