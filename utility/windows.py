from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from typing import TextIO

import ctypes
import enum
import subprocess
import sys

from .typing import MISSING


assert sys.platform == "win32"


import ctypes.wintypes
import msvcrt


def _get_console_mode(
    handle: int,
    /,
) -> int:
    """
    |internal|

    TODO
    """

    handle_c = ctypes.wintypes.HANDLE(handle)
    mode_c = ctypes.wintypes.DWORD()

    if ctypes.windll.kernel32.GetConsoleMode(handle_c, ctypes.byref(mode_c)) == 0:
        raise ctypes.WinError(ctypes.get_last_error())

    return mode_c.value


def get_console_mode(
    *,
    stream: TextIO = MISSING,
) -> ConsoleMode:
    """
    TODO
    """

    if stream is MISSING:
        mode = 0b00000100000000001

        input_handle: int = ctypes.windll.kernel32.GetStdHandle(subprocess.STD_INPUT_HANDLE)
        input_mode = _get_console_mode(input_handle)

        mode &= input_mode << 1

        output_handle: int = ctypes.windll.kernel32.GetStdHandle(subprocess.STD_OUTPUT_HANDLE)
        output_mode = _get_console_mode(output_handle)

        mode &= output_mode << 12
    else:
        if stream.writable():
            mode = 0b1 << 11
        else:
            mode = 0b1 << 0

        stream_handle = msvcrt.get_osfhandle(stream.fileno())
        stream_mode = _get_console_mode(stream_handle)

        if stream.writable():  # TODO(console-writable): is this as accurate as it needs to be?
            mode &= mode << 12
        else:
            mode &= mode << 1

    # NOTE: DISABLE_NEWLINE_AUTO_RETURN is normalized to ENABLE_* here.
    mode ^= 0b01000 << 12

    return ConsoleMode(mode)


class _F_ConsoleModeInput(enum.IntFlag):
    # fmt: off
    ENABLE_PROCESSED_INPUT        = 0b0000000001
    ENABLE_LINE_INPUT             = 0b0000000010
    ENABLE_ECHO_INPUT             = 0b0000000100
    ENABLE_WINDOW_INPUT           = 0b0000001000
    ENABLE_MOUSE_INPUT            = 0b0000010000
    ENABLE_INSERT_MODE            = 0b0000100000
    ENABLE_QUICK_EDIT_MODE        = 0b0001000000
    ENABLE_EXTENDED_FLAGS         = 0b0010000000  # NOTE: undocumented
    ENABLE_AUTO_POSITION          = 0b0100000000  # NOTE: undocumented
    ENABLE_VIRTUAL_TERMINAL_INPUT = 0b1000000000
    # fmt: on


class _F_ConsoleModeOutput(enum.IntFlag):
    # fmt: off
    ENABLE_PROCESSED_OUTPUT            = 0b00001
    ENABLE_WRAP_AT_EOL_OUTPUT          = 0b00010
    ENABLE_VIRTUAL_TERMINAL_PROCESSING = 0b00100
    DISABLE_NEWLINE_AUTO_RETURN        = 0b01000
    ENABLE_LVB_GRID_WORLDWIDE          = 0b10000
    # fmt: on


class ConsoleMode(enum.IntFlag):
    """
    TODO
    """

    input = 0b1 << 0
    """
    TODO
    """

    input_processed = _F_ConsoleModeInput.ENABLE_PROCESSED_INPUT << 1
    """
    TODO
    """

    input_line = _F_ConsoleModeInput.ENABLE_LINE_INPUT << 1
    """
    TODO
    """

    input_echo = _F_ConsoleModeInput.ENABLE_ECHO_INPUT << 1
    """
    TODO
    """

    input_window_events = _F_ConsoleModeInput.ENABLE_WINDOW_INPUT << 1
    """
    TODO
    """

    input_mouse_events = _F_ConsoleModeInput.ENABLE_MOUSE_INPUT
    """
    TODO
    """

    input_insert = _F_ConsoleModeInput.ENABLE_INSERT_MODE
    """
    TODO
    """

    input_edit = _F_ConsoleModeInput.ENABLE_QUICK_EDIT_MODE
    """
    TODO
    """

    input_extended_flags = _F_ConsoleModeInput.ENABLE_EXTENDED_FLAGS
    """
    TODO
    """

    input_auto_position = _F_ConsoleModeInput.ENABLE_AUTO_POSITION << 1
    """
    TODO
    """

    input_virtual_terminal_processing = _F_ConsoleModeInput.ENABLE_VIRTUAL_TERMINAL_INPUT << 1
    """
    TODO
    """

    output = 0b1 << 11
    """
    TODO
    """

    output_processed = _F_ConsoleModeOutput.ENABLE_PROCESSED_OUTPUT << 12
    """
    TODO
    """

    output_wrap_at_eol = _F_ConsoleModeOutput.ENABLE_WRAP_AT_EOL_OUTPUT << 12
    """
    TODO
    """

    output_virtual_terminal_processing = _F_ConsoleModeOutput.ENABLE_VIRTUAL_TERMINAL_PROCESSING << 12
    """
    TODO
    """

    output_newline_auto_return = _F_ConsoleModeOutput.DISABLE_NEWLINE_AUTO_RETURN << 12
    """
    TODO
    """

    output_lvb_grid_worldwide = _F_ConsoleModeOutput.ENABLE_LVB_GRID_WORLDWIDE << 12
    """
    TODO
    """


__all__ = [
    "get_console_mode",
    "ConsoleMode",
]
