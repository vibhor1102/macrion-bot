"""One Gateway listener, one destination, no remotely executable operations."""

import asyncio
from datetime import datetime, timezone
import logging
import os

from aiohttp import web
import discord

from .config import Config, ConfigError

LOG = logging.getLogger("macrion_jr")
REQUIRED_PERMISSIONS = ("view_channel", "send_messages", "embed_links")


def membership_embed(user, *, joined: bool, observed_at: datetime) -> discord.Embed:
    embed = discord.Embed(
        title="Member joined" if joined else "Member departed",
        colour=0x43A047 if joined else 0xEF6C00,
        timestamp=observed_at,
    )
    # Plain labels and disabled mentions prevent names from causing notifications.
    name = discord.utils.escape_markdown(str(user))[:200]
    embed.add_field(name="Username", value=name or "Unknown", inline=False)
    embed.add_field(name="User ID", value=str(user.id))
    embed.add_field(name="Account type", value="Bot" if user.bot else "Person")
    embed.set_footer(text="Observed by Macrion Jr. • Departures include leaves, kicks and bans")
    return embed


class MembershipLogger(discord.Client):
    def __init__(self, config: Config):
        intents = discord.Intents.none()
        intents.guilds = True
        intents.members = True
        super().__init__(
            intents=intents,
            member_cache_flags=discord.MemberCacheFlags.none(),
            chunk_guilds_at_startup=False,
            max_messages=None,
            allowed_mentions=discord.AllowedMentions.none(),
        )
        self.config = config
        self.destination = None
        self.connected = False

    async def setup_hook(self):
        channel = await self.fetch_channel(self.config.channel_id)
        if not isinstance(channel, discord.TextChannel) or channel.guild.id != self.config.guild_id:
            raise ConfigError("Log channel must be a text channel in the configured server.")
        self.destination = channel

    async def on_ready(self):
        self.connected = False
        guild = self.get_guild(self.config.guild_id)
        if guild is None:
            LOG.error("Configured server is unavailable to the bot.")
            await self.close()
            return
        # Use the Gateway's current channel/role state after each READY.
        channel = guild.get_channel(self.config.channel_id)
        member = guild.me
        if not isinstance(channel, discord.TextChannel) or member is None:
            LOG.error("Configured channel or bot membership is unavailable.")
            await self.close()
            return
        permissions = channel.permissions_for(member)
        if not all(getattr(permissions, name) for name in REQUIRED_PERMISSIONS):
            LOG.error("Log channel requires View Channel, Send Messages and Embed Links.")
            await self.close()
            return
        self.destination = channel
        self.connected = True
        LOG.info("Membership logger connected.")

    async def on_disconnect(self):
        self.connected = False

    async def on_resumed(self):
        self.connected = True

    async def on_member_join(self, member):
        if member.guild.id == self.config.guild_id:
            await self.record(member, joined=True)

    async def on_raw_member_remove(self, payload):
        # Unlike on_member_remove, this also works for uncached members.
        if payload.guild_id == self.config.guild_id:
            await self.record(payload.user, joined=False)

    async def record(self, user, *, joined):
        if self.destination is None:
            LOG.error("Membership event could not be delivered: destination unavailable.")
            return
        try:
            await self.destination.send(
                embed=membership_embed(user, joined=joined, observed_at=datetime.now(timezone.utc)),
                allowed_mentions=discord.AllowedMentions.none(),
            )
        except discord.HTTPException as error:
            # Provider response bodies can contain supplied data; don't log them.
            LOG.error("Membership delivery failed (HTTP %s, Discord code %s).", error.status, error.code)

    async def on_error(self, event_method, *args, **kwargs):
        LOG.error("Discord handler failed: %s", event_method)


def health_app(client):
    async def health(request):
        ready = client.connected and client.is_ready() and not client.is_closed()
        return web.json_response({"status": "ready" if ready else "starting"}, status=200 if ready else 503)

    app = web.Application(client_max_size=1024)
    app.router.add_get("/healthz", health)
    return app


async def run():
    config = Config.from_mapping(os.environ)
    client = MembershipLogger(config)
    runner = web.AppRunner(health_app(client), access_log=None)
    await runner.setup()
    try:
        await web.TCPSite(runner, "0.0.0.0", int(os.environ.get("PORT", "10000"))).start()
        async with client:
            await client.start(config.token)
    finally:
        await runner.cleanup()


def main():
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    logging.getLogger("discord").setLevel(logging.WARNING)
    try:
        asyncio.run(run())
    except KeyboardInterrupt:
        return
    except ConfigError as error:
        LOG.error("%s", error)
        raise SystemExit(1) from None
    except discord.PrivilegedIntentsRequired:
        LOG.error("Enable Server Members Intent in the Discord Developer Portal.")
        raise SystemExit(1) from None
    except Exception as error:
        # Never emit raw authentication failures, URLs, response bodies or tokens.
        LOG.error("Startup/connection failed (%s). Check credentials, channel access and network.", type(error).__name__)
        raise SystemExit(1) from None
