import telebot
from telebot import types
import random
import time
import threading
import psycopg2
import json
import os
import sys
from psycopg2.extras import RealDictCursor
from psycopg2 import pool
from contextlib import contextmanager
import logging
from datetime import datetime
from typing import Optional, Dict, Any, Tuple, List

# ================= НАСТРОЙКА ЛОГИРОВАНИЯ =================
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ================= КОНФИГ =================
TOKEN = os.environ.get('BOT_TOKEN')
ADMIN_ID = int(os.environ.get('ADMIN_ID', 123456789))

if not TOKEN:
    logger.error("❌ BOT_TOKEN не найден!")
    sys.exit(1)

logger.info(f"🤖 Бот запускается... Админ ID: {ADMIN_ID}")

bot = telebot.TeleBot(TOKEN)

# ================= ПРЕДМЕТЫ И КЕЙСЫ =================
ITEMS = {
    'free': {
        '1': '🗑 Мусорный пакет',
        '2': '🍌 Банан',
        '3': '🧦 Грязный носок',
        '4': '📦 Пустая коробка',
        '5': '🪙 Медная монета'
    },
    'premium': {
        '1': '🌟 Звездный подарок',
        '2': '💎 Алмазный стикер',
        '3': '👑 Королевский эмодзи',
        '4': '🚀 Ракетный апгрейд',
        '5': '🎁 Мега-подарок'
    },
    'legendary': {
        '1': '⚡ Молния Тора',
        '2': '🔥 Огненный меч',
        '3': '🌊 Трезубец Посейдона',
        '4': '🛡 Щит Ахиллеса',
        '5': '👑 Корона Бессмертия'
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
    'mythical': {
        '1': '🌙 Лунный камень',
        '2': '☀️ Солнечный амулет',
        '3': '⭐ Звездная пыль',
        '4': '🌌 Галактический кристалл',
        '5': '💜 Сердце Вселенной'
    },
    'elite': {
        '1': '❤️ Рубин вечности',
        '2': '💎 Алмаз власти',
        '3': '👑 Корона императора',
        '4': '⚜️ Скипетр короля',
        '5': '🏆 Трофей чемпиона'
    },
    'cosmic': {
        '1': '🌌 Туманность Андромеды',
        '2': '🪐 Кольца Сатурна',
        '3': '🌠 Падающая звезда',
        '4': '🌍 Планета сокровищ',
        '5': '☄️ Комета удачи'
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
    'free': {'1': 35, '2': 25, '3': 20, '4': 15, '5': 5},
    'premium': {'1': 30, '2': 25, '3': 20, '4': 15, '5': 10},
    'legendary': {'1': 25, '2': 20, '3': 20, '4': 20, '5': 15},
    'halloween': {'1': 25, '2': 20, '3': 20, '4': 20, '5': 15},
    'newyear': {'1': 20, '2': 20, '3': 20, '4': 20, '5': 20},
    'mythical': {'1': 20, '2': 20, '3': 20, '4': 20, '5': 20},
    'elite': {'1': 15, '2': 20, '3': 20, '4': 25, '5': 20},
    'cosmic': {'1': 10, '2': 15, '3': 20, '4': 25, '5': 30},
    'pepe': {'1': 30, '2': 25, '3': 20, '4': 15, '5': 10}
}

PEPE_LEGENDARY_CHANCE = 1

# ================= ЦЕНЫ ПРОДАЖИ =================
PRICES = {
    'free': {'1': 1, '2': 2, '3': 3, '4': 5, '5': 10},
    'premium': {'1': 50, '2': 75, '3': 100, '4': 150, '5': 200},
    'legendary': {'1': 500, '2': 750, '3': 1000, '4': 1500, '5': 2000},
    'halloween': {'1': 800, '2': 1200, '3': 1600, '4': 2000, '5': 3000},
    'newyear': {'1': 1500, '2': 2000, '3': 2500, '4': 3000, '5': 5000},
    'mythical': {'1': 3000, '2': 4000, '3': 5000, '4': 7000, '5': 10000},
    'elite': {'1': 10000, '2': 15000, '3': 20000, '4': 30000, '5': 50000},
    'cosmic': {'1': 30000, '2': 50000, '3': 80000, '4': 120000, '5': 200000},
    'pepe': {'1': 30000, '2': 50000, '3': 60000, '4': 80000, '5': 1000000}
}

# ================= КОНФИГУРАЦИЯ КЕЙСОВ =================
CASE_CONFIG = {
    'free': {'price': 0, 'temporary': False, 'emoji': '🗑️'},
    'premium': {'price': 100, 'temporary': False, 'emoji': '💎'},
    'legendary': {'price': 500, 'temporary': False, 'emoji': '⚡'},
    'halloween': {'price': 2500, 'temporary': True, 'emoji': '🎃'},
    'newyear': {'price': 5000, 'temporary': True, 'emoji': '🎄'},
    'mythical': {'price': 1000, 'temporary': False, 'emoji': '💜'},
    'elite': {'price': 5000, 'temporary': False, 'emoji': '❤️'},
    'cosmic': {'price': 10000, 'temporary': False, 'emoji': '🌌'},
    'pepe': {'price': 100000, 'temporary': False, 'emoji': '🐸'}
}

# ================= ПОДКЛЮЧЕНИЕ К БАЗЕ =================
class Database:
    def __init__(self):
        self.pool = None
        self.init_pool()

    def init_pool(self):
        database_url = os.environ.get('DATABASE_URL')
        if database_url:
            try:
                self.pool = psycopg2.pool.SimpleConnectionPool(
                    1, 20, database_url, sslmode='require'
                )
                logger.info("✅ Пул подключений PostgreSQL создан")
            except Exception as e:
                logger.error(f"❌ Ошибка создания пула: {e}")
                raise
        else:
            logger.error("❌ DATABASE_URL не найден!")
            raise Exception("DATABASE_URL not found")

    @contextmanager
    def get_connection(self):
        conn = None
        try:
            conn = self.pool.getconn()
            yield conn
            conn.commit()
        except Exception as e:
            if conn:
                conn.rollback()
            logger.error(f"❌ Ошибка базы данных: {e}")
            raise
        finally:
            if conn:
                self.pool.putconn(conn)

    def close_all_connections(self):
        if self.pool:
            self.pool.closeall()
            logger.info("✅ Все соединения с БД закрыты")

db = Database()

# ================= ИНИЦИАЛИЗАЦИЯ БАЗЫ =================
def init_db():
    try:
        with db.get_connection() as conn:
            cur = conn.cursor()
            
            # Таблица пользователей
            cur.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    user_id BIGINT PRIMARY KEY,
                    stars INTEGER DEFAULT 15,
                    inventory TEXT DEFAULT '{}',
                    username TEXT DEFAULT ''
                )
            ''')
            
            # Таблица промокодов
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
            
            # Таблица кейсов
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
            
            # Все кейсы
            all_cases = [
                ('free', '🗑️ Кейс Бомжа', 1, 0, 0, '🗑️'),
                ('premium', '💎 Премиум Кейс', 1, 100, 0, '💎'),
                ('legendary', '⚡ Легендарный Кейс', 1, 500, 0, '⚡'),
                ('halloween', '🎃 Хеллоуинский Кейс', 1, 2500, 1, '🎃'),
                ('newyear', '🎄 Новогодний Кейс', 1, 5000, 1, '🎄'),
                ('mythical', '💜 Мифический Кейс', 1, 1000, 0, '💜'),
                ('elite', '❤️ Элитный Кейс', 1, 5000, 0, '❤️'),
                ('cosmic', '🌌 Космический Кейс', 1, 10000, 0, '🌌'),
                ('pepe', '🐸 PePe праздник🔥', 1, 100000, 0, '🐸')
            ]
            
            for case in all_cases:
                cur.execute('''
                    INSERT INTO cases (case_id, name, enabled, price, is_temporary, emoji) 
                    VALUES (%s, %s, %s, %s, %s, %s)
                    ON CONFLICT (case_id) DO UPDATE SET
                    name = EXCLUDED.name,
                    price = EXCLUDED.price,
                    is_temporary = EXCLUDED.is_temporary,
                    emoji = EXCLUDED.emoji
                ''', case)
            
            conn.commit()
            cur.close()
            logger.info("✅ База данных инициализирована")
            return True
    except Exception as e:
        logger.error(f"❌ Ошибка инициализации базы: {e}")
        return False

# ================= ФУНКЦИИ РАБОТЫ С ПОЛЬЗОВАТЕЛЯМИ =================
def get_user(user_id: int) -> Dict[str, Any]:
    """Получение данных пользователя с обработкой ошибок"""
    try:
        with db.get_connection() as conn:
            cur = conn.cursor(cursor_factory=RealDictCursor)
            cur.execute('SELECT stars, inventory, username FROM users WHERE user_id = %s', (user_id,))
            result = cur.fetchone()
            
            if result:
                inventory = json.loads(result['inventory']) if result['inventory'] else {}
                return {
                    'stars': result['stars'],
                    'inventory': inventory,
                    'username': result['username'] or ''
                }
            else:
                cur.execute(
                    'INSERT INTO users (user_id, stars, inventory, username) VALUES (%s, %s, %s, %s)',
                    (user_id, 15, json.dumps({}), '')
                )
                conn.commit()
                return {'stars': 15, 'inventory': {}, 'username': ''}
    except Exception as e:
        logger.error(f"❌ Ошибка в get_user: {e}")
        return {'stars': 15, 'inventory': {}, 'username': ''}

def update_user(user_id: int, stars: int, inventory: Dict[str, Any]) -> bool:
    """Обновление данных пользователя с транзакцией"""
    try:
        with db.get_connection() as conn:
            cur = conn.cursor()
            cur.execute(
                'UPDATE users SET stars = %s, inventory = %s WHERE user_id = %s',
                (stars, json.dumps(inventory), user_id)
            )
            conn.commit()
            cur.close()
            return True
    except Exception as e:
        logger.error(f"❌ Ошибка в update_user: {e}")
        return False

def update_username(user_id: int, username: str) -> bool:
    try:
        with db.get_connection() as conn:
            cur = conn.cursor()
            cur.execute('UPDATE users SET username = %s WHERE user_id = %s', (username, user_id))
            conn.commit()
            cur.close()
            return True
    except Exception as e:
        logger.error(f"❌ Ошибка в update_username: {e}")
        return False

def get_all_users() -> List[int]:
    try:
        with db.get_connection() as conn:
            cur = conn.cursor()
            cur.execute('SELECT user_id FROM users')
            users = cur.fetchall()
            cur.close()
            return [user[0] for user in users]
    except Exception as e:
        logger.error(f"❌ Ошибка в get_all_users: {e}")
        return []

def get_all_users_data() -> List[Tuple[int, int, str]]:
    try:
        with db.get_connection() as conn:
            cur = conn.cursor()
            cur.execute('''
                SELECT user_id, stars, username 
                FROM users 
                ORDER BY stars DESC 
                LIMIT 50
            ''')
            users = cur.fetchall()
            cur.close()
            
            formatted_users = []
            for user_id, stars, username in users:
                if not username or username == '':
                    try:
                        chat = bot.get_chat(user_id)
                        if chat.username:
                            username = chat.username
                            update_username(user_id, username)
                        else:
                            username = f"ID:{user_id}"
                    except:
                        username = f"ID:{user_id}"
                
                formatted_users.append((user_id, stars, username))
            
            return formatted_users
    except Exception as e:
        logger.error(f"❌ Ошибка в get_all_users_data: {e}")
        return []

# ================= ФУНКЦИИ РАБОТЫ С КЕЙСАМИ =================
def is_case_enabled(case_id: str) -> bool:
    try:
        with db.get_connection() as conn:
            cur = conn.cursor()
            cur.execute('SELECT enabled FROM cases WHERE case_id = %s', (case_id,))
            result = cur.fetchone()
            cur.close()
            return result and result[0] == 1
    except Exception as e:
        logger.error(f"❌ Ошибка в is_case_enabled: {e}")
        return False

def get_case_price(case_id: str) -> int:
    try:
        with db.get_connection() as conn:
            cur = conn.cursor()
            cur.execute('SELECT price FROM cases WHERE case_id = %s', (case_id,))
            result = cur.fetchone()
            cur.close()
            return result[0] if result else 0
    except Exception as e:
        logger.error(f"❌ Ошибка в get_case_price: {e}")
        return 0

def get_case_name(case_id: str) -> Tuple[str, str]:
    try:
        with db.get_connection() as conn:
            cur = conn.cursor()
            cur.execute('SELECT name, emoji FROM cases WHERE case_id = %s', (case_id,))
            result = cur.fetchone()
            cur.close()
            return (result[0], result[1]) if result else (case_id, '🎁')
    except Exception as e:
        logger.error(f"❌ Ошибка в get_case_name: {e}")
        return (case_id, '🎁')

def toggle_case(case_id: str) -> Optional[int]:
    try:
        with db.get_connection() as conn:
            cur = conn.cursor()
            cur.execute('SELECT enabled FROM cases WHERE case_id = %s', (case_id,))
            result = cur.fetchone()
            if result:
                new_status = 0 if result[0] == 1 else 1
                cur.execute('UPDATE cases SET enabled = %s WHERE case_id = %s', (new_status, case_id))
                conn.commit()
                cur.close()
                return new_status
            cur.close()
            return None
    except Exception as e:
        logger.error(f"❌ Ошибка в toggle_case: {e}")
        return None

def get_item_price(item_id: str, case_type: Optional[str] = None) -> int:
    """Получение цены предмета с обработкой всех форматов"""
    try:
        # Если item_id содержит подчеркивание (например premium_5)
        if '_' in item_id:
            parts = item_id.split('_')
            if len(parts) == 2:
                case_type = parts[0]
                item_num = parts[1]
                
                if case_type in PRICES and item_num in PRICES[case_type]:
                    return PRICES[case_type][item_num]
        
        # Если передан тип
        if case_type and case_type in PRICES:
            if item_id in PRICES[case_type]:
                return PRICES[case_type][item_id]
        
        # Пробуем найти по всем типам
        for ct, prices in PRICES.items():
            if item_id in prices:
                return prices[item_id]
            if f"{ct}_{item_id}" in prices:
                return prices[f"{ct}_{item_id}"]
        
        return 1
    except Exception as e:
        logger.error(f"❌ Ошибка в get_item_price: {e}")
        return 1

def open_case(case_type: str) -> Tuple[str, str]:
    """Открытие кейса с проверкой шансов"""
    try:
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
    except Exception as e:
        logger.error(f"❌ Ошибка в open_case: {e}")
        return '1', 'Ошибка'

# ================= ФУНКЦИИ РАБОТЫ С ПРОМОКОДАМИ =================
def validate_item_id(item_id: str) -> Optional[str]:
    """Проверка существования предмета в формате: case_type_number"""
    if not item_id or '_' not in item_id:
        return None
    
    parts = item_id.split('_')
    if len(parts) != 2:
        return None
    
    case_type, item_num = parts
    
    if case_type not in ITEMS:
        return None
    
    if item_num not in ITEMS[case_type]:
        return None
    
    return case_type

def parse_item_id(item_id: str) -> Tuple[Optional[str], Optional[str]]:
    """Парсит строку вида premium_5 и возвращает (case_type, item_num)"""
    if not item_id or '_' not in item_id:
        return None, None
    
    parts = item_id.split('_')
    if len(parts) != 2:
        return None, None
    
    return parts[0], parts[1]

def create_promocode(code: str, type: str, item_id: Optional[str] = None, 
                     stars: int = 0, uses: int = 1) -> Tuple[bool, str]:
    try:
        with db.get_connection() as conn:
            cur = conn.cursor()
            
            if type == 'item' and item_id:
                case_type = validate_item_id(item_id)
                if not case_type:
                    return False, "❌ Предмет не найден. Используйте формат: case_type_number (например: premium_5, free_3)"
            
            cur.execute('''
                INSERT INTO promocodes (code, type, item_id, stars, uses) 
                VALUES (%s, %s, %s, %s, %s)
            ''', (code, type, item_id, stars, uses))
            conn.commit()
            cur.close()
            
            if type == 'stars':
                return True, f"✅ Промокод создан!\n🔑 Код: `{code}`\n⭐ Звезды: {stars:,}\n👥 Использований: {uses}"
            else:
                case_type, item_num = parse_item_id(item_id)
                if case_type and item_num in ITEMS[case_type]:
                    item_name = ITEMS[case_type][item_num]
                    return True, f"✅ Промокод создан!\n🔑 Код: `{code}`\n🎁 Предмет: {item_name}\n👥 Использований: {uses}"
                else:
                    return True, f"✅ Промокод создан!\n🔑 Код: `{code}`\n🎁 ID: {item_id}\n👥 Использований: {uses}"
    except psycopg2.IntegrityError:
        return False, "❌ Промокод с таким названием уже существует"
    except Exception as e:
        logger.error(f"❌ Ошибка в create_promocode: {e}")
        return False, f"❌ Ошибка: {str(e)}"

def delete_promocode(code: str) -> bool:
    try:
        with db.get_connection() as conn:
            cur = conn.cursor()
            cur.execute('DELETE FROM promocodes WHERE code = %s', (code,))
            conn.commit()
            cur.close()
            return True
    except Exception as e:
        logger.error(f"❌ Ошибка в delete_promocode: {e}")
        return False

def get_all_promocodes() -> List[Tuple[str, str, str, int, int]]:
    try:
        with db.get_connection() as conn:
            cur = conn.cursor()
            cur.execute('SELECT code, type, item_id, stars, uses FROM promocodes')
            codes = cur.fetchall()
            cur.close()
            return codes
    except Exception as e:
        logger.error(f"❌ Ошибка в get_all_promocodes: {e}")
        return []

def use_promocode(code: str, user_id: int) -> Tuple[Optional[str], str]:
    try:
        with db.get_connection() as conn:
            cur = conn.cursor()
            cur.execute('SELECT type, item_id, stars, uses, used_by FROM promocodes WHERE code = %s', (code,))
            result = cur.fetchone()
            
            if not result:
                return None, "❌ Промокод не найден"
            
            type, item_id, stars, uses, used_by_json = result
            used_by = json.loads(used_by_json) if used_by_json else []
            user_str = str(user_id)
            
            if user_str in used_by:
                return None, "❌ Вы уже использовали этот промокод"
            
            if len(used_by) >= uses:
                cur.execute('DELETE FROM promocodes WHERE code = %s', (code,))
                conn.commit()
                return None, "❌ Промокод уже использован максимальное количество раз"
            
            user_data = get_user(user_id)
            
            if type == 'stars':
                user_data['stars'] += stars
                update_user(user_id, user_data['stars'], user_data['inventory'])
                used_by.append(user_str)
                
                cur.execute('UPDATE promocodes SET used_by = %s WHERE code = %s', (json.dumps(used_by), code))
                conn.commit()
                
                if len(used_by) >= uses:
                    cur.execute('DELETE FROM promocodes WHERE code = %s', (code,))
                    conn.commit()
                
                cur.close()
                return 'stars', f"⭐ Вы получили {stars:,} звезд!"
            
            elif type == 'item':
                case_type = validate_item_id(item_id)
                if not case_type:
                    return None, f"❌ Предмет {item_id} не найден"
                
                _, item_num = parse_item_id(item_id)
                if not item_num or item_num not in ITEMS[case_type]:
                    return None, f"❌ Предмет {item_id} не найден"
                
                item_name = ITEMS[case_type][item_num]
                inventory = user_data['inventory']
                
                if item_id in inventory:
                    inventory[item_id]['count'] += 1
                    inventory[item_id]['type'] = case_type
                else:
                    inventory[item_id] = {
                        'name': item_name,
                        'count': 1,
                        'type': case_type
                    }
                
                update_user(user_id, user_data['stars'], inventory)
                used_by.append(user_str)
                
                cur.execute('UPDATE promocodes SET used_by = %s WHERE code = %s', (json.dumps(used_by), code))
                conn.commit()
                
                if len(used_by) >= uses:
                    cur.execute('DELETE FROM promocodes WHERE code = %s', (code,))
                    conn.commit()
                
                cur.close()
                return 'item', f"🎁 Вы получили предмет: {item_name}"
            
            cur.close()
            return None, "❌ Неизвестный тип промокода"
    except Exception as e:
        logger.error(f"❌ Ошибка в use_promocode: {e}")
        return None, f"❌ Ошибка: {str(e)}"

# ================= ФУНКЦИЯ ПРОДАЖИ =================
def sell_item(user_id: int, item_id: str) -> Tuple[bool, str]:
    """Продажа предмета с транзакцией"""
    try:
        user_data = get_user(user_id)
        inventory = user_data['inventory']
        
        if item_id not in inventory:
            return False, "❌ Предмет не найден в инвентаре"
        
        item = inventory[item_id]
        price = get_item_price(item_id, item.get('type', ''))
        
        if price <= 0:
            return False, "❌ Этот предмет нельзя продать"
        
        # Уменьшаем количество
        item['count'] -= 1
        if item['count'] <= 0:
            del inventory[item_id]
        
        # Добавляем звезды
        user_data['stars'] += price
        update_user(user_id, user_data['stars'], inventory)
        
        return True, f"✅ Продано за {price:,} ⭐!"
    except Exception as e:
        logger.error(f"❌ Ошибка в sell_item: {e}")
        return False, f"❌ Ошибка: {str(e)}"

# ================= АНИМАЦИЯ =================
def animate_case(call: types.CallbackQuery, case_type: str):
    try:
        message = call.message
        case_name, emoji = get_case_name(case_type)
        
        animation_frames = [
            ['🎰', '🎲', '✨', '⭐'],
            ['✨', '🎰', '🎲', '💫'],
            ['🎲', '✨', '🎰', '🌟'],
            ['⭐', '💫', '🌟', '✨'],
            ['💫', '🌟', '⭐', '🎰'],
            ['🌟', '⭐', '💫', '🎲']
        ]
        
        anim_msg = bot.send_message(
            message.chat.id,
            f"{emoji} **Открываем {case_name}...**\n\n"
            f"🌀 Подготовка..."
        )
        
        for frame in animation_frames:
            time.sleep(0.25)
            try:
                bot.edit_message_text(
                    chat_id=message.chat.id,
                    message_id=anim_msg.message_id,
                    text=f"{emoji} **Открываем {case_name}...**\n\n"
                         f"{' '.join(frame)}",
                    parse_mode='Markdown'
                )
            except:
                pass
        
        # Открываем кейс
        item_id, item_name = open_case(case_type)
        
        # Получаем данные пользователя
        user_data = get_user(message.chat.id)
        inventory = user_data['inventory']
        
        # Сохраняем предмет с полным ID
        full_item_id = f"{case_type}_{item_id}"
        if full_item_id in inventory:
            inventory[full_item_id]['count'] += 1
            inventory[full_item_id]['type'] = case_type
        else:
            inventory[full_item_id] = {
                'name': item_name,
                'count': 1,
                'type': case_type
            }
        
        # Сохраняем изменения
        update_user(message.chat.id, user_data['stars'], inventory)
        
        # Получаем цену
        price = get_item_price(item_id, case_type)
        
        # Определяем редкость
        if price >= 1000000:
            rarity = "🔥🔥🔥 **ЛЕГЕНДАРНО!** 🔥🔥🔥"
        elif price >= 50000:
            rarity = "✨✨ **ЭПИЧЕСКИЙ ВЫПАД!** ✨✨"
        elif price >= 10000:
            rarity = "🌟 **РЕДКИЙ ПРЕДМЕТ!** 🌟"
        elif price >= 1000:
            rarity = "⭐ **НЕПЛОХОЙ ПРЕДМЕТ!** ⭐"
        else:
            rarity = "📦 Обычный предмет"
        
        final_text = f"{rarity}\n\n"
        final_text += f"🎉 Вам выпало: **{item_name}**\n"
        final_text += f"💰 Цена продажи: **{price:,}** ⭐\n"
        final_text += f"\n💡 Предмет добавлен в инвентарь!"
        
        try:
            bot.edit_message_text(
                chat_id=message.chat.id,
                message_id=anim_msg.message_id,
                text=final_text,
                parse_mode='Markdown'
            )
        except:
            bot.send_message(message.chat.id, final_text, parse_mode='Markdown')
        
        time.sleep(0.5)
        show_main_menu(message.chat.id)
    except Exception as e:
        logger.error(f"❌ Ошибка в animate_case: {e}")
        try:
            bot.send_message(call.message.chat.id, f"❌ Ошибка при открытии кейса: {str(e)}")
        except:
            pass

# ================= КЛАВИАТУРЫ =================
def main_menu_keyboard(user_id: int) -> types.InlineKeyboardMarkup:
    keyboard = types.InlineKeyboardMarkup(row_width=2)
    
    case_list = [
        ('free', '🗑️ Кейс Бомжа (Бесплатно)'),
        ('premium', '💎 Премиум Кейс (100 ⭐)'),
        ('mythical', '💜 Мифический Кейс (1 000 ⭐)'),
        ('legendary', '⚡ Легендарный Кейс (500 ⭐)'),
        ('elite', '❤️ Элитный Кейс (5 000 ⭐)'),
        ('cosmic', '🌌 Космический Кейс (10 000 ⭐)')
    ]
    
    try:
        with db.get_connection() as conn:
            cur = conn.cursor()
            cur.execute('SELECT case_id, name, price, emoji FROM cases WHERE enabled = 1 AND is_temporary = 1')
            temp_cases = cur.fetchall()
            cur.close()
            
            for case in temp_cases:
                price_text = f"{case[2]:,} ⭐".replace(',', ' ')
                case_list.append((case[0], f"{case[3]} {case[1]} ({price_text})"))
    except Exception as e:
        logger.error(f"❌ Ошибка в main_menu_keyboard: {e}")
    
    case_list.append(('pepe', '🐸 PePe праздник🔥 (100 000 ⭐)'))
    
    for case_id, label in case_list:
        if is_case_enabled(case_id):
            btn = types.InlineKeyboardButton(label, callback_data=f"case_{case_id}")
            keyboard.add(btn)
    
    btn_profile = types.InlineKeyboardButton("👤 Мой профиль", callback_data="profile")
    btn_sell = types.InlineKeyboardButton("💰 Продать предметы", callback_data="sell")
    btn_leaderboard = types.InlineKeyboardButton("🏆 Лидеры", callback_data="leaderboard")
    btn_promocode = types.InlineKeyboardButton("🎫 Промокод", callback_data="promocode")
    
    keyboard.add(btn_profile, btn_sell)
    keyboard.add(btn_leaderboard, btn_promocode)
    
    return keyboard

def show_main_menu(chat_id: int):
    try:
        user = get_user(chat_id)
        total_items = sum(item['count'] for item in user['inventory'].values())
        
        text = f"""🏠 **Главное меню**

⭐ **Баланс:** {user['stars']:,} звезд
📦 **Предметов:** {total_items}

💡 Выберите действие:"""
        
        bot.send_message(
            chat_id,
            text,
            reply_markup=main_menu_keyboard(chat_id),
            parse_mode='Markdown'
        )
    except Exception as e:
        logger.error(f"❌ Ошибка в show_main_menu: {e}")

def sell_keyboard(user_id: int) -> types.InlineKeyboardMarkup:
    try:
        user = get_user(user_id)
        inventory = user['inventory']
        keyboard = types.InlineKeyboardMarkup(row_width=2)
        
        if not inventory:
            keyboard.add(types.InlineKeyboardButton("🔙 Назад", callback_data="back"))
            return keyboard
        
        # Сортируем предметы по цене
        sorted_items = sorted(
            inventory.items(),
            key=lambda x: get_item_price(x[0], x[1].get('type', '')),
            reverse=True
        )
        
        for item_id, data in sorted_items:
            price = get_item_price(item_id, data.get('type', ''))
            
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
    except Exception as e:
        logger.error(f"❌ Ошибка в sell_keyboard: {e}")
        keyboard = types.InlineKeyboardMarkup()
        keyboard.add(types.InlineKeyboardButton("🔙 Назад", callback_data="back"))
        return keyboard

def admin_menu_keyboard() -> types.InlineKeyboardMarkup:
    keyboard = types.InlineKeyboardMarkup(row_width=1)
    keyboard.add(
        types.InlineKeyboardButton("📊 Промокоды", callback_data="admin_promocodes"),
        types.InlineKeyboardButton("➕ Создать промокод", callback_data="admin_create_promo"),
        types.InlineKeyboardButton("📢 Рассылка", callback_data="admin_broadcast"),
        types.InlineKeyboardButton("🎮 Управление кейсами", callback_data="admin_cases"),
        types.InlineKeyboardButton("🔙 Назад", callback_data="back")
    )
    return keyboard

def admin_cases_keyboard() -> types.InlineKeyboardMarkup:
    keyboard = types.InlineKeyboardMarkup(row_width=1)
    try:
        with db.get_connection() as conn:
            cur = conn.cursor()
            cur.execute('SELECT case_id, name, enabled, emoji, is_temporary, price FROM cases ORDER BY price')
            cases = cur.fetchall()
            cur.close()
            
            for case_id, name, enabled, emoji, is_temporary, price in cases:
                status = "✅ Включен" if enabled == 1 else "❌ Выключен"
                temp_tag = " 🕐" if is_temporary == 1 else ""
                price_text = f"{price:,} ⭐" if price > 0 else "Бесплатно"
                btn = types.InlineKeyboardButton(
                    f"{emoji} {name}{temp_tag} - {status} ({price_text})",
                    callback_data=f"admin_toggle_case_{case_id}"
                )
                keyboard.add(btn)
    except Exception as e:
        logger.error(f"❌ Ошибка в admin_cases_keyboard: {e}")
    
    keyboard.add(types.InlineKeyboardButton("🔙 Назад в админку", callback_data="admin_back"))
    return keyboard

# ================= ОБРАБОТЧИКИ КОМАНД =================
@bot.message_handler(commands=['start'])
def start(message: types.Message):
    try:
        user_id = message.chat.id
        logger.info(f"✅ /start от {user_id}")
        
        if message.from_user.username:
            update_username(user_id, message.from_user.username)
        
        get_user(user_id)
        
        welcome_text = """👋 **Добро пожаловать в Игровой Бот!**

🎁 Тебе выдано **15** ⭐ звезд.
💰 Открывай кейсы, собирай предметы и продавай их!

**Доступные кейсы:**
🗑️ **Кейс Бомжа** - бесплатный
💎 **Премиум Кейс** - 100 ⭐
💜 **Мифический Кейс** - 1 000 ⭐
⚡ **Легендарный Кейс** - 500 ⭐
❤️ **Элитный Кейс** - 5 000 ⭐
🌌 **Космический Кейс** - 10 000 ⭐
🎃 **Хеллоуинский Кейс** - 2 500 ⭐
🎄 **Новогодний Кейс** - 5 000 ⭐
🐸 **PePe праздник🔥** - 100 000 ⭐

🎯 **Цель:** Собрать легендарного Пепе и стать самым богатым!
"""
        
        bot.send_message(user_id, welcome_text, parse_mode='Markdown')
        show_main_menu(user_id)
    except Exception as e:
        logger.error(f"❌ Ошибка в start: {e}")

@bot.message_handler(commands=['admin'])
def admin_panel(message: types.Message):
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
        logger.error(f"❌ Ошибка в admin_panel: {e}")

# ================= ОБРАБОТЧИКИ CALLBACK =================
@bot.callback_query_handler(func=lambda call: call.data.startswith("case_"))
def handle_case(call: types.CallbackQuery):
    try:
        user_id = call.message.chat.id
        user_data = get_user(user_id)
        case_id = call.data.replace("case_", "")
        
        if not is_case_enabled(case_id):
            bot.answer_callback_query(call.id, "❌ Этот кейс временно отключен!", show_alert=True)
            return
        
        price = get_case_price(case_id)
        
        if price > 0:
            if user_data['stars'] >= price:
                user_data['stars'] -= price
                update_user(user_id, user_data['stars'], user_data['inventory'])
                try:
                    bot.delete_message(user_id, call.message.message_id)
                except:
                    pass
                threading.Thread(target=animate_case, args=(call, case_id), daemon=True).start()
            else:
                bot.answer_callback_query(
                    call.id, 
                    f"❌ Недостаточно звезд! Нужно: {price:,} ⭐".replace(',', ' '), 
                    show_alert=True
                )
        else:
            try:
                bot.delete_message(user_id, call.message.message_id)
            except:
                pass
            threading.Thread(target=animate_case, args=(call, case_id), daemon=True).start()
    except Exception as e:
        logger.error(f"❌ Ошибка в handle_case: {e}")
        try:
            bot.answer_callback_query(call.id, f"❌ Ошибка: {str(e)}", show_alert=True)
        except:
            pass

@bot.callback_query_handler(func=lambda call: call.data == "profile")
def handle_profile(call: types.CallbackQuery):
    try:
        user_id = call.message.chat.id
        user_data = get_user(user_id)
        
        try:
            if call.message.from_user.username:
                update_username(user_id, call.message.from_user.username)
        except:
            pass
        
        inv_text = ""
        total_items = 0
        total_value = 0
        
        if user_data['inventory']:
            for item_id, data in user_data['inventory'].items():
                price = get_item_price(item_id, data.get('type', ''))
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
        
        user_full = get_user(user_id)
        display_name = user_full['username'] or f"ID:{user_id}"
        
        text = f"""👤 **Профиль игрока**

👤 **Имя:** {display_name}
⭐ **Звезды:** {user_data['stars']:,}
📦 **Предметов:** {total_items}
💰 **Общая стоимость:** {total_value:,} ⭐

**📦 Инвентарь:**
{inv_text}"""
        
        try:
            bot.edit_message_text(
                chat_id=user_id,
                message_id=call.message.message_id,
                text=text,
                parse_mode='Markdown',
                reply_markup=types.InlineKeyboardMarkup().add(
                    types.InlineKeyboardButton("🔄 Обновить", callback_data="profile"),
                    types.InlineKeyboardButton("🔙 Назад", callback_data="back")
                )
            )
        except:
            bot.send_message(
                user_id,
                text,
                parse_mode='Markdown',
                reply_markup=types.InlineKeyboardMarkup().add(
                    types.InlineKeyboardButton("🔄 Обновить", callback_data="profile"),
                    types.InlineKeyboardButton("🔙 Назад", callback_data="back")
                )
            )
    except Exception as e:
        logger.error(f"❌ Ошибка в handle_profile: {e}")

@bot.callback_query_handler(func=lambda call: call.data == "sell")
def handle_sell_menu(call: types.CallbackQuery):
    try:
        user_id = call.message.chat.id
        keyboard = sell_keyboard(user_id)
        try:
            bot.edit_message_text(
                chat_id=user_id,
                message_id=call.message.message_id,
                text="💰 **Выберите предмет для продажи:**",
                parse_mode='Markdown',
                reply_markup=keyboard
            )
        except:
            bot.send_message(
                user_id,
                "💰 **Выберите предмет для продажи:**",
                parse_mode='Markdown',
                reply_markup=keyboard
            )
    except Exception as e:
        logger.error(f"❌ Ошибка в handle_sell_menu: {e}")

@bot.callback_query_handler(func=lambda call: call.data.startswith("sell_"))
def handle_sell_item(call: types.CallbackQuery):
    try:
        user_id = call.message.chat.id
        # Получаем полный ID предмета (например premium_5)
        item_id = call.data.replace("sell_", "")
        user_data = get_user(user_id)
        
        # Проверяем наличие предмета в инвентаре
        if item_id not in user_data['inventory']:
            bot.answer_callback_query(call.id, "❌ Предмет не найден в инвентаре!", show_alert=True)
            return
        
        item = user_data['inventory'][item_id]
        price = get_item_price(item_id, item.get('type', ''))
        
        # Если предмет очень дорогой - запрашиваем подтверждение
        if price >= 1000000:
            confirm = types.InlineKeyboardMarkup()
            confirm.add(
                types.InlineKeyboardButton("✅ Да, продать", callback_data=f"confirm_sell_{item_id}"),
                types.InlineKeyboardButton("❌ Нет", callback_data="sell")
            )
            try:
                bot.edit_message_text(
                    chat_id=user_id,
                    message_id=call.message.message_id,
                    text=f"⚠️ **Вы уверены?**\nВы хотите продать **{item['name']}** за {price:,} ⭐\n\nЭто очень ценный предмет!",
                    parse_mode='Markdown',
                    reply_markup=confirm
                )
            except:
                bot.send_message(
                    user_id,
                    f"⚠️ **Вы уверены?**\nВы хотите продать **{item['name']}** за {price:,} ⭐\n\nЭто очень ценный предмет!",
                    parse_mode='Markdown',
                    reply_markup=confirm
                )
            return
        
        # Обычная продажа
        success, msg = sell_item(user_id, item_id)
        bot.answer_callback_query(call.id, msg, show_alert=False)
        
        if success:
            # Обновляем меню продажи
            keyboard = sell_keyboard(user_id)
            try:
                bot.edit_message_text(
                    chat_id=user_id,
                    message_id=call.message.message_id,
                    text="💰 **Выберите предмет для продажи:**",
                    parse_mode='Markdown',
                    reply_markup=keyboard
                )
            except:
                bot.send_message(
                    user_id,
                    "💰 **Выберите предмет для продажи:**",
                    parse_mode='Markdown',
                    reply_markup=keyboard
                )
    except Exception as e:
        logger.error(f"❌ Ошибка в handle_sell_item: {e}")
        try:
            bot.answer_callback_query(call.id, f"❌ Ошибка: {str(e)}", show_alert=True)
        except:
            pass

@bot.callback_query_handler(func=lambda call: call.data.startswith("confirm_sell_"))
def handle_confirm_sell(call: types.CallbackQuery):
    try:
        user_id = call.message.chat.id
        item_id = call.data.replace("confirm_sell_", "")
        
        success, msg = sell_item(user_id, item_id)
        bot.answer_callback_query(call.id, msg, show_alert=False)
        
        if success:
            keyboard = sell_keyboard(user_id)
            try:
                bot.edit_message_text(
                    chat_id=user_id,
                    message_id=call.message.message_id,
                    text="💰 **Выберите предмет для продажи:**",
                    parse_mode='Markdown',
                    reply_markup=keyboard
                )
            except:
                bot.send_message(
                    user_id,
                    "💰 **Выберите предмет для продажи:**",
                    parse_mode='Markdown',
                    reply_markup=keyboard
                )
    except Exception as e:
        logger.error(f"❌ Ошибка в handle_confirm_sell: {e}")
        try:
            bot.answer_callback_query(call.id, f"❌ Ошибка: {str(e)}", show_alert=True)
        except:
            pass

@bot.callback_query_handler(func=lambda call: call.data == "leaderboard")
def handle_leaderboard(call: types.CallbackQuery):
    try:
        user_id = call.message.chat.id
        users = get_all_users_data()
        text = "🏆 **Топ игроков по звездам:**\n\n"
        if users:
            for i, (user_id, stars, display_name) in enumerate(users[:10], 1):
                medal = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else f"{i}."
                stars_formatted = f"{stars:,}".replace(',', ' ')
                text += f"{medal} {display_name} - {stars_formatted} ⭐\n"
        else:
            text += "❌ Нет игроков в таблице лидеров"
        
        text += f"\n🔄 Обновлено: {datetime.now().strftime('%H:%M:%S')}"
        
        try:
            bot.edit_message_text(
                chat_id=user_id,
                message_id=call.message.message_id,
                text=text,
                parse_mode='Markdown',
                reply_markup=types.InlineKeyboardMarkup().add(
                    types.InlineKeyboardButton("🔄 Обновить", callback_data="leaderboard"),
                    types.InlineKeyboardButton("🔙 Назад", callback_data="back")
                )
            )
        except:
            bot.send_message(
                user_id,
                text,
                parse_mode='Markdown',
                reply_markup=types.InlineKeyboardMarkup().add(
                    types.InlineKeyboardButton("🔄 Обновить", callback_data="leaderboard"),
                    types.InlineKeyboardButton("🔙 Назад", callback_data="back")
                )
            )
    except Exception as e:
        logger.error(f"❌ Ошибка в handle_leaderboard: {e}")

@bot.callback_query_handler(func=lambda call: call.data == "promocode")
def handle_promocode(call: types.CallbackQuery):
    try:
        user_id = call.message.chat.id
        try:
            bot.edit_message_text(
                chat_id=user_id,
                message_id=call.message.message_id,
                text="🎫 **Введите промокод:**\nНапишите его в чат.",
                parse_mode='Markdown',
                reply_markup=types.InlineKeyboardMarkup().add(
                    types.InlineKeyboardButton("🔙 Назад", callback_data="back")
                )
            )
        except:
            bot.send_message(
                user_id,
                "🎫 **Введите промокод:**\nНапишите его в чат.",
                parse_mode='Markdown',
                reply_markup=types.InlineKeyboardMarkup().add(
                    types.InlineKeyboardButton("🔙 Назад", callback_data="back")
                )
            )
        bot.register_next_step_handler(call.message, process_promocode)
    except Exception as e:
        logger.error(f"❌ Ошибка в handle_promocode: {e}")

@bot.callback_query_handler(func=lambda call: call.data == "back")
def handle_back(call: types.CallbackQuery):
    try:
        user_id = call.message.chat.id
        try:
            bot.delete_message(user_id, call.message.message_id)
        except:
            pass
        show_main_menu(user_id)
    except Exception as e:
        logger.error(f"❌ Ошибка в handle_back: {e}")

# ================= АДМИН ОБРАБОТЧИКИ CALLBACK =================
@bot.callback_query_handler(func=lambda call: call.data == "admin_back")
def handle_admin_back(call: types.CallbackQuery):
    try:
        user_id = call.message.chat.id
        try:
            bot.delete_message(user_id, call.message.message_id)
        except:
            pass
        admin_panel(call.message)
    except Exception as e:
        logger.error(f"❌ Ошибка в handle_admin_back: {e}")

@bot.callback_query_handler(func=lambda call: call.data == "admin_promocodes")
def handle_admin_promocodes(call: types.CallbackQuery):
    try:
        user_id = call.message.chat.id
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
        
        try:
            bot.edit_message_text(
                chat_id=user_id,
                message_id=call.message.message_id,
                text=text,
                parse_mode='Markdown',
                reply_markup=keyboard
            )
        except:
            bot.send_message(
                user_id,
                text,
                parse_mode='Markdown',
                reply_markup=keyboard
            )
    except Exception as e:
        logger.error(f"❌ Ошибка в handle_admin_promocodes: {e}")

@bot.callback_query_handler(func=lambda call: call.data == "admin_create_promo")
def handle_admin_create_promo(call: types.CallbackQuery):
    try:
        user_id = call.message.chat.id
        text = """📝 **Создание промокода**

Введите данные в формате:
`название_кода тип_награды параметр количество_использований`

**Типы:**
• `stars` - звезды (параметр: количество)
• `item` - предмет (параметр: ID предмета)

**Доступные ID предметов:**
`free_1-5`, `premium_1-5`, `legendary_1-5`,
`halloween_1-5`, `newyear_1-5`, `mythical_1-5`,
`elite_1-5`, `cosmic_1-5`, `pepe_1-5`

**Примеры:**
`WELCOME stars 50 10` - 50 звезд, 10 использований
`GIFT item premium_5 5` - Мега-подарок, 5 использований"""
        
        try:
            bot.edit_message_text(
                chat_id=user_id,
                message_id=call.message.message_id,
                text=text,
                parse_mode='Markdown',
                reply_markup=types.InlineKeyboardMarkup().add(
                    types.InlineKeyboardButton("🔙 Назад", callback_data="admin_promocodes")
                )
            )
        except:
            bot.send_message(
                user_id,
                text,
                parse_mode='Markdown',
                reply_markup=types.InlineKeyboardMarkup().add(
                    types.InlineKeyboardButton("🔙 Назад", callback_data="admin_promocodes")
                )
            )
        bot.register_next_step_handler(call.message, process_create_promo)
    except Exception as e:
        logger.error(f"❌ Ошибка в handle_admin_create_promo: {e}")

@bot.callback_query_handler(func=lambda call: call.data.startswith("admin_delete_promo_"))
def handle_admin_delete_promo(call: types.CallbackQuery):
    try:
        user_id = call.message.chat.id
        code = call.data.replace("admin_delete_promo_", "")
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
        
        try:
            bot.edit_message_text(
                chat_id=user_id,
                message_id=call.message.message_id,
                text=text,
                parse_mode='Markdown',
                reply_markup=keyboard
            )
        except:
            bot.send_message(
                user_id,
                text,
                parse_mode='Markdown',
                reply_markup=keyboard
            )
    except Exception as e:
        logger.error(f"❌ Ошибка в handle_admin_delete_promo: {e}")

@bot.callback_query_handler(func=lambda call: call.data == "admin_broadcast")
def handle_admin_broadcast(call: types.CallbackQuery):
    try:
        user_id = call.message.chat.id
        try:
            bot.edit_message_text(
                chat_id=user_id,
                message_id=call.message.message_id,
                text="📢 **Рассылка**\nВведите текст для рассылки всем пользователям:",
                parse_mode='Markdown',
                reply_markup=types.InlineKeyboardMarkup().add(
                    types.InlineKeyboardButton("🔙 Назад", callback_data="admin_back")
                )
            )
        except:
            bot.send_message(
                user_id,
                "📢 **Рассылка**\nВведите текст для рассылки всем пользователям:",
                parse_mode='Markdown',
                reply_markup=types.InlineKeyboardMarkup().add(
                    types.InlineKeyboardButton("🔙 Назад", callback_data="admin_back")
                )
            )
        bot.register_next_step_handler(call.message, process_broadcast)
    except Exception as e:
        logger.error(f"❌ Ошибка в handle_admin_broadcast: {e}")

@bot.callback_query_handler(func=lambda call: call.data == "admin_cases")
def handle_admin_cases(call: types.CallbackQuery):
    try:
        user_id = call.message.chat.id
        keyboard = admin_cases_keyboard()
        try:
            bot.edit_message_text(
                chat_id=user_id,
                message_id=call.message.message_id,
                text="🎮 **Управление кейсами**\nНажмите на кейс, чтобы включить/выключить:",
                parse_mode='Markdown',
                reply_markup=keyboard
            )
        except:
            bot.send_message(
                user_id,
                "🎮 **Управление кейсами**\nНажмите на кейс, чтобы включить/выключить:",
                parse_mode='Markdown',
                reply_markup=keyboard
            )
    except Exception as e:
        logger.error(f"❌ Ошибка в handle_admin_cases: {e}")

@bot.callback_query_handler(func=lambda call: call.data.startswith("admin_toggle_case_"))
def handle_admin_toggle_case(call: types.CallbackQuery):
    try:
        user_id = call.message.chat.id
        case_id = call.data.replace("admin_toggle_case_", "")
        new_status = toggle_case(case_id)
        
        if new_status is not None:
            status_text = "включен" if new_status == 1 else "выключен"
            bot.answer_callback_query(call.id, f"✅ Кейс {status_text}!", show_alert=False)
            
            keyboard = admin_cases_keyboard()
            try:
                bot.edit_message_text(
                    chat_id=user_id,
                    message_id=call.message.message_id,
                    text="🎮 **Управление кейсами**\nНажмите на кейс, чтобы включить/выключить:",
                    parse_mode='Markdown',
                    reply_markup=keyboard
                )
            except:
                bot.send_message(
                    user_id,
                    "🎮 **Управление кейсами**\nНажмите на кейс, чтобы включить/выключить:",
                    parse_mode='Markdown',
                    reply_markup=keyboard
                )
        else:
            bot.answer_callback_query(call.id, "❌ Ошибка при переключении кейса!", show_alert=True)
    except Exception as e:
        logger.error(f"❌ Ошибка в handle_admin_toggle_case: {e}")

# ================= ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ =================
def process_promocode(message: types.Message):
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
        logger.error(f"❌ Ошибка в process_promocode: {e}")
        bot.send_message(message.chat.id, f"❌ Ошибка: {str(e)}")
        show_main_menu(message.chat.id)

def process_create_promo(message: types.Message):
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
            success, msg = create_promocode(code, type, None, stars, uses)
            bot.send_message(user_id, msg)
        elif type == 'item':
            success, msg = create_promocode(code, type, param, 0, uses)
            bot.send_message(user_id, msg)
        else:
            bot.send_message(user_id, "❌ Неизвестный тип! Используйте `stars` или `item`")
    except ValueError:
        bot.send_message(user_id, "❌ Неверный формат! Количество использования должно быть числом")
    except Exception as e:
        bot.send_message(user_id, f"❌ Ошибка: {str(e)}")
    
    admin_panel(message)

def process_broadcast(message: types.Message):
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
        logger.info("🤖 Бот запускается...")
        init_db()
        logger.info("✅ База данных PostgreSQL готова")
        logger.info(f"👑 Админ ID: {ADMIN_ID}")
        logger.info("🚀 Бот готов к работе!")
        bot.infinity_polling()
    except KeyboardInterrupt:
        logger.info("👋 Бот остановлен пользователем")
        db.close_all_connections()
        sys.exit(0)
    except Exception as e:
        logger.error(f"❌ Критическая ошибка: {e}")
        db.close_all_connections()
        sys.exit(1)
