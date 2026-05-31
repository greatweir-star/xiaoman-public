"""Shared filesystem paths for the Xiaoman backend."""

from __future__ import annotations

import os

PACKAGE_DIR = os.path.dirname(__file__)
PROJECT_DIR = os.path.dirname(PACKAGE_DIR)
DEFAULT_DATA_DIR = os.path.join(PROJECT_DIR, "data")

DATA_DIR = os.path.abspath(os.environ.get("XIAOMAN_DATA_DIR") or DEFAULT_DATA_DIR)
TEMPLATES_DIR = os.path.join(DATA_DIR, "templates")

os.makedirs(DATA_DIR, exist_ok=True)
