import telebot
import sqlite3
import logging
from telebot import types
from datetime import datetime
from threading import Lock, Thread
import time

# ================= CONFIG =================
API_TOKEN = "8716693601:AAFc9rt0DDPETnG8cVpNGjwu18Qw8YHf-Vg"
CHANNEL_ID = -1002449896845
CHANNEL_USERNAME = "@Stars_5_odam_1stars"
ADMIN_ID = 2010030869
BOT_USERNAME = "stars_sovga_gifbot"          # ←←← BU YERNI O'ZGARTIRING! Masalan: saacaaaaa_bot

bot = telebot.TeleBot(API_TOKEN, parse_mode="HTML", threaded=True)

# ================= LOGGING =================
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("BOT")

# ================= DB =================
lock = Lock()

class DB:
    def __init__(self):
        self.conn = sqlite3.connect("bot.db", check_same_thread=False)
        self.cur = self.conn.cursor()
        self.init()

    def init(self):
        with lock:
            self.cur.execute("""
            CREATE TABLE IF NOT EXISTS users(
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                first_name TEXT,
                invites INTEGER DEFAULT 0,
                stars INTEGER DEFAULT 0,
                vip INTEGER DEFAULT 0
            )
            """)
            self.conn.commit()

    def create_user(self, uid, username, name):
        self.cur.execute("INSERT OR IGNORE INTO users(user_id, username, first_name) VALUES(?,?,?)", 
                        (uid, username, name))
        self.conn.commit()

    def get(self, uid):
        self.cur.execute("SELECT invites, stars, vip FROM users WHERE user_id=?", (uid,))
        return self.cur.fetchone() or (0, 0, 0)

    def update_user(self, uid, username, name):
        self.cur.execute("UPDATE users SET username=?, first_name=? WHERE user_id=?", 
                        (username, name, uid))
        self.conn.commit()

    def add_invite(self, uid, count):
        self.cur.execute("UPDATE users SET invites = invites + ? WHERE user_id=?", (count, uid))
        self.conn.commit()

    def recalc_stars(self, uid):
        self.cur.execute("SELECT invites FROM users WHERE user_id=?", (uid,))
        row = self.cur.fetchone()
        invites = row[0] if row else 0
        stars = invites // 5
        self.cur.execute("UPDATE users SET stars=? WHERE user_id=?", (stars, uid))
        self.conn.commit()
        return invites, stars

    def sub_star(self, uid, amount):
        self.cur.execute("UPDATE users SET stars = stars - ? WHERE user_id=?", (amount, uid))
        self.conn.commit()

    def get_top(self, limit=10):
        self.cur.execute("""
        SELECT username, first_name, invites, stars 
        FROM users ORDER BY invites DESC LIMIT ?
        """, (limit,))
        return self.cur.fetchall()

db = DB()


# ================= SHOP MENU (3 ustunli grid) =================
def shop(chat_id, uid):
    _, stars, _ = db.get(uid)
    
    markup = types.InlineKeyboardMarkup(row_width=3)   # 3 ta ustun
    
    for price, (name, emoji, photo, desc) in SHOP.items():
        button_text = f"{emoji} {price}⭐"
        markup.add(types.InlineKeyboardButton(button_text, callback_data=f"buy_{price}"))
    
    text = f"""
🎁 <b>TELEGRAM GIFTS DO‘KONI</b>

⭐ Sizning balansingiz: <b>{stars}</b> yulduz

Pastdagi sovg‘alardan birini tanlang 👇
"""
    bot.send_message(chat_id, text, reply_markup=markup)


