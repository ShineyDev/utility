from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Iterable, Generator
    from typing import TextIO
    from typing_extensions import Self

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
            mode &= stream_mode << 12
        else:
            mode &= stream_mode << 1

    # NOTE: DISABLE_NEWLINE_AUTO_RETURN is normalized to ENABLE_* here.
    mode ^= 0b01000 << 12

    return ConsoleMode(mode)


def _read_console_input(
    handle: int,
    /,
    *,
    buffer_size: int,
) -> Iterable[_S_INPUT_RECORD]:
    """
    |internal|

    TODO
    """

    handle_c = ctypes.wintypes.HANDLE(handle)
    buffer_c = (_S_INPUT_RECORD * buffer_size)()
    buffer_size_c = ctypes.wintypes.DWORD(buffer_size)
    count_c = ctypes.wintypes.DWORD()

    if ctypes.windll.kernel32.ReadConsoleInputW(handle_c, ctypes.byref(buffer_c), buffer_size_c, ctypes.byref(count_c)) == 0:
        raise ctypes.WinError(ctypes.get_last_error())

    return buffer_c[:count_c.value]  # fmt: skip


def read_console_input(
    *,
    buffer_size: int = MISSING,
    stream: TextIO = MISSING,
) -> Generator[ConsoleInputEvent, None, None]:
    """
    TODO
    """

    if buffer_size is MISSING:
        buffer_size = 1

    if stream is MISSING:
        handle = ctypes.windll.kernel32.GetStdHandle(subprocess.STD_INPUT_HANDLE)
    else:
        handle = msvcrt.get_osfhandle(stream.fileno())

    while True:
        for c_record in _read_console_input(handle, buffer_size=buffer_size):
            if c_record.EventType == ConsoleInputEventType.focus:
                yield ConsoleInputFocusEvent(c_record.Event.FocusEvent)
            elif c_record.EventType == ConsoleInputEventType.key:
                yield ConsoleInputKeyEvent(c_record.Event.KeyEvent)
            elif c_record.EventType == ConsoleInputEventType.menu:
                yield ConsoleInputMenuEvent(c_record.Event.MenuEvent)
            elif c_record.EventType == ConsoleInputEventType.mouse:
                yield ConsoleInputMouseEvent(c_record.Event.MouseEvent)
            elif c_record.EventType == ConsoleInputEventType.resize:
                yield ConsoleInputResizeEvent(c_record.Event.WindowBufferSizeEvent)
            else:
                # TODO: warn?
                continue


def _set_console_mode(
    handle: int,
    mode: int,
    /,
) -> None:
    """
    |internal|

    TODO
    """

    handle_c = ctypes.wintypes.HANDLE(handle)
    mode_c = ctypes.wintypes.DWORD(mode)

    if ctypes.windll.kernel32.SetConsoleMode(handle_c, mode_c) == 0:
        raise ctypes.WinError(ctypes.get_last_error())

    return None


def set_console_mode(
    mode: ConsoleMode,
    /,
    *,
    stream: TextIO,
) -> None:
    """
    TODO
    """

    mode_i = int(mode)

    # NOTE: output_newline_auto_return is inverted to DISABLE_* here
    mode_i ^= 0b01000 << 12

    if stream is MISSING:
        input_handle: int = ctypes.windll.kernel32.GetStdHandle(subprocess.STD_INPUT_HANDLE)
        input_mode = mode_i >> 1 & 0b11111

        _set_console_mode(input_handle, input_mode)

        output_handle: int = ctypes.windll.kernel32.GetStdHandle(subprocess.STD_OUTPUT_HANDLE)
        output_mode = mode_i >> 12 & 0b1111111111

        _set_console_mode(output_handle, output_mode)
    else:
        stream_handle = msvcrt.get_osfhandle(stream.fileno())

        if stream.writable():  # TODO(console-writable): is this as accurate as it needs to be?
            stream_mode = mode_i >> 12 & 0b1111111111
        else:
            stream_mode = mode_i >> 1 & 0b11111

        _set_console_mode(stream_handle, stream_mode)


class _S_COORD(ctypes.Structure):
    _fields_ = [
        ("X", ctypes.wintypes.SHORT),
        ("Y", ctypes.wintypes.SHORT),
    ]


