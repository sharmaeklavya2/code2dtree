import sys
import os
from enum import IntEnum
from typing import NamedTuple, Optional, TextIO

TERM_ESC = '\033['
TERM_RESET = TERM_ESC + '0m'


class Color(IntEnum):
    black = 0
    red = 1
    green = 2
    yellow = 3
    blue = 4
    magenta = 5
    cyan = 6
    white = 7


class TermColorOptions(NamedTuple):
    fgColor: Optional[Color] = None
    bgColor: Optional[Color] = None
    bright: Optional[bool] = None


def getTermString(options: TermColorOptions) -> str:
    nums: list[str] = []
    if options.fgColor is not None:
        nums.append(str(30 + options.fgColor))
    if options.bgColor is not None:
        nums.append(str(40 + options.bgColor))
    if options.bright is not None:
        nums.append('1' if options.bright else '21')
    if not nums:
        return ''
    else:
        return TERM_ESC + ';'.join(nums) + 'm'


def termPrint(*args: object, options: Optional[TermColorOptions], file: TextIO = sys.stdout) -> None:
    if options is None:
        termString = ''
    else:
        termString = getTermString(options)
    if termString and os.isatty(file.fileno()):
        try:
            file.write(termString)
            print(*args, file=file, end='')
        finally:
            file.write(TERM_RESET + '\n')
    else:
        print(*args, file=file)
