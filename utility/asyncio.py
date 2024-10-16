from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from asyncio import Task
    from collections.abc import Awaitable, Iterable
    from typing import TypeVar

    _T = TypeVar("_T")

import asyncio

from .typing import MISSING


async def wait_or_raise(
    aws: Iterable[Awaitable[_T]],
    /,
    *,
    timeout: float = MISSING,
) -> Iterable[Task[_T]]:
    done, pending = await asyncio.wait(
        (*(asyncio.Task(aw) for aw in aws),),
        timeout=timeout if timeout is not MISSING else None,
        return_when=asyncio.FIRST_EXCEPTION,
    )

    for task in pending:
        task.cancel()

    exceptions = list()

    for task in done:
        exceptions.append(task.exception())

    for exception in exceptions:
        if exception is not None:
            raise exception

    return done


__all__ = [
    "wait_or_raise",
]
