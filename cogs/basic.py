from discord.ext import commands, tasks
from main import MyBot
import discord
import logging
from models.config import config
import asyncio
from datetime import datetime, timedelta
from typing import Optional
from openai import OpenAI
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
    @commands.command(name = 'T1')
    async def T1(self, ctx: commands.Context[commands.Bot]):
        """
        Gửi một bức ảnh cố định đã được định sẵn khi gõ !T1.
        """
        
        # Đường dẫn cố định đến bức ảnh trên máy chủ của bot
        file_path = "/home/mq/Desktop/Project/bot/spammer-selfbot-main/image.png"
        
        try:
            # Tạo một đối tượng discord.File từ đường dẫn và gửi
            # Lệnh sẽ được gửi ngay tại kênh mà người dùng gõ !T1
            await ctx.send(file=discord.File(file_path))
            
            # (Tùy chọn) Nếu bạn muốn bot xóa tin nhắn "!T1" của người dùng
            # await ctx.message.delete()

        except FileNotFoundError:
            # Gửi thông báo lỗi nếu bot không tìm thấy file
            await ctx.send(f"Lỗi: Không tìm thấy file tại đường dẫn: {file_path}. "
                           "Hãy kiểm tra lại đường dẫn trên máy chủ bot.")
        except discord.errors.Forbidden:
            # Gửi thông báo nếu bot không có quyền gửi file
            await ctx.send("Lỗi: Bot không có quyền 'Attach Files' (Đính kèm tệp) trong kênh này.")
        except Exception as e:
            # Gửi thông báo cho các lỗi khác
            await ctx.send(f"Đã xảy ra lỗi không xác định: {e}")
    # command: !ping
    @commands.command(name='ping') # Đặt tên lệnh là 'ping'
    async def ping(self, ctx: commands.Context[commands.Bot], *, prompt: str):
        """
        Gửi một prompt đến API NVIDIA và stream câu trả lời.
        Cách dùng: !ping [nội dung câu hỏi của bạn]
        """
        
        # Thêm phản ứng '⏳' để báo cho người dùng biết bot đang xử lý
        try:
            await ctx.message.add_reaction('⏳')
        except discord.Forbidden:
            pass # Bỏ qua nếu bot không có quyền thêm reaction

        try:
            # 1. Gọi API với prompt từ người dùng
            completion = client.chat.completions.create(
                model="qwen/qwen3-coder-480b-a35b-instruct",
                messages=[{"role": "user", "content": f'answer below 2000 words : {prompt}'}],
                temperature=0.7,
                top_p=0.8,
                max_tokens=16000, # Đây là con số rất lớn, API có thể có giới hạn riêng
                stream=True
                # Dòng 'setdb()' không hợp lệ đã bị xóa
            )

            # 2. Xử lý stream và gửi tin nhắn
            response_text = ""
            for chunk in completion:
                # Kiểm tra xem có nội dung trong chunk không
                if chunk.choices[0].delta.content:
                    new_content = chunk.choices[0].delta.content
                    
                    # Kiểm tra xem việc thêm nội dung mới có vượt quá 2000 ký tự không
                    if len(response_text) + len(new_content) >= 2000:
                        # Nếu vượt quá, gửi tin nhắn hiện tại trước
                        if response_text: # Đảm bảo không gửi chuỗi rỗng
                            await ctx.send(response_text)
                        # Bắt đầu tin nhắn mới với nội dung chunk
                        response_text = new_content
                    else:
                        # Nếu không, tiếp tục cộng dồn
                        response_text += new_content

            # 3. Gửi phần tin nhắn cuối cùng còn lại
            if response_text:
                await ctx.send(response_text)

            # Xóa reaction '⏳' sau khi hoàn tất
            try:
                await ctx.message.remove_reaction('⏳', self.bot.user) # type: ignore
            except discord.Forbidden:
                pass

        except Exception as e:
            # Xử lý lỗi nếu có
            logger.error(f"Lỗi khi gọi API NVIDIA: {e}") # Giả sử bạn có logger
            print(f"Lỗi khi gọi API NVIDIA: {e}") # In ra console
            await ctx.send(f"Đã xảy ra lỗi: {e}")
            # Thêm reaction '❌' nếu thất bại
            try:
                await ctx.message.remove_reaction('⏳', self.bot.user) # type: ignore
                await ctx.message.add_reaction('❌')
            except discord.Forbidden:
                pass

