# rFlyingTower Bot

This bot is being developed to maybe help out the mods at https://www.reddit.com/r/flying/ one day.

## Installation
### 1. Install `poetry`
See https://python-poetry.org/docs/ for details.

### 2. Clone git repo
```
$ git clone https://github.com/kdknigga/rflying_tower_bot.git
```

### 3. Set up dependancies
```
$ cd rflying_tower_bot
$ poetry install
```

### 4. Get Reddit script credentials
See https://redditclient.readthedocs.io/en/latest/oauth/ for details.

### 5. Set up secrets in environment variables
```
$ export PRAW_CLIENT_ID="your_client_id_here"
$ export PRAW_CLIENT_SECRET="your_client_secret_here"
$ export PRAW_USERNAME="your_reddit_username_here"
$ export PRAW_PASSWORD="your_reddit_password_here"
$ export SUBREDDIT="the_name_of_a_subreddit_here"
```

### 6. Set up bot config wiki page
In your subreddit, create a wiki page called `botconfig/rflying_tower_bot`.  This will contain the rules the bot will follow in YAML format.  See example_rules.yaml for an example.

See https://www.reddit.com/wiki/wiki/#wiki_how_to_make_a_new_wiki_page for details on creating a new wiki page.

### 7. Run
```
$ poetry run python -m rflying_tower_bot
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
