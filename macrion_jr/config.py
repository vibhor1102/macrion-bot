# Copyright (C) 2026 Vibhor Goel
# SPDX-License-Identifier: GPL-3.0-or-later

"""The bot's three required environment variables."""

from dataclasses import dataclass, field


class ConfigError(ValueError):
    pass


def snowflake(value: str) -> int:
    if not isinstance(value, str) or not value.isascii() or not value.isdecimal():
        raise ConfigError("Discord IDs must contain ASCII digits only.")
    result = int(value)
    if not 0 < result < 2**64:
        raise ConfigError("Discord ID is outside the supported range.")
    return result


@dataclass(frozen=True)
class Config:
    token: str = field(repr=False)
    guild_id: int
    channel_id: int

    @classmethod
    def from_mapping(cls, data):
        token = data.get("DISCORD_BOT_TOKEN", "")
        if not token or not token.isascii() or any(ord(c) < 33 or ord(c) > 126 for c in token):
            raise ConfigError("DISCORD_BOT_TOKEN must be set without whitespace.")
        return cls(
            token,
            snowflake(data.get("DISCORD_GUILD_ID", "")),
            snowflake(data.get("DISCORD_LOG_CHANNEL_ID", "")),
        )
