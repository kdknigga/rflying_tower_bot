# rFlyingTower Bot - AI Coding Agent Instructions

## Project Overview

This is an **async Reddit moderation bot** built with `asyncpraw` that automates moderation tasks for r/flying. The bot reads rule configurations from a subreddit wiki page and runs three concurrent event loops to monitor different Reddit streams.

## Architecture

**Three Concurrent Streams** (see `__main__.py`):
- `ModLog`: Watches mod actions (flair changes) → triggers automated actions (comment, remove, ban)
- `PostStream`: Watches new submissions → creates "posterity comments" (locked copy of original post body)
- `Inbox`: Watches private messages from moderators → handles commands (`reload_config`, `dump_current_config`, `exit`)

**Configuration Flow**:
1. Rules stored in subreddit wiki page `botconfig/rflying_tower_bot` (YAML format)
2. `BotConfig.update_rules()` parses YAML using `pydantic-yaml` → `Ruleset` schema
3. On successful parse: syncs post flair templates and removal reasons to subreddit
4. On parse error: sends modmail to subreddit with error details

**Data Persistence** (`history.py`):
- SQLAlchemy async with `aiosqlite` backend
- Tracks completed actions by URL to prevent duplicate processing
- Default: in-memory database (override with `RFTB_DB_CONNECTION_STRING`)

## Key Conventions

**Environment Variables**: All config via `RFTB_*` env vars (see README.md). Use `dotenv` for local dev with `.env` file.

**Logging**:
- Supports multiple handlers: console (default), Discord webhook, Sentry
- Configure via `RFTB_LOG_HANDLERS`, `RFTB_LOG_LEVEL`, and handler-specific vars
- Each class uses `logging.getLogger(f"{__name__}.{self.__class__.__name__}")` pattern

**Schema Validation** (`ruleset_schemas.py`):
- All config uses Pydantic models with strict validation
- `FlairAction.valid_action()` validator enforces allowed actions and required arguments
- Example: `remove_with_reason` requires `argument`, `remove` does not

**Error Handling**:
- Reddit API errors caught in stream loops → log + set `stop_event` to gracefully shutdown
- Config parse errors → send modmail to subreddit, don't crash
- Rate limits → sleep 15 minutes (`await asyncio.sleep(900)`)

## Development Workflow

**Dependencies**: Managed with Poetry (`poetry install`)

**Run Bot**: `poetry run python -m rflying_tower_bot` (ensure `.env` configured)

**Code Quality Tools**:
- `ruff` for linting (pyupgrade + pydocstyle enabled, D203/D212 ignored)
- `mypy` with pydantic plugin for type checking
- `prospector` with bandit and mypy integration
- `pre-commit` hooks configured (see `.pre-commit-config.yaml`)

**Testing**:
- Run: `poetry run pytest` or `poetry run pytest-cov` for coverage
- Uses `pytest-asyncio` for async tests, `pytest-mock` for mocking
- Currently minimal test coverage (only version test exists in `tests/test_rflying_tower_bot.py`)

**Version Bumping**: Uses `poetry-bumpversion` to update version in `__init__.py` and test file

## Critical Integration Points

**Reddit API** (via `asyncpraw`):
- All Reddit interactions use shared `BotConfig.reddit` instance
- Must distinguish + approve/sticky bot comments: `await comment.mod.distinguish(sticky=True)`
- Removal reasons require both `reason_id` and sending message: `post.mod.remove(reason_id=...) + post.mod.send_removal_message(...)`

**Flair Actions** (`modlog.py`):
- Triggered when mod applies flair to post
- Actions: `comment` (distinguished/stickied), `remove`, `remove_with_reason`
- Example rule in `example_rules.yaml`: `'DPE report'` → creates comment warning to be nice

**Posterity Comments** (`post_stream.py`):
- Captures original post body in distinguished, locked comment
- Truncates at 9500 chars (Reddit's 10k limit, leaving room for header/footer)
- Skip if author in `ignore_users` list or already processed (checked via `history.check()`)

## Common Patterns

**Async Context**: All file operations and Reddit API calls are async. Use `async with` for sessions.

**History Tracking**: Before processing, always check `await config.history.check(item.permalink, "action_name")`. After completion, call `await config.history.add(item.permalink, "action_name")`.

**Stream Pause Pattern**: All streams use `pause_after=N` parameter and check for `None` to periodically break and verify `stop_event` isn't set.
