"""Source: a text string → puffy 3D toy-sans via Blender's build_text.py.

This module is a thin marker/validator. The actual Blender work happens in
puffbox.render.build_text_scene.
"""
from __future__ import annotations


def validate(text: str) -> str:
    text = text.strip()
    if not text:
        raise ValueError("Text source requires a non-empty string")
    return text
