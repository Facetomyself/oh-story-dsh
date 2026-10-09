"""Minimal Qidian-mobile and Fanqie rank providers."""

from .fanqie import fetch_fanqie_rank
from .qidian import fetch_qidian_mobile

__all__ = ["fetch_fanqie_rank", "fetch_qidian_mobile"]
