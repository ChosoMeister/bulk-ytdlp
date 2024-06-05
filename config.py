# config.py
import os
from dotenv import load_dotenv

load_dotenv()

API_HASH = os.environ.get('API_HASH')
APP_ID = int(os.environ.get('APP_ID'))
BOT_TOKEN = os.environ.get('BOT_TOKEN')
OWNER_ID = os.environ.get('OWNER_ID')
BUTTONS = bool(os.environ.get('BUTTONS', False))
