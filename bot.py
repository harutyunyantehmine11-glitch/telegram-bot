import os
import sys
import logging

# ========== ДОБАВЬ ЭТО ==========
# Настройка логирования для Render
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Проверка переменных окружения
TOKEN = os.environ.get('TELEGRAM_TOKEN')
if not TOKEN:
    logger.error("❌ TELEGRAM_TOKEN не установлен!")
    logger.info("Добавь TELEGRAM_TOKEN в Environment на Render")
    sys.exit(1)
# ================================

# Твой остальной код НИЖЕ...
bot = telebot.TeleBot(TOKEN)

# ===========================================
# ВАШ ОРИГИНАЛЬНЫЙ КОД НИЖЕ
# ===========================================
# ... ваш существующий код ...


import sqlite3
import asyncio
from aiogram import Bot, Dispatcher, types
from aiogram.filters import CommandStart, StateFilter
from aiogram.fsm.state import StatesGroup, State
from aiogram.fsm.context import FSMContext
from aiogram.types import FSInputFile

# ===========================================
#                Կարգավորում
# ===========================================
TOKEN = "8580894538:AAF9UlkAlXR6q2umeI0MUe-JbnO-cJk9GmA"
bot = Bot(token=TOKEN)
dp = Dispatcher()

# ===========================================
#            Բաժանորդագրվելու ալիքներ
# ===========================================
# Ստուգվող ալիքներ
CHANNELS = [
    {"name": "🎰 LuckyDoll շոփը", "url": "https://t.me/LuckyDoll108", "id": "@LuckyDoll108"},
    {"name": "🎁Մեր ալիքը", "url": "https://t.me/meAnonimus", "id": "@meAnonimus"}
]

# Թաքնված ալիք (առանց ստուգման)
HIDDEN_CHANNELS = [
    {"name": "🔒 Փակ ալիքը", "url": "https://t.me/+5R6HH-GzN745NWVi", "id": "@your_private_channel"}
]

# Բոլոր ալիքները միասին (ցուցադրման համար)
ALL_CHANNELS = CHANNELS + HIDDEN_CHANNELS

# ===========================================
#              Նվազագույն սահմանափակումներ
# ===========================================
MIN_DRAM = 1500
MIN_STARS = 214
MIN_UC = 300

# ===========================================
#            Բոնուսային համակարգ
# ===========================================
REFERRAL_BONUS_THRESHOLD = 50    # x2 ակտիվացման շեմ
BASE_REFERRAL_REWARD = 100       # բազային պարգև
BONUS_REFERRAL_REWARD = 200      # պարգև 50 ռեֆերալից հետո

