from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Callable
    from typing import Any, overload

import functools
import operator
import sys
import types
import typing

from .version import PY_39, SUPPORTS_ANNOTATED, SUPPORTS_FLATLITERAL, SUPPORTS_ISTYPEDDICT, SUPPORTS_TYPEKEYWORD, SUPPORTS_UNIONTYPE


if PY_39 and not TYPE_CHECKING:
    from typing import Annotated
elif SUPPORTS_ANNOTATED:
    from typing_extensions import Annotated


class _MissingSentinel:
    __slots__ = ()

    def __repr__(self) -> str:
        return "..."

    def __bool__(self) -> bool:
        return False


MISSING: Any = _MissingSentinel()
"""
TODO
"""


def is_typeddict(
    type: type[object],
    /,
) -> bool:  # NOTE: cannot TypeGuard[type[TypedDict]] here
    """

    """

    origin = typing.get_origin(type) or type

    if SUPPORTS_ISTYPEDDICT:
        return typing.is_typeddict(origin)  # type: ignore  # typing.is_typeddict does exist
    else:
        return isinstance(origin, typing._TypedDictMeta)  # type: ignore  # typing._TypedDictMeta does exist


def resolve_annotation(
    annotation: Any,
    /,
    *,
    globals: dict[str, Any],
    locals: dict[str, Any],
) -> Any:
    if annotation is None:
        return type(None)

    if isinstance(annotation, str):
        return resolve_annotation(eval(annotation, globals, locals), globals=globals, locals=locals)

    if isinstance(annotation, typing.ForwardRef):
        if annotation.__forward_evaluated__:
            return annotation.__forward_value__

        value = resolve_annotation(annotation.__forward_arg__, globals=globals, locals=locals)

        annotation.__forward_evaluated__ = True
        annotation.__forward_value__ = value

        return value

    if origin := typing.get_origin(annotation):
        args = typing.get_args(annotation)

        if SUPPORTS_TYPEKEYWORD and isinstance(origin, typing.TypeAliasType):  # type: ignore  # typing.TypeAliasType does exist
            return resolve_annotation(origin.__value__[args], globals=globals, locals=locals)

        if not SUPPORTS_FLATLITERAL and origin is typing.Literal:
            args = list(args)

            i = 0
            while i < len(args):
                arg = args[i]
                arg_origin = typing.get_origin(arg) or arg

                if arg_origin is typing.Literal:
                    args.pop(i)

                    for j, inner_arg in enumerate(arg.__args__):
                        args.insert(i + j, inner_arg)
                else:
                    i += 1

            args = tuple(args)

        if SUPPORTS_ANNOTATED and origin is Annotated:
            args = (resolve_annotation(args[0], globals=globals, locals=locals), *args[1:])
        elif origin is not typing.Literal:
            args = tuple(map(lambda arg: resolve_annotation(arg, locals=locals, globals=globals), args))

        if SUPPORTS_UNIONTYPE and origin is types.UnionType:  # type: ignore  # types.UnionType does exist
            return functools.reduce(operator.or_, args)
        else:
            return origin[args]

    if SUPPORTS_TYPEKEYWORD and isinstance(annotation, typing.TypeAliasType):  # type: ignore  # typing.TypeAliasType does exist
        return resolve_annotation(annotation.__value__, globals=globals, locals=locals)

    return annotation


if TYPE_CHECKING:

    @overload
    def resolve_annotations(
        thing: Any,
        /,
        *,
        extend_globals: dict[str, Any] = ...,
        extend_locals: dict[str, Any] = ...,
        update_globals: dict[str, Any] = ...,
        update_locals: dict[str, Any] = ...,
    ) -> dict[str, Any]: ...

    @overload
    def resolve_annotations(
        thing: Any,
        /,
        *,
        replace_globals: dict[str, Any] = ...,
        replace_locals: dict[str, Any] = ...,
    ) -> dict[str, Any]: ...

    @overload
    def resolve_annotations(
        thing: type[Any],
        /,
        *,
        extend_globals: dict[str, Any] = ...,
        extend_locals: dict[str, Any] = ...,
        filter_mro: Callable[[type[Any]], bool] = ...,
        update_globals: dict[str, Any] = ...,
        update_locals: dict[str, Any] = ...,
    ) -> dict[str, Any]: ...

    @overload
    def resolve_annotations(
        thing: type[Any],
        /,
        *,
        filter_mro: Callable[[type[Any]], bool] = ...,
        replace_globals: dict[str, Any] = ...,
        replace_locals: dict[str, Any] = ...,
    ) -> dict[str, Any]: ...


