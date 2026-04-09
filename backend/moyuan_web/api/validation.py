"""Shared API validation constants used by request models and route parameters."""

from __future__ import annotations


NON_BLANK_TEXT_PATTERN = r".*\S.*"
SESSION_ID_PATTERN = r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$"
MODEL_ID_PATTERN = r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$"
SHARE_ID_PATTERN = r"^[a-f0-9]{10}$"
CITY_ID_PATTERN = r"^[a-z0-9][a-z0-9-]{0,63}$"
