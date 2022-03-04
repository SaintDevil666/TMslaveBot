#!/usr/bin/python
# -*- coding: iso-8859-5 -*-
import sys
import asyncio
import requests
from datetime import datetime
from aiogram import Bot
import aioschedule as schedule
from bs4 import BeautifulSoup
from babel.dates import format_datetime
import config

bot = Bot(config.TOKEN)


class ErrorLogs(object):
    errs = []

    def flush(self):
        requests.post("https://api.telegram.org/bot" + config.TOKEN + "/sendMessage",
                      {"chat_id": 448741268, "text": "".join(self.errs)})
        self.errs = []

    def write(self, data):
        self.errs.append(str(data))


sys.stderr = ErrorLogs()


async def send_holidays():
    date = format_datetime(datetime.today(), 'd MMMM YYYY', locale='uk_UA')
    url = "https://www.unian.ua/lite/holidays"
    soup = BeautifulSoup(requests.get(url).text, features="html.parser")
    posts = soup.find('div', {'class': 'lite-background--all'}).findAll('a', {"class": "lite-background__link"})
    for post in posts:
        if post.getText().startswith("\n" + date):
            url = post['href']
            resp = requests.get(url)
            soup = BeautifulSoup(resp.text, features="html.parser")
            article = soup.find('div', {'class': 'article-text'})
            paragraph = article.findAll('p')[0]
            ad = paragraph.find('a', {"class": "read-also"})
            if ad:
                ad.decompose()
            hyperlink = paragraph.find('a')
            if hyperlink:
                hyperlink.replace_with(hyperlink.getText())
            text = paragraph.getText()
            cur = paragraph.next_element
            while not cur.name:
                cur = cur.next_element
            if cur.name == "p":
                text += "\n\n" + cur.getText()
            await bot.send_message(-1001247268742, text)
            break


if __name__ == "__main__":
    loop = asyncio.get_event_loop()

    schedule.every().day.at("6:01").do(send_holidays)
    schedule.every().tuesday.at("23:01").do(bot.send_sticker, chat_id=-1001247268742, sticker="CAACAgIAAxkBAAEKkbJg2J33eYHwNrmjAgJ8VYcqPO_GIgACGAEAApXcNhsZWSFEX9acniAE")
    
    while True:
        loop.run_until_complete(schedule.run_pending())
