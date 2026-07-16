import telebot
from telebot import types
import random
import time
import threading
import psycopg2
import json
import os
from psycopg2.extras import RealDictCursor

# ================= КОНФИГ =================
TOKEN = os.environ.get('BOT_TOKEN', 'ТВОЙ_ТОКЕН_СЮДА')
ADMIN_ID = int(os.environ.get('ADMIN_ID', 123456789))

if not os.path.exists('data'):
    os.makedirs('data')

bot = telebot.TeleBot(TOKEN)

# ================= ПРЕДМЕТЫ =================
ITEMS = {
    'premium': {
        '1': '🌟 Звездный подарок',
        '2': '💎 Алмазный стикер',
        '3': '👑 Королевский эмодзи',
        '4': '🚀 Ракетный апгрейд',
        '5': '🎁 Мега-подарок'
    },
    'free': {
        '1': '🗑 Мусорный пакет',
        '2': '🍌 Банан',
        '3': '🧦 Грязный носок',
        '4': '📦 Пустая коробка',
        '5': '🪙 Медная монета'
    },
    'halloween': {
        '1': '🎃 Тыква-светильник',
        '2': '🧛 Клыки вампира',
        '3': '🕷 Паук-талисман',
        '4': '💀 Череп сокровищ',
        '5': '👻 Призрачный дар'
    },
    'newyear': {
        '1': '❄️ Снежинка удачи',
        '2': '🎄 Елочный шар',
        '3': '🎅 Мешок подарков',
        '4': '🦌 Олень-проводник',
        '5': '⭐ Новогодняя звезда'
    },
    'legendary': {
        '1': '⚡ Молния Тора',
        '2': '🔥 Огненный меч',
        '3': '🌊 Трезубец Посейдона',
        '4': '🛡 Щит Ахиллеса',
        '5': '👑 Корона Бессмертия'
    },
    'pepe': {
        '1': '🐸 Пепе Обычный',
        '2': '🐸 Пепе Счастливый',
        '3': '🐸 Пепе Грустный',
        '4': '🐸 Пепе Злой',
        '5': '🐸 ПЕПЕ ЛЕГЕНДАРНЫЙ 💎'
    }
}

# ================= ШАНСЫ ВЫПАДЕНИЯ =================
CHANCES = {
    'premium': {'1': 20, '2': 15, '3': 10, '4': 5, '5': 50},
    'free': {'1': 30, '2': 25, '3': 20, '4': 15, '5': 10},
    'halloween': {'1': 25, '2': 20, '3': 20, '4': 15, '5': 20},
    'newyear': {'1': 30, '2': 25, '3': 15, '4': 15, '5': 15},
    'legendary': {'1': 25, '2': 20, '3': 20, '4': 15, '5': 20},
    'pepe': {'1': 30, '2': 25, '3': 20, '4': 15, '5': 10}
}

PEPE_LEGENDARY_CHANCE = 1

# ================= ЦЕНЫ ПРОДАЖИ =================
PRICES = {
    'premium': {'1': 50, '2': 75, '3': 100, '4': 150, '5': 200},
    'free': {'1': 1, '2': 2, '3': 3, '4': 5, '5': 10},
    'halloween': {'1': 60, '2': 80, '3': 100, '4': 150, '5': 200},
    'newyear': {'1': 50, '2': 70, '3': 90, '4': 130, '5': 180},
    'legendary': {'1': 500, '2': 750, '3': 1000, '4': 1500, '5': 2000},
    'pepe': {
        '1': 30000,
        '2': 50000,
        '3': 60000,
        '4': 80000,
        '5': 1000000
    }
}

# ================= ПОДКЛЮЧЕНИЕ К БАЗЕ =================
def get_db_connection():
    """Подключение к PostgreSQL на Railway"""
    database_url = os.environ.get('DATABASE_URL')
    if database_url:
        return psycopg2.connect(database_url, sslmode='require')
    else:
        return psycopg2.connect(
            host=os.environ.get('DB_HOST', 'localhost'),
            database=os.environ.get('DB_NAME', 'game_bot'),
            user=os.environ.get('DB_USER', 'postgres'),
            password=os.environ.get('DB_PASSWORD', 'password'),
            port=os.environ.get('DB_PORT', 5432)
        )

