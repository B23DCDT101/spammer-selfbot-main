from discord.ext import commands
from main import MyBot
import discord
import logging
from models.config import config
import asyncio
import discord
from openai import OpenAI  # <-- IMPORT MỚI
logger = logging.getLogger(__name__)

client = OpenAI(
    base_url="https://integrate.api.nvidia.com/v1",
    api_key="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"
)
class Test(commands.Cog):
    def __init__(self, bot: MyBot):
        self.bot = bot

    # helper function to join voice channel
    async def join_vc(self):
        # wait 5s for session to be fully ready
        await asyncio.sleep(5)

        # clean up ALL stale voice clients before connecting
        if self.bot.voice_clients:
            logger.info(f"Found {len(self.bot.voice_clients)} stale voice client(s), attempting to clean up...")
            for vc in list(self.bot.voice_clients):
                try:
                    await vc.disconnect(force=True)
                    logger.info("Cleaned up old voice client.")
                except Exception as e:
                    logger.warning(f"Error cleaning up old voice client: {e}")
            # Wait longer after disconnect so Discord can expire the old session
            # This prevents error 4006 (session no longer valid)
            logger.info("Waiting for Discord to expire old voice session...")
            await asyncio.sleep(5)

        max_retries = 3
        retry_delay = 5  # seconds

        channels_to_try = [
            ('VOICE_CHANNEL_ID', config.get('VOICE_CHANNEL_ID')),
            ('BACKUP_VOICE_CHANNEL_ID', config.get('BACKUP_VOICE_CHANNEL_ID')),
        ]

        for channel_key, channel_id in channels_to_try:
            if not channel_id:
                logger.warning(f"Config key {channel_key} not set, skipping.")
                continue

            logger.info(f"Attempting to connect to {channel_key} ({channel_id})...")
            voice_channel = self.bot.get_channel(channel_id)

            if not (voice_channel and isinstance(voice_channel, discord.VoiceChannel)):
                logger.error(f"ERROR: Could not find voice channel ID {channel_id} or it is not a voice channel.")
                continue

            for attempt in range(1, max_retries + 1):
                try:
                    await voice_channel.connect(timeout=60.0, reconnect=False)
                    logger.info(f"Connected to voice channel: {voice_channel.name}")
                    return
                except discord.errors.ConnectionClosed as e:
                    # Error 4006 = session no longer valid, need to wait longer
                    if e.code == 4006:
                        wait = retry_delay * attempt
                        logger.warning(
                            f"Voice connection closed with code 4006 (session expired) "
                            f"on attempt {attempt}/{max_retries}. Retrying in {wait}s..."
                        )
                        await asyncio.sleep(wait)
                    else:
                        logger.error(f"Voice connection closed with code {e.code}: {e}")
                        break
                except discord.ClientException as e:
                    if "Already connected" in str(e):
                        logger.info("Already connected to a voice channel.")
                        return
                    logger.error(f"ClientException on attempt {attempt}/{max_retries}: {e}")
                    await asyncio.sleep(retry_delay)
                except Exception as e:
                    logger.error(f"Unexpected error on attempt {attempt}/{max_retries}: {e}")
                    await asyncio.sleep(retry_delay)
            else:
                logger.error(f"Failed to connect to {channel_key} after {max_retries} attempts, trying next channel.")
                continue
            break

    # event: if the bot is ready
    @commands.Cog.listener()
    async def on_ready(self):
        if not self.bot.user:
            raise RuntimeError("Bot user is not available")
        logger.info(f'Logged in as {self.bot.user} (ID: {self.bot.user.id})')
        logger.info('------')
        try:
            logger.info(f"Waiting for searching admin: {self.bot.owner_id}...")
            admin_user = await self.bot.fetch_user(self.bot.owner_id or config['OWNER_ID'])
            logger.info(f"Found admin: {admin_user.name}")
            if admin_user:
                await admin_user.send("Bot has started successfully!")
                logger.info(f"Sent startup DM to admin: {admin_user.name}")

        except discord.NotFound:
            logger.error(f"ERROR: Admin with ID {self.bot.owner_id or config['OWNER_ID']} not found.")
        except discord.Forbidden as e:
            logger.error(f"ERROR: Could not send DM to admin. (They may have DMs disabled)")
        except Exception as e:
            logger.error(f"ERROR: Unexpected error occurred while sending DM: {e}")
        
        # join voice channel
        await self.join_vc()

    @commands.Cog.listener()
    async def on_voice_state_update(self, member: discord.Member, before: discord.VoiceState, after: discord.VoiceState):
        # ensure the bot user is available
        if not self.bot.user:
            raise RuntimeError("Bot user is not available")
        
        if member.id == self.bot.user.id:
            # if before was in a channel and after is not, bot was disconnected
            if before.channel is not None and after.channel is None:
                logger.warning("Bot was disconnected from voice channel, attempting to rejoin...")
                await self.join_vc()

    # command: !add 5 10
    @commands.command(name='khoinghia')
    async def khoinghia(self, ctx: commands.Context):
        """
        Khi gõ !khoinghia, bot sẽ nhắc tên người dùng và gửi lời kêu gọi lãnh đạo.
        """
        # ctx.author.mention sẽ tạo ra chuỗi dạng <@ID_người_dùng>
        user_mention = ctx.author.mention
        
        # Đường dẫn ảnh (nếu bạn vẫn muốn gửi kèm ảnh)
        file_path = "/home/mq/Desktop/Project/bot/spammer-selfbot-main/image.png"
        
        try:
            # Gửi tin nhắn kèm mention
            # Chúng ta dùng f-string để chèn biến vào chuỗi dễ dàng hơn
            response_msg = f"tuôi chỉ đi dạo xung quanh thôi!!!"
            
            # Nếu bạn muốn gửi kèm cả bức ảnh image.png:
            # await ctx.send(response_msg, file=discord.File(file_path))
            
            # Nếu chỉ muốn gửi tin nhắn văn bản:
            await ctx.send(response_msg)

        except FileNotFoundError:
            await ctx.send(f"Lỗi: Không tìm thấy file ảnh tại {file_path}, nhưng sếp {user_mention} vẫn phải lãnh đạo!")
        except Exception as e:
            await ctx.send(f"Đã xảy ra lỗi: {e}")
    # command: !ping
    # @commands.command(name='ping') # Đặt tên lệnh là 'ping'
    # async def ping(self, ctx: commands.Context[commands.Bot], *, prompt: str):
    #     """
    #     Gửi một prompt đến API NVIDIA và stream câu trả lời.
    #     Cách dùng: !ping [nội dung câu hỏi của bạn]
    #     """
        
    #     # Thêm phản ứng '⏳' để báo cho người dùng biết bot đang xử lý
    #     try:
    #         await ctx.message.add_reaction('⏳')
    #     except discord.Forbidden:
    #         pass # Bỏ qua nếu bot không có quyền thêm reaction

    #     try:
    #         # 1. Gọi API với prompt từ người dùng
    #         completion = client.chat.completions.create(
    #             model="qwen/qwen3-coder-480b-a35b-instruct",
    #             messages=[{"role": "user", "content": f'answer below 2000 words : {prompt}'}],
    #             temperature=0.7,
    #             top_p=0.8,
    #             max_tokens=16000, # Đây là con số rất lớn, API có thể có giới hạn riêng
    #             stream=True
    #             # Dòng 'setdb()' không hợp lệ đã bị xóa
    #         )

    #         # 2. Xử lý stream và gửi tin nhắn
    #         response_text = ""
    #         for chunk in completion:
    #             # Kiểm tra xem có nội dung trong chunk không
    #             if chunk.choices[0].delta.content:
    #                 new_content = chunk.choices[0].delta.content
                    
    #                 # Kiểm tra xem việc thêm nội dung mới có vượt quá 2000 ký tự không
    #                 if len(response_text) + len(new_content) >= 2000:
    #                     # Nếu vượt quá, gửi tin nhắn hiện tại trước
    #                     if response_text: # Đảm bảo không gửi chuỗi rỗng
    #                         await ctx.send(response_text)
    #                     # Bắt đầu tin nhắn mới với nội dung chunk
    #                     response_text = new_content
    #                 else:
    #                     # Nếu không, tiếp tục cộng dồn
    #                     response_text += new_content

    #         # 3. Gửi phần tin nhắn cuối cùng còn lại
    #         if response_text:
    #             await ctx.send(response_text)

    #         # Xóa reaction '⏳' sau khi hoàn tất
    #         try:
    #             await ctx.message.remove_reaction('⏳', self.bot.user) # type: ignore
    #         except discord.Forbidden:
    #             pass

    #     except Exception as e:
    #         # Xử lý lỗi nếu có
    #         logger.error(f"Lỗi khi gọi API NVIDIA: {e}") # Giả sử bạn có logger
    #         print(f"Lỗi khi gọi API NVIDIA: {e}") # In ra console
    #         await ctx.send(f"Đã xảy ra lỗi: {e}")
    #         # Thêm reaction '❌' nếu thất bại
    #         try:
    #             await ctx.message.remove_reaction('⏳', self.bot.user) # type: ignore
    #             await ctx.message.add_reaction('❌')
    #         except discord.Forbidden:
    #             pass

async def setup(bot: MyBot):
    await bot.add_cog(Test(bot))