"""
utility: A Python package with utilities I use in several of my other projects.
"""

from __future__ import annotations
from typing import NamedTuple

from utility.cache import *
from utility.cache import __all__ as _cache__all__
from utility.typing import *
from utility.typing import __all__ as _typing__all__
from utility.version import *
from utility.version import __all__ as _version__all__
from utility.warning import *
from utility.warning import __all__ as _warning__all__
from utility.wrapper import *
from utility.wrapper import __all__ as _wrapper__all__


class _VersionInfo(NamedTuple):
    major: int
    minor: int
    micro: int
    release: str
    serial: int


version: str = "0.1.0a"
version_info: _VersionInfo = _VersionInfo(0, 1, 0, "alpha", 0)


__all__ = [  # pyright: ignore[reportUnsupportedDunderAll]
    *_cache__all__,
    *_typing__all__,
    *_version__all__,
    *_warning__all__,
    *_wrapper__all__,
]
