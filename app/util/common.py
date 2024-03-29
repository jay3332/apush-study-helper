from __future__ import annotations

import asyncio
import datetime
import random
import re
from functools import wraps
from typing import (
    Any,
    Awaitable,
    Callable,
    Iterable,
    Mapping,
    TYPE_CHECKING,
    Type,
    overload,
)

from discord import PartialEmoji
from discord.ext.commands import Converter

from config import Emojis

if TYPE_CHECKING:
    from app.core import Context

__all__ = (
    'sentinel',
    'converter',
)

EMOJI_REGEX: re.Pattern[str] = re.compile(r'<(a)?:([a-zA-Z0-9_]{2,32}):([0-9]{17,25})>')
PLURALIZE_REGEX: re.Pattern[str] = re.compile(r'(?P<quantity>-?[0-9.,]+) (?P<thing>[a-zA-Z]+)\((?P<plural>i?e?s)\)')


# This exists for type checkers
class ConstantT:
    pass


def _create_sentinel_callback[V](v: V) -> Callable[[ConstantT], V]:
    def wrapper(_self: ConstantT) -> V:
        return v

    return wrapper


def sentinel(name: str, **dunders) -> ConstantT:
    attrs = {f'__{k}__': _create_sentinel_callback(v) for k, v in dunders.items()}
    return type(name, (ConstantT,), attrs)()


def converter[T](f: Callable[[Context, str], T]) -> Type[Converter[T] | T]:
    class Wrapper(Converter[T]):
        async def convert(self, ctx: Context, argument: str) -> T:
            return await f(ctx, argument)

    return Wrapper


def ordinal(number: int) -> str:
    """Convert a number to its ordinal representation."""
    if number % 100 // 10 != 1:
        if number % 10 == 1:
            return f"{number}st"

        if number % 10 == 2:
            return f"{number}nd"

        if number % 10 == 3:
            return f"{number}rd"

    return f"{number}th"


def cutoff(string: str, /, max_length: int = 64, *, exact: bool = False) -> str:
    """Cuts-off a string at a certain length, and if it has been cutoff, append "..." to it."""
    if len(string) <= max_length:
        return string

    offset = 0 if not exact else 3
    return string[:max_length - offset] + '...'


def pluralize(text: str, /) -> str:
    """Automatically finds words that need to be pluralized in a string and pluralizes it."""
    def callback(match):
        quantity = abs(float((q := match.group('quantity')).replace(',', '')))
        return f'{q} ' + match.group('thing') + (('', match.group('plural'))[quantity != 1])

    return PLURALIZE_REGEX.sub(callback, text)


def humanize_list(li: list[Any], *, joiner: str = 'and') -> str:
    """Takes a list and returns it joined."""
    if len(li) <= 2:
        return f' {joiner} '.join(li)

    return ", ".join(li[:-1]) + f", {joiner} {li[-1]}"


def humanize_small_duration(seconds: float, /) -> str:
    """Turns a very small duration into a human-readable string."""
    units = ('ms', 'μs', 'ns', 'ps')

    for i, unit in enumerate(units, start=1):
        boundary = 10 ** 3 * i

        if seconds > 1 / boundary:
            m = seconds * boundary
            m = round(m, 2) if m >= 10 else round(m, 3)

            return f"{m} {unit}"

    return "<1 ps"


def humanize_duration(seconds: int | float | datetime.timedelta, depth: int = 3):
    """Formats a duration (in seconds) into one that is human-readable."""
    if isinstance(seconds, datetime.timedelta):
        seconds = seconds.total_seconds()
    if seconds < 1:
        return '<1 second'

    m, s = divmod(seconds, 60)
    h, m = divmod(m, 60)
    d, h = divmod(h, 24)
    mo, d = divmod(d, 30)
    y, mo = divmod(mo, 12)

    if y > 100:
        return ">100 years"

    y, mo, d, h, m, s = [int(entity) for entity in (y, mo, d, h, m, s)]
    items = (y, 'year'), (mo, 'month'), (d, 'day'), (h, 'hour'), (m, 'minute'), (s, 'second')

    as_list = [f"{quantity} {unit}{'s' if quantity != 1 else ''}" for quantity, unit in items if quantity > 0]
    return humanize_list(as_list[:depth])