class _S_FOCUS_EVENT_RECORD(ctypes.Structure):
    _fields_ = [
        ("bSetFocus", ctypes.wintypes.BOOL),
    ]


class _S_KEY_EVENT_RECORD(ctypes.Structure):
    class _U_CHAR(ctypes.Union):
        _fields_ = [
            ("UnicodeChar", ctypes.wintypes.WCHAR),
            ("AsciiChar", ctypes.wintypes.CHAR),
        ]

    _fields_ = [
        ("bKeyDown", ctypes.wintypes.BOOL),
        ("wRepeatCount", ctypes.wintypes.WORD),
        ("wVirtualKeyCode", ctypes.wintypes.WORD),
        ("wVirtualScanCode", ctypes.wintypes.WORD),
        ("uChar", _U_CHAR),
        ("dwControlKeyState", ctypes.wintypes.DWORD),
    ]


class _S_MENU_EVENT_RECORD(ctypes.Structure):
    _fields_ = [
        # NOTE: menu_init = 278
        #       menu_select = 287 (also implies and on menu close)
        ("dwCommandId", ctypes.wintypes.DWORD),
    ]


class _S_MOUSE_EVENT_RECORD(ctypes.Structure):
    _fields_ = [
        ("dwMousePosition", _S_COORD),
        #
        # NOTE: we split dwButtonState into two words here. the high
        #       word of dwButtonState is a signed int which determines
        #       scroll delta, which was 120 (prior to Windows 10.22000,
        #       "11"?) and is now 128. the value shouldn't matter to
        #       users since windows implements mouse scrolling and key
        #       repeating outside of this api now.
        ("wButtonState", ctypes.wintypes.WORD),
        ("wScrollDelta", ctypes.wintypes.SHORT),
        #
        ("dwControlKeyState", ctypes.wintypes.DWORD),
        ("dwEventFlags", ctypes.wintypes.DWORD),
    ]


class _S_WINDOW_BUFFER_SIZE_RECORD(ctypes.Structure):
    _fields_ = [
        ("dwSize", _S_COORD),
    ]


class _S_INPUT_RECORD(ctypes.Structure):
    class _U_EVENT(ctypes.Union):
        _fields_ = [
            ("FocusEvent", _S_FOCUS_EVENT_RECORD),
            ("KeyEvent", _S_KEY_EVENT_RECORD),
            ("MenuEvent", _S_MENU_EVENT_RECORD),
            ("MouseEvent", _S_MOUSE_EVENT_RECORD),
            ("WindowBufferSizeEvent", _S_WINDOW_BUFFER_SIZE_RECORD),
        ]

    _fields_ = [
        ("EventType", ctypes.wintypes.WORD),
        ("Event", _U_EVENT),
    ]


class Coordinate:
    """
    TODO
    """

    def __init__(
        self: Self,
        /,
        x: int,
        y: int,
    ) -> None:
        self.x: int = x
        self.y: int = y

    def __repr__(
        self: Self,
        /,
    ) -> str:
        return f"<{self.__class__.__name__} x={self.x!r} y={self.y!r}>"


class ConsoleInputEvent:
    """
    TODO
    """

    pass


class ConsoleInputFocusEvent(ConsoleInputEvent):
    """
    TODO
    """

    def __init__(
        self: Self,
        c_event: _S_FOCUS_EVENT_RECORD,
        /,
    ) -> None:
        """
        TODO
        """

        self.is_focused: bool = c_event.bSetFocus

    def __repr__(
        self: Self,
        /,
    ) -> str:
        """
        TODO
        """

        ...


class ConsoleInputKeyEvent(ConsoleInputEvent):
    """
    TODO
    """

    def __init__(
        self: Self,
        c_event: _S_KEY_EVENT_RECORD,
        /,
    ) -> None:
        """
        TODO
        """

        self.is_key_down: bool = bool(c_event.bKeyDown)
        self.repeat_count: int = c_event.wRepeatCount
        self.virtual_key_code: int = c_event.wVirtualKeyCode
        self.virtual_scan_code: int = c_event.wVirtualScanCode
        self.unicode_char: str = c_event.uChar.UnicodeChar
        self.ascii_char: str = c_event.uChar.AsciiChar
        self.control_key_state: ControlKeyState = ControlKeyState(c_event.dwControlKeyState)

    def __repr__(
        self: Self,
        /,
    ) -> str:
        """
        TODO
        """

        ...


