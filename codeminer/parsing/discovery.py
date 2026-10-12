"""Multi-language file discovery."""

import os
from logging import getLogger

from .registry import ParserRegistry

logger = getLogger(__name__)


class FileDiscovery:
    """Discover source files grouped by language using the parser registry."""

    GLOBAL_EXCLUDED_DIRS = {".git", "node_modules", ".idea", ".vscode"}

    def __init__(self, parser_registry: ParserRegistry) -> None:
        self._registry = parser_registry

    def discover_files(
        self,
        dir_path: str,
        languages: list[str] | None = None,
        folders: list[str] | None = None,
    ) -> dict[str, list[str]]:
        """Return files grouped by language.

        Args:
            dir_path: Root directory to scan.
            languages: Optional language filter. None = all registered.
            folders: Optional folder prefix filter (relative to dir_path). None = entire tree.

        Returns:
            Dict mapping language name to list of absolute file paths.
        """
        # Build extension -> language map for requested languages
        ext_to_lang: dict[str, str] = {}
        lang_excluded: set[str] = set()

        for lang_name in self._registry.get_supported_languages():
            if languages and lang_name not in languages:
                continue
            parser = self._registry.get_parser_for_language(lang_name)
            if parser is None:
                continue
            for ext in parser.get_supported_extensions():
                ext_to_lang[ext] = lang_name
            lang_excluded.update(parser.get_excluded_dirs())

        all_excluded = self.GLOBAL_EXCLUDED_DIRS | lang_excluded

        # Normalize folder prefixes
        folder_prefixes: list[str] | None = None
        if folders is not None:
            folder_prefixes = []
            for f in folders:
                normalized = f.strip("/").strip("\\")
                if normalized:
                    folder_prefixes.append(normalized)

        result: dict[str, list[str]] = {}

        visited_real_dirs: set[str] = set()

        for root, dirs, files in os.walk(dir_path, topdown=True, followlinks=True):
            real_root = os.path.realpath(root)
            if real_root in visited_real_dirs:
                dirs[:] = []
                continue
            visited_real_dirs.add(real_root)

            # Prune excluded directories
            dirs[:] = [
                d for d in dirs
                if d not in all_excluded and not d.startswith(".")
            ]

            rel_root = os.path.relpath(root, dir_path)
            if rel_root == ".":
                rel_root = ""

            # Apply folder filter
            if folder_prefixes is not None:
                if rel_root:
                    if not any(
                        rel_root == prefix or rel_root.startswith(prefix + os.sep)
                        for prefix in folder_prefixes
                    ):
                        continue
                else:
                    # At root level — only continue if some prefix is "" or we need to descend
                    pass

            for file_name in files:
                _, ext = os.path.splitext(file_name)
                lang = ext_to_lang.get(ext)
                if lang is None:
                    continue

                file_path = os.path.join(root, file_name)

                # If folder filter active, verify the relative path matches a prefix
                if folder_prefixes is not None:
                    rel_path = os.path.relpath(file_path, dir_path)
                    if not any(rel_path.startswith(prefix) for prefix in folder_prefixes):
                        continue

                result.setdefault(lang, []).append(file_path)

        return result
