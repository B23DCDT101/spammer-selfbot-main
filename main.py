import logging
import discord
from discord.ext import commands
from models.config import config

description = '''A simple self-bot
1. Types !ping to get a cute response.
2. Replies to messages from admin and other users.'''

logger = logging.getLogger('discord')

# MyBot class inherits from commands.Bot (which itself inherits from discord.Client)
class MyBot(commands.Bot):
    # Constructor
    def __init__(self, command_prefix: str = '!', description: str = description, self_bot: bool = False, owner_id: int = config['OWNER_ID'], user_bot: bool = False):
        # Trả về constructor gốc với user_bot=True
        super().__init__(command_prefix=command_prefix, description=description, self_bot=self_bot, owner_id=owner_id, user_bot=user_bot)

    # setup hook to load cogs
    async def setup_hook(self) -> None:
        try:
            logger.info("Loading cogs...")
            await self.load_extension('cogs.basic')
            await self.load_extension('cogs.chat')
            logger.info("Cogs loaded successfully!")
        except Exception as e:
            logger.error(f"Error loading cogs: {e}")
    
        # event: if a message is received
    # event: if a message is received
    async def on_message(self, message: discord.Message):
        # Đảm bảo bot user có sẵn
        if not self.user:
            raise RuntimeError("Bot user is not available")
        
        # === PHẦN SỬA ĐỔI GỐC CỦA BẠN ===
        # CHỈ bỏ qua tin nhắn do chính bot này gửi
        if message.author.id == self.user.id:
            return
        # (Dòng 'or message.author.bot' đã được XÓA)
        # ==================================
        
        # Xử lý lệnh nếu tin nhắn bắt đầu bằng prefix
        if message.content.lower().startswith(self.command_prefix): # type: ignore
            await self.process_commands(message)
            return
        
        # Phần code trả lời "hello" khi được mention của bạn
        if self.user in message.mentions:
            try:
                async with message.channel.typing():
                    pass
            except Exception as e:
                # logger.error(f"ERROR khi cố trả lời mention: {e}")
                print(f"ERROR khi cố trả lời mention: {e}") # In ra console cho dễ debug


# run the bot
if __name__ == '__main__':
    # Trả về cách gọi bot gốc, dùng user_bot=True
    bot = MyBot(command_prefix='!', description=description, owner_id=config['OWNER_ID'], user_bot=True)
    bot.run(str(config['DISCORD_TOKEN']), root_logger=True) # use root logger