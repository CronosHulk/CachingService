import io
import json
from pathlib import Path
from uuid import uuid4

import pytest
from httpx import AsyncClient, MockTransport, Request, Response
from pydantic import ValidationError

from caching_service.adapters.inbound.cli.main import (
    CliSettings,
    load_input,
    main,
    run_requests,
    write_output,
)

BODY = '{"list_1": ["hello"], "list_2": ["cat"]}'


def test_short_options() -> None:
    settings = CliSettings(
        _cli_parse_args=[
            "-H",
            "http://localhost:9000",
            "-r",
            "2",
            "-j",
            BODY,
            "-o",
            "-",
        ]
    )
    assert settings.repeat == 2
    assert settings.host.port == 9000
    assert load_input(settings).list_1 == ["hello"]


@pytest.mark.parametrize(
    "arguments",
    [[], ["-j", BODY, "-i", "-"], ["-j", BODY, "-r", "0"], ["-j", BODY, "-H", "bad"]],
)
def test_invalid_arguments(arguments: list[str]) -> None:
    with pytest.raises(ValidationError):
        CliSettings(_cli_parse_args=arguments)


def test_file_input_and_output(tmp_path: Path) -> None:
    source = tmp_path / "input.json"
    target = tmp_path / "output.jsonl"
    source.write_text(BODY, encoding="utf-8")
    settings = CliSettings(_cli_parse_args=["-i", str(source), "-o", str(target)])

    assert load_input(settings).list_2 == ["cat"]
    write_output(settings, ['{"output":"HELLO, CAT"}'])
    assert json.loads(target.read_text()) == {"output": "HELLO, CAT"}


def test_stdin_and_stdout(monkeypatch, capsys) -> None:
    monkeypatch.setattr("sys.stdin", io.StringIO(BODY))
    settings = CliSettings(_cli_parse_args=["-i", "-"])
    assert load_input(settings).list_1 == ["hello"]
    write_output(settings, ['{"output":"HELLO, CAT"}'])
    assert json.loads(capsys.readouterr().out) == {"output": "HELLO, CAT"}


def test_invalid_input_json() -> None:
    settings = CliSettings(_cli_parse_args=["-j", '{"list_1":[1],"list_2":["cat"]}'])
    with pytest.raises(ValidationError):
        load_input(settings)


async def test_repeat_creates_and_reads_each_iteration() -> None:
    payload_id = str(uuid4())
    requests = []

    def respond(request: Request) -> Response:
        requests.append((request.method, request.url.path))
        if request.method == "POST":
            assert json.loads(request.content) == json.loads(BODY)
            return Response(200, json={"id": payload_id})
        return Response(200, json={"output": "HELLO, CAT"})

    settings = CliSettings(_cli_parse_args=["-j", BODY, "-r", "2"])
    async with AsyncClient(transport=MockTransport(respond)) as client:
        results = await run_requests(settings, load_input(settings), client)

    assert [json.loads(row) for row in results] == [{"output": "HELLO, CAT"}] * 2
    assert requests == [("POST", "/payload"), ("GET", f"/payload/{payload_id}")] * 2


def test_network_error_has_nonzero_exit(monkeypatch, capsys) -> None:
    from httpx import ConnectError

    async def fail(settings):
        raise ConnectError("Server unavailable")

    monkeypatch.setattr("sys.argv", ["cache-cli", "-j", BODY])
    monkeypatch.setattr("caching_service.adapters.inbound.cli.main.run", fail)
    with pytest.raises(SystemExit) as error:
        main()
    assert error.value.code == 1
    captured = capsys.readouterr()
    assert captured.out == ""
    assert "Server unavailable" in captured.err
