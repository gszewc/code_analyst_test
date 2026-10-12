"""Application configuration using pydantic-settings."""

from pathlib import Path
from typing import Any, List, Type
from pydantic import BaseModel, Field, field_validator
from pydantic.fields import FieldInfo
from pydantic_settings import BaseSettings, EnvSettingsSource, SettingsConfigDict
from pydantic_settings import DotEnvSettingsSource, PydanticBaseSettingsSource



def _split_comma_string(value: Any) -> Any:
    """Split a plain comma-separated string into a list; leave other values unchanged."""
    if isinstance(value, str):
        stripped = value.strip()
        if stripped and not stripped.startswith('[') and not stripped.startswith('{'):
            return [item.strip() for item in stripped.split(',') if item.strip()]
    return None  # sentinel: caller should use original path


class CommaListEnvSettingsSource(EnvSettingsSource):
    """EnvSettingsSource that accepts comma-separated strings for List[str] fields.

    pydantic-settings v2 normally calls json.loads() on complex-typed fields.
    This subclass intercepts plain strings (not JSON arrays/objects) and splits
    them on commas instead, so FIELD=a,b,c works in addition to FIELD=["a","b","c"].
    """

    def decode_complex_value(self, field_name: str, field: FieldInfo, value: Any) -> Any:
        result = _split_comma_string(value)
        if result is not None:
            return result
        return super().decode_complex_value(field_name, field, value)


class CommaListDotEnvSettingsSource(DotEnvSettingsSource):
    """DotEnvSettingsSource with comma-separated list support (same behaviour as CommaListEnvSettingsSource)."""

    def decode_complex_value(self, field_name: str, field: FieldInfo, value: Any) -> Any:
        result = _split_comma_string(value)
        if result is not None:
            return result
        return super().decode_complex_value(field_name, field, value)


SUPPORTED_NODE_TYPES = frozenset({
    "File", "Module", "Package", "Class", "Interface", "Enum",
    "Function", "Method", "Constructor", "Variable", "Import", "ExternalModule"
})


class AnalysisDefaults(BaseModel):
    """Analysis default configuration."""

    delete_graph_data: bool = False
    enabled_node_types: List[str] = []
    enabled_relationship_types: List[str] = []


