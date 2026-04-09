"""Source: text prompt or image file → Meshy AI → downloaded .glb file.

Two endpoints:
- text-to-3d uses Meshy v2
- image-to-3d uses Meshy v1 (these are different API versions, not a typo)
"""
from __future__ import annotations

import base64
import json
import os
import sys
import time
import urllib.request
from pathlib import Path

MESHY_API_V1 = "https://api.meshy.ai/openapi/v1"
MESHY_API_V2 = "https://api.meshy.ai/openapi/v2"
MESHY_API_BASE = MESHY_API_V2  # back-compat alias


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


def _request(base: str, method: str, endpoint: str, api_key: str, data: dict | None = None) -> dict:
    url = f"{base}/{endpoint}"
    body = json.dumps(data).encode() if data else None
    req = urllib.request.Request(url, data=body, method=method)
    req.add_header("Authorization", f"Bearer {api_key}")
    if body:
        req.add_header("Content-Type", "application/json")
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read())


def _wait(base: str, endpoint: str, task_id: str, api_key: str, label: str = "") -> dict:
    while True:
        result = _request(base, "GET", f"{endpoint}/{task_id}", api_key)
        status = result.get("status", "PENDING")
        progress = result.get("progress", 0)
        print(f"  {label} {status} {progress}%", end="\r", file=sys.stderr)
        if status == "SUCCEEDED":
            print(f"  {label} SUCCEEDED 100%", file=sys.stderr)
            return result
        if status == "FAILED":
            raise RuntimeError(f"{label} FAILED: {result.get('task_error', 'unknown')}")
        time.sleep(10)


def _extract_task_id(response: dict) -> str:
    """Meshy returns the task id in different shapes across endpoints. Handle both."""
    result = response.get("result")
    if isinstance(result, str):
        return result
    if isinstance(result, dict) and "id" in result:
        return result["id"]
    if "id" in response:
        return response["id"]
    raise RuntimeError(f"Could not find task id in Meshy response: {response}")


def _image_to_data_uri(image_path: Path) -> str:
    """Encode a local .png/.jpg/.jpeg file as a base64 data URI Meshy accepts."""
    suffix = image_path.suffix.lower().lstrip(".")
    if suffix == "jpg":
        suffix = "jpeg"
    if suffix not in ("jpeg", "png"):
        raise ValueError(
            f"Unsupported image format: .{suffix}. Use .png, .jpg, or .jpeg."
        )
    data = base64.b64encode(image_path.read_bytes()).decode("ascii")
    return f"data:image/{suffix};base64,{data}"


def fetch_glb(prompt: str, dest: Path, *, skip_refine: bool = False) -> Path:
    """Text → 3D (Meshy v2 text-to-3d, two-phase preview + refine)."""
    api_key = _api_key()
    print(f"[meshy] generating preview: {prompt!r}")
    res = _request(MESHY_API_V2, "POST", "text-to-3d", api_key, {
        "mode": "preview",
        "prompt": prompt,
        "art_style": "realistic",
    })
    preview_id = _extract_task_id(res)
    preview = _wait(MESHY_API_V2, "text-to-3d", preview_id, api_key, "preview")

    if skip_refine:
        glb_url = preview["model_urls"]["glb"]
    else:
        print("[meshy] refining with textures")
        res = _request(MESHY_API_V2, "POST", "text-to-3d", api_key, {
            "mode": "refine",
            "preview_task_id": preview_id,
        })
        refined = _wait(MESHY_API_V2, "text-to-3d", _extract_task_id(res), api_key, "refine")
        glb_url = refined["model_urls"]["glb"]

    dest.parent.mkdir(parents=True, exist_ok=True)
    urllib.request.urlretrieve(glb_url, dest)
    print(f"[meshy] downloaded {dest} ({dest.stat().st_size} bytes)")
    return dest


def fetch_glb_from_image(
    image_path: Path,
    dest: Path,
    *,
    should_texture: bool = True,
    should_remesh: bool = True,
    enable_pbr: bool = False,
) -> Path:
    """Image → 3D (Meshy v1 image-to-3d). Encodes the local image as a base64
    data URI in the request body — no separate upload step."""
    api_key = _api_key()
    image_path = Path(image_path).expanduser().resolve()
    if not image_path.exists():
        raise FileNotFoundError(f"Image not found: {image_path}")

    print(f"[meshy] image-to-3d: {image_path.name} ({image_path.stat().st_size} bytes)")
    payload = {
        "image_url": _image_to_data_uri(image_path),
        "should_texture": should_texture,
        "should_remesh": should_remesh,
        "enable_pbr": enable_pbr,
    }
    res = _request(MESHY_API_V1, "POST", "image-to-3d", api_key, payload)
    task_id = _extract_task_id(res)
    print(f"[meshy] task: {task_id}")

    task = _wait(MESHY_API_V1, "image-to-3d", task_id, api_key, "image-to-3d")
    glb_url = task.get("model_urls", {}).get("glb")
    if not glb_url:
        raise RuntimeError(f"No GLB in Meshy result: {task}")

    dest.parent.mkdir(parents=True, exist_ok=True)
    urllib.request.urlretrieve(glb_url, dest)
    print(f"[meshy] downloaded {dest} ({dest.stat().st_size} bytes)")
    return dest