class ConsoleInputMenuEvent(ConsoleInputEvent):
    """
    TODO
    """

    def __init__(
        self: Self,
        c_event: _S_MENU_EVENT_RECORD,
        /,
    ) -> None:
        """
        TODO
        """

        self.command_id: int = c_event.dwCommandId

    def __repr__(
        self: Self,
        /,
    ) -> str:
        """
        TODO
        """

        ...


class ConsoleInputMouseEvent(ConsoleInputEvent):
    """
    TODO
    """

    def __init__(
        self: Self,
        c_event: _S_MOUSE_EVENT_RECORD,
        /,
    ) -> None:
        """
        TODO
        """

        self.mouse_position: tuple[int, int] = (c_event.dwMousePosition.X, c_event.dwMousePosition.Y)
        self.scroll_delta: int = c_event.wScrollDelta

        scroll_direction = None
        if c_event.dwEventFlags == ConsoleInputMouseEventType.wheel_vertical:
            if c_event.wScrollDelta > 0:
                scroll_direction = ConsoleInputMouseScrollDirection.forward
            elif c_event.wScrollDelta < 0:
                scroll_direction = ConsoleInputMouseScrollDirection.backward
        elif c_event.dwEventFlags == ConsoleInputMouseEventType.wheel_horizontal:
            if c_event.wScrollDelta > 0:
                scroll_direction = ConsoleInputMouseScrollDirection.right
            elif c_event.wScrollDelta < 0:
                scroll_direction = ConsoleInputMouseScrollDirection.left

        self.scroll_direction: ConsoleInputMouseScrollDirection | None = scroll_direction

        self.button_state: ConsoleInputMouseButtonState = ConsoleInputMouseButtonState(c_event.wButtonState)
        self.control_key_state: ControlKeyState = ControlKeyState(c_event.dwControlKeyState)
        self.event_flags: ConsoleInputMouseEventType = ConsoleInputMouseEventType(c_event.dwEventFlags)

    def __repr__(
        self: Self,
        /,
    ) -> str:
        """
        TODO
        """

        ...


class ConsoleInputResizeEvent(ConsoleInputEvent):
    """
    TODO
    """

    def __init__(
        self: Self,
        c_event: _S_WINDOW_BUFFER_SIZE_RECORD,
        /,
    ) -> None:
        """
        TODO
        """

        self.size: tuple[int, int] = (c_event.dwSize.X, c_event.dwSize.Y)

    def __repr__(
        self: Self,
        /,
    ) -> str:
        """
        TODO
        """

        ...


class _E_EventType(enum.IntEnum):
    # fmt: off
    KEY_EVENT                = 0b00001
    MOUSE_EVENT              = 0b00010
    WINDOW_BUFFER_SIZE_EVENT = 0b00100
    MENU_EVENT               = 0b01000
    FOCUS_EVENT              = 0b10000
    # fmt: on


class ConsoleInputEventType(enum.IntEnum):
    """
    TODO
    """

    focus = _E_EventType.FOCUS_EVENT
    """
    TODO
    """

    key = _E_EventType.KEY_EVENT
    """
    TODO
    """

    menu = _E_EventType.MENU_EVENT
    """
    TODO
    """

    mouse = _E_EventType.MOUSE_EVENT
    """
    TODO
    """

    resize = _E_EventType.WINDOW_BUFFER_SIZE_EVENT
    """
    TODO
    """


class _F_ControlKeyState(enum.IntFlag):
    # fmt: off
    RIGHT_ALT_PRESSED  = 0b000000001
    LEFT_ALT_PRESSED   = 0b000000010
    RIGHT_CTRL_PRESSED = 0b000000100
    LEFT_CTRL_PRESSED  = 0b000001000
    SHIFT_PRESSED      = 0b000010000
    NUMLOCK_ON         = 0b000100000
    SCROLLLOCK_ON      = 0b001000000
    CAPSLOCK_ON        = 0b010000000
    ENHANCED_KEY       = 0b100000000
    # fmt: on