# ===========================================
#            Տվյալների բազա
# ===========================================
conn = sqlite3.connect("referrals.db", check_same_thread=False)
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY,
    base_balance INTEGER DEFAULT 0,
    referrals INTEGER DEFAULT 0,
    withdrawn INTEGER DEFAULT 0,
    referral_link TEXT,
    subscribed INTEGER DEFAULT 0,
    bonus_activated INTEGER DEFAULT 0
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS referrals (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    referrer_id INTEGER,
    referred_id INTEGER UNIQUE,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
)
""")
conn.commit()

# ===========================================
#             DB գործառույթներ
# ===========================================
def add_user(user_id: int):
    cursor.execute("INSERT OR IGNORE INTO users(user_id) VALUES(?)", (user_id,))
    conn.commit()

def set_referral_link(user_id: int, bot_username: str):
    cursor.execute("SELECT referral_link FROM users WHERE user_id=?", (user_id,))
    row = cursor.fetchone()
    if row and row[0]:
        return row[0]
    link = f"https://t.me/{bot_username}?start={user_id}"
    cursor.execute("UPDATE users SET referral_link=? WHERE user_id=?", (link, user_id))
    conn.commit()
    return link

def has_been_referred(referred_id: int) -> bool:
    cursor.execute("SELECT 1 FROM referrals WHERE referred_id=?", (referred_id,))
    return cursor.fetchone() is not None

def add_referral_db(referrer_id: int, referred_id: int):
    if has_been_referred(referred_id):
        return False
    
    # Ստանում ենք ռեֆերալների ընթացիկ քանակը
    cursor.execute("SELECT referrals, bonus_activated FROM users WHERE user_id=?", (referrer_id,))
    row = cursor.fetchone()
    if not row:
        return False
    
    current_referrals, bonus_activated = row
    
    # Որոշում ենք պարգևը՝ կախված ռեֆերալների քանակից
    if bonus_activated:
        reward = BONUS_REFERRAL_REWARD * 2  # Ավելացնել x2 բոնուս
    else:
        reward = BASE_REFERRAL_REWARD
    
    # Ավելացնում ենք ռեֆերալին
    cursor.execute("INSERT INTO referrals(referrer_id, referred_id) VALUES(?, ?)",
                   (referrer_id, referred_id))
    
    # Թարմացնում ենք հաշվեկշիռը և ռեֆերալների հաշվիչը
    cursor.execute("""
        UPDATE users
        SET referrals = referrals + 1,
            base_balance = base_balance + ?
        WHERE user_id=?
    """, (reward, referrer_id))
    
    # Ստուգում ենք՝ արդյոք հասել է բոնուսի ակտիվացման շեմին
    if not bonus_activated and current_referrals + 1 >= REFERRAL_BONUS_THRESHOLD:
        # Ակտիվացնել բոնուսը և բազմապատկել գոյություն ունեցող հաշվեկշիռը 2-ով
        cursor.execute("UPDATE users SET bonus_activated=1 WHERE user_id=?", (referrer_id,))
        cursor.execute("UPDATE users SET base_balance = base_balance * 2 WHERE user_id=?", (referrer_id,))
    
    conn.commit()
    return True

def get_balance(user_id: int):
    cursor.execute("SELECT base_balance, referrals, withdrawn, bonus_activated FROM users WHERE user_id=?", (user_id,))
    row = cursor.fetchone()
    if not row:
        add_user(user_id)
        return 0, 0, 0, 0
    
    base_balance, referrals, withdrawn, bonus_activated = row
    
    # Եթե բոնուսը ակտիվացված է, ապա բազմապատկում ենք ամբողջ հաշվեկշիռը
    if bonus_activated:
        final_balance = base_balance * 2
    else:
        final_balance = base_balance
    
    return final_balance, referrals, withdrawn, bonus_activated

def update_balance_withdraw(user_id: int, amount: int):
    # Ստանալ ներկայիս տվյալները
    cursor.execute("SELECT base_balance, bonus_activated FROM users WHERE user_id=?", (user_id,))
    row = cursor.fetchone()
    if not row:
        return
    
    base_balance, bonus_activated = row
    
    # Հաշվարկել փաստացի գումարը, որը պետք է հանել բազային հաշվեկշռից
    if bonus_activated:
        # Եթե բոնուսը ակտիվացված է, ապա գումարը բաժանել 2-ի
        actual_amount = amount // 2
        # Համոզվել, որ կա մնացորդ
        if actual_amount > base_balance:
            actual_amount = base_balance
    else:
        actual_amount = amount
    
    # Հաշվարկել փաստացի կանխիկացված գումարը
    actual_withdrawn = amount
    
    cursor.execute("""
        UPDATE users 
        SET base_balance = base_balance - ?, withdrawn = withdrawn + ?
        WHERE user_id=?
    """, (actual_amount, actual_withdrawn, user_id))
    conn.commit()

def set_subscribed(user_id: int):
    cursor.execute("UPDATE users SET subscribed=1 WHERE user_id=?", (user_id,))
    conn.commit()

def is_subscribed(user_id: int) -> bool:
    cursor.execute("SELECT subscribed FROM users WHERE user_id=?", (user_id,))
    row = cursor.fetchone()
    if not row:
        add_user(user_id)
        return False
    return row[0] == 1

def get_referral_stats(user_id: int):
    """Ստանում է ռեֆերալների վիճակագրությունը և բոնուսները"""
    cursor.execute("SELECT referrals, bonus_activated FROM users WHERE user_id=?", (user_id,))
    row = cursor.fetchone()
    if not row:
        return 0, 0, BASE_REFERRAL_REWARD, REFERRAL_BONUS_THRESHOLD
    
    referrals, bonus_activated = row
    
    if bonus_activated:
        current_reward = BONUS_REFERRAL_REWARD * 2  # x2 բոնուս
        remaining_to_bonus = 0
    else:
        current_reward = BASE_REFERRAL_REWARD
        remaining_to_bonus = max(0, REFERRAL_BONUS_THRESHOLD - referrals)
    
    return referrals, bonus_activated, current_reward, remaining_to_bonus

def get_base_balance(user_id: int):
    """Ստանում է բազային հաշվեկշիռը (առանց բազմապատկման)"""
    cursor.execute("SELECT base_balance FROM users WHERE user_id=?", (user_id,))
    row = cursor.fetchone()
    if not row:
        return 0
    return row[0]

# ===========================================
#          Ալիքներին բաժանորդագրվելու ստուգում
# ===========================================
async def check_subscription(user_id: int) -> tuple[bool, list]:
    """
    Ստուգում է բաժանորդագրությունը միայն հիմնական ալիքներին
    Վերադարձնում է (բոլորին_բաժանորդագրվա՞ծ, չբաժանորդագրված_ալիքների_ցանկ)
    """
    not_subscribed = []
    
    for channel in CHANNELS:  # Միայն ստուգվող ալիքներ
        try:
            member = await bot.get_chat_member(chat_id=channel["id"], user_id=user_id)
            if member.status in ["left", "kicked"]:
                not_subscribed.append(channel)
        except Exception as e:
            print(f"Սխալ ալիքին բաժանորդագրվելու ստուգման ժամանակ {channel['name']}: {e}")
            not_subscribed.append(channel)
    
    return len(not_subscribed) == 0, not_subscribed

# ===========================================
#                Ստեղնաշարեր
# ===========================================
def main_menu():
    return types.ReplyKeyboardMarkup(
        keyboard=[
            [types.KeyboardButton(text="Սկսենք գումար աշխատել՞")],
            [types.KeyboardButton(text="Իմ մնացորդը")],
            [types.KeyboardButton(text="Կանխիկացնել")]
        ],
        resize_keyboard=True
    )

def start_earn_menu():
    return types.ReplyKeyboardMarkup(
        keyboard=[
            [types.KeyboardButton(text="Ստանալ անհատական հղումը")],
            [types.KeyboardButton(text="Հետ վերադառնալ")]
        ],
        resize_keyboard=True
    )

def balance_menu():
    return types.ReplyKeyboardMarkup(
        keyboard=[
            [types.KeyboardButton(text="Ցույց տալ մնացորդը")],
            [types.KeyboardButton(text="Հետ վերադառնալ")]
        ],
        resize_keyboard=True
    )

def withdraw_menu():
    return types.ReplyKeyboardMarkup(
        keyboard=[
            [types.KeyboardButton(text="Կանխիկացնել դրամով")],
            [types.KeyboardButton(text="Փոխանակել UC-ի հետ")],
            [types.KeyboardButton(text="Փոխանակել TG Stars-ի հետ")],
            [types.KeyboardButton(text="Հետ վերադառնալ")]
        ],
        resize_keyboard=True
    )

def get_channels_keyboard(not_subscribed_channels=None):
    buttons = []
    # Ցույց տալ ԲՈԼՈՐ ալիքները (հիմնական + թաքնված)
    channels_to_show = ALL_CHANNELS
    
    for i, channel in enumerate(channels_to_show, 1):
        buttons.append([types.InlineKeyboardButton(
            text=f"📢 {i}. {channel['name']}", 
            url=channel['url']
        )])
    
    buttons.append([types.InlineKeyboardButton(
        text="✅ Ես բաժանորդագրվել եմ", 
        callback_data="check_subscription"
    )])
    return types.InlineKeyboardMarkup(inline_keyboard=buttons)

# ===========================================
#        /start + ռեֆերալային համակարգ
# ===========================================
BOT_USERNAME = None

@dp.message(CommandStart())
async def start_handler(message: types.Message):
    global BOT_USERNAME
    user_id = message.from_user.id
    add_user(user_id)

    # ռեֆերալի մշակում
    payload = message.text.split()
    if len(payload) > 1:
        try:
            referrer = int(payload[1])
            if referrer != user_id:
                ok = add_referral_db(referrer, user_id)
                if ok:
                    # Ստանում ենք պարգևի մասին տեղեկատվություն ծանուցման համար
                    referrals, bonus_activated, current_reward, _ = get_referral_stats(referrer)
                    
                    if bonus_activated:
                        bonus_text = " 🚀 ԲՈՆՈՒՍԸ ԱԿՏԻՎԱՑԱԾ Է! Այժմ ամբողջ հաշվեկշիռը x2 է"
                    else:
                        remaining = REFERRAL_BONUS_THRESHOLD - referrals
                        bonus_text = f" Մինչև x2 բոնուս մնացել է՝ {remaining} ռեֆերալ"
                    
                    try:
                        await bot.send_message(
                            referrer, 
                            f"🥳 Նոր ռեֆերալ միացավ! +{current_reward} դրամ\n{bonus_text}"
                        )
                    except:
                        pass
        except:
            pass

    if BOT_USERNAME is None:
        me = await bot.get_me()
        BOT_USERNAME = me.username

    set_referral_link(user_id, BOT_USERNAME)

    # լուսանկարի ուղարկում + ողջույն + ալիքի հղում
    photo = FSInputFile("logo.jpg")  # ֆայլը bot.py-ի կողքին
    kb = main_menu()
    await bot.send_photo(
        chat_id=user_id,
        photo=photo,
        caption=(
            "Բարև! 👋\n"
            "Ուրախ ենք ողջունել ձեզ մեր բոտում։\n"
            "Մինչև 50 ռեֆերալ վճարում ենք 100 դրամ, երբ հասնեք 50 ռեֆերալի ձեր չկանխիկացրած բալանսը կբազմապատկվի 2-ով և այդ պահից սկսած բոլոր ռեֆերալները կլինեն 200 դրամ ։\n"
            "Եթե ձեր ռեֆերալները չլինեն ալիքներում, կանխիկացումը կկասեցվի\n"
            "Կանխիկացումից առաջ ստուգեք արդյոք միացած եք բոլոր ալիքներին։"
        ),  
        reply_markup=kb
    )

# ===========================================
#    "Ստուգել բաժանորդագրությունը" կոճակի մշակիչ
# ===========================================
@dp.callback_query(lambda c: c.data == "check_subscription")
async def check_subscription_callback(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    
    is_subscribed_all, not_subscribed_channels = await check_subscription(user_id)
    
    if is_subscribed_all:
        set_subscribed(user_id)
        await callback.message.edit_text("✅ Շնորհակալություն բաժանորդագրվելու համար! Այժմ կարող եք ստանալ ձեր ռեֆերալային հղումը։")
        
        # Ցույց տալ եկամուտ ստանալու ընտրացանկը
        await callback.message.answer("Ընտրեք գործառույթը։", reply_markup=start_earn_menu())
    else:
        # Ցույց տալ միայն այն ալիքները, որոնց չի բաժանորդագրվել (հիմնականներից)
        channels_text = "❌ Դուք բաժանորդագրված չեք բոլոր ալիքներին!\n\n📢 Խնդրում ենք բաժանորդագրվել այս ալիքներին:\n\n"
        for i, channel in enumerate(not_subscribed_channels, 1):
            channels_text += f"{i}. {channel['name']}\n"
        
        # Ավելացնել թաքնված ալիքների մասին տեղեկատվություն
        if HIDDEN_CHANNELS:
            channels_text += "\n🔒 Նաև բաժանորդագրվեք փակ ալիքներին:\n"
            for i, channel in enumerate(HIDDEN_CHANNELS, len(not_subscribed_channels) + 1):
                channels_text += f"{i}. {channel['name']}\n"
        
        channels_text += "\nԲաժանորդագրվելուց հետո սեղմեք ստորև նշված կոճակը ↓"
        
        await callback.message.edit_text(
            channels_text,
            reply_markup=get_channels_keyboard(not_subscribed_channels)
        )
        await callback.answer("Դուք բաժանորդագրված չեք բոլոր ալիքներին!", show_alert=False)

# ===========================================
#         FSM — ԿԱՆԽԻԿԱՑՈՒՄ
# ===========================================
class WithdrawDrama(StatesGroup):
    waiting_amount = State()
    waiting_code = State()
    waiting_bank = State()

class WithdrawUC(StatesGroup):
    waiting_uc = State()
    waiting_id = State()

class WithdrawStars(StatesGroup):
    waiting_stars = State()
    waiting_username = State()

# ===========================================
#   Ամենուր հետ
# ===========================================
@dp.message(lambda m: (m.text or "") == "Հետ վերադառնալ")
async def cancel_any_state(message: types.Message, state: FSMContext):
    await state.clear()
    await message.answer("Դուք վերադարձաք գլխավոր ընտրացանկ։", reply_markup=main_menu())

# ===========================================
#          Հիմնական մշակիչ
# ===========================================
@dp.message(StateFilter(None))
async def message_handler(message: types.Message, state: FSMContext):
    global BOT_USERNAME
    user_id = message.from_user.id
    text = message.text or ""
    add_user(user_id)

    # --- Սկսենք գումար աշխատել՞ ---
    if text == "Սկսենք գումար աշխատել՞":
        await message.answer("Ընտրեք գործառույթը։", reply_markup=start_earn_menu())
        return

    if text == "Ստանալ անհատական հղումը":
        # Ստուգել բաժանորդագրությունը միայն հիմնական ալիքներին
        is_subscribed_all, not_subscribed_channels = await check_subscription(user_id)
        
        if is_subscribed_all:
            set_subscribed(user_id)
            # Եթե բաժանորդագրված է՝ ցույց տալ հղումը
            if BOT_USERNAME is None:
                me = await bot.get_me()
                BOT_USERNAME = me.username
            link = set_referral_link(user_id, BOT_USERNAME)
            
            # Ստանալ բոնուսների մասին տեղեկատվություն ցուցադրման համար
            referrals, bonus_activated, current_reward, remaining_to_bonus = get_referral_stats(user_id)
            
            if bonus_activated:
                bonus_info = f"🚀 ԲՈՆՈՒՍԸ ԱԿՏԻՎԱՑԱԾ Է! Ամբողջ հաշվեկշիռը x2 է\n🎯 Յուրաքանչյուր նոր ռեֆերալ = {current_reward} դրամ"
            else:
                bonus_info = f"🎯 Յուրաքանչյուր ռեֆերալի համար՝ {current_reward} դրամ\n📈 x2 բոնուսին մնաց՝ {remaining_to_bonus} ռեֆերալ"
            
            kb = types.InlineKeyboardMarkup(
                inline_keyboard=[[types.InlineKeyboardButton(text="Բացել հղումը", url=link)]]
            )
            await message.answer(
                f"Ձեր անձնական հղումը՝\n{link}\n\n"
                f"{bonus_info}", 
                reply_markup=kb
            )
        else:
            # Ցույց տալ բոլոր ալիքները (հիմնական + թաքնված)
            channels_text = "📢 Խնդրում ենք բաժանորդագրվել այս ալիքներին:\n\n"
            for i, channel in enumerate(ALL_CHANNELS, 1):
                channels_text += f"{i}. {channel['name']}\n"
            channels_text += "\nԲաժանորդագրվելուց հետո սեղմեք ստորև նշված կոճակը ↓"
            
            await message.answer(
                channels_text,
                reply_markup=get_channels_keyboard(not_subscribed_channels)
            )
        return

    # --- Իմ մնացորդը ---
    if text == "Իմ մնացորդը" or text == "Ցույց տալ մնացորդը":
        bal, refs, withdrawn, bonus_activated = get_balance(user_id)
        referrals, _, current_reward, remaining_to_bonus = get_referral_stats(user_id)
        base_bal = get_base_balance(user_id)
        
        if bonus_activated:
            bonus_status = "✅ ԱԿՏԻՎԱՑԱԾ Է (x2)"
            bonus_details = f"🎯 Ընթացիկ պարգև՝ {current_reward} դրամ ռեֆերալի համար\n💰 Բազային հաշվեկշիռ՝ {base_bal} դրամ"
        else:
            bonus_status = "❌ ԱԿՏԻՎԱՑԱԾ ՉԷ"
            bonus_details = f"🎯 Ընթացիկ պարգև՝ {current_reward} դրամ\n📈 x2 բոնուսին մնաց՝ {remaining_to_bonus} ռեֆերալ"
        
        await message.answer(
            f"👥 Ռեֆերալներ՝ {refs}\n"
            f"💰 Մնացորդ՝ {bal} դրամ\n"
            f"📤 Կանխիկացված՝ {withdrawn} դրամ\n\n"
            f"🚀 x2 բոնուս՝ {bonus_status}\n"
            f"{bonus_details}",
            reply_markup=balance_menu()
        )
        return

    # --- Կանխիկացնել ---
    if text == "Կանխիկացնել":
        await message.answer("Ընտրեք կանխիկացման եղանակը։", reply_markup=withdraw_menu())
        return

    if text == "Կանխիկացնել դրամով":
        bal, _, _, _ = get_balance(user_id)
        await message.answer(f"Ձեր մնացորդը՝ {bal} դրամ է։\nՄուտքագրեք գումարը։\nՆվազագույնը՝ {MIN_DRAM} դրամ")
        await state.set_state(WithdrawDrama.waiting_amount)
        return

    if text == "Փոխանակել UC-ի հետ":
        bal, _, _, _ = get_balance(user_id)
        await message.answer(f"Ձեր մնացորդը՝ {bal} դրամ է։\nՄուտքագրեք UC-ի քանակը։\nՆվազագույնը՝ {MIN_UC} UC (30-ի բազմապատիկ)")
        await state.set_state(WithdrawUC.waiting_uc)
        return

    if text == "Փոխանակել TG Stars-ի հետ":
        bal, _, _, _ = get_balance(user_id)
        await message.answer(f"Ձեր մնացորդը՝ {bal} դրամ է։\nՄուտքագրեք Stars-ի քանակը։\nՆվազագույնը՝ {MIN_STARS} ⭐")
        await state.set_state(WithdrawStars.waiting_stars)
        return

# ===========================================
#              DRAM FSM
# ===========================================
@dp.message(WithdrawDrama.waiting_amount)
async def withdraw_drama_amount(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    bal, _, _, _ = get_balance(user_id)
    if not message.text.isdigit():
        await message.answer("❌ Մուտքագրեք միայն թիվ։")
        return

    amount = int(message.text)
    
    if amount < MIN_DRAM:
        await message.answer(f"❌ Նվազագույն գումարը {MIN_DRAM} դրամ է։")
        return
        
    if amount > bal:
        await message.answer(f"❌ Մնացորդը բավարար չէ։ Առավելագույնը՝ {bal} դրամ։")
        return

    await state.update_data(amount=amount)
    await message.answer("Մուտքագրեք քարտի 16 թիվը։")
    await state.set_state(WithdrawDrama.waiting_code)

@dp.message(WithdrawDrama.waiting_code)
async def withdraw_drama_code(message: types.Message, state: FSMContext):
    if not message.text.isdigit() or len(message.text) != 16:
        await message.answer("❌ Սխալ կոդ։ Մուտքագրեք 16 թիվ։")
        return
    await message.answer("Մուտքագրեք ձեր բանկի անունը։ Ստուգեք այն քանի որ հաստատելուց հետո փոխելը անհնարին կլինի")
    await state.set_state(WithdrawDrama.waiting_bank)

@dp.message(WithdrawDrama.waiting_bank)
async def withdraw_drama_bank(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    data = await state.get_data()
    amount = data["amount"]
    update_balance_withdraw(user_id, amount)
    bal, refs, withdrawn, bonus_activated = get_balance(user_id)
    
    bonus_status = "✅ ԱԿՏԻՎԱՑԱԾ Է (x2)" if bonus_activated else "❌ ԱԿՏԻՎԱՑԱԾ ՉԷ"
    
    await message.answer(
        f"✅ Գործողությունը հաջողությամբ ավարտվեց։\n"
        f"ԿԱՐևՈՐ❗️։\n"
        f"Բագերից խուսափելու համար խնդրում ենք, կանխիկացումը վիդեո տարբերակով ուղարկեք մեզ անձնական նամակով @Bonus_HunterAdm։\n"
        f"Մեր մասնագետները գումարը կփոխանցեն 3-10 աշխատանքային օրվա ընթացքում։\n"
        f"Բոտից կամ ալիքներից դուրս գալու դեպքում ձեր կանխիկացումը ավտոմատ կմերժվի ինչից հետո այն վերականգնելը անհնարին կլինի։\n"
        f"Մնացորդ՝ {bal} դրամ\n"
        f"Կանխիկացված՝ {withdrawn} դրամ\n"
        f"Ռեֆերալներ՝ {refs}\n"
        f"🚀 x2 բոնուս՝ {bonus_status}"
    )
    await state.clear()

# ===========================================
#                UC FSM
# ===========================================
@dp.message(WithdrawUC.waiting_uc)
async def withdraw_uc_amount(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    bal, _, _, _ = get_balance(user_id)
    uc_value = 5

    if not message.text.isdigit():
        await message.answer("❌ Մուտքագրեք միայն թիվ։")
        return

    amount = int(message.text)

    if amount < MIN_UC:
        await message.answer(f"❌ UC-ի նվազագույն քանակը {MIN_UC} է։")
        return
        
    if amount % 30 != 0:
        await message.answer("❌ UC-ի քանակը պետք է լինի 30-ի բազմապատիկ։")
        return

    total_cost = amount * uc_value
    if total_cost > bal:
        await message.answer("❌ Մնացորդը բավարար չէ։")
        return

    await state.update_data(amount=total_cost)
    await message.answer("Մուտքագրեք ձեր խաղային ID-ին։ Ստուգեք այն քանի որ հաստատելուց հետո փոխելը անհնարին կլինի")
    await state.set_state(WithdrawUC.waiting_id)

@dp.message(WithdrawUC.waiting_id)
async def withdraw_uc_id(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    data = await state.get_data()
    amount = data["amount"]
    update_balance_withdraw(user_id, amount)
    bal, refs, withdrawn, bonus_activated = get_balance(user_id)
    
    bonus_status = "✅ ԱԿՏԻՎԱՑԱԾ Է (x2)" if bonus_activated else "❌ ԱԿՏԻՎԱՑԱԾ ՉԷ"
    
    await message.answer(
        f"✅ Գործողությունը հաջողությամբ ավարտվեց։\n"
        f"ԿԱՐևՈՐ❗️։\n"
        f"Բագերից խուսափելու համար խնդրում ենք, կանխիկացումը վիդեո տարբերակով ուղարկեք մեզ անձնական նամակով @Bonus_HunterAdm։\n"
        f"Մեր մասնագետները գումարը կփոխանցեն 3-10 աշխատանքային օրվա ընթացքում։\n"
        f"Բոտից կամ ալիքներից դուրս գալու դեպքում ձեր կանխիկացումը ավտոմատ կմերժվի ինչից հետո այն վերականգնելը անհնարին կլինի։\n"
        f"Մնացորդ՝ {bal} դրամ\n"
        f"Կանխիկացված՝ {withdrawn} դրամ\n"
        f"Ռեֆերալներ՝ {refs}\n"
        f"🚀 x2 բոնուս՝ {bonus_status}"
    )
    await state.clear()

# ===========================================
#              STARS FSM
# ===========================================
@dp.message(WithdrawStars.waiting_stars)
async def withdraw_stars_amount(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    bal, _, _, _ = get_balance(user_id)
    star_value = 7

    if not message.text.isdigit():
        await message.answer("❌ Մուտքագրեք ճիշտ թիվ։")
        return

    amount = int(message.text)
    
    if amount < MIN_STARS:
        await message.answer(f"❌ Նվազագույն քանակը {MIN_STARS} ⭐ է։")
        return

    max_stars = bal // star_value

    if amount > max_stars:
        await message.answer(f"❌ Բավարար գումար չկա։ Առավելագույնը՝ {max_stars} ⭐")
        return

    total_cost = amount * star_value
    await state.update_data(amount=total_cost)
    await message.answer("Մուտքագրեք @username-ը։")
    await state.set_state(WithdrawStars.waiting_username)

@dp.message(WithdrawStars.waiting_username)
async def withdraw_stars_username(message: types.Message, state: FSMContext):
    if not message.text.startswith("@"):
        await message.answer("❌ Username-ը պետք է սկսվի @-ով։ Ստուգեք այն քանի որ հաստատելուց հետո փոխելը անհնարին կլինի")
        return

    user_id = message.from_user.id
    data = await state.get_data()
    amount = data["amount"]
    update_balance_withdraw(user_id, amount)
    bal, refs, withdrawn, bonus_activated = get_balance(user_id)
    
    bonus_status = "✅ ԱԿՏԻՎԱՑԱԾ Է (x2)" if bonus_activated else "❌ ԱԿՏԻՎԱՑԱԾ ՉԷ"
    
    await message.answer(
        f"✅ Գործողությունը հաջողությամբ ավարտվեց։\n"
        f"ԿԱՐևՈՐ❗️։\n"
        f"Բագերից խուսափելու համար խնդրում ենք, կանխիկացումը վիդեո տարբերակով ուղարկեք մեզ անձնական նամակով @Bonus_HunterAdm։\n"
        f"Մեր մասնագետները գումարը կփոխանցեն 3-10 աշխատանքային օրվա ընթացքում։\n"
        f"Բոտից կամ ալիքներից դուրս գալու դեպքում ձեր կանխիկացումը ավտոմատ կմերժվի ինչից հետո այն վերականգնելը անհնարին կլինի։\n"
        f"Մնացորդ՝ {bal} դրամ\n"
        f"Կանխիկացված՝ {withdrawn} դրամ\n"
        f"Ռեֆերալներ՝ {refs}\n"
        f"🚀 x2 բոնուս՝ {bonus_status}"
    )
    await state.clear()

# ===========================================
#              Բոտի գործարկում
# ===========================================
async def main():
    # Удаляем старое преобразование таблицы - начинаем с чистой
    await dp.start_polling(bot)

if __name__ == "__main__":

    asyncio.run(main())

# ========== ДОБАВЬ В КОНЕЦ ==========
if __name__ == '__main__':
    logger.info("🤖 Бот запускается на Render...")
    logger.info(f"Токен: {TOKEN[:10]}...")  # Показываем только часть токена
    
    try:
        bot.infinity_polling()
    except Exception as e:
        logger.error(f"❌ Ошибка: {e}")
        time.sleep(5)  # Пауза перед перезапуском
# ====================================
