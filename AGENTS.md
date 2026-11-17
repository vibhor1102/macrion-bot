# Macrion Jr.

This public GPL-3.0-or-later repository contains a small Discord bot for the Macrion community.
Keep the scope to requested features; currently it only records member joins and
departures. There is no AI integration, management API, dashboard or skill.

- Runtime: Python 3.14, discord.py and aiohttp. Start with `python -m macrion_jr`.
- Test with `.venv/bin/python -m unittest discover -s tests -v`.
- Configuration comes from the three environment variables in `.env.example`.
  Never commit tokens, print environment values, or include raw provider response
  bodies in logs. The app does not automatically load `.env` files.
- Only one production Gateway listener should run. Don't start the local bot with
  production credentials while the Render instance is running.
- Deployment targets Render Free Web Service, with no paid feature assumptions.
  Browser setup is allowed when requested by the user. Leave credential entry
  and environment-variable values to the user unless explicitly authorized.
- Keep dependencies pinned and the public HTTP surface to `/healthz`.
- Commit completed changes normally. The Android app and its private `.agents`
  repository live separately and do not need changes for this bot.
