import os
import json
import random
import smtplib
from email.message import EmailMessage
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler, CallbackQueryHandler,
    filters, ContextTypes
)
from telegram.constants import ChatMemberStatus # لاستخدام حالة العضوية

# === إعدادات البوت ===
# ⚠️ استبدل التوكن بالتوكن الجديد الخاص بك
BOT_TOKEN = "8578684413:AAGy_qXKox1BQMci5xfw9GOc-AXa_VT6nZo"
ADMIN_ID = 7044930530  # الآيدي الخاص بك

# === إعدادات القناة (الجديدة) ===
# ضع معرف القناة (مع @) التي يجب على المستخدم الاشتراك فيها
# مثال: @ssdionlain 
CHANNEL_USERNAME = "@ssdionlain" 

# === إعدادات الإيميل ===
SENDER_EMAIL = "ngmtm2024@gmail.com"
EMAIL_PASSWORD = "kydr nsms vsib ugku" 

FILES = {}  # اسم الملف → {path, type, file_id}
USERS_FILE = "users.json"
FILES_RECORD = "files_record.json" 

# تحميل البيانات
if os.path.exists(USERS_FILE):
    with open(USERS_FILE, "r") as f:
        USERS = json.load(f)
else:
    USERS = {}

if os.path.exists(FILES_RECORD):
    with open(FILES_RECORD, "r") as f:
        FILES = json.load(f)

if not os.path.exists("downloads"):
    os.makedirs("downloads")

# ==== وظائف مساعدة ====
def save_users():
    with open(USERS_FILE, "w") as f:
        json.dump(USERS, f, indent=4)

def save_files_record():
    with open(FILES_RECORD, "w") as f:
        json.dump(FILES, f, indent=4)

def detect_type(filename):
    ext = filename.split(".")[-1].lower() if "." in filename else ""
    if ext in ["jpg", "jpeg", "png", "gif", "webp"]:
        return "Image"
    elif ext in ["mp4", "mov", "avi", "mkv"]:
        return "Video"
    elif ext in ["pdf"]:
        return "PDF"
    else:
        return "Other"

def send_verification_email(to_email, code):
    try:
        msg = EmailMessage()
        msg.set_content(f"Your verification code is: {code}")
        msg["Subject"] = "Telegram Bot Verification Code"
        msg["From"] = SENDER_EMAIL
        msg["To"] = to_email

        server = smtplib.SMTP_SSL("smtp.gmail.com", 465)
        server.login(SENDER_EMAIL, EMAIL_PASSWORD)
        server.send_message(msg)
        server.quit()
        return True
    except Exception as e:
        print(f"Error sending email: {e}")
        return False
        
