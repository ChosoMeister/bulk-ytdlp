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
        user_states[user_id] = None  # Reset state
        if BUTTONS:
            await message.reply('Uploading methods.', True, reply_markup=InlineKeyboardMarkup(CB_BUTTONS))
        else:
            await process_links(message, message.text.split('\n'))

async def process_links(update: Message, urlx):
    dirs = f'downloads/{update.from_user.id}'
    os.makedirs(dirs, exist_ok=True)
    pablo = await update.reply_text('Downloading...')
    rm, total, up = len(urlx), len(urlx), 0
    await pablo.edit_text(f"Total: {total}\nDownloaded: {up}\nDownloading: {rm}")
    for url in urlx:
        await download_file(url, dirs)
        up += 1
        rm -= 1
        try:
            await pablo.edit_text(f"Total: {total}\nDownloaded: {up}\nDownloading: {rm}")
        except BadRequest:
            pass
    await pablo.edit_text('Uploading...')
    dldirs = [i async for i in absolute_paths(dirs)]
    rm, total, up = len(dldirs), len(dldirs), 0
    await pablo.edit_text(f"Total: {total}\nUploaded: {up}\nUploading: {rm}")
    for files in dldirs:
        await send_media(files, pablo)
        up += 1
        rm -= 1
        try:
            await pablo.edit_text(f"Total: {total}\nUploaded: {up}\nUploading: {rm}")
        except BadRequest:
            pass
        time.sleep(1)
    await pablo.delete()
    shutil.rmtree(dirs)

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
        pablo = await update.reply_text('Downloading...')
        fl = await update.download()
        with open(fl) as f:
            urls = f.read().split('\n')
            rm, total, up = len(urls), len(urls), 0
            await pablo.edit_text(f"Total: {total}\nDownloaded: {up}\nDownloading: {rm}")
            for url in urls:
                await download_file(url, dirs)
                up += 1
                rm -= 1
                try:
                    await pablo.edit_text(f"Total: {total}\nDownloaded: {up}\nDownloading: {rm}")
                except BadRequest:
                    pass
        await pablo.edit_text('Uploading...')
        os.remove(fl)
        dldirs = [i async for i in absolute_paths(dirs)]
        rm, total, up = len(dldirs), len(dldirs), 0
        await pablo.edit_text(f"Total: {total}\nUploaded: {up}\nUploading: {rm}")
        for files in dldirs:
            await send_media(files, pablo)
            up += 1
            rm -= 1
            try:
                await pablo.edit_text(f"Total: {total}\nUploaded: {up}\nUploading: {rm}")
            except BadRequest:
                pass
            time.sleep(1)
        await pablo.delete()
        shutil.rmtree(dirs)

@xbot.on_callback_query()
async def callbacks(bot: Client, updatex: CallbackQuery):
    cb_data = updatex.data
    update = updatex.message.reply_to_message
    await updatex.message.delete()
    dirs = f'downloads/{update.from_user.id}'
    os.makedirs(dirs, exist_ok=True)
    if update.document:
        output_filename = update.document.file_name[:-4]
        pablo = await update.reply_text('Downloading...')
        fl = await update.download()
        with open(fl) as f:
            urls = f.read().split('\n')
            rm, total, up = len(urls), len(urls), 0
            await pablo.edit_text(f"Total: {total}\nDownloaded: {up}\nDownloading: {rm}")
            for url in urls:
                if cb_data == 'mp3':
                    await download_and_convert_to_mp3(url, dirs)
                else:
                    await download_file(url, dirs)
                up += 1
                rm -= 1
                try:
                    await pablo.edit_text(f"Total: {total}\nDownloaded: {up}\nDownloading: {rm}")
                except BadRequest:
                    pass
        os.remove(fl)
    elif update.text:
        output_filename = str(update.from_user.id)
        pablo = await update.reply_text('Downloading...')
        urlx = update.text.split('\n')
        rm, total, up = len(urlx), len(urlx), 0
        await pablo.edit_text(f"Total: {total}\nDownloaded: {up}\nDownloading: {rm}")
        for url in urlx:
            if cb_data == 'mp3':
                await download_and_convert_to_mp3(url, dirs)
            else:
                await download_file(url, dirs)
            up += 1
            rm -= 1
            try:
                await pablo.edit_text(f"Total: {total}\nDownloaded: {up}\nDownloading: {rm}")
            except BadRequest:
                pass
    await pablo.edit_text('Uploading...')
    if cb_data == 'Video':
        dldirs = [i async for i in absolute_paths(dirs)]
        rm, total, up = len(dldirs), len(dldirs), 0
        await pablo.edit_text(f"Total: {total}\nUploaded: {up}\nUploading: {rm}")
        for files in dldirs:
            await send_media(files, pablo)
            up += 1
            rm -= 1
            try:
                await pablo.edit_text(f"Total: {total}\nUploaded: {up}\nUploading: {rm}")
            except BadRequest:
                pass
            time.sleep(1)
        await pablo.delete()
        shutil.rmtree(dirs)
    elif cb_data == 'mp3':
        mp3_files = [f for f in os.listdir(dirs) if f.endswith('.mp3')]
        rm, total, up = len(mp3_files), len(mp3_files), 0
        await pablo.edit_text(f"Total: {total}\nUploaded: {up}\nUploading: {rm}")
        for mp3_file in mp3_files:
            await send_media(os.path.join(dirs, mp3_file), pablo)
            up += 1
            rm -= 1
            try:
                await pablo.edit_text(f"Total: {total}\nUploaded: {up}\nUploading: {rm}")
            except BadRequest:
                pass
            time.sleep(1)
        await pablo.delete()
        shutil.rmtree(dirs)

xbot.run()
