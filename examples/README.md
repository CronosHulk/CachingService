# CLI demo

Run these commands from the project root:

```bash
source .venv/bin/activate
docker compose up -d
```

## Input file and repeated requests

```bash
cache-cli -H http://127.0.0.1:8000 -i examples/payload.json -r 3
```

Expected output, repeated three times:

```json
{"output":"FIRST STRING, OTHER STRING, SECOND STRING, ANOTHER STRING, THIRD STRING, LAST STRING"}
```

## Inline JSON

```bash
cache-cli -H http://127.0.0.1:8000 -j '{"list_1":["hello","world"],"list_2":["cat","dog"]}'
```

Expected output:

```json
{"output":"HELLO, CAT, WORLD, DOG"}
```

## Standard input

```bash
cache-cli -H http://127.0.0.1:8000 -i - < examples/payload.json
```

## Save the response

```bash
cache-cli -H http://127.0.0.1:8000 -i examples/payload.json -r 2 -o /tmp/caching-service-response.jsonl
cat /tmp/caching-service-response.jsonl
```

## Duplicate strings and reuse across different requests

Run in this order:

```bash
cache-cli -i examples/duplicates.json
cache-cli -i examples/cached-strings.json
```

Expected responses:

```json
{"output":"HELLO, CAT, HELLO, HELLO, CAT, WORLD"}
{"output":"WORLD, HELLO, CAT, HELLO"}
```

The first request has only three unique strings. The second request uses only
those strings, so no new transformations are needed. CLI output shows payload
content; transformer call counts and reused IDs are verified by the tests.

## Invalid input

```bash
cache-cli -i examples/invalid-lengths.json
echo $?
```

Expected: a validation error on stderr and exit code `1`. The CLI rejects this
request before contacting the API.