class Settings(BaseSettings):
    """Application settings loaded from environment variables and .env files."""

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", case_sensitive=False, extra="ignore"
    )

    # API Configuration
    api_host: str = Field(default="0.0.0.0", description="Host to bind the API server")
    api_port: int = Field(
        default=8080, ge=1, le=65535, description="Port to bind the API server"
    )

    # Database Configuration
    sqlite_path: str = Field(
        default="data/projects.sqlite", description="Path to SQLite database file"
    )
    neo4j_uri: str = Field(
        default="bolt://localhost:7687", description="Neo4j connection URI"
    )
    neo4j_user: str = Field(default="neo4j", description="Neo4j username")
    neo4j_password: str = Field(default="password", description="Neo4j password")

    # File Configuration
    upload_dir: str = Field(
        default="uploads", description="Directory for uploaded files"
    )
    max_upload_size: int = Field(
        default=20 * 1024 * 1024,  # 20MB
        description="Maximum upload file size in bytes",
    )

    # Graph Write Batching Configuration
    graph_write_batch_size: int = Field(
        default=500,
        description="Batch size for Neo4j UNWIND writes (default 500)",
    )
    graph_write_batch_size_min: int = Field(
        default=100,
        description="Minimum allowed batch size for Neo4j UNWIND writes",
    )
    graph_write_batch_size_max: int = Field(
        default=1000,
        description="Maximum allowed batch size for Neo4j UNWIND writes",
    )

    @field_validator("sqlite_path", "upload_dir", "log_file")
    @classmethod
    def expand_user_path(cls, v: str) -> str:
        """Expand a leading ``~`` to the user's home directory.

        ``sqlite3.connect`` and ``pathlib.Path`` do not expand ``~`` on their
        own, so paths like ``~/app-data/...`` (as shipped in ``.env.example``)
        would otherwise be treated literally relative to the cwd.
        """
        if v and v != ":memory:":
            return str(Path(v).expanduser())
        return v

    @field_validator("graph_write_batch_size")
    @classmethod
    def validate_graph_write_batch_size(cls, v: int) -> int:
        """Enforce guardrails: batch size must be in [100, 1000]."""
        if not (100 <= v <= 1000):
            raise ValueError(
                f"GRAPH_WRITE_BATCH_SIZE={v} is outside the allowed range [100, 1000]. "
                "Please set a value between 100 and 1000."
            )
        return v

    # Logging Configuration
    log_level: str = Field(default="INFO", description="Logging level")
    log_file: str = Field(default="logs/app.log", description="Path to log file")

    # CORS Configuration
    cors_origins: str = Field(
        default="http://localhost:5173,http://localhost:3000",
        description="Comma-separated list of allowed CORS origins",
    )

    # Application Metadata
    app_name: str = Field(
        default="Legacy Code Analysis API", description="Application name"
    )
    app_version: str = Field(default="0.1.0", description="Application version")
    debug: bool = Field(default=False, description="Debug mode")

    # Analysis Defaults (flat fields to avoid nested delimiter conflicts)
    # Graph UI Configuration
    graph_default_visible_nodes: List[str] = Field(
        default=["File",
            "Module",
            "Package",
            "Class",
            "Interface",
            "Enum",
            "Function",
            "Method",
            "Constructor",
            "Variable",
            "Import",
            "ExternalModule",],
        description="Default visible node types in graph UI (comma-separated in env: GRAPH_DEFAULT_VISIBLE_NODES)",
    )
    analysis_default_delete_graph_data: bool = Field(
        default=False, description="Default: delete graph data before analysis"
    )
    analysis_default_enabled_node_types: List[str] = Field(
        default=[
            "File",
            "Module",
            "Package",
            "Class",
            "Interface",
            "Enum",
            "Function",
            "Method",
            "Constructor",
            "Variable",
            "Import",
            "ExternalModule",
        ],
        description="Default enabled node types (comma-separated in env)",
    )
    analysis_default_enabled_relationship_types: List[str] = Field(
        default=[
            "CONTAINS",
            "EXTENDS",
            "IMPLEMENTS",
            "CALLS",
            "DEPENDS_ON",
            "USES",
            "IMPORTS",
        ],
        description="Default enabled relationship types (comma-separated in env)",
    )

    @field_validator(
        "analysis_default_enabled_node_types",
        "analysis_default_enabled_relationship_types",
        mode="before",
    )
    @classmethod
    def split_comma_separated(cls, v):
        if isinstance(v, str):
            return [item.strip() for item in v.split(",") if item.strip()]
        return v

    @field_validator("graph_default_visible_nodes", mode="before")
    @classmethod
    def parse_graph_visible_nodes(cls, v):
        """Parse comma-separated string and filter unknown types."""
        import logging

        logger = logging.getLogger(__name__)
        if isinstance(v, str):
            v = [item.strip() for item in v.split(",") if item.strip()]
        if isinstance(v, list):
            unknown = [t for t in v if t not in SUPPORTED_NODE_TYPES]
            if unknown:
                logger.warning(
                    "Unknown node types in GRAPH_DEFAULT_VISIBLE_NODES (will be ignored): %s",
                    unknown,
                )
            seen: set = set()
            result = []
            for t in v:
                if t in SUPPORTED_NODE_TYPES and t not in seen:
                    seen.add(t)
                    result.append(t)
            return result
        return v

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: Type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> tuple[PydanticBaseSettingsSource, ...]:
        """Replace default env/dotenv sources with comma-list-aware versions."""
        # Read env_file from the pre-built dotenv_settings so we honour _env_file=None
        # passed to Settings() (which overrides model_config's env_file).
        env_file = getattr(dotenv_settings, 'env_file', None)
        return (
            init_settings,
            CommaListEnvSettingsSource(settings_cls),
            CommaListDotEnvSettingsSource(settings_cls, env_file=env_file) if env_file else dotenv_settings,
            file_secret_settings,
        )

    @property
    def analysis_defaults(self) -> "AnalysisDefaults":
        """Compose analysis defaults from flat fields."""
        return AnalysisDefaults(
            delete_graph_data=self.analysis_default_delete_graph_data,
            enabled_node_types=self.analysis_default_enabled_node_types,
            enabled_relationship_types=self.analysis_default_enabled_relationship_types,
        )

    @field_validator("neo4j_uri")
    @classmethod
    def validate_neo4j_uri(cls, v: str) -> str:
        """Validate Neo4j URI format."""
        if not v.startswith(("bolt://", "neo4j://")):
            raise ValueError("NEO4J_URI must start with bolt:// or neo4j://")
        return v

    @field_validator("log_level")
    @classmethod
    def validate_log_level(cls, v: str) -> str:
        """Validate log level."""
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if v.upper() not in valid_levels:
            raise ValueError(f"LOG_LEVEL must be one of: {valid_levels}")
        return v.upper()

    def get_cors_origins(self) -> list[str]:
        """Parse CORS origins from comma-separated string."""
        return [origin.strip() for origin in self.cors_origins.split(",")]

    def validate_on_startup(self) -> None:
        """Validate configuration and create necessary directories on startup."""
        # Create SQLite directory if needed
        sqlite_dir = Path(self.sqlite_path).parent
        sqlite_dir.mkdir(parents=True, exist_ok=True)

        # Create upload directory if needed
        Path(self.upload_dir).mkdir(parents=True, exist_ok=True)

        # Create log directory if needed
        if self.log_file:
            Path(self.log_file).parent.mkdir(parents=True, exist_ok=True)


# Global settings instance
settings = Settings()


def get_settings() -> Settings:
    """Get application settings (for dependency injection)."""
    return settings
