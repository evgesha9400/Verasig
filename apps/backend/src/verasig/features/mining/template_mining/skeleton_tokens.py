"""Verasig - Template Mining: skeleton tokenizer.

Shared by specificity and subsumption scoring, both of which walk a
normalized skeleton (``template.py``) token by token: a ``<*>`` wildcard, a
``<PLACEHOLDER>``, or a structural word/digit run.

Faithful port of ``skeletonTokens.js``.
"""

from __future__ import annotations

import regex as re

TOKEN = re.compile(r"<\*>|<[A-Z_]+>|[\p{L}\p{N}]+")
