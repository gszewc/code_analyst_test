"""Tests for dependency injection container."""


def test_repo_map_generator_registered():
    from codeminer.container import Container
    from codeminer.services.repo_map_generator import RepoMapGenerator
    container = Container()
    assert isinstance(container.repo_map_generator(), RepoMapGenerator)


def test_orchestrator_has_repo_map_generator():
    from codeminer.container import Container
    from codeminer.services.repo_map_generator import RepoMapGenerator
    container = Container()
    orchestrator = container.analysis_orchestrator()
    assert isinstance(orchestrator.repo_map_generator, RepoMapGenerator)
