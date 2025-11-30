import asyncio
import logging
from telegram import Update, Bot
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from database import db

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class CloneBotHandler:
    def __init__(self, owner_id, token, username):
        self.owner_id = owner_id
        self.token = token
        self.username = username
    
    async def start_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        db.add_clone_bot_user(self.owner_id, user.id, user.username, user.first_name)
        await update.message.reply_text(f"👋 Welcome to @{self.username}!\n\nSend any message:")
    
    async def handle_user_msg(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        msg = update.message
        db.add_clone_bot_user(self.owner_id, user.id, user.username, user.first_name)
        try:
            sent = await context.bot.send_message(self.owner_id, f"📨 From: {user.first_name} ({user.id})\n@{user.username or 'None'}\nVia: @{self.username}\n\n💬:", parse_mode='HTML')
            db.map_clone_message(self.owner_id, user.id, sent.message_id)
            if msg.text:
                c = await context.bot.send_message(self.owner_id, msg.text)
            elif msg.photo:
                c = await context.bot.send_photo(self.owner_id, msg.photo[-1].file_id, caption=msg.caption or "")
            elif msg.video:
                c = await context.bot.send_video(self.owner_id, msg.video.file_id, caption=msg.caption or "")
            elif msg.document:
                c = await context.bot.send_document(self.owner_id, msg.document.file_id, caption=msg.caption or "")
            elif msg.voice:
                c = await context.bot.send_voice(self.owner_id, msg.voice.file_id)
            elif msg.audio:
                c = await context.bot.send_audio(self.owner_id, msg.audio.file_id, caption=msg.caption or "")
            else:
                c = None
            if c:
                db.map_clone_message(self.owner_id, user.id, c.message_id)
            await msg.reply_text("✅ Sent to owner!")
        except Exception as e:
            await msg.reply_text("❌ Failed")
    
    async def handle_owner_reply(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if update.effective_user.id != self.owner_id or not update.message.reply_to_message:
            return
        target = db.get_clone_user_from_msg(self.owner_id, update.message.reply_to_message.message_id)
        if not target:
            return
        msg = update.message
        try:
            if msg.text:
                await context.bot.send_message(target, msg.text)
            elif msg.photo:
                await context.bot.send_photo(target, msg.photo[-1].file_id, caption=msg.caption or "")
            elif msg.video:
                await context.bot.send_video(target, msg.video.file_id, caption=msg.caption or "")
            elif msg.document:
                await context.bot.send_document(target, msg.document.file_id, caption=msg.caption or "")
            elif msg.voice:
                await context.bot.send_voice(target, msg.voice.file_id)
            elif msg.audio:
                await context.bot.send_audio(target, msg.audio.file_id, caption=msg.caption or "")
            await msg.reply_text("✅ Reply sent!")
        except Exception as e:
            await msg.reply_text(f"❌ Failed")
    
    async def start_bot(self):
        try:
            app = Application.builder().token(self.token).build()
            app.add_handler(CommandHandler("start", self.start_handler))
            app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_owner_reply))
            app.add_handler(MessageHandler(filters.PHOTO | filters.VIDEO | filters.Document.ALL | filters.VOICE | filters.AUDIO, self.handle_owner_reply))
            app.add_handler(MessageHandler(filters.ALL & ~filters.COMMAND, self.handle_user_msg))
            logger.info(f"🤖 Starting @{self.username}")
            await app.initialize()
            await app.start()
            await app.updater.start_polling(allowed_updates=Update.ALL_TYPES)
        except Exception as e:
            logger.error(f"❌ @{self.username}: {e}")

async def start_all_clone_bots():
    logger.info("🔄 Clone Manager Starting...")
    bots = db.get_all_active_cloned_bots()
    if not bots:
        logger.info("No clones")
        await asyncio.sleep(36000)
        return
    logger.info(f"Found {len(bots)} clone(s)")
    tasks = [CloneBotHandler(int(oid), b['bot_token'], b['bot_username']).start_bot() for oid, b in bots.items()]
    await asyncio.gather(*tasks)
    while True:
        await asyncio.sleep(3600)

def main():
    try:
        asyncio.run(start_all_clone_bots())
    except:
        pass

if __name__ == '__main__':
    main()
