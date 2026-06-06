import logging
import time
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, ContextTypes, CommandHandler, 
    MessageHandler, CallbackQueryHandler, filters
)
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# --- সেটিংস ও কনফিগারেশন ---
BOT_TOKEN = "8857697073:AAEJoIBndrXvWdMV8Nd4_Agzb43MoNUaCb8"
ADMIN_ID = 8273597769  # আপনার টেলিগ্রাম আইডি
SHEET_NAME = "File receipt"

# গুগল শিট কানেকশন সেটআপ
SCOPE = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
CREDS = ServiceAccountCredentials.from_json_keyfile_name('service_account.json', SCOPE)
CLIENT = gspread.authorize(CREDS)
SHEET = CLIENT.open(SHEET_NAME).sheet1

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

# --- ফাংশন: স্টার্ট মেনু ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("English", callback_data='lang_en'), 
         InlineKeyboardButton("বাংলা", callback_data='lang_bn')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("Select Language / ভাষা নির্বাচন করুন:", reply_markup=reply_markup)

# --- ফাংশন: চ্যানেল ভেরিফিকেশন ও মেনু নেভিগেশন ---
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    # ভাষা সিলেকশন
    if query.data in ['lang_en', 'lang_bn']:
        keyboard = [
            [InlineKeyboardButton("Join Channel 1", url="https://t.me/Cyber_Shield_official"), 
             InlineKeyboardButton("Join Channel 2", url="https://t.me/fegasus_1")],
            [InlineKeyboardButton("✅ Verify & Continue", callback_data='verify_check')]
        ]
        await query.edit_message_text("চ্যানেলগুলোতে জয়েন করে ভেরিফাই বাটনে ক্লিক করুন:", reply_markup=InlineKeyboardMarkup(keyboard))
    
    # ভেরিফিকেশন চেক
    elif query.data == 'verify_check':
        keyboard = [
            [InlineKeyboardButton("Instagram 2FA", callback_data='type_2fa'), 
             InlineKeyboardButton("Instagram Cookies", callback_data='type_cookies')]
        ]
        await query.edit_message_text("চ্যানেল ভেরিফাইড! এখন আপনার কাজের ধরন নির্বাচন করুন:", reply_markup=InlineKeyboardMarkup(keyboard))
    
    # টাইপ সিলেকশন
    elif query.data in ['type_2fa', 'type_cookies']:
        await query.edit_message_text("ধন্যবাদ! এখন আপনার ফাইলটি (সর্বোচ্চ ১০ এমবি) নিচে পাঠান।")

# --- ফাংশন: ফাইল রিসিভ ও টোকেন জেনারেশন ---
async def handle_document(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.document.file_size > 10 * 1024 * 1024:
        await update.message.reply_text("ফাইলটি ১০ এমবি এর বেশি! দয়া করে ছোট ফাইল পাঠান।")
        return
    
    # ইউনিক টোকেন জেনারেশন
    token = str(int(time.time()))[-6:]
    
    # গুগল শিটে ডাটা এন্ট্রি (Token, Username, UserID, Status, Payment, FileID)
    SHEET.append_row([token, update.message.from_user.username, update.message.from_user.id, "Pending", "N/A", update.message.document.file_id])
    
    # পেমেন্ট বাটন প্রদর্শন
    keyboard = [
        [InlineKeyboardButton("বিকাশ (Bkash)", callback_data=f'pay_bkash_{token}'),
         InlineKeyboardButton("নগদ (Nagad)", callback_data=f'pay_nagad_{token}'),
         InlineKeyboardButton("রকেট (Rocket)", callback_data=f'pay_rocket_{token}')]
    ]
    await update.message.reply_text(f"✅ ফাইলটি সফলভাবে জমা হয়েছে!\n\n🆔 আপনার ইউনিক টোকেন নাম্বার: {token}\n\nআপনার পেমেন্ট মেথড সিলেক্ট করুন:", reply_markup=InlineKeyboardMarkup(keyboard))

# --- ফাংশন: পেমেন্ট মেথড সেভ করা ---
async def payment_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    data = query.data.split('_')
    method = data[1]
    token = data[2]
    
    cell = SHEET.find(token)
    if cell:
        SHEET.update_cell(cell.row, 5, method.upper()) # ৫ম কলামে পেমেন্ট মেথড আপডেট
        await query.edit_message_text(f"আপনার পেমেন্ট মেথড {method.upper()} হিসেবে সেট করা হয়েছে।\nএডমিন পেমেন্ট চেক করার পর আপনাকে নোটিফিকেশন দিবে।")

# --- ফাংশন: এডমিন ও ইউজার কন্ট্রোল ---
async def admin_and_status_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    text = update.message.text
    
    # ১. এডমিন কমান্ড: /done {token}
    if user_id == ADMIN_ID and text.startswith("/done "):
        token = text.split()[1]
        cell = SHEET.find(token)
        if cell:
            SHEET.update_cell(cell.row, 4, "Done") # স্ট্যাটাস আপডেট
            target_user_id = SHEET.cell(cell.row, 3).value
            await context.bot.send_message(target_user_id, f"🎉 অভিনন্দন! আপনার টোকেন {token} এর পেমেন্ট সফল হয়েছে।")
            await update.message.reply_text(f"টোকেন {token} সাকসেসফুলি ডান করা হয়েছে।")
    
    # ২. এডমিন কমান্ড: /search {token}
    elif user_id == ADMIN_ID and text.startswith("/search "):
        token = text.split()[1]
        cell = SHEET.find(token)
        if cell:
            row_data = SHEET.row_values(cell.row)
            await update.message.reply_text(f"তথ্য পাওয়া গেছে:\n{row_data}")
            
    # ৩. ইউজার স্ট্যাটাস চেক: টোকেন নাম্বার পাঠালে
    elif text.isdigit() and len(text) == 6:
        cell = SHEET.find(text)
        if cell:
            status = SHEET.cell(cell.row, 4).value
            await update.message.reply_text(f"আপনার টোকেন: {text}\nবর্তমান স্ট্যাটাস: {status}")
        else:
            await update.message.reply_text("দুঃখিত, এই টোকেনটি ডাটাবেসে পাওয়া যায়নি।")

# --- বট রান করার মেইন ব্লক ---
if __name__ == '__main__':
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_handler, pattern='^(lang_|verify_check|type_)'))
    app.add_handler(CallbackQueryHandler(payment_handler, pattern='^pay_'))
    app.add_handler(MessageHandler(filters.Document.ALL, handle_document))
    app.add_handler(MessageHandler(filters.TEXT, admin_and_status_handler))
    
    print("Bot is running...")
    app.run_polling()