def init_db():
    conn = get_db_connection()
    cur = conn.cursor()
    
    cur.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id BIGINT PRIMARY KEY,
            stars INTEGER DEFAULT 15,
            inventory TEXT DEFAULT '{}',
            username TEXT DEFAULT ''
        )
    ''')
    
    cur.execute('''
        CREATE TABLE IF NOT EXISTS promocodes (
            code TEXT PRIMARY KEY,
            type TEXT,
            item_id TEXT,
            stars INTEGER DEFAULT 0,
            uses INTEGER DEFAULT 1,
            used_by TEXT DEFAULT '[]'
        )
    ''')
    
    cur.execute('''
        CREATE TABLE IF NOT EXISTS cases (
            case_id TEXT PRIMARY KEY,
            name TEXT,
            enabled INTEGER DEFAULT 1,
            price INTEGER DEFAULT 0,
            is_temporary INTEGER DEFAULT 0,
            emoji TEXT DEFAULT '🎁'
        )
    ''')
    
    default_cases = [
        ('free', '🗑️ Кейс Бомжа', 1, 0, 0, '🗑️'),
        ('premium', '💎 Премиум Кейс', 1, 100, 0, '💎'),
        ('halloween', '🎃 Хеллоуинский Кейс', 0, 150, 1, '🎃'),
        ('newyear', '🎄 Новогодний Кейс', 0, 150, 1, '🎄'),
        ('legendary', '⚡ Легендарный Кейс', 1, 500, 0, '⚡'),
        ('pepe', '🐸 PePe праздник🔥', 1, 100000, 0, '🐸')
    ]
    
    for case in default_cases:
        cur.execute('''
            INSERT INTO cases (case_id, name, enabled, price, is_temporary, emoji) 
            VALUES (%s, %s, %s, %s, %s, %s) 
            ON CONFLICT (case_id) DO NOTHING
        ''', case)
    
    conn.commit()
    cur.close()
    conn.close()
    print("✅ База данных PostgreSQL инициализирована")

def get_user(user_id):
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute('SELECT stars, inventory, username FROM users WHERE user_id = %s', (user_id,))
        result = cur.fetchone()
        
        if result:
            cur.close()
            conn.close()
            return {
                'stars': result['stars'], 
                'inventory': json.loads(result['inventory']), 
                'username': result['username'] or ''
            }
        else:
            cur.execute('INSERT INTO users (user_id, stars, inventory, username) VALUES (%s, %s, %s, %s)', 
                        (user_id, 15, json.dumps({}), ''))
            conn.commit()
            cur.close()
            conn.close()
            return {'stars': 15, 'inventory': {}, 'username': ''}
    except Exception as e:
        print(f"❌ Ошибка в get_user: {e}")
        return {'stars': 15, 'inventory': {}, 'username': ''}

def update_user(user_id, stars, inventory):
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute('UPDATE users SET stars = %s, inventory = %s WHERE user_id = %s', 
                    (stars, json.dumps(inventory), user_id))
        conn.commit()
        cur.close()
        conn.close()
        return True
    except Exception as e:
        print(f"❌ Ошибка в update_user: {e}")
        return False

def update_username(user_id, username):
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute('UPDATE users SET username = %s WHERE user_id = %s', (username, user_id))
        conn.commit()
        cur.close()
        conn.close()
        return True
    except Exception as e:
        print(f"❌ Ошибка в update_username: {e}")
        return False

def get_all_users():
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute('SELECT user_id FROM users')
        users = cur.fetchall()
        cur.close()
        conn.close()
        return [user[0] for user in users]
    except:
        return []

def get_all_users_data():
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute('SELECT user_id, stars, username FROM users ORDER BY stars DESC')
        users = cur.fetchall()
        cur.close()
        conn.close()
        return users
    except:
        return []

def is_case_enabled(case_id):
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute('SELECT enabled FROM cases WHERE case_id = %s', (case_id,))
        result = cur.fetchone()
        cur.close()
        conn.close()
        return result and result[0] == 1
    except:
        return False

def get_case_price(case_id):
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute('SELECT price FROM cases WHERE case_id = %s', (case_id,))
        result = cur.fetchone()
        cur.close()
        conn.close()
        return result[0] if result else 0
    except:
        return 0

def get_case_name(case_id):
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute('SELECT name, emoji FROM cases WHERE case_id = %s', (case_id,))
        result = cur.fetchone()
        cur.close()
        conn.close()
        return (result[0], result[1]) if result else (case_id, '🎁')
    except:
        return (case_id, '🎁')

def get_item_price(item_id, case_type):
    return PRICES.get(case_type, {}).get(item_id, 1)

def open_case(case_type):
    if case_type == 'pepe':
        if random.randint(1, 100) <= PEPE_LEGENDARY_CHANCE:
            return '5', ITEMS['pepe']['5']
        
        rand_num = random.randint(1, 100)
        cumulative = 0
        for item_id, chance in CHANCES['pepe'].items():
            cumulative += chance
            if rand_num <= cumulative:
                return item_id, ITEMS['pepe'][item_id]
    
    rand_num = random.randint(1, 100)
    cumulative = 0
    for item_id, chance in CHANCES.get(case_type, {}).items():
        cumulative += chance
        if rand_num <= cumulative:
            return item_id, ITEMS[case_type][item_id]
    
    return '1', 'Ошибка'

def create_promocode(code, type, item_id=None, stars=0, uses=1):
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute('INSERT INTO promocodes (code, type, item_id, stars, uses) VALUES (%s, %s, %s, %s, %s)',
                    (code, type, item_id, stars, uses))
        conn.commit()
        cur.close()
        conn.close()
        return True
    except:
        return False

def delete_promocode(code):
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute('DELETE FROM promocodes WHERE code = %s', (code,))
        conn.commit()
        cur.close()
        conn.close()
        return True
    except:
        return False

def get_all_promocodes():
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute('SELECT code, type, item_id, stars, uses FROM promocodes')
        codes = cur.fetchall()
        cur.close()
        conn.close()
        return codes
    except:
        return []

def use_promocode(code, user_id):
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute('SELECT type, item_id, stars, uses, used_by FROM promocodes WHERE code = %s', (code,))
        result = cur.fetchone()
        if not result:
            cur.close()
            conn.close()
            return None, "❌ Промокод не найден"
        
        type, item_id, stars, uses, used_by_json = result
        used_by = json.loads(used_by_json) if used_by_json else []
        
        if str(user_id) in used_by:
            cur.close()
            conn.close()
            return None, "❌ Вы уже использовали этот промокод"
        
        if uses <= len(used_by):
            cur.close()
            conn.close()
            return None, "❌ Промокод уже использован максимальное количество раз"
        
        user_data = get_user(user_id)
        if type == 'stars':
            user_data['stars'] += stars
            update_user(user_id, user_data['stars'], user_data['inventory'])
            used_by.append(str(user_id))
            cur.execute('UPDATE promocodes SET used_by = %s WHERE code = %s', (json.dumps(used_by), code))
            conn.commit()
            cur.close()
            conn.close()
            return 'stars', f"⭐ Вы получили {stars:,} звезд!"
        
        elif type == 'item':
            inventory = user_data['inventory']
            if item_id in inventory:
                inventory[item_id]['count'] += 1
            else:
                case_type = None
                for ct, items in ITEMS.items():
                    if item_id in items:
                        case_type = ct
                        break
                if case_type:
                    inventory[item_id] = {'name': ITEMS[case_type][item_id], 'count': 1, 'type': case_type}
            update_user(user_id, user_data['stars'], inventory)
            used_by.append(str(user_id))
            cur.execute('UPDATE promocodes SET used_by = %s WHERE code = %s', (json.dumps(used_by), code))
            conn.commit()
            cur.close()
            conn.close()
            return 'item', f"🎁 Вы получили предмет: {ITEMS.get(case_type, {}).get(item_id, 'Неизвестно')}"
        
        cur.close()
        conn.close()
        return None, "❌ Неизвестный тип промокода"
    except Exception as e:
        print(f"❌ Ошибка в use_promocode: {e}")
        return None, "❌ Ошибка при использовании промокода"

# ================= АНИМАЦИЯ =================
def animate_case(call, case_type):
    try:
        message = call.message
        case_name, emoji = get_case_name(case_type)
        
        animation_frames = [
            ['🎰', '🎲', '✨'],
            ['✨', '🎰', '🎲'],
            ['🎲', '✨', '🎰'],
            ['⭐', '💫', '🌟'],
            ['💫', '🌟', '⭐'],
            ['🌟', '⭐', '💫']
        ]
        
        anim_msg = bot.send_message(
            message.chat.id, 
            f"{emoji} **Открываем {case_name}...**\n\n"
            f"🌀 Подготовка..."
        )
        
        for frame in animation_frames:
            time.sleep(0.3)
            bot.edit_message_text(
                chat_id=message.chat.id,
                message_id=anim_msg.message_id,
                text=f"{emoji} **Открываем {case_name}...**\n\n"
                     f"{' '.join(frame)}",
                parse_mode='Markdown'
            )
        
        item_id, item_name = open_case(case_type)
        
        user_data = get_user(message.chat.id)
        inventory = user_data['inventory']
        
        if item_id in inventory:
            inventory[item_id]['count'] += 1
        else:
            inventory[item_id] = {'name': item_name, 'count': 1, 'type': case_type}
        
        update_user(message.chat.id, user_data['stars'], inventory)
        
        price = get_item_price(item_id, case_type)
        
        if price >= 1000000:
            rarity = "🔥🔥🔥 **ЛЕГЕНДАРНО!** 🔥🔥🔥"
        elif price >= 50000:
            rarity = "✨✨ **ЭПИЧЕСКИЙ ВЫПАД!** ✨✨"
        elif price >= 10000:
            rarity = "🌟 **РЕДКИЙ ПРЕДМЕТ!** 🌟"
        else:
            rarity = "📦 Обычный предмет"
        
        final_text = f"{rarity}\n\n"
        final_text += f"🎉 Вам выпало: **{item_name}**\n"
        final_text += f"💰 Цена продажи: **{price:,}** ⭐\n"
        final_text += f"\n💡 Предмет добавлен в инвентарь!"
        
        bot.edit_message_text(
            chat_id=message.chat.id,
            message_id=anim_msg.message_id,
            text=final_text,
            parse_mode='Markdown'
        )
        
        time.sleep(0.5)
        show_main_menu(message.chat.id)
    except Exception as e:
        print(f"❌ Ошибка в animate_case: {e}")

# ================= КЛАВИАТУРЫ =================
def main_menu_keyboard(user_id):
    keyboard = types.InlineKeyboardMarkup(row_width=2)
    
    cases = [
        ('free', '🗑️ Кейс Бомжа (Бесплатно)'),
        ('premium', '💎 Премиум Кейс (100 ⭐)'),
        ('legendary', '⚡ Легендарный Кейс (500 ⭐)')
    ]
    
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute('SELECT case_id, name, price, emoji FROM cases WHERE enabled = 1 AND case_id NOT IN ("free", "premium", "legendary")')
        temp_cases = cur.fetchall()
        cur.close()
        conn.close()
        
        for case in temp_cases:
            price_text = "Бесплатно" if case[2] == 0 else f"{case[2]:,} ⭐".replace(',', ' ')
            emoji = case[3] if len(case) > 3 else '🎁'
            cases.append((case[0], f"{emoji} {case[1]} ({price_text})"))
    except:
        pass
    
    for case_id, label in cases:
        btn = types.InlineKeyboardButton(label, callback_data=f"case_{case_id}")
        keyboard.add(btn)
    
    btn_profile = types.InlineKeyboardButton("👤 Мой профиль", callback_data="profile")
    btn_sell = types.InlineKeyboardButton("💰 Продать предметы", callback_data="sell")
    btn_leaderboard = types.InlineKeyboardButton("🏆 Лидеры", callback_data="leaderboard")
    btn_promocode = types.InlineKeyboardButton("🎫 Промокод", callback_data="promocode")
    
    keyboard.add(btn_profile, btn_sell)
    keyboard.add(btn_leaderboard, btn_promocode)
    
    return keyboard

def show_main_menu(chat_id):
    try:
        user = get_user(chat_id)
        
        text = f"""🏠 **Главное меню**

⭐ **Баланс:** {user['stars']:,} звезд
📦 **Предметов:** {sum(item['count'] for item in user['inventory'].values())}

Выберите действие:"""
        
        bot.send_message(
            chat_id,
            text,
            reply_markup=main_menu_keyboard(chat_id),
            parse_mode='Markdown'
        )
    except Exception as e:
        print(f"❌ Ошибка в show_main_menu: {e}")

def sell_keyboard(user_id):
    try:
        user = get_user(user_id)
        inventory = user['inventory']
        keyboard = types.InlineKeyboardMarkup(row_width=2)
        
        if not inventory:
            keyboard.add(types.InlineKeyboardButton("🔙 Назад", callback_data="back"))
            return keyboard
        
        for item_id, data in inventory.items():
            price = get_item_price(item_id, data['type'])
            if price >= 1000000:
                rarity = "💎💎💎"
            elif price >= 50000:
                rarity = "💎✨"
            elif price >= 10000:
                rarity = "✨⭐"
            elif price >= 1000:
                rarity = "⭐"
            else:
                rarity = "📦"
            
            btn = types.InlineKeyboardButton(
                f"{rarity} {data['name']} x{data['count']} (+{price:,}⭐)",
                callback_data=f"sell_{item_id}"
            )
            keyboard.add(btn)
        
        keyboard.add(types.InlineKeyboardButton("🔙 Назад", callback_data="back"))
        return keyboard
    except:
        keyboard = types.InlineKeyboardMarkup()
        keyboard.add(types.InlineKeyboardButton("🔙 Назад", callback_data="back"))
        return keyboard

def admin_menu_keyboard():
    keyboard = types.InlineKeyboardMarkup(row_width=1)
    keyboard.add(
        types.InlineKeyboardButton("📊 Промокоды", callback_data="admin_promocodes"),
        types.InlineKeyboardButton("➕ Создать промокод", callback_data="admin_create_promo"),
        types.InlineKeyboardButton("📢 Рассылка", callback_data="admin_broadcast"),
        types.InlineKeyboardButton("🎮 Управление кейсами", callback_data="admin_cases"),
        types.InlineKeyboardButton("🔙 Назад", callback_data="back")
    )
    return keyboard

def admin_cases_keyboard():
    keyboard = types.InlineKeyboardMarkup(row_width=1)
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute('SELECT case_id, name, enabled, emoji, is_temporary FROM cases')
        cases = cur.fetchall()
        cur.close()
        conn.close()
        
        for case_id, name, enabled, emoji, is_temporary in cases:
            status = "✅ Включен" if enabled else "❌ Выключен"
            temp_tag = " 🕐" if is_temporary else ""
            btn = types.InlineKeyboardButton(
                f"{emoji} {name}{temp_tag} - {status}",
                callback_data=f"admin_toggle_case_{case_id}"
            )
            keyboard.add(btn)
    except:
        pass
    
    keyboard.add(types.InlineKeyboardButton("🔙 Назад в админку", callback_data="admin_back"))
    return keyboard

# ================= ОБРАБОТЧИКИ =================
@bot.message_handler(commands=['start'])
def start(message):
    try:
        print(f"✅ Получена команда /start от {message.chat.id}")
        user_id = message.chat.id
        
        if message.from_user.username:
            update_username(user_id, message.from_user.username)
        
        get_user(user_id)
        
        welcome_text = """👋 **Добро пожаловать в Игровой Бот!**

🎁 Тебе выдано **15** ⭐ звезд.
💰 Открывай кейсы, собирай предметы и продавай их!

**Доступные кейсы:**
🗑️ **Кейс Бомжа** - бесплатный, для старта
💎 **Премиум Кейс** - 100 ⭐, редкие предметы
⚡ **Легендарный Кейс** - 500 ⭐, эпические предметы
🐸 **PePe праздник🔥** - 100 000 ⭐, шанс на Пепе за 1 млн!

**Цены Пепе:**
🐸 Обычный - 30 000 ⭐
🐸 Счастливый - 50 000 ⭐
🐸 Грустный - 60 000 ⭐
🐸 Злой - 80 000 ⭐
🐸 ЛЕГЕНДАРНЫЙ - 1 000 000 ⭐ (шанс 1%)

🎯 **Цель:** Собрать легендарного Пепе и стать самым богатым!
"""
        
        bot.send_message(
            user_id,
            welcome_text,
            parse_mode='Markdown'
        )
        
        show_main_menu(user_id)
        print(f"✅ Приветствие отправлено пользователю {user_id}")
    except Exception as e:
        print(f"❌ Ошибка в start: {e}")

@bot.message_handler(commands=['admin'])
def admin_panel(message):
    try:
        if message.chat.id != ADMIN_ID:
            bot.reply_to(message, "⛔ Доступ запрещен!")
            return
        
        bot.send_message(
            message.chat.id,
            "👑 **Админ панель**\nВыберите действие:",
            reply_markup=admin_menu_keyboard(),
            parse_mode='Markdown'
        )
    except Exception as e:
        print(f"❌ Ошибка в admin_panel: {e}")

@bot.callback_query_handler(func=lambda call: True)
def callback_handler(call):
    try:
        user_id = call.message.chat.id
        user_data = get_user(user_id)
        
        if call.data.startswith("case_"):
            case_id = call.data.split("_")[1]
            
            if not is_case_enabled(case_id):
                bot.answer_callback_query(call.id, "❌ Этот кейс временно отключен!", show_alert=True)
                return
            
            price = get_case_price(case_id)
            
            if price > 0:
                if user_data['stars'] >= price:
                    user_data['stars'] -= price
                    update_user(user_id, user_data['stars'], user_data['inventory'])
                    bot.delete_message(user_id, call.message.message_id)
                    threading.Thread(target=animate_case, args=(call, case_id)).start()
                else:
                    bot.answer_callback_query(call.id, f"❌ Недостаточно звезд! Нужно: {price:,} ⭐".replace(',', ' '), show_alert=True)
            else:
                bot.delete_message(user_id, call.message.message_id)
                threading.Thread(target=animate_case, args=(call, case_id)).start()
        
        elif call.data == "profile":
            inv_text = ""
            total_items = 0
            total_value = 0
            
            if user_data['inventory']:
                for item_id, data in user_data['inventory'].items():
                    price = get_item_price(item_id, data['type'])
                    total_value += price * data['count']
                    total_items += data['count']
                    if price >= 1000000:
                        rarity = "💎💎💎"
                    elif price >= 50000:
                        rarity = "💎✨"
                    elif price >= 10000:
                        rarity = "✨⭐"
                    elif price >= 1000:
                        rarity = "⭐"
                    else:
                        rarity = "📦"
                    inv_text += f"{rarity} {data['name']} x{data['count']} (+{price:,}⭐)\n"
            else:
                inv_text = "Пусто"
            
            text = f"""👤 **Ваш профиль**

⭐ **Звезды:** {user_data['stars']:,}
📦 **Предметов:** {total_items}
💰 **Общая стоимость:** {total_value:,} ⭐

**📦 Инвентарь:**
{inv_text}"""
            
            bot.edit_message_text(
                chat_id=user_id,
                message_id=call.message.message_id,
                text=text,
                parse_mode='Markdown',
                reply_markup=types.InlineKeyboardMarkup().add(
                    types.InlineKeyboardButton("🔙 Назад", callback_data="back")
                )
            )
        
        elif call.data == "sell":
            keyboard = sell_keyboard(user_id)
            bot.edit_message_text(
                chat_id=user_id,
                message_id=call.message.message_id,
                text="💰 **Выберите предмет для продажи:**",
                parse_mode='Markdown',
                reply_markup=keyboard
            )
        
        elif call.data.startswith("sell_"):
            item_id = call.data.split("_")[1]
            if item_id in user_data['inventory']:
                item = user_data['inventory'][item_id]
                price = get_item_price(item_id, item['type'])
                
                if price >= 1000000:
                    confirm = types.InlineKeyboardMarkup()
                    confirm.add(
                        types.InlineKeyboardButton("✅ Да, продать", callback_data=f"confirm_sell_{item_id}"),
                        types.InlineKeyboardButton("❌ Нет", callback_data="sell")
                    )
                    bot.edit_message_text(
                        chat_id=user_id,
                        message_id=call.message.message_id,
                        text=f"⚠️ **Вы уверены?**\nВы хотите продать **{item['name']}** за {price:,} ⭐\n\nЭто очень ценный предмет!",
                        parse_mode='Markdown',
                        reply_markup=confirm
                    )
                else:
                    item['count'] -= 1
                    if item['count'] <= 0:
                        del user_data['inventory'][item_id]
                    
                    user_data['stars'] += price
                    update_user(user_id, user_data['stars'], user_data['inventory'])
                    
                    bot.answer_callback_query(call.id, f"✅ Продано за {price:,} ⭐!".replace(',', ' '), show_alert=False)
                    
                    keyboard = sell_keyboard(user_id)
                    bot.edit_message_text(
                        chat_id=user_id,
                        message_id=call.message.message_id,
                        text="💰 **Выберите предмет для продажи:**",
                        parse_mode='Markdown',
                        reply_markup=keyboard
                    )
            else:
                bot.answer_callback_query(call.id, "❌ Этого предмета больше нет!", show_alert=True)
        
        elif call.data.startswith("confirm_sell_"):
            item_id = call.data.split("_")[2]
            if item_id in user_data['inventory']:
                item = user_data['inventory'][item_id]
                price = get_item_price(item_id, item['type'])
                
                item['count'] -= 1
                if item['count'] <= 0:
                    del user_data['inventory'][item_id]
                
                user_data['stars'] += price
                update_user(user_id, user_data['stars'], user_data['inventory'])
                
                bot.answer_callback_query(call.id, f"✅ Продано за {price:,} ⭐!".replace(',', ' '), show_alert=False)
                
                keyboard = sell_keyboard(user_id)
                bot.edit_message_text(
                    chat_id=user_id,
                    message_id=call.message.message_id,
                    text="💰 **Выберите предмет для продажи:**",
                    parse_mode='Markdown',
                    reply_markup=keyboard
                )
        
        elif call.data == "leaderboard":
            users = get_all_users_data()
            text = "🏆 **Топ игроков по звездам:**\n\n"
            if users:
                for i, (user_id, stars, username) in enumerate(users[:10], 1):
                    name = username or f"Игрок {user_id}"
                    medal = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else f"{i}."
                    text += f"{medal} {name} - {stars:,} ⭐\n"
            else:
                text += "Нет игроков"
            
            bot.edit_message_text(
                chat_id=user_id,
                message_id=call.message.message_id,
                text=text,
                parse_mode='Markdown',
                reply_markup=types.InlineKeyboardMarkup().add(
                    types.InlineKeyboardButton("🔙 Назад", callback_data="back")
                )
            )
        
        elif call.data == "promocode":
            bot.edit_message_text(
                chat_id=user_id,
                message_id=call.message.message_id,
                text="🎫 **Введите промокод:**\nНапишите его в чат.",
                parse_mode='Markdown',
                reply_markup=types.InlineKeyboardMarkup().add(
                    types.InlineKeyboardButton("🔙 Назад", callback_data="back")
                )
            )
            bot.register_next_step_handler(call.message, process_promocode)
        
        elif call.data == "back":
            bot.delete_message(user_id, call.message.message_id)
            show_main_menu(user_id)
        
        elif call.data == "admin_back":
            bot.delete_message(user_id, call.message.message_id)
            admin_panel(call.message)
        
        elif call.data == "admin_promocodes":
            codes = get_all_promocodes()
            text = "📊 **Список промокодов:**\n\n"
            if codes:
                for code, type, item_id, stars, uses in codes:
                    text += f"🔑 Код: `{code}`\n"
                    text += f"📌 Тип: {type}\n"
                    if type == 'stars':
                        text += f"⭐ Звезды: {stars:,}\n"
                    else:
                        text += f"🎁 Предмет: {item_id}\n"
                    text += f"👥 Использований: {uses}\n"
                    text += "➖➖➖➖➖➖➖\n"
            else:
                text += "Промокодов нет"
            
            keyboard = admin_menu_keyboard()
            if codes:
                for code, _, _, _, _ in codes:
                    btn = types.InlineKeyboardButton(f"🗑 Удалить {code}", callback_data=f"admin_delete_promo_{code}")
                    keyboard.add(btn)
            
            bot.edit_message_text(
                chat_id=user_id,
                message_id=call.message.message_id,
                text=text,
                parse_mode='Markdown',
                reply_markup=keyboard
            )
        
        elif call.data == "admin_create_promo":
            bot.edit_message_text(
                chat_id=user_id,
                message_id=call.message.message_id,
                text="📝 **Создание промокода**\n\n"
                     "Введите данные в формате:\n"
                     "`название_кода тип_награды параметр количество_использований`\n\n"
                     "**Типы:**\n"
                     "• `stars` - звезды (параметр: количество)\n"
                     "• `item` - предмет (параметр: ID предмета)\n\n"
                     "**Примеры:**\n"
                     "`WELCOME stars 50 10` - 50 звезд, 10 использований\n"
                     "`GIFT item premium_5 5` - Мега-подарок, 5 использований\n"
                     "`PEPE item pepe_5 1` - Легендарный Пепе, 1 использование",
                parse_mode='Markdown',
                reply_markup=types.InlineKeyboardMarkup().add(
                    types.InlineKeyboardButton("🔙 Назад", callback_data="admin_promocodes")
                )
            )
            bot.register_next_step_handler(call.message, process_create_promo)
        
        elif call.data.startswith("admin_delete_promo_"):
            code = call.data.split("_")[3]
            delete_promocode(code)
            bot.answer_callback_query(call.id, "✅ Промокод удален!", show_alert=False)
            
            codes = get_all_promocodes()
            text = "📊 **Список промокодов:**\n\n"
            if codes:
                for code, type, item_id, stars, uses in codes:
                    text += f"🔑 Код: `{code}`\n"
                    text += f"📌 Тип: {type}\n"
                    if type == 'stars':
                        text += f"⭐ Звезды: {stars:,}\n"
                    else:
                        text += f"🎁 Предмет: {item_id}\n"
                    text += f"👥 Использований: {uses}\n"
                    text += "➖➖➖➖➖➖➖\n"
            else:
                text += "Промокодов нет"
            
            keyboard = admin_menu_keyboard()
            if codes:
                for code, _, _, _, _ in codes:
                    btn = types.InlineKeyboardButton(f"🗑 Удалить {code}", callback_data=f"admin_delete_promo_{code}")
                    keyboard.add(btn)
            
            bot.edit_message_text(
                chat_id=user_id,
                message_id=call.message.message_id,
                text=text,
                parse_mode='Markdown',
                reply_markup=keyboard
            )
        
        elif call.data == "admin_broadcast":
            bot.edit_message_text(
                chat_id=user_id,
                message_id=call.message.message_id,
                text="📢 **Рассылка**\nВведите текст для рассылки всем пользователям:",
                parse_mode='Markdown',
                reply_markup=types.InlineKeyboardMarkup().add(
                    types.InlineKeyboardButton("🔙 Назад", callback_data="admin_back")
                )
            )
            bot.register_next_step_handler(call.message, process_broadcast)
        
        elif call.data == "admin_cases":
            keyboard = admin_cases_keyboard()
            bot.edit_message_text(
                chat_id=user_id,
                message_id=call.message.message_id,
                text="🎮 **Управление кейсами**\nНажмите на кейс, чтобы включить/выключить:",
                parse_mode='Markdown',
                reply_markup=keyboard
            )
        
        elif call.data.startswith("admin_toggle_case_"):
            case_id = call.data.split("_")[3]
            conn = get_db_connection()
            cur = conn.cursor()
            cur.execute('SELECT enabled FROM cases WHERE case_id = %s', (case_id,))
            current = cur.fetchone()[0]
            new_status = 0 if current else 1
            cur.execute('UPDATE cases SET enabled = %s WHERE case_id = %s', (new_status, case_id))
            conn.commit()
            cur.close()
            conn.close()
            
            status_text = "включен" if new_status else "выключен"
            bot.answer_callback_query(call.id, f"✅ Кейс {status_text}!", show_alert=False)
            
            keyboard = admin_cases_keyboard()
            bot.edit_message_text(
                chat_id=user_id,
                message_id=call.message.message_id,
                text="🎮 **Управление кейсами**\nНажмите на кейс, чтобы включить/выключить:",
                parse_mode='Markdown',
                reply_markup=keyboard
            )
    
    except Exception as e:
        print(f"❌ Ошибка в callback_handler: {e}")
        try:
            bot.answer_callback_query(call.id, f"❌ Ошибка: {str(e)}", show_alert=True)
        except:
            pass

# ================= ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ =================
def process_promocode(message):
    try:
        user_id = message.chat.id
        code = message.text.strip()
        
        if code.startswith('/'):
            show_main_menu(user_id)
            return
        
        result, msg = use_promocode(code, user_id)
        if result:
            bot.send_message(user_id, f"✅ {msg}")
        else:
            bot.send_message(user_id, f"❌ {msg}")
        show_main_menu(user_id)
    except Exception as e:
        print(f"❌ Ошибка в process_promocode: {e}")

def process_create_promo(message):
    try:
        user_id = message.chat.id
        if user_id != ADMIN_ID:
            return
        
        parts = message.text.strip().split()
        if len(parts) != 4:
            bot.send_message(user_id, "❌ Неверный формат! Используйте: `название тип параметр использование`", parse_mode='Markdown')
            admin_panel(message)
            return
        
        code, type, param, uses = parts
        uses = int(uses)
        
        if type == 'stars':
            stars = int(param)
            if create_promocode(code, type, None, stars, uses):
                bot.send_message(user_id, f"✅ Промокод создан!\n🔑 Код: `{code}`\n⭐ Звезды: {stars:,}\n👥 Использований: {uses}", parse_mode='Markdown')
            else:
                bot.send_message(user_id, "❌ Ошибка при создании промокода")
        elif type == 'item':
            found = False
            for case_type, items in ITEMS.items():
                if param in items:
                    found = True
                    break
            if found:
                if create_promocode(code, type, param, 0, uses):
                    bot.send_message(user_id, f"✅ Промокод создан!\n🔑 Код: `{code}`\n🎁 Предмет: {param}\n👥 Использований: {uses}", parse_mode='Markdown')
                else:
                    bot.send_message(user_id, "❌ Ошибка при создании промокода")
            else:
                bot.send_message(user_id, f"❌ Предмет {param} не найден!\nДоступные ID: premium_1-5, free_1-5, halloween_1-5, newyear_1-5, legendary_1-5, pepe_1-5")
        else:
            bot.send_message(user_id, "❌ Неизвестный тип! Используйте `stars` или `item`")
    except ValueError:
        bot.send_message(user_id, "❌ Неверный формат! Количество использования должно быть числом")
    except Exception as e:
        bot.send_message(user_id, f"❌ Ошибка: {str(e)}")
    
    admin_panel(message)

def process_broadcast(message):
    try:
        user_id = message.chat.id
        if user_id != ADMIN_ID:
            return
        
        text = message.text
        users = get_all_users()
        
        if not users:
            bot.send_message(user_id, "❌ Нет пользователей для рассылки")
            admin_panel(message)
            return
        
        bot.send_message(user_id, f"📢 Начинаю рассылку для {len(users)} пользователей...")
        
        success = 0
        for user in users:
            try:
                bot.send_message(user, text)
                success += 1
                time.sleep(0.05)
            except:
                pass
        
        bot.send_message(user_id, f"✅ Рассылка завершена!\n📤 Отправлено: {success}/{len(users)} пользователям")
    except Exception as e:
        bot.send_message(user_id, f"❌ Ошибка при рассылке: {str(e)}")
    
    admin_panel(message)

# ================= ЗАПУСК =================
if __name__ == '__main__':
    try:
        print("🤖 Бот запускается...")
        init_db()
        print("✅ База данных PostgreSQL готова")
        print(f"👑 Админ ID: {ADMIN_ID}")
        print("🚀 Бот готов к работе!")
        print("\n📌 Доступные кейсы:")
        print("   🗑️ Кейс Бомжа - бесплатный")
        print("   💎 Премиум Кейс - 100 ⭐")
        print("   ⚡ Легендарный Кейс - 500 ⭐")
        print("   🐸 PePe праздник🔥 - 100 000 ⭐")
        print("\n📊 Цены Пепе:")
        print("   🐸 Обычный - 30 000 ⭐")
        print("   🐸 Счастливый - 50 000 ⭐")
        print("   🐸 Грустный - 60 000 ⭐")
        print("   🐸 Злой - 80 000 ⭐")
        print("   🐸 ЛЕГЕНДАРНЫЙ - 1 000 000 ⭐ (шанс 1%)")
        bot.infinity_polling()
    except Exception as e:
        print(f"❌ Критическая ошибка: {e}")