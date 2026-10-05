import asyncio
import sys
from pathlib import Path
from typing import Self

from httpx import AsyncClient, HTTPError
from pydantic import Field, HttpUrl, ValidationError, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict, SettingsError

from caching_service.adapters.inbound.api.schemas import (
    CreatePayloadRequest,
    CreatePayloadResponse,
    ReadPayloadResponse,
)


class CliSettings(BaseSettings):
    """Create and read a payload once per iteration; emit JSON Lines."""

    host: HttpUrl = HttpUrl("http://127.0.0.1:8000")
    repeat: int = Field(default=1, ge=1, description="Number of iterations")
    input_file: str | None = Field(
        default=None, validation_alias="input", description="JSON file or - for stdin"
    )
    json_payload: str | None = Field(
        default=None, validation_alias="json", description="Inline JSON request"
    )
    output_file: str = Field(
        default="-",
        validation_alias="output",
        description="JSON Lines file or - for stdout",
    )

    model_config = SettingsConfigDict(
        cli_parse_args=True,
        case_sensitive=True,
        cli_prog_name="cache-cli",
        cli_exit_on_error=False,
        cli_hide_none_type=True,
        cli_shortcuts={
            "host": "H",
            "repeat": "r",
            "input": "i",
            "json": "j",
            "output": "o",
        },
        env_prefix="CACHE_CLI_",
        populate_by_name=True,
    )

    @model_validator(mode="after")
    def validate_input_source(self) -> Self:
        if (self.input_file is None) == (self.json_payload is None):
            raise ValueError("Provide exactly one of --input or --json")
        if not self.output_file or self.input_file == "":
            raise ValueError("File paths must not be empty")
        if (
            self.host.query
            or self.host.fragment
            or self.host.username
            or self.host.password
        ):
            raise ValueError(
                "Host URL must not contain credentials, query, or fragment"
            )
        return self


def load_input(settings: CliSettings) -> CreatePayloadRequest:
    if settings.json_payload is not None:
        raw = settings.json_payload
    elif settings.input_file == "-":
        raw = sys.stdin.read()
    else:
        raw = Path(settings.input_file).read_text(encoding="utf-8")
    return CreatePayloadRequest.model_validate_json(raw)


async def run_requests(
    settings: CliSettings,
    payload: CreatePayloadRequest,
    client: AsyncClient,
) -> list[str]:
    endpoint = f"{str(settings.host).rstrip('/')}/payload"
    results = []
    for _ in range(settings.repeat):
        response = await client.post(endpoint, json=payload.model_dump())
        response.raise_for_status()
        created = CreatePayloadResponse.model_validate_json(response.content)

        response = await client.get(f"{endpoint}/{created.id}")
        response.raise_for_status()
        result = ReadPayloadResponse.model_validate_json(response.content)
        results.append(result.model_dump_json())
    return results


def write_output(settings: CliSettings, results: list[str]) -> None:
    content = "\n".join(results) + "\n"
    if settings.output_file == "-":
        sys.stdout.write(content)
    else:
        Path(settings.output_file).write_text(content, encoding="utf-8")


async def run(settings: CliSettings) -> None:
    payload = await asyncio.to_thread(load_input, settings)
    async with AsyncClient(timeout=30) as client:
        results = await run_requests(settings, payload, client)
    await asyncio.to_thread(write_output, settings, results)


def main() -> None:
    try:
        settings = CliSettings()
        asyncio.run(run(settings))
    except (ValidationError, SettingsError, OSError, UnicodeError, HTTPError) as exc:
        print(f"cache-cli: {exc}", file=sys.stderr)
        raise SystemExit(1) from None
    except KeyboardInterrupt:
        raise SystemExit(130) from None


if __name__ == "__main__":
    main()