class ControlKeyState(enum.IntFlag):
    """
    TODO
    """

    right_alt = _F_ControlKeyState.RIGHT_ALT_PRESSED
    """
    TODO
    """

    left_alt = _F_ControlKeyState.LEFT_ALT_PRESSED
    """
    TODO
    """

    right_ctrl = _F_ControlKeyState.RIGHT_CTRL_PRESSED
    """
    TODO
    """

    left_ctrl = _F_ControlKeyState.LEFT_CTRL_PRESSED
    """
    TODO
    """

    shift = _F_ControlKeyState.SHIFT_PRESSED
    """
    TODO
    """

    numlock = _F_ControlKeyState.NUMLOCK_ON
    """
    TODO
    """

    scrolllock = _F_ControlKeyState.SCROLLLOCK_ON
    """
    TODO
    """

    capslock = _F_ControlKeyState.CAPSLOCK_ON
    """
    TODO
    """

    enhanced_key = _F_ControlKeyState.ENHANCED_KEY
    """
    TODO
    """


class _F_MouseButtonState(enum.IntFlag):
    # fmt: off
    FROM_LEFT_1ST_BUTTON_PRESSED = 0b00001
    RIGHTMOST_BUTTON_PRESSED     = 0b00010
    FROM_LEFT_2ND_BUTTON_PRESSED = 0b00100
    FROM_LEFT_3RD_BUTTON_PRESSED = 0b01000
    FROM_LEFT_4TH_BUTTON_PRESSED = 0b10000
    # fmt: on


class ConsoleInputMouseButtonState(enum.IntFlag):
    """
    TODO
    """

    left = _F_MouseButtonState.FROM_LEFT_1ST_BUTTON_PRESSED
    """
    TODO
    """

    right = _F_MouseButtonState.RIGHTMOST_BUTTON_PRESSED
    """
    TODO
    """

    middle = _F_MouseButtonState.FROM_LEFT_2ND_BUTTON_PRESSED
    """
    TODO
    """

    x1 = _F_MouseButtonState.FROM_LEFT_3RD_BUTTON_PRESSED
    """
    TODO
    """

    x2 = _F_MouseButtonState.FROM_LEFT_4TH_BUTTON_PRESSED
    """
    TODO
    """


class _E_MouseEventFlags(enum.IntEnum):
    # fmt: off
    MOUSE_MOVED    = 0b0001
    DOUBLE_CLICK   = 0b0010
    MOUSE_WHEELED  = 0b0100
    MOUSE_HWHEELED = 0b1000
    # fmt: on


class ConsoleInputMouseEventType(enum.IntEnum):
    """
    TODO
    """

    none = 0
    """
    TODO
    """

    move = _E_MouseEventFlags.MOUSE_MOVED
    """
    TODO
    """

    double_click = _E_MouseEventFlags.DOUBLE_CLICK
    """
    TODO
    """

    wheel_vertical = _E_MouseEventFlags.MOUSE_WHEELED
    """
    TODO
    """

    wheel_horizontal = _E_MouseEventFlags.MOUSE_HWHEELED
    """
    TODO
    """


class ConsoleInputMouseScrollDirection(enum.IntEnum):
    """
    TODO
    """

    forward = 1
    """
    TODO
    """

    backward = 2
    """
    TODO
    """

    left = 3
    """
    TODO
    """

    right = 4
    """
    TODO
    """


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

    input_mouse_events = _F_ConsoleModeInput.ENABLE_MOUSE_INPUT << 1
    """
    TODO
    """

    input_insert = _F_ConsoleModeInput.ENABLE_INSERT_MODE << 1
    """
    TODO
    """

    input_edit = _F_ConsoleModeInput.ENABLE_QUICK_EDIT_MODE << 1
    """
    TODO
    """

    input_extended_flags = _F_ConsoleModeInput.ENABLE_EXTENDED_FLAGS << 1
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
    "read_console_input",
    "set_console_mode",
    "ConsoleMode",
    "ConsoleInputEvent",
    "ConsoleInputFocusEvent",
    "ConsoleInputKeyEvent",
    "ConsoleInputMenuEvent",
    "ConsoleInputMouseEvent",
    "ConsoleInputResizeEvent",
]
