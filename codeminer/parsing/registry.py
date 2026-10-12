"""Central registry for language parsers."""

from logging import getLogger

from .interfaces import LanguageParser
from .types import NodeTypeDefinition, RelationshipTypeDefinition

logger = getLogger(__name__)


class ParserRegistry:
    """Registry mapping languages and file extensions to parser instances."""

    def __init__(self) -> None:
        self._parsers: dict[str, LanguageParser] = {}
        self._extension_map: dict[str, str] = {}

    def register(self, parser: LanguageParser) -> None:
        """Register a language parser."""
        lang = parser.get_language_name()
        if lang in self._parsers:
            raise ValueError(f"Language '{lang}' already registered")

        for ext in parser.get_supported_extensions():
            if ext in self._extension_map:
                existing = self._extension_map[ext]
                raise ValueError(
                    f"Extension '{ext}' already claimed by '{existing}'"
                )

        self._parsers[lang] = parser
        for ext in parser.get_supported_extensions():
            self._extension_map[ext] = lang

        logger.info(f"Registered parser: {lang} ({parser.get_supported_extensions()})")

    def get_parser_for_extension(self, extension: str) -> LanguageParser | None:
        lang = self._extension_map.get(extension)
        return self._parsers.get(lang) if lang else None

    def get_parser_for_language(self, language: str) -> LanguageParser | None:
        return self._parsers.get(language)

    def get_supported_languages(self) -> list[str]:
        return list(self._parsers.keys())

    def get_all_node_type_definitions(self) -> list[NodeTypeDefinition]:
        result = []
        for parser in self._parsers.values():
            result.extend(parser.get_node_type_definitions())
        return result

    def get_all_relationship_type_definitions(self) -> list[RelationshipTypeDefinition]:
        result = []
        for parser in self._parsers.values():
            result.extend(parser.get_relationship_type_definitions())
        return result

    def get_definitions_for_language(self, language: str) -> dict:
        parser = self._parsers.get(language)
        if not parser:
            return {"node_types": [], "relationship_types": []}
        return {
            "node_types": parser.get_node_type_definitions(),
            "relationship_types": parser.get_relationship_type_definitions(),
        }