# ================= BUY SOVGA =================
def buy(call, uid, price):
    invites, stars, vip = db.get(uid)
    
    if stars < price:
        return bot.answer_callback_query(call.id, "❌ Yetarli yulduz yo‘q!", show_alert=True)

    db.sub_star(uid, price)
    name, emoji, photo, desc = SHOP[price]

    if price >= 50:
        db.cur.execute("UPDATE users SET vip = 1 WHERE user_id = ?", (uid,))
        db.conn.commit()
        extra = "\n\n👑 <b>VIP</b> statusi berildi!"
    else:
        extra = ""

    caption = f"""
🎉 <b>Tabriklaymiz!</b> 🎉

{emoji} <b>{name}</b>

{desc}

💰 Sarflangan: <b>{price} ⭐</b>
⭐ Qolgan: <b>{stars - price}</b>{extra}

🌟 Yana ko‘proq odam qo‘shing!
"""

    bot.send_photo(call.message.chat.id, photo, caption=caption)
    bot.answer_callback_query(call.id, f"{emoji} Sovg‘a yetkazildi!", show_alert=True)
    
    bot.send_message(ADMIN_ID, f"🛒 SOTUV: {uid} — {price}⭐ → {name}")

# ================= MENU =================
def menu(uid, chat_id):
    invites, stars, vip = db.get(uid)
    text = f"""
🌟 <b>REFERRAL SYSTEM</b> 🌟

👤 Sizning holatingiz:
👥 Taklif qilganingiz: <b>{invites}</b> ta
⭐ Yulduzlar: <b>{stars}</b>
👑 VIP: <b>{"✅ HA" if vip else "❌ YO‘Q"}</b>

🎯 <i>5 ta taklif = 1 yulduz</i>
"""
    m = types.InlineKeyboardMarkup(row_width=1)
    m.add(types.InlineKeyboardButton("🔗 Mening Invite Linkim", callback_data="link"))
    m.add(types.InlineKeyboardButton("🛒 Sovg‘alar Do‘koni", callback_data="shop"))
    bot.send_message(chat_id, text, reply_markup=m)

# ================= CHECK SUB =================
def check_sub(uid):
    try:
        member = bot.get_chat_member(CHANNEL_USERNAME, uid)
        return member.status in ["member", "administrator", "creator"]
    except:
        return False

# ================= START =================
@bot.message_handler(commands=["start"])
def start(m):
    uid = m.from_user.id
    if not check_sub(uid):
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("📢 Kanalga obuna bo‘lish", url=f"https://t.me/{CHANNEL_USERNAME[1:]}"))
        return bot.send_message(m.chat.id, "❌ Avval kanalga obuna bo‘ling!", reply_markup=markup)

    db.create_user(uid, m.from_user.username, m.from_user.first_name)
    db.update_user(uid, m.from_user.username, m.from_user.first_name)
    menu(uid, m.chat.id)

# ================= NEW MEMBER =================
@bot.message_handler(content_types=['new_chat_members'])
def new_member(message):
    if not message.new_chat_members:
        return

    inviter = message.from_user
    added_users = message.new_chat_members

    real_added = 0
    for user in added_users:
        # Botlarni va o'zini o'zi qo'shgan holatni hisoblamaymiz
        if user.is_bot or user.id == inviter.id:
            continue
        real_added += 1

    if real_added == 0:
        return

    db.create_user(inviter.id, inviter.username, inviter.first_name)
    db.add_invite(inviter.id, real_added)
    invites, stars = db.recalc_stars(inviter.id)

    text = f"""
🎉 <b>{inviter.first_name}</b> guruhga odam qo‘shdi!

➕ Qo‘shildi: <b>{real_added}</b> ta haqiqiy foydalanuvchi
👥 Jami taklif: <b>{invites}</b> ta
⭐ Yulduzlar: <b>{stars}</b>
"""
    bot.send_message(message.chat.id, text)

# ================= LEADERBOARD =================
def send_leaderboard():
    top = db.get_top(10)
    if not top:
        return
    text = "🏆 <b>GURUHDA ENG FAOL REFERRALLAR</b>\n\n"
    for i, (username, name, invites, stars) in enumerate(top, 1):
        user = f"@{username}" if username else name
        text += f"{i}️⃣ <b>{user}</b> — 👥 <b>{invites}</b> ta | ⭐ <b>{stars}</b>\n"
    text += "\n🔥 Har 5 ta odam = 1 ⭐"
    try:
        bot.send_message(CHANNEL_ID, text)
    except:
        pass


