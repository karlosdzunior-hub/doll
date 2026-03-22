# Микрокапитализм: Жизнь на 1 доллар

A production Telegram bot for an economic simulation game. Players start with $1 and must build businesses, manage resources, and navigate a dynamic market to grow their wealth.

## Architecture

- **Language:** Python 3.12
- **Framework:** aiogram 3.x (async Telegram Bot API)
- **Database:** SQLite (`game.db`) — PostgreSQL-ready schema
- **Entry point:** `bot.py`

## Project Layout

```
bot.py          — Main entry point, polling loop, background tasks
config.py       — Game configuration (BotConfig dataclass)
db.py           — Database layer (all CRUD operations)
handlers/
  main.py       — All command & callback handlers
services/
  energy.py     — Energy regeneration logic
  market.py     — Dynamic pricing & NPC trades
  events.py     — Random global events
  chat.py       — Group chat XP/level logic
utils.py        — Helper functions
game.db         — SQLite database
```

## Environment Variables

| Secret      | Description                          |
|-------------|--------------------------------------|
| `BOT_TOKEN` | Telegram Bot API token from @BotFather |

## Workflow

- **Start application** — runs `python bot.py` (console output, no web port)

## Game Features

- Economic loop: produce resources → sell on market → buy more businesses
- Energy system with regeneration over time
- Dynamic market prices with NPC traders
- Monetization via Telegram Stars
- Referral system and group chat leaderboards
- Random global events (booms, crashes)

## Database Migration Notes

The initial `game.db` from the GitHub import had an older schema missing energy-related columns. These were added via migration:
- `energy`, `max_energy`, `last_energy_update`, `boost_expire`, `shield_active`, `lottery_tickets` on the `users` table
