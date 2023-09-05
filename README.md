# web-scrapper-noti-telegram
Don't want to keep looking at websites? This script will do it for you.

## Why
Well, sometimes you are eager to know what happens to your request, your property, or even your lawsuit. But, then, the only way to know "electronically" is via keep looking at the websites. 

I'm lazy, and that's why I created a "simple" script to do it for me.

## How (AKA installation)

You need:
1. A computer/server running Linux-based OS continuously. I use Linux Mint. Pi should be okay I guess.
2. A Telegram account and a bot.

### Command
0. [Install Python 3](https://www.python.org/downloads/)
1. Install required libs and create folders:

```bash
pip install facebook_scraper pyquery python-dotenv asyncio requests playwright
playwright install
mkdir -p /etc/projects/webscrape_noti && mkdir -p /var/projects/webscrape_noti
```

2. Copy [`webscrape_noti.py`](./webscrape_noti.py) to `/usr/local/bin`.
3. [Get your Telegram Bot ID, its credential, and your chat room ID.](https://core.telegram.org/bots/features#botfather)
4. Setup `.env` file by creating `/etc/projects/webscrape_noti/.env` file from [`sample.env`](./sample.env)
5. For some reason, the `coj.go.th` domain does not register its certificate properly. [Copy their web certificate](https://www.instructables.com/How-to-Download-the-SSL-Certificate-From-a-Website/) to `/etc/projects/webscrape_noti/coj.go.th.pem`.
6. Test run: `python3 /usr/local/bin/webscrape_noti.py`.
7. Set up cron to run this command: `python3 /usr/local/bin/webscrape_noti.py >> /var/projects/webscrape_noti/cron.log 2>&1`

## License

See [LICENSE](./LICENSE)

## PR, Issue, etc.

I use this program for my personal benefit. So, you may fork and stuff; I might not accept your PR if it does not fit my personal interest though.
