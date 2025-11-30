from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler
from database import db

BROADCAST_MSG, EDIT_BATCHES = range(2)

async def owner_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != int(context.bot_data.get('OWNER_ID')):
        return
    keyboard = [
        [InlineKeyboardButton("📊 Stats", callback_data="owner_stats")],
        [InlineKeyboardButton("�� Active", callback_data="owner_active"), InlineKeyboardButton("🚫 Banned", callback_data="owner_banned")],
        [InlineKeyboardButton("📢 Broadcast", callback_data="owner_broadcast")],
        [InlineKeyboardButton("🚫 Ban", callback_data="owner_ban"), InlineKeyboardButton("✅ Unban", callback_data="owner_unban")],
        [InlineKeyboardButton("📚 Edit Batches", callback_data="edit_batches")],
        [InlineKeyboardButton("💳 Payments", callback_data="owner_payments")]
    ]
    await update.message.reply_text(f"👑 Owner Panel - {context.bot_data.get('OWNER_NAME','Owner')}", reply_markup=InlineKeyboardMarkup(keyboard))

async def owner_stats_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()
    await update.callback_query.message.reply_text(f"📊 Stats\n\n👥 Users: {len(db.get_all_users())}\n✅ Active: {len(db.get_active_users())}\n🚫 Banned: {len(db.get_banned_users())}\n💳 Pending: {len(db.get_pending_payments())}\n⏳ Awaiting Token: {len(db.data['awaiting_token'])}\n🤖 Clones: {sum(1 for c in db.data['cloned_bots'].values() if c.get('active'))}")

async def owner_active_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()
    active = db.get_active_users()
    if not active:
        await update.callback_query.message.reply_text("No active users.")
        return
    keyboard = [[InlineKeyboardButton(f"{u['name']} (@{u.get('username','None')})", callback_data=f"userinfo_{uid}")] for uid, u in list(active.items())[:50]]
    await update.callback_query.message.reply_text(f"✅ Active ({len(active)})", reply_markup=InlineKeyboardMarkup(keyboard))

async def owner_banned_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()
    banned = db.get_banned_users()
    if not banned:
        await update.callback_query.message.reply_text("No banned users.")
        return
    keyboard = [[InlineKeyboardButton(f"{u['name']} (@{u.get('username','None')})", callback_data=f"userinfo_{uid}")] for uid, u in banned.items()]
    await update.callback_query.message.reply_text(f"🚫 Banned ({len(banned)})", reply_markup=InlineKeyboardMarkup(keyboard))

async def user_info_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = int(update.callback_query.data.split('_')[1])
    user = db.get_user(uid)
    if not user:
        await update.callback_query.answer("Not found", show_alert=True)
        return
    await update.callback_query.answer()
    is_banned = db.is_banned(uid)
    keyboard = [[InlineKeyboardButton("✅ Unban" if is_banned else "🚫 Ban", callback_data=f"{'unban' if is_banned else 'ban'}_{uid}")]]
    await update.callback_query.message.reply_text(f"👤 {user['name']}\n@{user.get('username','None')}\nID: {uid}\nStatus: {'🚫 Banned' if is_banned else '✅ Active'}", reply_markup=InlineKeyboardMarkup(keyboard))

async def ban_user_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = int(update.callback_query.data.split('_')[1])
    db.ban_user(uid)
    await update.callback_query.answer("✅ Banned!", show_alert=True)
    await update.callback_query.message.edit_text(f"✅ User {uid} banned.")

async def unban_user_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = int(update.callback_query.data.split('_')[1])
    db.unban_user(uid)
    await update.callback_query.answer("✅ Unbanned!", show_alert=True)
    await update.callback_query.message.edit_text(f"✅ User {uid} unbanned.")

async def owner_ban_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()
    await update.callback_query.message.reply_text("🚫 Send user ID to ban:")
    context.user_data['awaiting_ban'] = True

async def owner_unban_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()
    await update.callback_query.message.reply_text("✅ Send user ID to unban:")
    context.user_data['awaiting_unban'] = True

async def owner_broadcast_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()
    await update.callback_query.message.reply_text("📢 Send broadcast message.\n/cancel to stop")
    return BROADCAST_MSG

async def receive_broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message
    users = db.get_active_users()
    status = await msg.reply_text(f"📤 Broadcasting...")
    success = 0
    for uid in users.keys():
        try:
            if msg.text:
                await context.bot.send_message(int(uid), msg.text)
            elif msg.photo:
                await context.bot.send_photo(int(uid), msg.photo[-1].file_id, caption=msg.caption or "")
            elif msg.video:
                await context.bot.send_video(int(uid), msg.video.file_id, caption=msg.caption or "")
            elif msg.document:
                await context.bot.send_document(int(uid), msg.document.file_id, caption=msg.caption or "")
            elif msg.voice:
                await context.bot.send_voice(int(uid), msg.voice.file_id)
            success += 1
        except:
            pass
    await status.edit_text(f"✅ Sent to {success} users")
    return ConversationHandler.END

async def edit_batches_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()
    await update.callback_query.message.reply_text(f"📚 Current:\n{db.get_paid_batches()}\n\nSend new text.\n/cancel to stop")
    return EDIT_BATCHES

async def receive_batches_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    db.set_paid_batches(update.message.text)
    await update.message.reply_text(f"✅ Updated!\n\n{update.message.text}")
    return ConversationHandler.END

async def owner_payments_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()
    pending = db.get_pending_payments()
    if not pending:
        await update.callback_query.message.reply_text("💳 No pending payments.")
        return
    for p in pending:
        user = db.get_user(p['user_id'])
        keyboard = [[InlineKeyboardButton("✅", callback_data=f"approve_{p['id']}_{p['user_id']}"), InlineKeyboardButton("❌", callback_data=f"reject_{p['id']}_{p['user_id']}")]]
        await context.bot.send_photo(update.callback_query.message.chat_id, p['screenshot'], caption=f"💳 #{p['id']}\n\n{user['name'] if user else 'Unknown'}\nID: {p['user_id']}\n\n{p['plan_days']}d - ₹{p['plan_price']}", reply_markup=InlineKeyboardMarkup(keyboard))

async def cancel_conversation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("❌ Cancelled")
    return ConversationHandler.END
