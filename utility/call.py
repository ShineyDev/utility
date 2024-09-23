from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable
    from typing import Any, TypeVar
    from typing_extensions import ParamSpec

    _P = ParamSpec("_P")
    _T = TypeVar("_T")

import inspect


async def call_maybe_coroutine(
    callable: Callable[_P, _T | Awaitable[_T]],
    *args: _P.args,
    **kwargs: _P.kwargs,
) -> _T:
    object = callable(*args, **kwargs)

    if inspect.isawaitable(object):
        object = await object

    return object


__all__ = [
    "call_maybe_coroutine",
]
