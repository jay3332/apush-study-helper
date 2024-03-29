from os import getenv as env
from platform import system
from typing import Collection

import discord
from discord import AllowedMentions
from dotenv import load_dotenv

load_dotenv()

__all__ = (
    'beta',
    'name',
    'version',
    'description',
    'owner',
    'default_prefix',
    'allowed_mentions',
    'Colors',
    'DatabaseConfig',
    'Emojis',
    'token',
)

beta: bool = system() != 'Linux'

name: str = 'AP Study Helper'
version: str = '0.0.0'
description: str = 'APUSH study helper'

# An ID or list of IDs
owner: Collection[int] | int = 414556245178056706
default_prefix: Collection[str] | str = ',,'
token: str = env('DISCORD_TOKEN' if not beta else 'DISCORD_STAGING_TOKEN')

default_permissions: int = 414531833025
support_server = 'https://discord.gg/BjzrQZjFwk'  # caif
# support_server = 'https://discord.gg/bpnedYgFVd'  # unnamed bot testing
website = 'https://jay3332.tech'

allowed_mentions: AllowedMentions = AllowedMentions.none()
allowed_mentions.users = True


class _RandomColor:
    def __get__(self, *_) -> int:
        return discord.Color.random().value


class Colors:
    primary: int = 0x6199f2
    secondary: int = 0x6199f2
    success: int = 0x17ff70
    warning: int = 0xfcba03
    error: int = 0xff1759


class DatabaseConfig:
    name: str = 'ap_study_helper' if beta else 'lambda_util'
    user: str | None = None if beta else 'postgres'
    host: str | None = 'localhost'
    port: int | None = None
    password: str | None = None if beta else env('DATABASE_PASSWORD')


class Emojis:
    loading = '<a:l:825862907626913842>'
    space = '<:s:940748421701185637>'
    arrow = '<:a:831333449562062908>'

    enabled = '<:e:939549340458954762>'
    disabled = '<:d:939549360570662952>'
    neutral = '<:n:838593591965384734>'

    class Arrows:
        previous: str = '\u25c0'
        forward: str = '\u25b6'
        first: str = '\u23ea'
        last: str = '\u23e9'

    class Expansion:
        first = '<:x:968651020097945811>'
        mid = '<:x:968652421721120828>'
        last = '<:x:968652421700124723>'
        ext = '<:x:968653920106872842>'
        single = standalone = '<:x:968652421377167371>'

    class ProgressBars:
        left_empty = '<:p:937082616333602836>'
        left_low = '<:p:937082634046173194>'
        left_mid = '<:p:937082669068595300>'
        left_high = '<:p:937082728376045598>'
        left_full = '<:p:937082777927561297>'

        mid_empty = '<:p:937082833107828786>'
        mid_low = '<:p:937082868226752552>'
        mid_mid = '<:p:937082902880083988>'
        mid_high = '<:p:937082944655351860>'
        mid_full = '<:p:937082993057595473>'

        right_empty = '<:p:937083054340595803>'
        right_low = '<:p:937083097969754193>'
        right_mid = '<:p:937083245173026887>'
        right_high = '<:p:937083276827439164>'
        right_full = '<:p:937083328648056862>'