async def setup(bot: MyBot):
    await bot.add_cog(Test(bot))
    await bot.add_cog(Pomodoro(bot))


# ──────────────────────────────────────────────
# POMODORO
# ──────────────────────────────────────────────

class PomodoroSession:
    """Lớp đại diện cho một phiên Pomodoro"""

    def __init__(self, user_id: int, work_duration: int = 25, break_duration: int = 5):
        self.user_id = user_id
        self.work_duration = work_duration  # phút
        self.break_duration = break_duration  # phút
        self.is_work_time = True  # True = thời gian làm việc, False = thời gian nghỉ
        self.is_running = False
        self.is_paused = False
        self.start_time: Optional[datetime] = None
        self.pause_time: Optional[datetime] = None
        self.paused_remaining: Optional[float] = None  # phút
        self.sessions_completed = 0
        self.current_session_start: Optional[datetime] = None
        self.pom_message: Optional[discord.Message] = None  # tin nhắn !pom gốc để reply

    def start(self):
        """Bắt đầu phiên Pomodoro"""
        if self.is_paused and self.paused_remaining:
            # Resume từ pause
            self.is_running = True
            self.is_paused = False
            self.start_time = datetime.now() - timedelta(
                minutes=self.work_duration if self.is_work_time else self.break_duration,
                seconds=(self.work_duration if self.is_work_time else self.break_duration) * 60 - self.paused_remaining * 60
            )
            logger.info(f"Resumed Pomodoro for user {self.user_id}")
        else:
            self.is_running = True
            self.is_paused = False
            self.start_time = datetime.now()
            self.current_session_start = datetime.now()
            if self.is_work_time:
                self.sessions_completed += 1
            logger.info(f"Started Pomodoro for user {self.user_id} ({self.get_phase_name()})")

    def pause(self):
        """Tạm dừng phiên Pomodoro"""
        if self.is_running and not self.is_paused:
            self.is_paused = True
            self.pause_time = datetime.now()
            self.paused_remaining = self.get_remaining_time()
            logger.info(f"Paused Pomodoro for user {self.user_id}")

    def resume(self):
        """Tiếp tục phiên Pomodoro từ pause"""
        if self.is_paused:
            self.start()

    def stop(self):
        """Dừng phiên Pomodoro"""
        self.is_running = False
        self.is_paused = False
        self.start_time = None
        self.pause_time = None
        self.paused_remaining = None
        logger.info(f"Stopped Pomodoro for user {self.user_id}")

    def get_remaining_time(self) -> float:
        """Tính thời gian còn lại (phút)"""
        if not self.start_time:
            total = self.work_duration if self.is_work_time else self.break_duration
            return float(total)
        elapsed = (datetime.now() - self.start_time).total_seconds() / 60
        total = self.work_duration if self.is_work_time else self.break_duration
        return max(0, total - elapsed)

    def is_finished(self) -> bool:
        """Kiểm tra xem phiên có kết thúc hay không"""
        if not self.is_running or self.is_paused:
            return False
        return self.get_remaining_time() <= 0

    def switch_phase(self):
        """Chuyển sang phase tiếp theo (work <-> break)"""
        self.is_work_time = not self.is_work_time
        self.start_time = datetime.now()
        self.is_paused = False
        self.paused_remaining = None
        logger.info(f"Switched to {self.get_phase_name()} for user {self.user_id}")

    def get_phase_name(self) -> str:
        """Lấy tên phase hiện tại"""
        return "💼 Làm việc" if self.is_work_time else "☕ Nghỉ"

    def get_status(self) -> str:
        """Lấy chuỗi mô tả trạng thái"""
        if not self.is_running:
            return "Chưa bắt đầu"
        if self.is_paused:
            return f"⏸️ Tạm dừng ({self.paused_remaining:.1f} phút còn lại)"
        remaining = self.get_remaining_time()
        minutes = int(remaining)
        seconds = int((remaining % 1) * 60)
        return f"⏱️ {minutes:02d}:{seconds:02d}"


