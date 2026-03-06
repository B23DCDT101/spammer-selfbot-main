import discord
from discord.ext import commands
from motor.motor_asyncio import AsyncIOMotorClient
from bson import ObjectId
from bson.errors import InvalidId
import logging
import os

logger = logging.getLogger(__name__)


class Todo(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        mongo_uri = os.getenv("MONGO_URI", "mongodb://localhost:27017")
        self._client = AsyncIOMotorClient(mongo_uri)
        self._col = self._client["todo_db"]["todos"]
        logger.info("Todo cog connected to MongoDB")

    def cog_unload(self):
        self._client.close()

    # ── helpers ──────────────────────────────────────────

    def _to_id(self, raw: str) -> ObjectId | None:
        """Chuyển chuỗi sang ObjectId, trả None nếu không hợp lệ."""
        try:
            return ObjectId(raw)
        except (InvalidId, Exception):
            return None

    # ── commands ─────────────────────────────────────────

    @commands.command(name="todoadd")
    async def todo_add(self, ctx: commands.Context, *, title: str):
        """Thêm todo mới. Cách dùng: !todoadd <tiêu đề>"""
        doc = {
            "title": title,
            "description": None,
            "done": False,
            "user_id": str(ctx.author.id),
        }
        result = await self._col.insert_one(doc)
        short_id = str(result.inserted_id)
        await ctx.send(
            f"✅ Đã thêm: **{title}**\n"
            f"ID: `{result.inserted_id}` (gõ `{short_id}...` cũng được)"
        )

    @commands.command(name="todolist")
    async def todo_list(self, ctx: commands.Context):
        """Xem danh sách todo. Cách dùng: !todolist"""
        todos = await self._col.find(
            {"user_id": str(ctx.author.id)}
        ).to_list(length=50)

        if not todos:
            await ctx.send("📭 Chưa có todo nào!")
            return

        lines = [
            f"{'✅' if t['done'] else '⬜'} `{str(t['_id'])}` — {t['title']}"
            for t in todos
        ]
        # Chia nhỏ nếu danh sách quá dài (>2000 ký tự)
        msg = "📋 **Todo list:**\n" + "\n".join(lines)
        if len(msg) > 1900:
            for i in range(0, len(lines), 20):
                await ctx.send("📋 **Todo list:**\n" + "\n".join(lines[i:i+20]))
        else:
            await ctx.send(msg)

    @commands.command(name="tododone")
    async def todo_done(self, ctx: commands.Context, todo_id: str):
        """Đánh dấu todo đã xong. Cách dùng: !tododone <id>"""
        oid = self._to_id(todo_id)
        if not oid:
            await ctx.send("❌ ID không hợp lệ!")
            return
        result = await self._col.update_one(
            {"_id": oid, "user_id": str(ctx.author.id)},
            {"$set": {"done": True}}
        )
        if result.matched_count == 0:
            await ctx.send("❌ Không tìm thấy todo!")
            return
        await ctx.send("✅ Đã đánh dấu hoàn thành!")

    @commands.command(name="todoedit")
    async def todo_edit(self, ctx: commands.Context, todo_id: str, *, new_title: str):
        """Sửa tiêu đề todo. Cách dùng: !todoedit <id> <tiêu đề mới>"""
        oid = self._to_id(todo_id)
        if not oid:
            await ctx.send("❌ ID không hợp lệ!")
            return
        result = await self._col.find_one_and_update(
            {"_id": oid, "user_id": str(ctx.author.id)},
            {"$set": {"title": new_title}},
            return_document=True,
        )
        if not result:
            await ctx.send("❌ Không tìm thấy todo!")
            return
        await ctx.send(f"✏️ Đã sửa thành: **{result['title']}**")

    @commands.command(name="tododelete")
    async def todo_delete(self, ctx: commands.Context, todo_id: str):
        """Xóa todo. Cách dùng: !tododelete <id>"""
        oid = self._to_id(todo_id)
        if not oid:
            await ctx.send("❌ ID không hợp lệ!")
            return
        result = await self._col.delete_one(
            {"_id": oid, "user_id": str(ctx.author.id)}
        )
        if result.deleted_count == 0:
            await ctx.send("❌ Không tìm thấy todo!")
            return
        await ctx.send("🗑️ Đã xóa!")

    @commands.command(name="todohelp")
    async def todo_help(self, ctx: commands.Context):
        """Hiển thị hướng dẫn sử dụng Todo"""
        await ctx.send(
            "📋 **Todo - Hướng dẫn sử dụng**\n\n"
            "**!todoadd <tiêu đề>** — Thêm todo mới\n"
            "**!todolist** — Xem danh sách (tối đa 50)\n"
            "**!tododone <id>** — Đánh dấu hoàn thành\n"
            "**!todoedit <id> <tiêu đề mới>** — Sửa tiêu đề\n"
            "**!tododelete <id>** — Xóa todo\n\n"
        )


async def setup(bot: commands.Bot):
    await bot.add_cog(Todo(bot))
