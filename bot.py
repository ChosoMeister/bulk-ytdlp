import os
import time
import math
import shutil
import asyncio
import random
import shlex
from urllib.parse import unquote
from urllib.error import HTTPError
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup, CallbackQuery, Message
from pyrogram.errors import BadRequest
from hachoir.metadata import extractMetadata
from hachoir.parser import createParser
from typing import Tuple
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Configs
API_HASH = os.environ.get('API_HASH')  # Api hash
APP_ID = int(os.environ.get('APP_ID'))  # Api id/App id
BOT_TOKEN = os.environ.get('BOT_TOKEN')  # Bot token
OWNER_ID = os.environ.get('OWNER_ID')  # Your telegram id
BUTTONS = bool(os.environ.get('BUTTONS', False))  # Upload mode

# Buttons
START_BUTTONS = [
    [
        InlineKeyboardButton("Source", url="https://github.com/ChosoMeister/bulk-ytdlp"),
        InlineKeyboardButton("MyWebsite", url="https://tayefi.me"),
    ],
    [InlineKeyboardButton("Author", url="https://t.me/tayefi")],
]

CB_BUTTONS = [
    [
        InlineKeyboardButton("Video", callback_data="Video"),
        InlineKeyboardButton("MP3", callback_data="mp3"),
    ]
]

# Helpers

async def progress_for_pyrogram(current, total, ud_type, message, start):
    now = time.time()
    diff = now - start
    if round(diff % 10.00) == 0 or current == total:
        percentage = current * 100 / total
        speed = current / diff
        elapsed_time = round(diff) * 1000
        time_to_completion = round((total - current) / speed) * 1000
        estimated_total_time = elapsed_time + time_to_completion

        elapsed_time = TimeFormatter(milliseconds=elapsed_time)
        estimated_total_time = TimeFormatter(milliseconds=estimated_total_time)

        progress = "[{0}{1}] \nP: {2}%\n".format(
            ''.join(["█" for _ in range(math.floor(percentage / 5))]),
            ''.join(["░" for _ in range(20 - math.floor(percentage / 5))]),
            round(percentage, 2))

        tmp = progress + "{0} of {1}\nSpeed: {2}/s\nETA: {3}\n".format(
            humanbytes(current),
            humanbytes(total),
            humanbytes(speed),
            estimated_total_time if estimated_total_time != '' else "0 s"
        )
        try:
            await message.edit(text="{}\n {}".format(ud_type, tmp))
        except Exception as e:
            print(f"Error updating message: {e}")

def humanbytes(size):
    if not size:
        return ""
    power = 2**10
    n = 0
    Dic_powerN = {0: '', 1: 'Ki', 2: 'Mi', 3: 'Gi', 4: 'Ti'}
    while size > power:
        size /= power
        n += 1
    return f"{round(size, 2)} {Dic_powerN[n]}B"

def TimeFormatter(milliseconds: int) -> str:
    seconds, milliseconds = divmod(int(milliseconds), 1000)
    minutes, seconds = divmod(seconds, 60)
    hours, minutes = divmod(minutes, 60)
    days, hours = divmod(hours, 24)
    return f"{days}d, {hours}h, {minutes}m, {seconds}s, {milliseconds}ms"

async def run_cmd(cmd) -> Tuple[str, str, int, int]:
    if isinstance(cmd, str):
        cmd = shlex.split(cmd)
    process = await asyncio.create_subprocess_exec(
        *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
    )
    stdout, stderr = await process.communicate()
    return (
        stdout.decode("utf-8", "replace").strip(),
        stderr.decode("utf-8", "replace").strip(),
        process.returncode,
        process.pid,
    )

async def send_media(file_name: str, update: Message) -> bool:
    if os.path.isfile(file_name):
        caption = os.path.basename(file_name)
        progress_args = ('Uploading...', update, time.time())
        try:
            if file_name.lower().endswith(('.mkv', '.mp4')):
                metadata = extractMetadata(createParser(file_name))
                duration = metadata.get('duration').seconds if metadata and metadata.has("duration") else 0
                rndmtime = str(random.randint(0, duration))
                await run_cmd(f'ffmpeg -ss {rndmtime} -i "{file_name}" -vframes 1 thumbnail.jpg')
                await update.reply_video(file_name, caption=caption, duration=duration, thumb='thumbnail.jpg', progress=progress_for_pyrogram, progress_args=progress_args)
                os.remove('thumbnail.jpg')
            elif file_name.lower().endswith(('.jpg', '.jpeg', '.png')):
                await update.reply_photo(file_name, caption=caption, progress=progress_for_pyrogram, progress_args=progress_args)
            elif file_name.lower().endswith('.mp3'):
                await update.reply_audio(file_name, caption=caption, progress=progress_for_pyrogram, progress_args=progress_args)
            else:
                await update.reply_document(file_name, caption=caption, progress=progress_for_pyrogram, progress_args=progress_args)
            return True
        except Exception as e:
            print(f"Error sending media: {e}")
            return False
    return False

async def download_file(url, dl_path):
    command = [
        'yt-dlp',
        '-f', 'best',
        '-i',
        '-o', f'{dl_path}/%(title)s.%(ext)s',
        url
    ]
    await run_cmd(command)

