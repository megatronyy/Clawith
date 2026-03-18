"""Sandbox configuration models."""

from enum import Enum
from pydantic import BaseModel, Field


class SandboxType(str, Enum):
    """Supported sandbox backend types."""

    SUBPROCESS = "subprocess"
    DOCKER = "docker"
    E2B = "e2b"
    JUDGE0 = "judge0"
    CODEDANDBOX = "codesandbox"
    SELF_HOSTED = "self_hosted"
    AIO_SANDBOX = "aio_sandbox"


class SandboxConfig(BaseModel):
    """Configuration for sandbox backend."""

    type: SandboxType = SandboxType.SUBPROCESS
    enabled: bool = True

    # Local sandbox options
    cpu_limit: str = "0.5"
    memory_limit: str = "256m"
    allow_network: bool = False

    # API sandbox options
    api_key: str = ""
    api_url: str = ""

    # Common options
    default_timeout: int = Field(default=30, ge=1, le=300)
    max_timeout: int = Field(default=60, ge=1, le=300)

    # Language mapping for API sandboxes
    # Maps our internal language names to API-specific language IDs
    language_mapping: dict[str, str] = Field(default_factory=lambda: {
        "python": "python",
        "bash": "bash",
        "node": "javascript",
        "javascript": "javascript",
    })

    class Config:
        use_enum_values = True