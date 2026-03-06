from discord.ext import commands
from main import MyBot
import discord
import logging
from models.config import config
import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
from openai import OpenAI
import os
import datetime
from dataclasses import dataclass, field
from typing import Optional

logger = logging.getLogger(__name__)

@dataclass
class PomodoroSession:
    user_id: int
    channel_id: int
    message_id: int                      # ID của message !pom gốc để reply
    work_minutes: int
    break_minutes: int
    total_rounds: int
    current_round: int = 1
    phase: str = "work"                  # "work" | "break" | "done"
    paused: bool = False
    task: Optional[asyncio.Task] = field(default=None, repr=False)
    start_time: datetime.datetime = field(default_factory=datetime.datetime.now)

client = OpenAI(
    base_url="https://integrate.api.nvidia.com/v1",
    api_key="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"
)
class Test(commands.Cog):
    def __init__(self, bot: MyBot):
        self.bot = bot
        # Kết nối MongoDB cho todo
        _mongo = AsyncIOMotorClient(os.getenv("MONGO_URI", "mongodb://localhost:27017"))
        self._todo = _mongo["todo_db"]["todos"]
        # Pomodoro sessions: user_id -> PomodoroSession
        self._pom_sessions: dict[int, PomodoroSession] = {}

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
            response_msg = f"sếp {user_mention} hãy lãnh đạo chúng em đi!!!"
            
            # Nếu bạn muốn gửi kèm cả bức ảnh image.png:
            # await ctx.send(response_msg, file=discord.File(file_path))
            
            # Nếu chỉ muốn gửi tin nhắn văn bản:
            await ctx.send(response_msg)

        except FileNotFoundError:
            await ctx.send(f"Lỗi: Không tìm thấy file ảnh tại {file_path}, nhưng sếp {user_mention} vẫn phải lãnh đạo!")
        except Exception as e:
            await ctx.send(f"Đã xảy ra lỗi: {e}")

    # ──────────────────────────────────────────────
    # POMODORO
    # ──────────────────────────────────────────────

    async def _pom_notify(self, session: PomodoroSession, text: str):
        """Reply vào message !pom gốc."""
        try:
            channel = self.bot.get_channel(session.channel_id)
            if not channel:
                return
            msg = await channel.fetch_message(session.message_id)  # type: ignore
            await msg.reply(text)
        except Exception as e:
            logger.warning(f"[Pomodoro] notify error: {e}")

    async def _pom_run(self, session: PomodoroSession):
        """Vòng lặp chính của Pomodoro."""
        try:
            while session.current_round <= session.total_rounds:
                # ── WORK ──
                session.phase = "work"
                await self._pom_notify(
                    session,
                    f"🍅 **Pomodoro {session.current_round}/{session.total_rounds}** — Bắt đầu làm việc!"
                    f" ({session.work_minutes} phút)"
                )
                await asyncio.sleep(session.work_minutes * 60)

                # Kiểm tra nếu bị cancel trong lúc sleep
                if session.phase == "cancelled":
                    return

                # ── BREAK (trừ round cuối) ──
                if session.current_round < session.total_rounds:
                    session.phase = "break"
                    await self._pom_notify(
                        session,
                        f"☕ **Nghỉ ngơi!** ({session.break_minutes} phút) — "
                        f"Còn {session.total_rounds - session.current_round} round nữa."
                    )
                    await asyncio.sleep(session.break_minutes * 60)

                    if session.phase == "cancelled":
                        return

                session.current_round += 1

            session.phase = "done"
            await self._pom_notify(
                session,
                f"🎉 **Pomodoro hoàn thành!** {session.total_rounds} round x {session.work_minutes} phút. Nghỉ ngơi xứng đáng nào!"
            )
        except asyncio.CancelledError:
            pass
        finally:
            self._pom_sessions.pop(session.user_id, None)

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        """Tự động hủy Pomodoro nếu user gửi tin nhắn trong lúc đang chạy."""
        if not self.bot.user or message.author.id == self.bot.user.id:
            return
        # Bỏ qua nếu là lệnh Pomodoro
        if message.content.lower().startswith(("!pom",)):
            return
        uid = message.author.id
        if uid in self._pom_sessions:
            session = self._pom_sessions[uid]
            session.phase = "cancelled"
            if session.task and not session.task.done():
                session.task.cancel()
            self._pom_sessions.pop(uid, None)
            try:
                await message.reply(
                    "⛔ **Pomodoro đã bị hủy** vì bạn gửi tin nhắn trong lúc làm việc!"
                )
            except Exception:
                pass

    @commands.command(name='pom')
    async def pom_start(self, ctx: commands.Context, work: int = 25, brk: int = 5, rounds: int = 4):
        """Bắt đầu Pomodoro. Cách dùng: !pom [work_phút] [break_phút] [số_round]"""
        uid = ctx.author.id

        if uid in self._pom_sessions:
            await ctx.send("⚠️ Bạn đang có session Pomodoro đang chạy! Dùng `!pomstop` để hủy.")
            return

        if not (1 <= work <= 120 and 1 <= brk <= 60 and 1 <= rounds <= 10):
            await ctx.send("❌ Giá trị không hợp lệ! Work: 1-120 phút, Break: 1-60 phút, Rounds: 1-10.")
            return

        session = PomodoroSession(
            user_id=uid,
            channel_id=ctx.channel.id,
            message_id=ctx.message.id,
            work_minutes=work,
            break_minutes=brk,
            total_rounds=rounds,
        )
        self._pom_sessions[uid] = session

        await ctx.reply(
            f"🍅 **Pomodoro bắt đầu!**\n"
            f"⏱ {work} phút làm / {brk} phút nghỉ × {rounds} rounds\n"
            f"💡 Gửi bất kỳ tin nhắn nào sẽ hủy session. Dùng `!pomstop` để dừng."
        )

        session.task = asyncio.create_task(self._pom_run(session))

    @commands.command(name='pomstop')
    async def pom_stop(self, ctx: commands.Context):
        """Dừng Pomodoro đang chạy. Cách dùng: !pomstop"""
        uid = ctx.author.id
        session = self._pom_sessions.get(uid)
        if not session:
            await ctx.send("⚠️ Bạn không có session Pomodoro nào đang chạy.")
            return
        session.phase = "cancelled"
        if session.task and not session.task.done():
            session.task.cancel()
        self._pom_sessions.pop(uid, None)
        await ctx.reply("⛔ Đã hủy Pomodoro!")

    @commands.command(name='pomstatus')
    async def pom_status(self, ctx: commands.Context):
        """Xem trạng thái Pomodoro. Cách dùng: !pomstatus"""
        uid = ctx.author.id
        session = self._pom_sessions.get(uid)
        if not session:
            await ctx.send("📭 Không có Pomodoro nào đang chạy.")
            return
        elapsed = (datetime.datetime.now() - session.start_time).seconds // 60
        phase_label = {"work": "🍅 Làm việc", "break": "☕ Nghỉ ngơi", "done": "✅ Xong"}.get(session.phase, session.phase)
        await ctx.reply(
            f"📊 **Pomodoro Status**\n"
            f"Phase: {phase_label}\n"
            f"Round: {session.current_round}/{session.total_rounds}\n"
            f"Thời gian: {session.work_minutes}p làm / {session.break_minutes}p nghỉ\n"
            f"Đã chạy: ~{elapsed} phút"
        )

    # ──────────────────────────────────────────────
    # TODO - MA TRẬN EISENHOWER
    # ──────────────────────────────────────────────

    # Q1=🔴 Quan trọng+Khẩn cấp  Q2=🟡 Quan trọng+Không khẩn cấp
    # Q3=🔵 Không quan trọng+Khẩn cấp  Q4=⚫ Không quan trọng+Không khẩn cấp
    _QUADRANTS = {
        "q1": ("Q1", "🔴", "Quan trọng & Khẩn cấp",       "Làm NGAY"),
        "q2": ("Q2", "🟡", "Quan trọng & Không khẩn cấp", "Lên LỊCH"),
        "q3": ("Q3", "🔵", "Không quan trọng & Khẩn cấp", "ỦY THÁC"),
        "q4": ("Q4", "⚫", "Không quan trọng & Không khẩn", "LOẠI BỎ"),
    }

    async def _resolve_todo(self, short_id: str, user_id: str):
        """Tìm todo bằng 8 ký tự đầu của ObjectId. Trả về document hoặc None."""
        if len(short_id) > 24:
            return None
        import re
        pattern = re.compile(f"^{re.escape(short_id)}", re.IGNORECASE)
        async for doc in self._todo.find({"user_id": user_id}):
            if pattern.match(str(doc["_id"])):
                return doc
        return None

    @commands.command(name='todoadd')
    async def todo_add(self, ctx: commands.Context, quadrant: str, *, title: str):
        """Thêm todo vào ma trận Eisenhower. Cách dùng: !todoadd <q1|q2|q3|q4> <tiêu đề>"""
        q = quadrant.lower()
        if q not in self._QUADRANTS:
            await ctx.send(
                "❌ Ô không hợp lệ! Chọn một trong:\n"
                "🔴 `q1` — Quan trọng & Khẩn cấp\n"
                "🟡 `q2` — Quan trọng & Không khẩn cấp\n"
                "🔵 `q3` — Không quan trọng & Khẩn cấp\n"
                "⚫ `q4` — Không quan trọng & Không khẩn cấp"
            )
            return
        _, emoji, label, action = self._QUADRANTS[q]
        doc = {
            "title": title,
            "quadrant": q,
            "done": False,
            "user_id": str(ctx.author.id),
        }
        result = await self._todo.insert_one(doc)
        await ctx.send(
            f"{emoji} Đã thêm vào **{q.upper()} — {label}** ({action})\n"
            f"📌 **{title}**\n"
            f"ID: `{result.inserted_id}`"
        )

    @commands.command(name='todolist')
    async def todo_list(self, ctx: commands.Context):
        """Xem ma trận Eisenhower. Cách dùng: !todolist"""
        todos = await self._todo.find(
            {"user_id": str(ctx.author.id), "done": False}
        ).to_list(length=100)

        if not todos:
            await ctx.send("📭 Ma trận trống, không có việc gì cần làm!")
            return

        # Nhóm theo quadrant
        groups: dict[str, list] = {"q1": [], "q2": [], "q3": [], "q4": []}
        for t in todos:
            q = t.get("quadrant", "q1")
            if q in groups:
                groups[q].append(t)

        lines = []
        for q, (label_short, emoji, label, action) in self._QUADRANTS.items():
            items = groups[q]
            lines.append(f"\n{emoji} **{label_short} — {label}** [{action}]")
            if items:
                for t in items:
                    lines.append(f"  ⬜ `{str(t['_id'])[:8]}` {t['title']}")
            else:
                lines.append("  _(trống)_")

        msg = "📊 **Ma trận Eisenhower**" + "\n".join(lines)
        if len(msg) > 1900:
            await ctx.send("📊 **Ma trận Eisenhower**" + "\n".join(lines[:40]))
        else:
            await ctx.send(msg)

    @commands.command(name='todoall')
    async def todo_all(self, ctx: commands.Context):
        """Xem tất cả todo kể cả đã xong. Cách dùng: !todoall"""
        todos = await self._todo.find(
            {"user_id": str(ctx.author.id)}
        ).to_list(length=100)

        if not todos:
            await ctx.send("📭 Chưa có todo nào!")
            return

        groups: dict[str, list] = {"q1": [], "q2": [], "q3": [], "q4": []}
        for t in todos:
            q = t.get("quadrant", "q1")
            if q in groups:
                groups[q].append(t)

        lines = []
        for q, (label_short, emoji, label, action) in self._QUADRANTS.items():
            items = groups[q]
            if not items:
                continue
            lines.append(f"\n{emoji} **{label_short} — {label}**")
            for t in items:
                status = "✅" if t["done"] else "⬜"
                lines.append(f"  {status} `{str(t['_id'])[:8]}` {t['title']}")

        await ctx.send("📊 **Tất cả Todo**" + "\n".join(lines))

    @commands.command(name='tododone')
    async def todo_done(self, ctx: commands.Context, todo_id: str):
        """Đánh dấu todo đã xong. Cách dùng: !tododone <id>"""
        doc = await self._resolve_todo(todo_id, str(ctx.author.id))
        if not doc:
            await ctx.send("❌ Không tìm thấy todo!")
            return
        await self._todo.update_one({"_id": doc["_id"]}, {"$set": {"done": True}})
        q = doc.get("quadrant", "q1")
        _, emoji, label, _ = self._QUADRANTS[q]
        await ctx.send(f"✅ Hoàn thành! {emoji} **{doc['title']}** ({label})")

    @commands.command(name='todoedit')
    async def todo_edit(self, ctx: commands.Context, todo_id: str, *, new_title: str):
        """Sửa tiêu đề todo. Cách dùng: !todoedit <id> <tiêu đề mới>"""
        doc = await self._resolve_todo(todo_id, str(ctx.author.id))
        if not doc:
            await ctx.send("❌ Không tìm thấy todo!")
            return
        await self._todo.update_one({"_id": doc["_id"]}, {"$set": {"title": new_title}})
        await ctx.send(f"✏️ Đã sửa thành: **{new_title}**")

    @commands.command(name='tododelete')
    async def todo_delete(self, ctx: commands.Context, todo_id: str):
        """Xóa todo. Cách dùng: !tododelete <id>"""
        doc = await self._resolve_todo(todo_id, str(ctx.author.id))
        if not doc:
            await ctx.send("❌ Không tìm thấy todo!")
            return
        await self._todo.delete_one({"_id": doc["_id"]})
        await ctx.send(f"🗑️ Đã xóa: **{doc['title']}**")

    @commands.command(name='todobump')
    async def todo_bump(self, ctx: commands.Context, todo_id: str, quadrant: str):
        """Chuyển todo sang ô khác. Cách dùng: !todobump <id> <q1|q2|q3|q4>"""
        q = quadrant.lower()
        if q not in self._QUADRANTS:
            await ctx.send("❌ Ô không hợp lệ! Dùng q1, q2, q3 hoặc q4")
            return
        doc = await self._resolve_todo(todo_id, str(ctx.author.id))
        if not doc:
            await ctx.send("❌ Không tìm thấy todo!")
            return
        await self._todo.update_one({"_id": doc["_id"]}, {"$set": {"quadrant": q}})
        _, emoji, label, action = self._QUADRANTS[q]
        await ctx.send(f"🔀 Đã chuyển **{doc['title']}** → {emoji} **{q.upper()} — {label}** ({action})")

    @commands.command(name='todohelp')
    async def todo_help(self, ctx: commands.Context):
        """Hiển thị hướng dẫn sử dụng Todo Eisenhower"""
        await ctx.send(
            "📊 **Ma trận Eisenhower — Hướng dẫn**\n\n"
            "🔴 `q1` Quan trọng & Khẩn cấp → **Làm NGAY**\n"
            "🟡 `q2` Quan trọng & Không khẩn → **Lên LỊCH**\n"
            "🔵 `q3` Không quan trọng & Khẩn cấp → **ỦY THÁC**\n"
            "⚫ `q4` Không quan trọng & Không khẩn → **LOẠI BỎ**\n\n"
            "**Lệnh:**\n"
            "`!todoadd <q1-q4> <tiêu đề>` — Thêm todo\n"
            "`!todolist` — Xem ma trận (chưa xong)\n"
            "`!todoall` — Xem tất cả kể cả đã xong\n"
            "`!tododone <id>` — Đánh dấu hoàn thành\n"
            "`!todoedit <id> <tiêu đề mới>` — Sửa tiêu đề\n"
            "`!todobump <id> <q1-q4>` — Chuyển sang ô khác\n"
            "`!tododelete <id>` — Xóa todo\n\n"
            "💡 ID lấy 8 ký tự đầu từ `!todolist`"
        )


async def setup(bot: MyBot):
    await bot.add_cog(Test(bot))