async def download_and_convert_to_mp3(url, dl_path):
    video_file = f'{dl_path}/%(title)s.%(ext)s'
    mp3_file = f'{dl_path}/%(title)s.mp3'
    await run_cmd(['yt-dlp', '-f', 'bestaudio', '-x', '--audio-format', 'mp3', '-o', video_file, url])
    await run_cmd(['ffmpeg', '-i', video_file, '-vn', '-ab', '192k', mp3_file])

async def absolute_paths(directory):
    for dirpath, _, filenames in os.walk(directory):
        for f in filenames:
            yield os.path.abspath(os.path.join(dirpath, f))

# Running bot
xbot = Client('Bulk-ytdl', api_id=APP_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

OWNER_FILTER = filters.chat(int(OWNER_ID)) & filters.incoming if OWNER_ID else filters.incoming

user_states = {}
download_queue = asyncio.Queue()
upload_queue = asyncio.Queue()

async def process_download_queue(queue, update, dirs):
    pablo = await update.reply_text('Downloading...')
    while not queue.empty():
        item = await queue.get()
        if isinstance(item, tuple):
            url, format_type = item
            if format_type == 'mp3':
                await download_and_convert_to_mp3(url, dirs)
            else:
                await download_file(url, dirs)
        else:
            url = item
            await download_file(url, dirs)
        queue.task_done()
        total = queue.qsize()
        await pablo.edit_text(f"Remaining: {total}")
    await pablo.edit_text('Download completed.')

async def process_upload_queue(queue, update, dirs):
    pablo = await update.reply_text('Uploading...')
    while not queue.empty():
        file_path = await queue.get()
        await send_media(file_path, update)
        queue.task_done()
        total = queue.qsize()
        await pablo.edit_text(f"Remaining: {total}")
    await pablo.delete()
    shutil.rmtree(dirs)

@xbot.on_message(filters.command('start') & OWNER_FILTER & filters.private)
async def start(bot, update):
    await update.reply_text("I'm Bulk-ytdlp\nYou can upload a list of URLs\n\n/help for more details!", True, reply_markup=InlineKeyboardMarkup(START_BUTTONS))

@xbot.on_message(filters.command('help') & OWNER_FILTER & filters.private)
async def help(bot, update):
    await update.reply_text("How to use Bulk-ytdlp?!\n\n2 Methods:\n- send command /link and then send URLs, separated by new line.\n- send txt file (links), separated by new line.", True, reply_markup=InlineKeyboardMarkup(START_BUTTONS))

@xbot.on_message(filters.command('link') & OWNER_FILTER & filters.private)
async def linkloader(bot, update):
    user_states[update.from_user.id] = 'awaiting_links'
    await update.reply_text('Send your links, separated each link by a new line')

@xbot.on_message(filters.text & OWNER_FILTER & filters.private)
async def handle_links(bot, message):
    user_id = message.from_user.id
    if user_states.get(user_id) == 'awaiting_links':
        user_states[user_id] = 'awaiting_format'
        user_states['urls'] = message.text.split('\n')
        await message.reply_text('Choose the format you want to download:', reply_markup=InlineKeyboardMarkup(CB_BUTTONS))

@xbot.on_message(filters.document & OWNER_FILTER & filters.private)
async def loader(bot, update):
    if BUTTONS:
        await update.reply('You wanna upload files as?', True, reply_markup=InlineKeyboardMarkup(CB_BUTTONS))
    else:
        dirs = f'downloads/{update.from_user.id}'
        os.makedirs(dirs, exist_ok=True)
        if not update.document.file_name.endswith('.txt'):
            return
        output_filename = update.document.file_name[:-4]
        position = download_queue.qsize() + 1
        await update.reply_text(f'You are in queue number {position}. Please wait...')
        pablo = await update.reply_text('Downloading...')
        fl = await update.download()
        with open(fl) as f:
            urls = f.read().split('\n')
            for url in urls:
                await download_queue.put(url)
            await process_download_queue(download_queue, update, dirs)
        os.remove(fl)
        async for file_path in absolute_paths(dirs):
            await upload_queue.put(file_path)
        await process_upload_queue(upload_queue, update, dirs)

@xbot.on_callback_query()
async def callbacks(bot: Client, updatex: CallbackQuery):
    cb_data = updatex.data
    user_id = updatex.from_user.id

    # Handle None case
    update = updatex.message.reply_to_message if updatex.message else None

    dirs = f'downloads/{user_id}'
    os.makedirs(dirs, exist_ok=True)

    if user_states.get(user_id) == 'awaiting_format':
        user_states[user_id] = None
        urls = user_states.pop('urls', [])
        for url in urls:
            await download_queue.put((url, cb_data))
        position = download_queue.qsize() + 1
        if update:
            await update.reply_text(f'You are in queue number {position}. Please wait...')
            await process_download_queue(download_queue, update, dirs)
            async for file_path in absolute_paths(dirs):
                await upload_queue.put(file_path)
            await process_upload_queue(upload_queue, update, dirs)
        else:
            await updatex.message.edit_text(f'You are in queue number {position}. Please wait...')
            await process_download_queue(download_queue, updatex.message, dirs)
            async for file_path in absolute_paths(dirs):
                await upload_queue.put(file_path)
            await process_upload_queue(upload_queue, updatex.message, dirs)
    else:
        if update:
            await update.reply_text('Invalid state. Please send /link again and follow the instructions.')
        else:
            await updatex.message.edit_text('Invalid state. Please send /link again and follow the instructions.')

xbot.run()
