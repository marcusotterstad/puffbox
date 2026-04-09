"""Source: a text prompt → Meshy text-to-3D → downloaded .glb file.

Adapted from Aerdash/tools/generate_perk_sprite.py.
"""
from __future__ import annotations

import json
import os
import sys
import time
import urllib.request
from pathlib import Path

MESHY_API_BASE = "https://api.meshy.ai/openapi/v2"


def _api_key() -> str:
    key = os.environ.get("MESHY_API_KEY")
    if key:
        return key
    env_path = Path.home() / ".env"
    if env_path.exists():
        for line in env_path.read_text().splitlines():
            if line.startswith("MESHY_API_KEY="):
                return line.split("=", 1)[1].strip()
    raise RuntimeError("MESHY_API_KEY not found (env var or ~/.env)")


def _request(method: str, endpoint: str, api_key: str, data: dict | None = None) -> dict:
    url = f"{MESHY_API_BASE}/{endpoint}"
    body = json.dumps(data).encode() if data else None
    req = urllib.request.Request(url, data=body, method=method)
    req.add_header("Authorization", f"Bearer {api_key}")
    if body:
        req.add_header("Content-Type", "application/json")
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read())


def _wait(task_id: str, api_key: str, label: str = "") -> dict:
    while True:
        result = _request("GET", f"text-to-3d/{task_id}", api_key)
        status = result["status"]
        progress = result.get("progress", 0)
        print(f"  {label} {status} {progress}%", end="\r", file=sys.stderr)
        if status == "SUCCEEDED":
            print(f"  {label} SUCCEEDED 100%", file=sys.stderr)
            return result
        if status == "FAILED":
            raise RuntimeError(f"{label} FAILED: {result.get('task_error', 'unknown')}")
        time.sleep(10)


def fetch_glb(prompt: str, dest: Path, *, skip_refine: bool = False) -> Path:
    api_key = _api_key()
    print(f"[meshy] generating preview: {prompt!r}")
    res = _request("POST", "text-to-3d", api_key, {
        "mode": "preview",
        "prompt": prompt,
        "art_style": "realistic",
    })
    preview_id = res["result"]
    preview = _wait(preview_id, api_key, "preview")

    if skip_refine:
        glb_url = preview["model_urls"]["glb"]
    else:
        print("[meshy] refining with textures")
        res = _request("POST", "text-to-3d", api_key, {
            "mode": "refine",
            "preview_task_id": preview_id,
        })
        refined = _wait(res["result"], api_key, "refine")
        glb_url = refined["model_urls"]["glb"]

    dest.parent.mkdir(parents=True, exist_ok=True)
    urllib.request.urlretrieve(glb_url, dest)
    print(f"[meshy] downloaded {dest} ({dest.stat().st_size} bytes)")
    return dest
