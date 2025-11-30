from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from database import db
import logging

logger = logging.getLogger(__name__)

PLANS = [{'days': 1, 'price': 2}, {'days': 7, 'price': 12}, {'days': 15, 'price': 18}, {'days': 30, 'price': 25}]
UPI_ID = "thefatherofficial-3@okaxis"

async def user_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if db.is_banned(user.id):
        await update.message.reply_text("⛔️ You are banned.")
        return
    db.add_user(user.id, user.username, user.first_name)
    keyboard = [
        [InlineKeyboardButton("📩 Send msg to Admin", callback_data="user_send")],
        [InlineKeyboardButton("📚 Paid Batches List", callback_data="paid_batches")],
        [InlineKeyboardButton("🤖 Want's to Clone Bot?", callback_data="clone_bot")],
        [InlineKeyboardButton("📋 My Clone Bot", callback_data="my_clone")],
        [InlineKeyboardButton("ℹ️ Help", callback_data="user_help")]
    ]
    await update.message.reply_text("Hello Namaste !!! 🙏\n\nYou can send any Paid Batch Related Queries to me\n\nJust Send a msg ✍️", reply_markup=InlineKeyboardMarkup(keyboard))

async def handle_user_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    msg = update.message
    if db.is_banned(user.id):
        return
    if db.is_awaiting_token(user.id):
        await handle_bot_token(update, context)
        return
    db.add_user(user.id, user.username, user.first_name)
    owner_id = int(context.bot_data.get('OWNER_ID'))
    try:
        sent = await context.bot.send_message(owner_id, f"📨 From: {user.first_name} (ID: {user.id})\n@{user.username or 'None'}\n\n💬 Content:", parse_mode='HTML')
        db.map_message(user.id, sent.message_id)
        if msg.text:
            content = await context.bot.send_message(owner_id, msg.text)
        elif msg.photo:
            content = await context.bot.send_photo(owner_id, msg.photo[-1].file_id, caption=msg.caption or "")
        elif msg.video:
            content = await context.bot.send_video(owner_id, msg.video.file_id, caption=msg.caption or "")
        elif msg.document:
            content = await context.bot.send_document(owner_id, msg.document.file_id, caption=msg.caption or "")
        elif msg.voice:
            content = await context.bot.send_voice(owner_id, msg.voice.file_id)
        elif msg.audio:
            content = await context.bot.send_audio(owner_id, msg.audio.file_id, caption=msg.caption or "")
        else:
            content = None
        if content:
            db.map_message(user.id, content.message_id)
        await msg.reply_text(db.get_random_greeting())
    except Exception as e:
        await msg.reply_text("❌ Failed to send.")

async def handle_bot_token(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    msg = update.message
    if not msg.text:
        await msg.reply_text("❌ Send only bot token as text.")
        return
    token = msg.text.strip()
    if ':' not in token or len(token) < 40:
        await msg.reply_text("❌ Invalid token format!")
        return
    payment_data = db.get_awaiting_token_data(user.id)
    if not payment_data:
        await msg.reply_text("❌ Payment data not found.")
        db.remove_awaiting_token(user.id)
        return
    try:
        from telegram import Bot
        test_bot = Bot(token=token)
        bot_info = await test_bot.get_me()
        db.add_cloned_bot(user.id, token, payment_data['plan_days'], bot_info.username)
        db.remove_awaiting_token(user.id)
        await msg.reply_text(f"🎉 Clone Bot Ready!\n\n🤖 @{bot_info.username}\n📅 {payment_data['plan_days']} days\n\n✅ Active! Users can message you.\n\nUse /start")
        await context.bot.send_message(int(context.bot_data.get('OWNER_ID')), f"✅ Clone: @{bot_info.username}\nOwner: {user.first_name} ({user.id})\nPlan: {payment_data['plan_days']}d - ₹{payment_data['plan_price']}")
    except Exception as e:
        await msg.reply_text(f"❌ Invalid token!\n{str(e)}")

async def user_send_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()
    await update.callback_query.message.reply_text("📝 Send your message now:")

async def paid_batches_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()
    await update.callback_query.message.reply_text(f"📚 Paid Batches\n\n{db.get_paid_batches()}")

async def clone_bot_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()
    keyboard = [[InlineKeyboardButton(f"{p['days']}Day{'s' if p['days']>1 else ''} - ₹{p['price']}", callback_data=f"plan_{p['days']}_{p['price']}")] for p in PLANS]
    await update.callback_query.message.reply_text("🤖 Choose a plan:", reply_markup=InlineKeyboardMarkup(keyboard))

async def plan_selected(update: Update, context: ContextTypes.DEFAULT_TYPE):
    parts = update.callback_query.data.split('_')
    days, price = int(parts[1]), int(parts[2])
    await update.callback_query.answer()
    await update.callback_query.message.reply_text(f"�� Payment\n\n📦 {days} day{'s' if days>1 else ''}\n💰 ₹{price}\n🔗 UPI: {UPI_ID}\n\n1. Pay ₹{price} to {UPI_ID}\n2. Note: {days}days\n3. Send screenshot here", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("❌ Cancel", callback_data="cancel_payment")]]))
    context.user_data['selected_plan'] = {'days': days, 'price': price}

async def handle_payment_screenshot(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if 'selected_plan' not in context.user_data or not update.message.photo:
        return
    plan = context.user_data['selected_plan']
    user = update.effective_user
    payment = db.add_pending_payment(user.id, plan['days'], plan['price'], update.message.photo[-1].file_id)
    await update.message.reply_text(f"✅ Screenshot received!\n\n🔍 Under review\n⏳ Wait for approval\n\nID: #{payment['id']}")
    keyboard = [[InlineKeyboardButton("✅ Approve", callback_data=f"approve_{payment['id']}_{user.id}"), InlineKeyboardButton("❌ Reject", callback_data=f"reject_{payment['id']}_{user.id}")]]
    await context.bot.send_photo(int(context.bot_data.get('OWNER_ID')), update.message.photo[-1].file_id, caption=f"💳 Payment #{payment['id']}\n\n👤 {user.first_name}\n🆔 {user.id}\n@{user.username or 'None'}\n\n📦 {payment['plan_days']}d\n💰 ₹{payment['plan_price']}", reply_markup=InlineKeyboardMarkup(keyboard))
    del context.user_data['selected_plan']

async def my_clone_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()
    clone = db.get_cloned_bot(update.callback_query.from_user.id)
    if not clone:
        await update.callback_query.message.reply_text("🤖 No active clone bot.\n\nPurchase a plan!")
        return
    from datetime import datetime
    expiry = datetime.fromisoformat(clone['expiry'])
    days_left = (expiry - datetime.now()).days
    users = db.get_clone_bot_users(update.callback_query.from_user.id)
    await update.callback_query.message.reply_text(f"🤖 Your Clone Bot\n\n✅ Active\n🤖 @{clone['bot_username']}\n📅 {days_left} days left\n⏰ Expires: {expiry.strftime('%Y-%m-%d')}\n👥 Users: {len(users)}")

async def user_help_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()
    await update.callback_query.message.reply_text("ℹ️ Help\n\n1️⃣ Send msg to Admin\n2️⃣ Paid Batches List\n3️⃣ Clone Bot (purchase)\n4️⃣ My Clone Bot (status)\n\n💡 Need help? Message admin!")

async def cancel_payment_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer("❌ Cancelled")
    if 'selected_plan' in context.user_data:
        del context.user_data['selected_plan']
    await update.callback_query.message.reply_text("❌ Cancelled. Use /start")
