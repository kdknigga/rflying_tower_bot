# rFlyingTower Bot

This bot is being developed to maybe help out the mods at https://www.reddit.com/r/flying/ one day.

## Installation
### 1. Install `uv`
See https://docs.astral.sh/uv/getting-started/installation/ for details.

### 2. Clone git repo
```
$ git clone https://github.com/kdknigga/rflying_tower_bot.git
```

### 3. Set up dependancies
```
$ cd rflying_tower_bot
$ uv sync
```

### 4. Get Reddit script credentials
See https://redditclient.readthedocs.io/en/latest/oauth/ for details.

### 5. Set up secrets in environment variables
```
$ export RFTB_PRAW_CLIENT_ID="your_client_id_here"
$ export RFTB_PRAW_CLIENT_SECRET="your_client_secret_here"
$ export RFTB_PRAW_USERNAME="your_reddit_username_here"
$ export RFTB_PRAW_PASSWORD="your_reddit_password_here"
$ export RFTB_SUBREDDIT="the_name_of_a_subreddit_here"
$ export RFTB_DB_CONNECTION_STRING="sqlite+aiosqlite:///:memory:" # Optional.  It keeps track of what actions have been done so they don't accidently get repeated.
$ export RFTB_LOG_HANDLERS="console" # Optional.  A comma-seperated list of places to send log messages.  Defaults to console, but discord is an option (with the correct additional configuration).
$ export RFTB_LOG_LEVEL="info" # Optional.  Can be debug, info, warning, error, or critical.
$ export RFTB_LOG_DISCORD_WEBHOOK_URL="your_discord_webhook_url_here" # Optional.  Only needed if RFTB_LOG_HANDLERS contains "discord".
$ export RFTB_LOG_DISCORD_BOT_NAME="your_discord_bot_name_here" # Optional.  Only used if RFTB_LOG_HANDLERS contains "discord".  Defaults to RFTB_PRAW_USERNAME.
$ export RFTB_LOG_DISCORD_BOT_AVATAR_URL="your_discord_bot_avatar_url_here" # Optional.  Only used if RFTB_LOG_HANDLERS contains "discord".
$ export RFTB_SENTRY_DSN="your_sentry_dsn" # Optional.  Enables Sentry logging
$ export RFTB_SENTRY_TRACE_RATE="0.1" # Optional.
$ export RFTB_SENTRY_PROFILE_RATE="0.1" # Optional.
$ export RFTB_ENVIRONMENT="development" # Optional.  This is for Sentry, mostly, currently
$ export RFTB_PRAW_OAUTH_URL="your_oauth_url_here" # Optional.  Used to point at an instance of Reddit not running at reddit.com.  This generally is only needed for deep development work.
```

or, put the secrets in a file called .env (see .env.example)

### 6. Set up bot config wiki page
In your subreddit, create a wiki page called `botconfig/rflying_tower_bot`.  This will contain the rules the bot will follow in YAML format.  See example_rules.yaml for an example.

See https://www.reddit.com/wiki/wiki/#wiki_how_to_make_a_new_wiki_page for details on creating a new wiki page.

### 7. Run
```
$ uv run python -m rflying_tower_bot
```

## Notes
* The user running the bot will need the following moderator permissions:
    * Manage Posts & Comments
        * To use removal reasons
    * Manage Mod Mail
        * To use removal reasons
    * Manage Flair
        * To add post flair templates
    * Manage Wiki Pages
        * To access the config wiki page
    * Manage Settings
        * To manage removal reasons
