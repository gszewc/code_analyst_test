"""Tests for cross_file_relations config in analysis API."""

import pytest
from codeminer.parsing.models import CrossFileConfig


class TestCrossFileConfigAPI:
    def test_default_config_when_not_provided(self):
        """When cross_file_relations is omitted, defaults apply."""
        config = CrossFileConfig()
        assert config.imports is True
        assert config.include_external is False

    def test_partial_config_merges_with_defaults(self):
        """Partial config fills missing fields with defaults."""
        config = CrossFileConfig(imports=False)
        assert config.imports is False
        assert config.inheritance is True
