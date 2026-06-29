"""
Secure JSON/YAML Parser.

Security features:
- Maximum file size (2 MB) enforced before reading.
- YAML parsed with ``yaml.safe_load`` only (never ``yaml.load``).
- Precise YAML anchor/alias detection (billion-laughs / DoS defence) that does
  NOT mistake legitimate wildcard values such as "s3:*" or "*" for aliases.
- Maximum nesting depth validation.
- Parse timeout.
- Logging (never logs secrets).
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import TimeoutError as FuturesTimeoutError

import yaml

# ---------------- Configuration ---------------- #

MAX_FILE_SIZE = 2 * 1024 * 1024  # 2 MB
MAX_DEPTH = 20
PARSE_TIMEOUT = 3  # seconds

# Libraries should not configure the root logger; only obtain a named logger.
logger = logging.getLogger(__name__)


class SecureParser:
    """Secure parser for JSON and YAML cloud configuration files."""

    def parse(self, file_path: str):
        file = Path(file_path)

        if not file.exists():
            raise FileNotFoundError(file_path)

        # -------- File size -------- #
        if file.stat().st_size > MAX_FILE_SIZE:
            raise ValueError(
                f"File exceeds maximum size of {MAX_FILE_SIZE // (1024 * 1024)} MB."
            )

        raw_text = file.read_text(encoding="utf-8")
        extension = file.suffix.lower()

        # -------- Reject YAML anchors/aliases (DoS defence) -------- #
        # Only meaningful for YAML; JSON has no anchors/aliases.
        if extension in (".yaml", ".yml", ""):
            self._reject_yaml_aliases(raw_text)

        logger.info("Parsing %s", file.name)

        with ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(self._parse_content, raw_text, extension)
            try:
                data = future.result(timeout=PARSE_TIMEOUT)
            except FuturesTimeoutError:
                raise TimeoutError("Parsing timed out.")

        self._validate_depth(data)
        logger.info("Parsing completed successfully.")
        return data

    # ------------------------------------------------ #

    def _parse_content(self, text: str, extension: str):
        if extension == ".json":
            try:
                return json.loads(text)
            except json.JSONDecodeError as e:
                raise ValueError(f"Invalid JSON: {e}")

        elif extension in (".yaml", ".yml"):
            try:
                return yaml.safe_load(text)
            except yaml.YAMLError as e:
                raise ValueError(f"Invalid YAML: {e}")

        else:
            # Unknown extension: auto-detect JSON, then YAML.
            try:
                return json.loads(text)
            except Exception:
                pass
            try:
                return yaml.safe_load(text)
            except Exception:
                pass
            raise ValueError("Unsupported file format.")

    # ------------------------------------------------ #

    def _reject_yaml_aliases(self, text: str):
        """
        Reject YAML anchors (``&name``) and aliases (``*name``) precisely, using
        the YAML event stream rather than naive substring matching.

        This is the key fix over the original implementation, which rejected any
        line containing ``*`` or ``&`` and therefore threw out perfectly valid
        configs such as ``action: "s3:*"`` (the exact input the wildcard rules
        need to inspect).
        """
        try:
            for event in yaml.parse(text, Loader=yaml.SafeLoader):
                if isinstance(event, yaml.events.AliasEvent):
                    raise ValueError("YAML aliases are not allowed.")
                if getattr(event, "anchor", None):
                    raise ValueError("YAML anchors are not allowed.")
        except yaml.YAMLError:
            # Not parseable as YAML here — let _parse_content surface the error.
            return

    # ------------------------------------------------ #

    def _validate_depth(self, obj, depth=1):
        if depth > MAX_DEPTH:
            raise ValueError(f"Maximum nesting depth ({MAX_DEPTH}) exceeded.")

        if isinstance(obj, dict):
            for value in obj.values():
                self._validate_depth(value, depth + 1)
        elif isinstance(obj, list):
            for value in obj:
                self._validate_depth(value, depth + 1)
