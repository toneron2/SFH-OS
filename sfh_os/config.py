"""Configuration management for SFH-OS."""

import os
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class LLMConfig:
    """LLM provider configuration."""

    provider: str = "anthropic"
    model: str = "claude-sonnet-4-20250514"
    api_key: str = field(default_factory=lambda: os.environ.get("ANTHROPIC_API_KEY", ""))
    max_tokens: int = 4096
    temperature: float = 0.7


@dataclass
class StorageConfig:
    """Storage configuration."""

    db_path: Path = field(default_factory=lambda: Path("./data/sfh_os.db"))
    artifacts_path: Path = field(default_factory=lambda: Path("./artifacts"))


@dataclass
class PipelineConfig:
    """Pipeline execution configuration."""

    max_iterations: int = 10
    convergence_threshold: float = 0.95
    parallel_variations: int = 3


@dataclass
class Config:
    """Main configuration container."""

    llm: LLMConfig = field(default_factory=LLMConfig)
    storage: StorageConfig = field(default_factory=StorageConfig)
    pipeline: PipelineConfig = field(default_factory=PipelineConfig)

    @classmethod
    def from_env(cls) -> "Config":
        """Load configuration from environment variables."""
        return cls(
            llm=LLMConfig(
                api_key=os.environ.get("ANTHROPIC_API_KEY", ""),
                model=os.environ.get("SFH_MODEL", "claude-sonnet-4-20250514"),
            ),
            storage=StorageConfig(
                db_path=Path(os.environ.get("SFH_DB_PATH", "./data/sfh_os.db")),
                artifacts_path=Path(os.environ.get("SFH_ARTIFACTS_PATH", "./artifacts")),
            ),
        )


# Global config instance
config = Config.from_env()
