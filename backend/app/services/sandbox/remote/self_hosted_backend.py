"""Self-hosted sandbox backend."""

import time

import httpx

from app.services.sandbox.base import BaseSandboxBackend, ExecutionResult, SandboxCapabilities
from app.services.sandbox.config import SandboxConfig


class SelfHostedBackend(BaseSandboxBackend):
    """Self-hosted sandbox backend.

    This backend connects to a user-deployed sandbox service.
    The service should implement a simple REST API:

    POST /execute
    {
        "code": "print('hello')",
        "language": "python",
        "timeout": 30
    }

    Response:
    {
        "success": true,
        "stdout": "hello\n",
        "stderr": "",
        "exit_code": 0,
        "duration_ms": 100
    }
    """

    name = "self_hosted"

    def __init__(self, config: SandboxConfig):
        self.config = config

        if not config.api_url:
            raise ValueError(
                "Self-hosted sandbox URL is required. "
                "Set SANDBOX_API_URL environment variable."
            )

        # Normalize URL (remove trailing slash)
        self.api_url = config.api_url.rstrip("/")

    def get_capabilities(self) -> SandboxCapabilities:
        # Capabilities depend on the self-hosted service
        # We'll report conservative defaults
        return SandboxCapabilities(
            supported_languages=["python", "bash", "node", "javascript"],
            max_timeout=self.config.max_timeout,
            max_memory_mb=256,
            network_available=True,
            filesystem_available=True,
        )

    async def health_check(self) -> bool:
        """Check if the self-hosted service is available."""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.api_url}/health",
                    timeout=5.0
                )
                return response.status_code == 200
        except Exception:
            return False

    async def execute(
        self,
        code: str,
        language: str,
        timeout: int = 30,
        work_dir: str | None = None,
        **kwargs
    ) -> ExecutionResult:
        """Execute code using the self-hosted sandbox service."""
        start_time = time.time()

        # Build request
        headers = {
            "Content-Type": "application/json",
        }

        # Add API key if configured
        if self.config.api_key:
            headers["Authorization"] = f"Bearer {self.config.api_key}"

        payload = {
            "code": code,
            "language": language,
            "timeout": timeout,
        }

        if work_dir:
            payload["work_dir"] = work_dir

        # Add any additional kwargs
        payload.update(kwargs)

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.api_url}/execute",
                    json=payload,
                    headers=headers,
                    timeout=float(timeout + 10)  # Add buffer for network
                )

                duration_ms = int((time.time() - start_time) * 1000)

                if response.status_code != 200:
                    return ExecutionResult(
                        success=False,
                        stdout="",
                        stderr="",
                        exit_code=response.status_code,
                        duration_ms=duration_ms,
                        error=f"Sandbox service error: HTTP {response.status_code}"
                    )

                result = response.json()

                # Parse response
                # Expected format:
                # {
                #     "success": true,
                #     "stdout": "...",
                #     "stderr": "...",
                #     "exit_code": 0,
                #     "duration_ms": 100,
                #     "error": null
                # }

                return ExecutionResult(
                    success=result.get("success", False),
                    stdout=(result.get("stdout") or "")[:10000],
                    stderr=(result.get("stderr") or "")[:5000],
                    exit_code=result.get("exit_code", 1),
                    duration_ms=result.get("duration_ms", duration_ms),
                    error=result.get("error")
                )

        except httpx.TimeoutException:
            duration_ms = int((time.time() - start_time) * 1000)
            return ExecutionResult(
                success=False,
                stdout="",
                stderr="",
                exit_code=124,
                duration_ms=duration_ms,
                error=f"Code execution timed out after {timeout}s"
            )

        except Exception as e:
            duration_ms = int((time.time() - start_time) * 1000)
            return ExecutionResult(
                success=False,
                stdout="",
                stderr="",
                exit_code=1,
                duration_ms=duration_ms,
                error=f"Self-hosted sandbox error: {str(e)[:200]}"
            )