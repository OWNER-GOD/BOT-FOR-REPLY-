import os
import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, ConversationHandler, filters
from database import db
from user_handlers import *
from owner_handlers import *

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

BOT_TOKEN = os.getenv('BOT_TOKEN')
OWNER_ID = int(os.getenv('8371945129'))
OWNER_NAME = os.getenv('OWNER_NAME', 'Sam')

async def start(update: Update, context):
    context.bot_data['OWNER_ID'] = OWNER_ID
    context.bot_data['OWNER_NAME'] = OWNER_NAME
    if update.effective_user.id == OWNER_ID:
        await owner_panel(update, context)
    else:
        await user_panel(update, context)

async def handle_text(update: Update, context):
    context.bot_data['OWNER_ID'] = OWNER_ID
    context.bot_data['OWNER_NAME'] = OWNER_NAME
    uid = update.effective_user.id
    msg = update.message
    if uid == OWNER_ID:
        if context.user_data.get('awaiting_ban'):
            try:
                db.ban_user(int(msg.text))
                await msg.reply_text(f"✅ User {msg.text} banned!")
                context.user_data['awaiting_ban'] = False
                return
            except:
                await msg.reply_text("❌ Invalid ID:")
                return
        if context.user_data.get('awaiting_unban'):
            try:
                db.unban_user(int(msg.text))
                await msg.reply_text(f"✅ User {msg.text} unbanned!")
                context.user_data['awaiting_unban'] = False
                return
            except:
                await msg.reply_text("❌ Invalid ID:")
                return
        if msg.reply_to_message:
            target = db.get_user_from_msg(msg.reply_to_message.message_id)
            if target:
                try:
                    await context.bot.send_message(target, msg.text)
                    await msg.reply_text(f"✅ Sent to {target}!")
                    return
                except:
                    pass
    await handle_user_message(update, context)

async def handle_media(update: Update, context):
    context.bot_data['OWNER_ID'] = OWNER_ID
    context.bot_data['OWNER_NAME'] = OWNER_NAME
    uid = update.effective_user.id
    msg = update.message
    if uid == OWNER_ID and msg.reply_to_message:
        target = db.get_user_from_msg(msg.reply_to_message.message_id)
        if target:
            try:
                if msg.photo:
                    await context.bot.send_photo(target, msg.photo[-1].file_id, caption=msg.caption or "")
                elif msg.video:
                    await context.bot.send_video(target, msg.video.file_id, caption=msg.caption or "")
                elif msg.document:
                    await context.bot.send_document(target, msg.document.file_id, caption=msg.caption or "")
                elif msg.voice:
                    await context.bot.send_voice(target, msg.voice.file_id)
                elif msg.audio:
                    await context.bot.send_audio(target, msg.audio.file_id, caption=msg.caption or "")
                await msg.reply_text(f"✅ Sent!")
                return
            except:
                pass
    if msg.photo and 'selected_plan' in context.user_data:
        await handle_payment_screenshot(update, context)
        return
    await handle_user_message(update, context)

async def handle_callback(update: Update, context):
    context.bot_data['OWNER_ID'] = OWNER_ID
    context.bot_data['OWNER_NAME'] = OWNER_NAME
    d = update.callback_query.data
    if d == "user_send":
        await user_send_callback(update, context)
    elif d == "paid_batches":
        await paid_batches_callback(update, context)
    elif d == "clone_bot":
        await clone_bot_callback(update, context)
    elif d.startswith("plan_"):
        await plan_selected(update, context)
    elif d == "my_clone":
        await my_clone_callback(update, context)
    elif d == "user_help":
        await user_help_callback(update, context)
    elif d == "cancel_payment":
        await cancel_payment_callback(update, context)
    elif d == "owner_stats":
        await owner_stats_callback(update, context)
    elif d == "owner_active":
        await owner_active_callback(update, context)
    elif d == "owner_banned":
        await owner_banned_callback(update, context)
    elif d.startswith("userinfo_"):
        await user_info_callback(update, context)
    elif d.startswith("ban_") and not d.startswith("ban_user"):
        await ban_user_callback(update, context)
    elif d.startswith("unban_") and not d.startswith("unban_user"):
        await unban_user_callback(update, context)
    elif d == "owner_ban":
        await owner_ban_callback(update, context)
    elif d == "owner_unban":
        await owner_unban_callback(update, context)
    elif d == "owner_broadcast":
        await owner_broadcast_callback(update, context)
    elif d == "edit_batches":
        await edit_batches_callback(update, context)
    elif d == "owner_payments":
        await owner_payments_callback(update, context)
    elif d.startswith("approve_"):
        parts = d.split("_")
        payment = db.approve_payment(int(parts[1]))
        if payment:
            await update.callback_query.answer("✅ Approved!", show_alert=True)
            await update.callback_query.message.edit_caption(caption=update.callback_query.message.caption + "\n\n✅ APPROVED")
            db.set_awaiting_token(int(parts[2]), payment)
            await context.bot.send_message(int(parts[2]), "🎉 Approved!\n\nNow send your bot token from @BotFather:\n\n1. /newbot\n2. Copy token\n3. Send here\n\n⚠️ Send ONLY the token!")
    elif d.startswith("reject_"):
        parts = d.split("_")
        if db.reject_payment(int(parts[1])):
            await update.callback_query.answer("❌ Rejected!", show_alert=True)
            await update.callback_query.message.edit_caption(caption=update.callback_query.message.caption + "\n\n❌ REJECTED")
            await context.bot.send_message(int(parts[2]), "❌ Payment Rejected\n\nContact admin.")

def main():
    if not BOT_TOKEN or not OWNER_ID:
        logger.error("❌ Missing BOT_TOKEN or OWNER_ID!")
        return
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(ConversationHandler(
        entry_points=[CallbackQueryHandler(owner_broadcast_callback, pattern="^owner_broadcast$")],
        states={BROADCAST_MSG: [MessageHandler(filters.ALL & ~filters.COMMAND, receive_broadcast)]},
        fallbacks=[CommandHandler("cancel", cancel_conversation)]
    ))
    app.add_handler(ConversationHandler(
        entry_points=[CallbackQueryHandler(edit_batches_callback, pattern="^edit_batches$")],
        states={EDIT_BATCHES: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_batches_text)]},
        fallbacks=[CommandHandler("cancel", cancel_conversation)]
    ))
    app.add_handler(CallbackQueryHandler(handle_callback))
    app.add_handler(MessageHandler(filters.PHOTO | filters.VIDEO | filters.Document.ALL | filters.VOICE | filters.AUDIO, handle_media))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    logger.info("🚀 Main Bot Starting...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()
