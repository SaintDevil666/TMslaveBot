#!/usr/bin/python
# -*- coding: utf8 -*-
import os
import sys
import random
import requests
import asyncpraw
import asyncio
import pymongo
from aiogram import Bot
from datetime import datetime
from aiogram.dispatcher import Dispatcher
from aiogram.utils import executor, exceptions
from aiogram.contrib.middlewares.logging import LoggingMiddleware
from bs4 import BeautifulSoup
# from babel.dates import format_datetime
import config

bot = Bot(config.TOKEN)
dp = Dispatcher(bot)
dp.middleware.setup(LoggingMiddleware())

db = pymongo.MongoClient("mongodb://localhost:27017/").TMslave

cached_last_id = {
}


class ErrorLogs(object):
    errs = []

    def flush(self):
        requests.post("https://api.telegram.org/bot" + config.TOKEN + "/sendMessage",
                      {"chat_id": config.ADMIN_ID, "text": "".join(self.errs)})
        self.errs = []

    def write(self, data):
        self.errs.append(str(data))


sys.stderr = ErrorLogs()

'''
last_holidays = {
    "date": None,
    "text": ""
}
@dp.message_handler(commands=["holidays"])
async def send_holidays(message):
    date = format_datetime(datetime.today(), 'd MMMM YYYY', locale='uk_UA')
    if last_holidays['date'] == date:
        await bot.send_message(message.chat.id, last_holidays['text'])
        return
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
            await bot.send_message(message.chat.id, text)
            last_holidays['date'] = date
            last_holidays['text'] = text
            break
'''


@dp.message_handler(commands=["roll"])
async def roll_list(message):
    if message.chat.id == config.GROUP_ID:
        await bot.send_message(message.chat.id, "\n".join(random.sample(config.GROUP_LIST, len(config.GROUP_LIST))))


@dp.message_handler(commands=["cat"])
async def random_cat(message):
    path = ""
    try:
        reddit = asyncpraw.Reddit(**config.REDDIT)
        subreddit = reddit.subreddit('cats')
        cat = (await (await subreddit).random()).url
        path = "c" + str(random.randrange(1000)) + ".jpg"
        wf = open(path, 'wb')
        wf.write(requests.get(cat).content)
        await reddit.close()
        wf.close()
        wr = open(path, 'rb')
        await bot.send_photo(message.chat.id, (path, wr))
        wr.close()
        os.remove(path)
    except:
        os.remove(path)
        asyncio.ensure_future(random_cat(message))


@dp.message_handler(commands=["komaru"])
async def random_komaru(message):
    global cached_last_id
    while True:
        i = random.randint(3, cached_last_id[config.KOMARU_COLLECTION_USERNAME])
        try:
            await bot.copy_message(from_chat_id=config.KOMARU_COLLECTION_ID, chat_id=message.chat.id, message_id=i)
        except exceptions.BadRequest:
            continue
        break


@dp.channel_post_handler(content_types=["animation", "video/mp4"])
async def new_cat(post):
    if post.chat.id == config.KOMARU_COLLECTION_ID:
        await bot.send_animation(config.GROUP_ID, post.animation.file_id)
        global cached_last_id
        cached_last_id[config.KOMARU_COLLECTION_USERNAME] = post.message_id


def get_last_id(source):
    try:
        resp = requests.get("https://xn--r1a.website/s/" + source)
        soup = BeautifulSoup(resp.text, features="html.parser")
        last_post = soup.find_all('div', {'class': 'tgme_widget_message'})[-1]
        return int(last_post['data-post'].split('/')[-1])
    except IndexError:
        return get_last_id(source)


@dp.message_handler(commands=["anek"])
async def random_anecdote(message):
    global cached_last_id
    source = random.choice(config.ANECDOTE_SOURCES)
    while True:
        i = random.randrange(2, cached_last_id[source])
        resp = requests.get("https://t.me/" + source + "/" + str(i))
        soup = BeautifulSoup(resp.text, features="html.parser")
        soup.find()
        text = soup.find('meta', {'name': 'twitter:description'})
        if text:
            caption = text['content']
            if not (('http' in caption) or ('/' in caption) or ('@' in caption) or caption == ""):
                try:
                    await bot.send_message(message.chat.id, caption)
                except exceptions.BadRequest:
                    continue
                break