def insert_random_u200b(text: str, /) -> str:
    """Inserts random zero-width space characters into a string, usually to make them copy-paste proof."""
    return ''.join(c + random.randint(0, 4) * '\u200b' for c in text)


def executor_function[**P, R](func: Callable[P, R]) -> Callable[P, Awaitable[R]]:
    """Runs the decorated function in an executor"""
    @wraps(func)
    def wrapper(*args: P.args, **kwargs: P.kwargs) -> Awaitable[R]:
        return asyncio.to_thread(func, *args, **kwargs)

    return wrapper  # type: ignore


def expansion_list(entries: Iterable[str]) -> str:
    """Formats a list into expansion format."""
    entries = list(entries)
    emojis = Emojis.Expansion

    if len(entries) == 1:
        first, *lines = entries[0].splitlines()
        result = f'{emojis.single} {first}'

        if lines:
            result += '\n' + '\n'.join(f'{Emojis.space} {line}' for line in lines)

        return result

    result = []

    for i, entry in enumerate(entries):
        first, *lines = entry.splitlines()

        if i + 1 == len(entries):
            result.append(f'{emojis.last} {first}')
            result.extend(f'{Emojis.space} {line}' for line in lines)
            continue

        emoji = emojis.first if i == 0 else emojis.mid

        result.append(f'{emoji} {first}')
        result.extend(f'{emojis.ext} {line}' for line in lines)

    return '\n'.join(result)


def image_url_from_emoji(emoji: str | PartialEmoji) -> str:
    if isinstance(emoji, PartialEmoji):
        return emoji.url

    if match := EMOJI_REGEX.match(emoji):
        animated, _, id = match.groups()
        extension = 'gif' if animated else 'png'
        return f'https://cdn.discordapp.com/emojis/{id}.{extension}?v=1'
    else:
        code = '-'.join(format(ord(c), 'x') for c in emoji if c != '\ufe0f')
        return f'https://twemoji.maxcdn.com/v/latest/72x72/{code}.png'


def progress_bar(ratio: float, *, length: int = 8, u200b: bool = True, provider: type = Emojis.ProgressBars) -> str:
    # noinspection PyTypeChecker
    ratio = min(1, max(0, ratio))

    result = ''
    span = 1 / length

    # Pre-calculate spans
    quarter_span = span / 4
    half_span = span / 2
    high_span = 3 * quarter_span

    for i in range(length):
        lower = i / length

        if ratio <= lower:
            key = 'empty'
        elif ratio <= lower + quarter_span:
            key = 'low'
        elif ratio <= lower + half_span:
            key = 'mid'
        elif ratio <= lower + high_span:
            key = 'high'
        else:
            key = 'full'

        if i == 0:
            start = 'left'
        elif i == length - 1:
            start = 'right'
        else:
            start = 'mid'

        result += getattr(provider, f'{start}_{key}')

    if u200b:
        return result + "\u200b"

    return result


@overload
def pick[K, V](d: Mapping[str, V], /, *keys: str, **transform_keys: V) -> dict[str, V]:
    ...


@overload
def pick[K, V](d: Mapping[K, V], /, *keys: K) -> dict[K, V]:
    ...


def pick[K, V](d: Mapping[K, V], /, *keys: K, **transform_keys: V) -> dict[K, V]:
    """Picks keys from a dictionary and returns them in a new dictionary."""
    if transform_keys:
        return {transform_keys.get(k, k): v for k, v in d.items() if k in keys or k in transform_keys}
    return {k: v for k, v in d.items() if k in keys}