async def is_member(user_id: int, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """يتحقق مما إذا كان المستخدم عضواً في القناة الإلزامية."""
    if user_id == ADMIN_ID: # الآدمن لديه وصول دائم
        return True
    
    try:
        # get_chat_member تتحقق من حالة العضوية
        member = await context.bot.get_chat_member(CHANNEL_USERNAME, user_id)
        # المستخدم يجب أن يكون عضواً أو مُنشئاً أو مُديراً
        return member.status in [
            ChatMemberStatus.MEMBER,
            ChatMemberStatus.OWNER,
            ChatMemberStatus.ADMINISTRATOR
        ]
    except Exception as e:
        print(f"Error checking membership: {e}")
        # إذا حدث خطأ (مثل عدم وجود البوت كمسؤول في القناة)
        return False

# ==== الهاندلرز (Handlers) ====

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    
    # 1. إذا لم يكن المستخدم مفعلاً، نطلب الإيميل
    if user_id not in USERS or not USERS[user_id].get("verified"):
        context.user_data["mode"] = "waiting_email"
        await update.message.reply_text(
            "مرحباً! هذا البوت محمي. الرجاء إرسال بريدك الإلكتروني لاستلام كود التحقق."
        )
        return

    # 2. إذا كان مفعلاً، نتحقق من الاشتراك
    await check_subscription_status(update, context, is_new_message=True)
    

async def check_subscription_status(update: Update, context: ContextTypes.DEFAULT_TYPE, is_new_message=False):
    """التحقق من حالة الاشتراك وعرض رسالة الاشتراك الإجباري."""
    
    user_id = update.effective_user.id
    
    if await is_member(user_id, context):
        # إذا كان عضواً، نعرض القائمة الرئيسية
        await show_main_menu(update, context, is_new_message=is_new_message)
    else:
        # إذا لم يكن عضواً، نطلب الاشتراك
        keyboard = [
            [InlineKeyboardButton("اشترك في القناة 📢", url=f"https://t.me/{CHANNEL_USERNAME.replace('@', '')}")],
            [InlineKeyboardButton("✅ تحقّق من الاشتراك", callback_data="check_subscription")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        message = "🛑 الوصول محظور!\n\nللوصول إلى محتوى البوت، يجب عليك أولاً الاشتراك في قناتنا."
        
        if update.callback_query:
            await update.callback_query.edit_message_text(message, reply_markup=reply_markup)
        elif is_new_message:
            await update.message.reply_text(message, reply_markup=reply_markup)
        else:
            # في حال تم استدعاؤه من مكان آخر غير متوقع
             await context.bot.send_message(user_id, message, reply_markup=reply_markup)


async def check_subscription_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """يعالج الضغط على زر التحقق من الاشتراك."""
    query = update.callback_query
    await query.answer("جاري التحقق من حالة اشتراكك...")
    
    # نستخدم نفس دالة التحقق من الاشتراك
    await check_subscription_status(update, context, is_new_message=False)


async def show_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE, is_new_message=False):
    """يعرض القائمة الرئيسية للمستخدم العادي والآدمن."""
    
    keyboard = []
    
    if update.effective_user.id == ADMIN_ID:
        keyboard.append([InlineKeyboardButton("⚙️ لوحة تحكم الآدمن", callback_data="admin_panel")])

    keyboard.append([InlineKeyboardButton("📚 تصفح الملفات حسب النوع", callback_data="show_types")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    if update.callback_query:
        await update.callback_query.edit_message_text("الرجاء الاختيار من القائمة الرئيسية:", reply_markup=reply_markup)
    elif is_new_message:
        await update.message.reply_text("الرجاء الاختيار من القائمة الرئيسية:", reply_markup=reply_markup)
    

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    mode = context.user_data.get("mode")
    text = update.message.text

    # منطق الآدمن لرفع الملفات
    if update.effective_user.id == ADMIN_ID and mode == "admin_waiting_file":
        
        if update.message.document:
            doc = update.message.document
            file_name = doc.file_name
            file_id = doc.file_id
            
            if file_name in FILES:
                await update.message.reply_text(f"الملف: **{file_name}** موجود مسبقاً. الرجاء تغيير اسمه أو حذفه أولاً.")
                return

            new_file = await context.bot.get_file(file_id)
            file_path = f"downloads/{file_name}"
                
            await new_file.download_to_drive(file_path)
            
            file_type = detect_type(file_name)
            
            FILES[file_name] = {"path": file_path, "type": file_type, "file_id": file_id} 
            save_files_record()
            
            context.user_data["mode"] = None
            
            await update.message.reply_text(
                f"✅ تم حفظ الملف: **{file_name}** كـ **{file_type}**.\nعد الآن إلى لوحة التحكم عبر الأزرار."
            )
            return

        elif update.message.photo or update.message.video:
            context.user_data["mode"] = None 
            await update.message.reply_text("❌ يجب إرسال الملف كمستند (Document). تم إلغاء عملية الإضافة.")
            return

        elif text:
            await update.message.reply_text("🚫 الرجاء إرسال **ملف** (Document) أو اضغط على إلغاء الإضافة.")
            return

    # منطق استلام الإيميل والتحقق منه (يتم تنفيذه قبل التحقق من الاشتراك)
    if mode == "waiting_email" and text:
        email = text.strip()
        if "@" not in email or "." not in email:
            await update.message.reply_text("بريد إلكتروني غير صالح، حاول مرة أخرى.")
            return
        
        code = str(random.randint(1000, 9999))
        if send_verification_email(email, code):
            context.user_data["verification_code"] = code
            context.user_data["mode"] = "waiting_code"
            USERS[user_id] = {"email": email, "verified": False} 
            save_users()
            await update.message.reply_text(f"تم إرسال الكود إلى {email}.\nالرجاء إرسال الكود هنا:")
        else:
            await update.message.reply_text("حدث خطأ أثناء إرسال الإيميل. تأكد من صحة البريد أو تواصل مع الإدارة.")
        return

    if mode == "waiting_code" and text:
        correct_code = context.user_data.get("verification_code")
        if text.strip() == correct_code:
            USERS[user_id]["verified"] = True
            save_users()
            context.user_data["mode"] = None 
            context.user_data.pop("verification_code", None)
            
            await update.message.reply_text("✅ تم التحقق بنجاح! يمكنك الآن المتابعة.")
            # بعد التحقق من الإيميل ننتقل للتحقق من الاشتراك
            await check_subscription_status(update, context, is_new_message=True) 
        else:
            await update.message.reply_text("❌ كود خاطئ، حاول مرة أخرى.")
        return

    # إذا أرسل رسالة عادية وهو مفعل، نتحقق من اشتراكه ونعرض القائمة
    if user_id in USERS and USERS[user_id].get("verified"):
        await check_subscription_status(update, context, is_new_message=True)
    else:
        await update.message.reply_text("الرجاء استخدام /start للبدء وإكمال عملية التحقق.")

# [هنا تضع بقية هاندلرات الآدمن وتصفح الملفات (admin_panel, show_delete_list, confirm_delete_file, show_file_types, handle_type_button, handle_file_button) كما هي في الكود السابق]

# [الكود السابق من هنا يكمل كما هو، فقط تأكد من تضمينه في الملف:]
async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # ... (كما هو) ...
    query = update.callback_query
    await query.answer()

    keyboard = [
        [InlineKeyboardButton("➕ إضافة ملف جديد", callback_data="admin_add_file_mode")],
        [InlineKeyboardButton("🗑️ حذف ملف موجود", callback_data="admin_delete_list")],
        [InlineKeyboardButton("🔙 رجوع للقائمة الرئيسية", callback_data="back_main_menu")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.edit_message_text("لوحة تحكم الآدمن:\nاختر الإجراء المطلوب.", reply_markup=reply_markup)
    
async def enter_add_file_mode(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # ... (كما هو) ...
    query = update.callback_query
    await query.answer()
    
    context.user_data["mode"] = "admin_waiting_file"
    
    keyboard = [[InlineKeyboardButton(" إلغاء الإضافة", callback_data="admin_cancel")]]
    await query.edit_message_text(
        "أرسل الملف الذي تريد إضافته الآن (مستند، صورة، فيديو، إلخ.).", 
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def cancel_admin_operation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # ... (كما هو) ...
    query = update.callback_query
    await query.answer()
    
    context.user_data["mode"] = None
    await admin_panel(update, context)

async def show_delete_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # ... (كما هو) ...
    query = update.callback_query
    await query.answer()

    files_list = sorted(list(FILES.keys()))
    
    if not files_list:
        keyboard = [[InlineKeyboardButton("🔙 رجوع", callback_data="admin_panel")]]
        await query.edit_message_text("لا يوجد ملفات حالياً للحذف.", reply_markup=InlineKeyboardMarkup(keyboard))
        return

    keyboard = []
    for file_name in files_list:
        file_type = FILES[file_name]["type"]
        keyboard.append([
            InlineKeyboardButton(f"[{file_type}] {file_name}", callback_data=f"file_info_{file_name}"),
            InlineKeyboardButton("🗑️ حذف", callback_data=f"delete_file_{file_name}")
        ])
    
    keyboard.append([InlineKeyboardButton("🔙 رجوع", callback_data="admin_panel")])

    await query.edit_message_text(
        "اختر الملف للحذف:", 
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def confirm_delete_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # ... (كما هو) ...
    query = update.callback_query
    await query.answer()

    file_name = query.data[12:]
    file_info = FILES.get(file_name)

    if not file_info:
        await query.edit_message_text(f"❌ الملف **{file_name}** غير موجود في السجل.")
        await show_delete_list(update, context)
        return

    file_path = file_info.get("path")
    
    FILES.pop(file_name, None)
    save_files_record()

    if file_path and os.path.exists(file_path):
        os.remove(file_path)

    await query.edit_message_text(f"✅ تم حذف الملف **{file_name}** بنجاح.")
    await show_delete_list(update, context)

async def show_file_types(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # ... (كما هو) ...
    query = update.callback_query
    await query.answer() 

    # 🛑 فحص الاشتراك قبل عرض الملفات
    user_id = update.effective_user.id
    if not await is_member(user_id, context):
        await query.answer("يجب عليك الاشتراك في القناة أولاً.", show_alert=True)
        await check_subscription_status(update, context)
        return

    types = sorted(set(info["type"] for info in FILES.values()))
    
    keyboard = []
    if types:
        keyboard = [[InlineKeyboardButton(f"📁 {t} ({sum(1 for info in FILES.values() if info['type'] == t)})", callback_data=f"type_{t}")] for t in types]
    
    keyboard.append([InlineKeyboardButton("🔙 رجوع للقائمة الرئيسية", callback_data="back_main_menu")])

    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text("اختر نوع الملفات:", reply_markup=reply_markup)


async def handle_type_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # ... (كما هو) ...
    query = update.callback_query
    await query.answer()
    
    # 🛑 فحص الاشتراك قبل عرض الملفات
    user_id = update.effective_user.id
    if not await is_member(user_id, context):
        await query.answer("يجب عليك الاشتراك في القناة أولاً.", show_alert=True)
        await check_subscription_status(update, context)
        return
        
    file_type = query.data[5:]
    files_in_type = [name for name, info in FILES.items() if info["type"] == file_type]
    
    keyboard = [[InlineKeyboardButton(name, callback_data=f"file_{name}")] for name in files_in_type]
    keyboard.append([InlineKeyboardButton("🔙 رجوع لاختيار النوع", callback_data="show_types")]) 
    
    await query.edit_message_text(f"الملفات من النوع: **{file_type}**", reply_markup=InlineKeyboardMarkup(keyboard))

async def handle_file_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # ... (كما هو) ...
    query = update.callback_query
    user_id = str(query.from_user.id)
    file_name = query.data[5:]
    file_info = FILES.get(file_name)
    
    if user_id not in USERS or not USERS[user_id].get("verified"):
        await query.answer("عذراً، يجب عليك تسجيل الدخول أولاً.", show_alert=True)
        return
    
    # 🛑 فحص الاشتراك قبل إرسال الملف
    if not await is_member(int(user_id), context):
        await query.answer("يجب عليك الاشتراك في القناة أولاً.", show_alert=True)
        await check_subscription_status(update, context)
        return
        
    if file_info:
        await query.answer("جاري إرسال الملف...")
        try:
            await context.bot.send_document(chat_id=user_id, document=file_info["file_id"])
        except Exception as e:
            print(f"Error sending with file_id, trying path: {e}")
            file_path = file_info.get("path")
            if file_path and os.path.exists(file_path):
                 await context.bot.send_document(chat_id=user_id, document=open(file_path, "rb"))
            else:
                 await query.answer("عذراً، الملف محذوف من السيرفر! ⚠️", show_alert=True)
    else:
        await query.answer("عذراً، الملف غير موجود في السجل. ⚠️", show_alert=True)


# ==== تشغيل البوت ====
if __name__ == "__main__":
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    # الأوامر
    app.add_handler(CommandHandler("start", start))
    
    # معالجة الرسائل
    app.add_handler(MessageHandler(filters.TEXT | filters.Document.ALL, handle_message))
    
    # الأزرار
    app.add_handler(CallbackQueryHandler(show_main_menu, pattern=r"^back_main_menu"))
    
    # 🆕 زر التحقق من الاشتراك
    app.add_handler(CallbackQueryHandler(check_subscription_callback, pattern=r"^check_subscription"))
    
    # منطق الآدمن
    app.add_handler(CallbackQueryHandler(admin_panel, pattern=r"^admin_panel", block=False)) 
    app.add_handler(CallbackQueryHandler(enter_add_file_mode, pattern=r"^admin_add_file_mode", block=False))
    app.add_handler(CallbackQueryHandler(cancel_admin_operation, pattern=r"^admin_cancel", block=False))
    app.add_handler(CallbackQueryHandler(show_delete_list, pattern=r"^admin_delete_list", block=False))
    app.add_handler(CallbackQueryHandler(confirm_delete_file, pattern=r"^delete_file_", block=False))

    # تصفح المستخدم العادي
    app.add_handler(CallbackQueryHandler(show_file_types, pattern=r"^show_types"))
    app.add_handler(CallbackQueryHandler(handle_type_button, pattern=r"^type_"))
    app.add_handler(CallbackQueryHandler(handle_file_button, pattern=r"^file_"))

    print("Bot is running...")
    app.run_polling()