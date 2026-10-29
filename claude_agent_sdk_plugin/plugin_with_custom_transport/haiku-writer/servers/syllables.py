"""A stdio MCP server that counts syllables.

It uses only the standard library, so it runs on any python3, including the
one in the sandbox, without installing anything.
"""

import json
import re
import sys

TOOL = {
    "name": "count_syllables",
    "description": "Count the syllables in each line of a poem.",
    "inputSchema": {
        "type": "object",
        "properties": {"text": {"type": "string"}},
        "required": ["text"],
    },
}


def syllables(word: str) -> int:
    count = len(re.findall(r"[aeiouy]+", word))
    if word.endswith("e") and not word.endswith("le") and count > 1:
        count -= 1
    return max(count, 1)


def count_syllables(text: str) -> str:
    return "\n".join(
        f"{sum(syllables(word) for word in re.findall('[a-z]+', line.lower()))}: {line}"
        for line in text.splitlines()
        if line.strip()
    )


def handle(method: str, params: dict) -> dict:
    if method == "initialize":
        return {
            "protocolVersion": params["protocolVersion"],
            "capabilities": {"tools": {}},
            "serverInfo": {"name": "syllables", "version": "1.0.0"},
        }
    if method == "tools/list":
        return {"tools": [TOOL]}
    if method == "tools/call":
        text = count_syllables(params["arguments"]["text"])
        return {"content": [{"type": "text", "text": text}]}
    return {}


for line in sys.stdin:
    request = json.loads(line)
    # Requests have an id. Notifications don't, and get no response.
    if "id" in request:
        result = handle(request["method"], request.get("params", {}))
        response = {"jsonrpc": "2.0", "id": request["id"], "result": result}
        print(json.dumps(response), flush=True)
