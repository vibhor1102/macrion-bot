# Copyright (C) 2026 Vibhor Goel
# SPDX-License-Identifier: GPL-3.0-or-later

from types import SimpleNamespace
import unittest
from unittest.mock import AsyncMock, Mock

from aiohttp.test_utils import TestClient, TestServer
import discord

from macrion_jr.bot import MembershipLogger, health_app
from macrion_jr.config import Config, ConfigError


CONFIG = Config("test-token-not-a-real-secret", 100, 200)


class ConfigTests(unittest.TestCase):
    def test_invalid_settings_do_not_echo_credentials(self):
        secret = "fake-secret-never-print"
        for bad_id in ("../123", "１２３", "0", str(2**64)):
            with self.subTest(value=bad_id), self.assertRaises(ConfigError) as caught:
                Config.from_mapping({"DISCORD_BOT_TOKEN": secret, "DISCORD_GUILD_ID": bad_id, "DISCORD_LOG_CHANNEL_ID": "200"})
            self.assertNotIn(secret, str(caught.exception))
        self.assertNotIn(CONFIG.token, repr(CONFIG))


class BotTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.bot = MembershipLogger(CONFIG)
        await self.bot.__aenter__()
        self.bot.destination = SimpleNamespace(send=AsyncMock())

    async def asyncTearDown(self):
        await self.bot.close()

    async def test_only_configured_server_is_logged_and_mentions_are_disabled(self):
        user = SimpleNamespace(id=300, bot=False, guild=SimpleNamespace(id=999))
        await self.bot.on_member_join(user)
        await self.bot.on_raw_member_remove(SimpleNamespace(guild_id=999, user=user))
        self.bot.destination.send.assert_not_awaited()
        user.guild.id = CONFIG.guild_id
        await self.bot.on_member_join(user)
        self.bot.destination.send.assert_awaited_once()
        sent = self.bot.destination.send.call_args.kwargs
        self.assertEqual(sent["embed"].title, "Member joined")
        self.assertEqual(sent["allowed_mentions"].to_dict(), {"parse": []})

    async def test_real_gateway_parser_delivers_uncached_departure_once(self):
        events = []
        self.bot._connection.dispatch = lambda name, *args: events.append((name, args))
        self.bot._connection.parse_guild_member_remove({
            "guild_id": str(CONFIG.guild_id),
            "user": {"id": "300", "username": "Departing user", "discriminator": "0", "avatar": None},
        })
        self.assertEqual([name for name, _ in events], ["raw_member_remove"])
        await self.bot.on_raw_member_remove(events[0][1][0])
        self.bot.destination.send.assert_awaited_once()
        embed = self.bot.destination.send.call_args.kwargs["embed"]
        self.assertEqual(embed.title, "Member departed")
        self.assertIn("300", [field.value for field in embed.fields])

    async def test_channel_from_another_server_rejected_at_startup(self):
        channel = Mock(spec=discord.TextChannel)
        channel.guild.id = 999
        self.bot.fetch_channel = AsyncMock(return_value=channel)
        with self.assertRaises(ConfigError):
            await self.bot.setup_hook()

    async def test_missing_send_permission_stops_bot(self):
        channel = Mock(spec=discord.TextChannel)
        channel.permissions_for.return_value = discord.Permissions(view_channel=True, embed_links=True)
        self.bot.get_guild = Mock(return_value=SimpleNamespace(get_channel=lambda _: channel, me=object()))
        self.bot.close = AsyncMock()
        with self.assertLogs("macrion_jr", level="ERROR"):
            await self.bot.on_ready()
        self.bot.close.assert_awaited_once()
        self.assertFalse(self.bot.connected)

    async def test_delivery_error_does_not_log_response_body(self):
        error = discord.Forbidden(SimpleNamespace(status=403, reason="Forbidden"), {"code": 50013, "message": "sensitive-response-body"})
        self.bot.destination.send.side_effect = error
        with self.assertLogs("macrion_jr", level="ERROR") as logs:
            await self.bot.record(SimpleNamespace(id=300, bot=False), joined=False)
        self.assertNotIn("sensitive-response-body", " ".join(logs.output))
        self.assertIn("403", " ".join(logs.output))

    async def test_disconnect_marks_health_unready(self):
        self.bot.connected = True
        await self.bot.on_disconnect()
        self.assertFalse(self.bot.connected)
        await self.bot.on_resumed()
        self.assertTrue(self.bot.connected)

    def test_runtime_does_not_subscribe_to_message_content_or_cache_members(self):
        self.assertTrue(self.bot.intents.members)
        self.assertTrue(self.bot.intents.guilds)
        self.assertFalse(self.bot.intents.message_content)
        self.assertFalse(self.bot.intents.presences)
        self.assertEqual(self.bot._connection.member_cache_flags.value, 0)


class HealthTests(unittest.IsolatedAsyncioTestCase):
    async def test_real_http_health_has_no_control_routes_or_private_data(self):
        state = SimpleNamespace(connected=False, is_ready=lambda: True, is_closed=lambda: False)
        async with TestClient(TestServer(health_app(state))) as client:
            response = await client.get("/healthz")
            self.assertEqual(response.status, 503)
            self.assertEqual(await response.json(), {"status": "starting"})
            state.connected = True
            response = await client.get("/healthz")
            self.assertEqual(response.status, 200)
            self.assertEqual(await response.json(), {"status": "ready"})
            self.assertEqual((await client.post("/healthz")).status, 405)
            self.assertEqual((await client.get("/admin")).status, 404)


if __name__ == "__main__":
    unittest.main()
