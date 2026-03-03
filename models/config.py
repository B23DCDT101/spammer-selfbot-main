import os
from dotenv import load_dotenv
from typing import TypedDict 

load_dotenv()

class Config(TypedDict):
    DISCORD_TOKEN: str
    OWNER_ID: int
    OPENROUTER_API_KEY: str
    GEMINI_API_KEY: str
    GEMINI_MODEL: str
    SYSTEM_INSTRUCTION: str
    ERROR_MESSAGE: str
    VOICE_CHANNEL_ID: int
    BACKUP_VOICE_CHANNEL_ID: int
    NOTIFY_CHANNEL_ID: int

config: Config = {
    'DISCORD_TOKEN': os.getenv('DISCORD_TOKEN', ''),
    'OWNER_ID': int(os.getenv('OWNER_ID', 0)),
    'OPENROUTER_API_KEY': os.getenv('OPENROUTER_API_KEY', ''),
    'GEMINI_API_KEY': os.getenv('GEMINI_API_KEY', ''),
    'GEMINI_MODEL': os.getenv('GEMINI_MODEL', 'gemini-flash-lite-latest'),
    'SYSTEM_INSTRUCTION': os.getenv('SYSTEM_INSTRUCTION', 'You are a helpful assistant.'),
    'ERROR_MESSAGE': os.getenv('ERROR_MESSAGE', "t đang mệt lắm đừng nói chuyện với t nữa"),
    'VOICE_CHANNEL_ID': int(os.getenv('VOICE_CHANNEL_ID', 0)),
    'BACKUP_VOICE_CHANNEL_ID': int(os.getenv('BACKUP_VOICE_CHANNEL_ID', 0)),
    'NOTIFY_CHANNEL_ID': int(os.getenv('NOTIFY_CHANNEL_ID', 0)),
}