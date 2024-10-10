from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable
    from typing import Any, TypeVar
    from typing_extensions import Concatenate, ParamSpec

    _P = ParamSpec("_P")
    _T = TypeVar("_T")
    _R = TypeVar("_R")

import inspect


def bind_function(
    callable: Callable[Concatenate[_T, _P], _R],
    instance: _T,
    /,
) -> Callable[_P, _R]:
    return callable.__get__(instance, instance.__class__)


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
    "bind_function",
    "call_maybe_coroutine",
]