def resolve_annotations(
    thing: Any,
    /,
    *,
    extend_globals: dict[str, Any] = MISSING,
    extend_locals: dict[str, Any] = MISSING,
    filter_mro: Callable[[type[Any]], bool] = MISSING,
    replace_globals: dict[str, Any] = MISSING,
    replace_locals: dict[str, Any] = MISSING,
    update_globals: dict[str, Any] = MISSING,
    update_locals: dict[str, Any] = MISSING,
) -> dict[str, Any]:
    if getattr(thing, "__no_type_check__", None):
        return dict()

    annotations: dict[str, Any] = dict()

    if isinstance(thing, type):
        for base in reversed(thing.__mro__):  # TODO: this can be optimized further by reading forward and never overwriting
            if filter_mro is not MISSING and not filter_mro(base):
                continue

            if getattr(base, "__no_type_check__", None):
                continue  # TODO: is this behavior correct?

            if "__annotations__" not in base.__dict__ or isinstance(base.__annotations__, types.GetSetDescriptorType):
                continue

            if replace_globals is not MISSING:
                globals = dict(replace_globals)
            else:
                globals: dict[str, Any] = dict(getattr(sys.modules.get(base.__module__), "__dict__", dict()))

                if extend_globals is not MISSING:
                    for key, value in extend_globals.items():
                        if key not in globals.keys():
                            globals[key] = value

                if update_globals is not MISSING:
                    globals.update(update_globals)

            if replace_locals is not MISSING:
                locals = dict(replace_locals)
            else:
                locals = dict(base.__dict__)

                if extend_locals is not MISSING:
                    for key, value in extend_locals.items():
                        if key not in locals.keys():
                            locals[key] = value

                if update_locals is not MISSING:
                    locals.update(update_locals)

            for name, annotation in base.__annotations__.items():
                annotations[name] = resolve_annotation(annotation, globals=globals, locals=locals)
    else:
        if not hasattr(thing, "__annotations__"):
            if isinstance(
                thing,
                (
                    types.BuiltinFunctionType,
                    types.FunctionType,
                    types.MethodDescriptorType,
                    types.MethodType,
                    types.MethodWrapperType,
                    types.ModuleType,
                    types.WrapperDescriptorType,
                ),
            ):
                return dict()
            else:
                raise ValueError(f"thing {thing} is not annotated")

        if replace_globals is not MISSING:
            globals = dict(replace_globals)
        else:
            if isinstance(thing, types.ModuleType):
                globals_name = "__dict__"
            else:
                globals_name = "__globals__"

            globals_object = thing

            while wrapped := getattr(globals_object, "__wrapped__", None):
                globals_object = wrapped

            globals = dict(getattr(globals_object, globals_name, dict()))

            if extend_globals is not MISSING:
                for key, value in extend_globals.items():
                    if key not in globals.keys():
                        globals[key] = value

            if update_globals is not MISSING:
                globals.update(update_globals)

        if replace_locals is not MISSING:
            locals = dict(replace_locals)
        else:
            locals = dict(globals)

            if extend_locals is not MISSING:
                for key, value in extend_locals.items():
                    if key not in locals.keys():
                        locals[key] = value

            if update_locals is not MISSING:
                locals.update(update_locals)

        for name, annotation in thing.__annotations__.items():
            annotations[name] = resolve_annotation(annotation, globals=globals, locals=locals)

    return annotations


__all__ = [
    "MISSING",
    "is_typeddict",
    "resolve_annotation",
    "resolve_annotations",
]