@dp.message_handler(commands=["pussy_reg"])
async def register_user(message):
    global db
    collection = str(message.chat.id)
    query = {"id": str(message["from"]["id"])}
    if not db[collection].find_one(query):
        query['name'] = message['from']['first_name'] + (
            (" " + message['from']['last_name']) if message['from']['last_name'] else "")
        query['username'] = message['from']['username'] or ""
        query['count'] = 0
        query['type'] = "user"
        db[collection].insert_one(query)
        await bot.send_message(message.chat.id, "Ти успішно зареєстрований(-а)!",
                               reply_to_message_id=message.message_id)
    else:
        await bot.send_message(message.chat.id, "Ти уже в грі!", reply_to_message_id=message.message_id)


@dp.message_handler(commands=["pussy_me"])
async def pussy_me(message):
    collection = str(message.chat.id)
    query = {"type": "user", "id": str(message['from']['id'])}
    user = db[collection].find_one(query)
    if not user:
        await bot.send_message(message.chat.id, "Ти не зареєстрований(-а) в грі!", reply_to_message_id=message.message_id)
    else:
        if user['count'] % 10 == 1:
            plural = "раз"
        elif 5 <= user['count'] % 100 <= 20:
            plural = "разів"
        else:
            plural = "рази"
        await bot.send_message(message.chat.id, f"Ти був(-ла) кіскою дня {user['count']} {plural}!",
                               reply_to_message_id=message.message_id)


@dp.message_handler(commands=["pussy_top"])
async def pussy_top(message):
    collection = str(message.chat.id)
    query = {"type": "user"}
    users = list(db[collection].find(query))
    for i in range(len(users) - 1):
        for j in range(len(users) - 2):
            if users[j]['count'] < users[j + 1]['count']:
                temp = users[j]
                users[j] = users[j + 1]
                users[j + 1] = temp

    text = "<u><i>Топ-10 кісок:</i></u>\n"

    symbol = ["🥇", "🥈", "🥉"]
    for i in range(min(10, len(users))):
        if users[i]['count'] % 10 == 1:
            plural = "раз"
        elif 5 <= users[i]['count'] % 100 <= 20:
            plural = "разів"
        else:
            plural = "рази"
        text += (symbol[i] if i < 3 else (str(i + 1) + ". ")) + "<b>" + \
                ((users[i]['username'] or "") or users[i]['name']) + "</b> - <i>" + str(
            users[i]['count']) + " " + plural + "</i>\n"
    text += f"\nВсього учасників: {len(users)}"
    await bot.send_message(message.chat.id, text, parse_mode="HTML")


@dp.message_handler(commands=["pussy"])
async def choose_pussy(message):
    collection = str(message.chat.id)
    query = {"type": "result"}
    prev_winner = db[collection].find_one(query)

    query = {"type": "user"}
    users = list(db[collection].find(query))

    now = datetime.fromtimestamp(datetime.now().timestamp() + 3600)
    last = datetime.fromtimestamp(prev_winner['date'] if prev_winner else 0)
    if (now.year > last.year) or (now.month > last.month) or (now.day > last.day):
        new_winner = random.choice(users)

        query = {"type": "result"}
        update = {"$set": {
            "winner": new_winner['id'],
            "date": now.timestamp()
        }}
        db[collection].update_one(query, update, upsert=True)

        query = {"type": "user", "id": new_winner["id"]}
        update = {"$inc": {"count": 1}}
        db[collection].update_one(query, update)

        await bot.send_message(message.chat.id,
                               "Сьогодні кіска дня - " + (
                                   ("@" + new_winner['username']) if new_winner["username"] else new_winner[
                                       'name']) + "!")
        await bot.send_sticker(message.chat.id,
                               "CAACAgUAAxkBAAEBfWxg1ikMdDsxNAccPVrQTi7KhFz9_QAC2gIAAoeTeFbh1He2hSXcMiAE")
    else:
        for user in users:
            if user["id"] == prev_winner["winner"]:
                await bot.send_message(message.chat.id,
                                       "Сьогодні кіскою дня уже обрано " + (
                                               (user['username'] or "") or user['name']) + "!")
                break


