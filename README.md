# Macrion Jr.

A small Discord bot for the Macrion server. It records member joins and departures
in one channel, with the username, user ID, account type and UTC observation time.
Departures include voluntary leaves, kicks and bans; the bot does not infer a cause.

There are no commands, settings screens, AI tools or remote management endpoints.
Configuration is three environment variables. Discord messages are the log; there
is no separate database. New features can be added to the code as needed.

## 1. Discord setup (browser)

1. Open the [Discord Developer Portal](https://discord.com/developers/applications)
   and create an application named **Macrion Jr.**
2. On **Bot**, enable **Server Members Intent**. Leave **Presence Intent** and
   **Message Content Intent** off. Generate a bot token and store it privately;
   never paste it into chat or Git. Keep **Public Bot** off for this personal bot.
3. Generate an installation URL using **OAuth2 → URL Generator**, selecting only
   the `bot` scope. Give it **View Channels**, **Send Messages** and **Embed Links**.
   Open the URL and install it into the Macrion server. No slash-command scope or
   Administrator permission is needed. If Installation settings require a public
   default link for a private bot, choose **None** there and use the OAuth2 URL.
4. Create a private text channel such as `#membership-log`. Allow the moderator
   role and the bot to view it, deny `@everyone` **View Channel**, and explicitly
   allow the bot **View Channel**, **Send Messages** and **Embed Links** there.
   The bot does not require **Read Message History**.
5. Enable Discord **User Settings → Advanced → Developer Mode**. Right-click the
   server and choose **Copy Server ID**; right-click the log channel and choose
   **Copy Channel ID**.

## 2. Render setup (browser)

Use one **Free Web Service**, not a background worker. Before creating another
service, check your existing workspace usage: Render's 750 free instance hours per
month are shared, so two continuously running free services will exceed it.
Leave existing services unchanged unless you intentionally replace one.

1. Open [Render](https://dashboard.render.com/), choose **New → Web Service**, and
   select **Public Git Repository** and enter
   `https://github.com/vibhor1102/macrion-bot`. This route does not require the
   Render GitHub integration or access to your other repositories.
2. Use these settings:

   | Setting | Value |
   | --- | --- |
   | Name | `macrion-bot` |
   | Branch | `main` |
   | Language/runtime | Python 3 |
   | Root directory | Leave blank |
   | Build command | `pip install -r requirements.txt` |
   | Start command | `python -m macrion_jr` |
   | Instance type | **Free** |
   | Health check path | `/healthz` |
   | Auto-deploy | Off; deploy deliberately after changes |

   `.python-version` selects the latest Python 3.14 patch. If Render has a
   `PYTHON_VERSION` override, remove it or select a released Python 3.14 version.
3. Add these variables in **Environment**:

   | Key | Value |
   | --- | --- |
   | `DISCORD_BOT_TOKEN` | Token from the Developer Portal |
   | `DISCORD_GUILD_ID` | Macrion server ID |
   | `DISCORD_LOG_CHANNEL_ID` | Membership log channel ID |

4. Deploy. Look for `Membership logger connected.` in the logs. Visit
   `https://YOUR-SERVICE.onrender.com/healthz`: it should return
   `{"status": "ready"}` with HTTP 200. A starting/disconnected bot returns 503;
   this checks the Discord connection rather than only the HTTP server.

`render.yaml` also records the intended free-service configuration. Follow the
manual public-repository steps above to bypass the GitHub integration.

## 3. UptimeRobot and live verification (browser)

1. In [UptimeRobot](https://dashboard.uptimerobot.com/), add an **HTTP(s)** monitor
   for `https://YOUR-SERVICE.onrender.com/healthz`. Use a five-minute interval if
   your account provides it, or another interval below Render's 15-minute idle
   threshold. No authentication or special headers are required.
2. Have a trusted person or a spare account join and leave the server. Check that
   both messages reach the private channel. The bot itself cannot perform this
   acceptance test, and an existing member at startup is not a new join.
3. After a manual Render redeploy, confirm health returns to 200 and repeat the
   event test if behaviour changed. Do not run a second local production listener.

Free hosting is best-effort: restarts, idle shutdown and quota suspension can
create gaps. Discord may resume a short interrupted session, but there is no
complete membership history to backfill after an extended outage. Delivery also
depends on channel permissions and Discord availability. Failed API sends are
reported by HTTP status/code; there is no durable retry queue or exactly-once
guarantee. Logs stay in Discord until someone deletes them.

## Local development

```bash
python3.14 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python -m unittest discover -s tests -v
```

For a local live run, supply the three variables through your terminal's secure
environment/secret facility, then run `.venv/bin/python -m macrion_jr`. The app does
not automatically load `.env`. Prefer a separate test bot/server; stop the hosted
instance before using its credentials locally. The HTTP port defaults to 10000
and follows Render's `PORT` variable when supplied.

## Security and operations

- The only public HTTP route is read-only `/healthz`; it returns no IDs, tokens,
  member data or configuration. There is no admin API or Python execution endpoint.
- Discord uses the bot token over HTTPS/WSS with normal certificate verification.
  Rotate a leaked token in the Developer Portal and update Render's environment.
- Only guild/member intents are enabled. Member and message caches are disabled;
  raw member-removal events record departures even for uncached users.
- Event handlers ignore other servers, and startup rejects a log channel belonging
  to another server. All outgoing mentions are disabled.
- Secrets belong in Render's Environment settings, never in `render.yaml`, commits,
  URLs, screenshots or support logs. `.env.example` contains placeholders only.

References: [Render Free](https://render.com/docs/free),
[Render environment variables](https://render.com/docs/configure-environment-variables),
[Discord Gateway events](https://docs.discord.com/developers/events/gateway-events),
[discord.py](https://discordpy.readthedocs.io/en/stable/).

## License

Copyright (C) 2026 Vibhor Goel.

Macrion Jr. is free software licensed under the GNU General Public License,
version 3 or (at your option) any later version (**GPL-3.0-or-later**), matching
Macrion's copyleft terms. See [LICENSE](LICENSE) for the complete terms.
This program is provided without warranty.
