"""
vdb — Chroma + SiliconFlow BGE-M3 混合检索。

用法:
    from indexer import build_index
    build_index(force=True)            # 全量重建

    from matcher import search
    results = search("部署 flask")     # 混合检索
"""

from .indexer import build_index
from .matcher import search

__all__ = ["build_index", "search"]