class Pomodoro(commands.Cog):
    """Cog cho tính năng Pomodoro"""

    def __init__(self, bot: MyBot):
        self.bot = bot
        self.sessions: dict[int, PomodoroSession] = {}
        self.notification_task.start()
        logger.info("Pomodoro cog initialized")

    def cog_unload(self):
        self.notification_task.cancel()
        logger.info("Pomodoro cog unloaded")

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        """Hủy phiên Pomodoro nếu user nhắn tin trong khi đang chạy"""
        if not self.bot.user or message.author.id == self.bot.user.id:
            return

        user_id = message.author.id
        session = self.sessions.get(user_id)

        # Bỏ qua nếu không có session đang chạy
        if not session or not session.is_running:
            return

        # Bỏ qua các lệnh pom (không hủy khi dùng !pompause, !pomstop, v.v.)
        if message.content.lower().startswith('!pom'):
            return

        # Hủy session
        completed = session.sessions_completed
        session.stop()
        del self.sessions[user_id]

        try:
            await message.reply(
                f"🚫 **Pomodoro bị hủy!**\n"
                f"Bạn đã nhắn tin trong khi đang trong phiên tập trung.\n"
                f"✅ Phiên hoàn thành trước khi hủy: {completed}"
            )
            logger.info(f"Pomodoro session cancelled for user {user_id} due to message: {message.content[:50]}")
        except Exception as e:
            logger.error(f"Error sending cancellation reply to user {user_id}: {e}")

    def get_user_session(self, user_id: int) -> PomodoroSession:
        if user_id not in self.sessions:
            self.sessions[user_id] = PomodoroSession(user_id)
        return self.sessions[user_id]

    @tasks.loop(seconds=5)
    async def notification_task(self):
        """Task lặp để kiểm tra session hoàn thành và gửi thông báo"""
        try:
            for user_id, session in list(self.sessions.items()):
                if session.is_running and not session.is_paused and session.is_finished():
                    try:
                        if not session.pom_message:
                            logger.error(f"No pom_message stored for user {user_id}.")
                            continue
                        if session.is_work_time:
                            session.switch_phase()
                            await session.pom_message.reply(
                                f"✅ **Phiên làm việc kết thúc!**\n"
                                f"Bạn đã hoàn thành {session.sessions_completed} phiên Pomodoro.\n"
                                f"Bước tiếp theo: Nghỉ {session.break_duration} phút ☕\n"
                                f"Thời gian còn lại: {session.get_status()}"
                            )
                            logger.info(f"Replied work completion to user {user_id}")
                        else:
                            session.switch_phase()
                            await session.pom_message.reply(
                                f"☕ **Phiên nghỉ kết thúc!**\n"
                                f"Đã đủ sức, quay lại làm việc nào! 💪\n"
                                f"Bước tiếp theo: Làm việc {session.work_duration} phút 💼\n"
                                f"Thời gian còn lại: {session.get_status()}"
                            )
                            logger.info(f"Replied break completion to user {user_id}")
                    except Exception as e:
                        logger.error(f"Error sending notification for user {user_id}: {e}")
        except Exception as e:
            logger.error(f"Error in notification task: {e}")

    @notification_task.before_loop
    async def before_notification_task(self):
        await self.bot.wait_until_ready()

    @commands.command(name='pom')
    async def pomodoro_start(self, ctx: commands.Context[commands.Bot], work: int = 25, break_time: int = 5):
        """Bắt đầu Pomodoro timer. Cách dùng: !pom [phút làm việc] [phút nghỉ]"""
        if work <= 0 or break_time <= 0:
            await ctx.send("❌ Thời gian phải > 0!")
            return
        if work > 120 or break_time > 60:
            await ctx.send("❌ Thời gian quá dài! Max: 120 phút (work), 60 phút (break)")
            return
        user_id = ctx.author.id
        session = self.get_user_session(user_id)
        if session.is_running:
            await ctx.send("⚠️ Bạn đã có Pomodoro đang chạy rồi! Dùng `!pomstop` để dừng trước.")
            return
        session.work_duration = work
        session.break_duration = break_time
        session.is_work_time = True
        session.sessions_completed = 0
        session.pom_message = ctx.message
        session.start()
        await ctx.send(
            f"🍅 **Pomodoro Started!**\n"
            f"💼 Làm việc: {work} phút | ☕ Nghỉ: {break_time} phút\n"
            f"Trạng thái: {session.get_status()}\n"
            f"Sử dụng !pompause, !pomresume, !pomstop, !pomstatus để điều khiển"
        )

    @commands.command(name='pomstatus')
    async def pomodoro_status(self, ctx: commands.Context[commands.Bot]):
        """Xem trạng thái Pomodoro hiện tại"""
        user_id = ctx.author.id
        if user_id not in self.sessions:
            await ctx.send("❌ Bạn chưa bắt đầu Pomodoro nào!")
            return
        session = self.sessions[user_id]
        if not session.is_running and not session.is_paused:
            await ctx.send("❌ Pomodoro của bạn không đang chạy!")
            return
        remaining = session.get_remaining_time()
        minutes = int(remaining)
        seconds = int((remaining % 1) * 60)
        await ctx.send(
            f"🍅 **Pomodoro Status** - {session.get_phase_name()}\n"
            f"Trạng thái: {session.get_status()}\n"
            f"⏱️ Còn lại: **{minutes:02d}:{seconds:02d}**\n"
            f"✅ Phiên hoàn thành: {session.sessions_completed}\n"
            f"💼 Cấu hình: Work {session.work_duration}m | Break {session.break_duration}m"
        )

    @commands.command(name='pompause')
    async def pomodoro_pause(self, ctx: commands.Context[commands.Bot]):
        """Tạm dừng Pomodoro hiện tại"""
        user_id = ctx.author.id
        if user_id not in self.sessions:
            await ctx.send("❌ Bạn chưa bắt đầu Pomodoro nào!")
            return
        session = self.sessions[user_id]
        if not session.is_running:
            await ctx.send("❌ Pomodoro không đang chạy!")
            return
        if session.is_paused:
            await ctx.send("⚠️ Pomodoro đã bị tạm dừng rồi!")
            return
        session.pause()
        remaining = session.paused_remaining
        minutes = int(remaining)
        seconds = int((remaining % 1) * 60)
        await ctx.send(
            f"⏸️ **Pomodoro đã tạm dừng!**\n"
            f"Thời gian còn lại: **{minutes:02d}:{seconds:02d}**\n"
            f"Dùng `!pomresume` để tiếp tục"
        )

    @commands.command(name='pomresume')
    async def pomodoro_resume(self, ctx: commands.Context[commands.Bot]):
        """Tiếp tục Pomodoro từ tạm dừng"""
        user_id = ctx.author.id
        if user_id not in self.sessions:
            await ctx.send("❌ Bạn chưa bắt đầu Pomodoro nào!")
            return
        session = self.sessions[user_id]
        if not session.is_paused:
            await ctx.send("⚠️ Pomodoro không ở trạng thái tạm dừng!")
            return
        session.resume()
        await ctx.send(
            f"▶️ **Pomodoro đã tiếp tục!**\n"
            f"Phase: {session.get_phase_name()}\n"
            f"Trạng thái: {session.get_status()}"
        )

    @commands.command(name='pomstop')
    async def pomodoro_stop(self, ctx: commands.Context[commands.Bot]):
        """Dừng Pomodoro hiện tại"""
        user_id = ctx.author.id
        if user_id not in self.sessions:
            await ctx.send("❌ Bạn chưa bắt đầu Pomodoro nào!")
            return
        session = self.sessions[user_id]
        if not session.is_running and not session.is_paused:
            await ctx.send("❌ Pomodoro không đang chạy!")
            return
        completed = session.sessions_completed
        session.stop()
        del self.sessions[user_id]
        await ctx.send(
            f"🛑 **Pomodoro Dừng**\n"
            f"Phiên Pomodoro của bạn đã kết thúc.\n"
            f"✅ Phiên hoàn thành: {completed}"
        )

    @commands.command(name='pomhelp')
    async def pomodoro_help(self, ctx: commands.Context[commands.Bot]):
        """Hiển thị hướng dẫn sử dụng Pomodoro"""
        await ctx.send(
            "🍅 **Pomodoro - Hướng dẫn sử dụng**\n"
            "Quản lý thời gian làm việc của bạn với Pomodoro technique!\n\n"
            "**!pom [phút work] [phút break]** — Bắt đầu Pomodoro (mặc định: 25m / 5m). VD: `!pom 25 5`\n"
            "**!pomstatus** — Xem trạng thái Pomodoro hiện tại\n"
            "**!pompause** — Tạm dừng Pomodoro\n"
            "**!pomresume** — Tiếp tục Pomodoro từ tạm dừng\n"
            "**!pomstop** — Dừng Pomodoro hoàn toàn\n\n"
            "💡 Tip: Bot sẽ tự gửi thông báo khi hết giờ!"
        )