@dp.message_handler(commands=["reverse"])
async def reverse_video(message):
    if message.reply_to_message:
        path = "temp/input" + str(int(random.random() * 10000)) + ".mp4"
        try:
            if message.reply_to_message.video:
                await bot.download_file_by_id(file_id=message.reply_to_message.video.file_id, destination=path, timeout=60)
            elif message.reply_to_message.animation:
                await bot.download_file_by_id(file_id=message.reply_to_message.animation.file_id, destination=path, timeout=60)
            else:
                await bot.send_message(message.chat.id, "Реплайни командою на відео або гіфку!",
                                       reply_to_message_id=message.message_id)
                return
        except asyncio.exceptions.TimeoutError:
            await bot.send_message(message.chat.id, "TimeoutError: took too much time to download",
                                   reply_to_message_id=message.message_id)
            os.remove(path)
            return
        new_path = "temp/output" + str(random.randrange(1000)) + ".mp4"
        os.system("ffmpeg -loglevel panic -i " + path + " -vf reverse " + new_path)
        await bot.send_animation(message.chat.id, animation=open(new_path, 'rb'))
        os.remove(path)
        os.remove(new_path)
        return
    await bot.send_message(message.chat.id, "Реплайни командою на відео або гіфку!",
                           reply_to_message_id=message.message_id)


@dp.message_handler(commands=["postirony"])
async def postirony(message):
    if message.reply_to_message:
        if message.reply_to_message.photo:
            path = "temp/input" + str(int(random.random() * 10000)) + ".jpg"
            try:
                await bot.download_file_by_id(file_id=message.reply_to_message.photo[-1].file_id, destination=path,
                                              timeout=60)
            except asyncio.exceptions.TimeoutError:
                await bot.send_message(message.chat.id, "TimeoutError: took too much time to download file",
                                       reply_to_message_id=message.message_id)
                os.remove(path)
                return
            try:
                text = message.text.split(" ", maxsplit=1)[1]
            except IndexError:
                await bot.send_message(message.chat.id, "А текст я сам вигадати маю?",
                                       reply_to_message_id=message.message_id)
                return
            meme_path = postironic(path, text)
            await bot.send_photo(message.chat.id, photo=open(meme_path, 'rb'))
            os.remove(path)
            os.remove(meme_path)
            return
    await bot.send_message(message.chat.id, "Реплайни командою на картинку!", reply_to_message_id=message.message_id)


def postironic(path, text):
    name = "temp/output" + str(int(random.random() * 10000)) + '.jpg'
    os.system(f"ffmpeg -i {path} -filter_complex \"[0]drawtext=fontfile=materials/Lobster.ttf:text='{text}': fontsize=(h/12): fontcolor=black: x=(w-text_w)/2: y=(h*0.9)[meme];"
              f"[meme]drawtext=fontfile=materials/Lobster.ttf:text='{text}': fontsize=(h/12): fontcolor=white: x=(w-text_w)/2: y=(h*0.9)-3[meme]\" -map [meme] -y {name}")
    return name


