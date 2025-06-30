import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, MessageHandler, filters, CallbackQueryHandler
import requests
import urllib.parse
import os
links = []
names = []
def search_radiojavan(song_name):
    encoded_query = urllib.parse.quote(song_name)
    url = f"https://play.radiojavan.com/api/p/search?query={encoded_query}"
    
    headers = {
        "Accept": "application/json, text/plain, */*",
        "x-api-key": "40e87948bd4ef75efe61205ac5f468a9fd2b970511acf58c49706ecb984f1d67",
        "x-rj-user-agent": "Radio Javan/4.0.2/badeda3b3ffa2488d32128a49526270ca7aa6f2e com.radioJavan.rj.web"
    }
    
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        data = response.json()
        
        results = []
        
        if data.get("mp3s"):
            for item in data["mp3s"]:
                results.append({
                    "type": "MP3",
                    "song": item.get("song_farsi", item["song"]),
                    "artist": item.get("artist_farsi", item["artist"]),
                    "link": item["link"],
                    "plays": item.get("plays", "N/A"),
                    "duration": f"{int(item['duration'] // 60)}:{int(item['duration'] % 60):02d}"
                })
        
        if data.get("videos"):
            for item in data["videos"]:
                results.append({
                    "type": "Video",
                    "song": item.get("song_farsi", item["song"]),
                    "artist": item.get("artist_farsi", item["artist"]),
                    "link": item["link"],
                    "views": item.get("views", "N/A")
                })
        
        if data.get("top"):
            for item in data["top"]:
                if item.get("type") == "mp3" and item not in data.get("mp3s", []):
                    results.append({
                        "type": "MP3",
                        "song": item.get("song_farsi", item["song"]),
                        "artist": item.get("artist_farsi", item["artist"]),
                        "link": item["link"],
                        "plays": item.get("plays", "N/A"),
                        "duration": f"{int(item['duration'] // 60)}:{int(item['duration'] % 60):02d}"
                    })
        
        return results
    except requests.exceptions.RequestException as e:
        print(f"Error: {e}")
        return None
    
# start
async def start(update: Update, context:ContextTypes.DEFAULT_TYPE):
    keyboard = [[InlineKeyboardButton("اضافه کردن به گروه ➕", url="https://t.me/Music_wealbot?startgroup=true")],
                [InlineKeyboardButton("راهنما ❕", callback_data="help")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("به ربات خوش آمدی! از دکمه های زیر استفاده کن :", reply_markup=reply_markup)



# inline buttoms
async def button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if query.data == "help":
        await query.message.reply_text("📌 راهنما: \n برای پیدا کردن و دریافت موسیقی از دستور /play استفاده کن.")
        return
    page = context.user_data.get("page", 0)
    if query.data == "next_page":
        page += 1
    elif query.data == "prev_page":
        page -= 1
    await send_result_page(update, context, page, edit=True)



async def play(update: Update, context:ContextTypes.DEFAULT_TYPE):
    query = " ".join(context.args)
    if not query:
        await update.message.reply_text("لطفا اسم آهنگ رو بنویس : /play آهنگ")
        return
    try:
        results = search_radiojavan(query)
        if not results:
            await update.message.reply_text("چیزی پیدا نشد.")
            return
        context.user_data["results"] = results
        context.user_data["links"] = links
        context.user_data["names"] = names
        context.user_data["page"]= 0
        await send_result_page(update, context, 0, edit= False)
    except Exception as e:
        await update.message.reply_text(f"خطا : {e}")



async def send_result_page(update, context, page, edit= True):
    results = context.user_data.get("results", [])
    per_page = 15
    total_page = (len(results) + per_page - 1) // per_page
    start = page * per_page
    end = start + per_page
    current_result = results[start:end]
    text = f"📃 صفحه {page + 1} از {total_page}\n\n"
    links = []
    names = []
    type = []
    for i, item in enumerate(current_result, start + 1):
        text = text + f"{i}. نوع: {item['type']}\nآهنگ: {item['song']}\nخواننده : {item['artist']}"
        if item['type'] == "MP3":
            text = text + f"\nمدت : {item['duration']}\nپخش : {item['plays']} \n"
        else:
            text = text + f"\nبازدید: {item['views']} \n"
        links.append(item['link'])    
        names.append(item['song'])
        type.append(item['type'])

    context.user_data["waiting_for_number"] = True
    context.user_data["links"] = links
    context.user_data["names"] = names
    context.user_data["type"] = type
    context.user_data["page"] = page

    buttons = []
    if page > 0:
        buttons.append(InlineKeyboardButton("قبلی ⏪", callback_data="prev_page"))
    if page < total_page - 1:
        buttons.append(InlineKeyboardButton("بعدی ⏩", callback_data="next_page"))

    keyboard = InlineKeyboardMarkup([buttons]) if buttons else None
    if edit and "last_message" in context.user_data:
        try:
                await context.user_data["last_message"].edit_text(text, reply_markup= keyboard)
        except:
                pass
    else:
        msg = await update.message.reply_text(text, reply_markup=keyboard)
        context.user_data["last_message"] = msg
        await update.message.reply_text("لطفا شماره آهنگ مورد نظرت رو ارسال کن:")

# send file
async def download(update: Update, context:ContextTypes.DEFAULT_TYPE):
                if not context.user_data.get("waiting_for_number"):
                    return
                links = context.user_data.get("links",[])
                names = context.user_data.get("names", [])
                type = context.user_data.get('type', [])
                try:
                    number = int(update.message.text)
                    number = number - 1
                    
                    if number < 0 or number >= len(links): 
                        await update.message.reply_text("لطفا عدد آهنگ مورد نظرتون رو وارد کنید.")
                        return
                    
                    context.user_data["selected_number"] = number
                    context.user_data["chat_id"] = update.effective_chat.id
                    buttons = [
                        [InlineKeyboardButton("📤 ارسال فایل", callback_data = "send_file")], 
                        [InlineKeyboardButton("▶ پخش در voice call", callback_data = "play_voice")]
                    ]
                    reply_markup = InlineKeyboardMarkup(buttons)
                    await update.message.reply_text("میخوای چطوری پخش بشه؟", reply_markup= reply_markup)
                    # -----------------------------------------------------------------------------




                    
                    waiting_message = await update.message.reply_text("لطفا منتظر بمانید...")
                    if type[number] == "MP3": 
                        await update.message.reply_audio(audio= links[number], title= names[number])
                    elif type[number] == "Video":
                        await update.message.reply_text("متاسفانه ارسال فایل ویدئویی در حال حاضر امکان پذیر نیست...")
                    context.user_data["waiting_for_number"] = False
                    await waiting_message.delete()
                except ValueError:
                    await update.message.reply_text("لطفا فقط عدد وارد کنید...")
                except Exception as e:
                   await update.message.reply_text(f"خطا در دانلود فایل : {e}")

   
# main
async def main():
    from config import API_Token


    app = ApplicationBuilder().token(API_Token).build()
    app.add_handler(CommandHandler("play", play))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, download))
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button))
    
    
    print("ربات فعال شد ...")
    await app.run_polling()
    
    
    

if __name__ == "__main__":
    import nest_asyncio
    nest_asyncio.apply()
    asyncio.get_event_loop().run_until_complete(main())