def leaderboard_scheduler():
    while True:
        send_leaderboard()
        time.sleep(300)  # 5 daqiqa


# ================= YANGI CHIROYLI SHOP =================
SHOP = {
    15: ("❤️ Heart Gift", "❤️", "https://i.imgur.com/8Yp9Z2M.jpg", "Chiroyli yurak sovg‘asi"),
    15: ("🧸 Teddy Bear", "🧸", "https://i.imgur.com/5f2vL8K.jpg", "Yoqimli ayiqcha"),
    25: ("🎁 Gift Box", "🎁", "https://i.imgur.com/3vX9pLm.jpg", "Qizil lenta bilan sovg‘a"),
    25: ("🌹 Red Rose", "🌹", "https://i.imgur.com/7zK9pQm.jpg", "Romantik atirgul"),
    50: ("🎂 Birthday Cake", "🎂", "https://i.imgur.com/9pL2mNx.jpg", "Shamli tort"),
    50: ("💐 Flower Bouquet", "💐", "https://i.imgur.com/XkP5vRt.jpg", "Gullar to‘plami"),
    50: ("🚀 Rocket", "🚀", "https://i.imgur.com/2fG7vKp.jpg", "Uchuvchi raketa"),
    100: ("🏆 Golden Trophy", "🏆", "https://i.imgur.com/vL9pQmN.jpg", "Oltin kubok"),
    100: ("💍 Diamond Ring", "💍", "https://i.imgur.com/kP8mNxZ.jpg", "Olmos uzuk")
}

# ================= SHOP MENU (3 ustunli grid) =================
def shop(chat_id, uid):
    _, stars, _ = db.get(uid)
    
    markup = types.InlineKeyboardMarkup(row_width=3)
    
    for price, (name, emoji, photo, desc) in SHOP.items():
        markup.add(types.InlineKeyboardButton(f"{emoji} {price}⭐", callback_data=f"buy_{price}"))
    
    text = f"""
🎁 <b>TELEGRAM GIFTS DO‘KONI</b>

⭐ Sizning balansingiz: <b>{stars}</b> yulduz

Pastdagi sovg‘alardan tanlang 👇
"""
    bot.send_message(chat_id, text, reply_markup=markup)


# ================= BUY =================
def buy(call, uid, price):
    invites, stars, vip = db.get(uid)
    if stars < price:
        return bot.answer_callback_query(call.id, "❌ Yetarli yulduz yo‘q!", show_alert=True)

    db.sub_star(uid, price)
    name, emoji, photo, desc = SHOP[price]

    extra = "\n\n👑 <b>VIP</b> statusi berildi!" if price >= 50 else ""

    caption = f"""
🎉 <b>Sizga sovg‘a yetkazildi!</b> 🎉

{emoji} <b>{name}</b>
{desc}

💰 Sarflandi: <b>{price} ⭐</b>
⭐ Qoldi: <b>{stars - price}</b>{extra}
"""

    bot.send_photo(call.message.chat.id, photo, caption=caption)
    bot.answer_callback_query(call.id, "✅ Sovg‘a yuborildi!", show_alert=True)
    bot.send_message(ADMIN_ID, f"🛒 SOTUV: {uid} — {price}⭐ → {name}")


# ================= CALLBACK =================
@bot.callback_query_handler(func=lambda c: True)
def cb(call):
    uid = call.from_user.id
    data = call.data

    if data == "shop":
        shop(call.message.chat.id, uid)
    elif data == "link":
        link = f"https://t.me/{BOT_USERNAME}?start={uid}"
        bot.send_message(call.message.chat.id, f"🔗 Invite linkingiz:\n<code>{link}</code>")
    elif data.startswith("buy_"):
        price = int(data.split("_")[1])
        buy(call, uid, price)

    bot.answer_callback_query(call.id)


# ================= RUN =================
if __name__ == "__main__":
    print("BOT STARTED 🚀")

    while True:
        try:
            bot.infinity_polling(timeout=30, long_polling_timeout=30)
        except Exception as e:
            print("RESTART:", e)
            time.sleep(5)