@dp.message_handler(commands=["demotivator"])
async def demotivators(message):
    if message.reply_to_message:
        if message.reply_to_message.photo:
            path = "temp/input" + str(int(random.random() * 10000)) + ".jpg"
            try:
                await bot.download_file_by_id(file_id=message.reply_to_message.photo[-1].file_id, destination=path,
                                              timeout=60)
            except asyncio.exceptions.TimeoutError:
                await bot.send_message(message.chat.id, "TimeoutError: took too much time to download file.",
                                       reply_to_message_id=message.message_id)
                os.remove(path)
                return
            try:
                text = message.text.split(" ", maxsplit=1)[1]
            except IndexError:
                await bot.send_message(message.chat.id, "А текст я сам вигадати маю?",
                                       reply_to_message_id=message.message_id)
                return
            captions = text.split("\n\n")
            for caption in captions:
                caption = caption.split("\n")
                if len(caption) == 2:
                    title, plain = caption
                else:
                    title = caption[0]
                    plain = ''
                meme_path = demotivator_generator(path, title, plain)
                os.remove(path)
                path = meme_path
            await bot.send_photo(message.chat.id, open(path, 'rb'))
            os.remove(path)
            return
        elif (message.reply_to_message.video or message.reply_to_message.animation) and (message['from']['id'] == config.ADMIN_ID or message['chat']['id'] == config.GROUP_ID):
            path = "temp/input" + str(int(random.random() * 10000)) + ".mp4"
            try:
                if message.reply_to_message.video:
                    await bot.download_file_by_id(file_id=message.reply_to_message.video.file_id, destination=path,
                                                  timeout=60)
                elif message.reply_to_message.animation:
                    await bot.download_file_by_id(file_id=message.reply_to_message.animation.file_id, destination=path,
                                                  timeout=60)
            except asyncio.exceptions.TimeoutError:
                await bot.send_message(message.chat.id, "TimeoutError: took too much time to download file.",
                                       reply_to_message_id=message.message_id)
                os.remove(path)
                return
            try:
                text = message.text.split(" ", maxsplit=1)[1]
            except IndexError:
                await bot.send_message(message.chat.id, "А текст я сам вигадати маю?",
                                       reply_to_message_id=message.message_id)
                return
            captions = text.split("\n\n")
            for caption in captions:
                caption = caption.split("\n")
                if len(caption) == 2:
                    title, plain = caption
                else:
                    title = caption[0]
                    plain = ''
                meme_path = demotivator_video(path, title, plain)
                os.remove(path)
                path = meme_path
            await bot.send_animation(message.chat.id, open(path, 'rb'))
            os.remove(path)
            return
    await bot.send_message(message.chat.id, "Реплайни командою на картинку, гіфку або відео!", reply_to_message_id=message.message_id)


def demotivator_generator(path='', title_text='', plain_text=''):
    filter_complex = []
    if path != '':
        filter_complex = ["[1]scale=480:320[inner]", "[0][inner]overlay=60:40[meme]"]
    filter_complex.append(f"[{'meme' if path != '' else '0'}]drawtext=fontfile=materials/TimesNewRoman.ttf:text='{title_text}':fontsize=40:fontcolor=white:x=(w-text_w)/2:y=385[meme]")
    if plain_text:
        filter_complex.append(f"[meme]drawtext=fontfile=materials/TimesNewRoman.ttf:text='{plain_text}': fontsize=25: fontcolor=white: x=(w-text_w)/2: y=440[meme]")
    name = "temp/output" + str(int(random.random() * 10000)) + '.jpg'
    command = f"ffmpeg -i materials/template.jpg{f' -i {path}' if path else ''} -filter_complex \"{';'.join(filter_complex)}\" -map [meme] -y {name}"
    os.system(command)
    return name


def demotivator_video(path, title_text, plain_text=""):
    template = demotivator_generator(title_text=title_text, plain_text=plain_text)
    name = "temp/output" + str(int(random.random() * 10000)) + '.mp4'
    os.system(f'ffmpeg -loglevel panic -loop 1 -i {template} -vf "movie={path},scale=480:320[inner];[in][inner]overlay=60:40:shortest=1[out]" -y {name}')
    os.remove(template)
    return name


for channel in config.ANECDOTE_SOURCES:
    cached_last_id[channel] = get_last_id(channel)
cached_last_id[config.KOMARU_COLLECTION_USERNAME] = get_last_id(config.KOMARU_COLLECTION_USERNAME)

executor.start_polling(dp)
