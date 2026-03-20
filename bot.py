"""
Telegram бот для игры "Микрокапитализм: Жизнь на 1 доллар"
Основной файл с обработчиками команд и меню
"""

import logging
from aiogram import Bot, Dispatcher, Router, F
from aiogram.filters import Command, CommandStart
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, Update
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
from aiogram.client.session.aiohttp import AiohttpSession
from aiohttp_socks import ProxyConnector

from config import config
from db import db
from utils import event_gen, game_logic, formatter

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ===== НАСТРОЙКА ПРОКСИ (MTProto) =====
# Ваш MTProto прокси от getsurfvpn.com
PROXY_URL: str | None = "socks5://getsurfvpn.com:443#5d450e4ea62584acb32519938893b939"

# Инициализация бота с прокси (если указан)
if PROXY_URL:
    session = AiohttpSession(proxy=PROXY_URL)
    bot = Bot(
        token=config.TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
        session=session,
    )
else:
    bot = Bot(
        token=config.TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML)
    )

dp = Dispatcher()
router = Router()


# ============== КЛАВИАТУРЫ ==============


def get_main_menu() -> InlineKeyboardMarkup:
    """Главное меню бота"""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🏠 Мой баланс", callback_data="menu_balance")],
            [InlineKeyboardButton(text="💼 Бизнес", callback_data="menu_business")],
            [InlineKeyboardButton(text="🎲 События дня", callback_data="menu_events")],
            [InlineKeyboardButton(text="⭐ VIP / Покупки", callback_data="menu_shop")],
            [
                InlineKeyboardButton(
                    text="🔝 Лидерборд", callback_data="menu_leaderboard"
                )
            ],
            [InlineKeyboardButton(text="🔁 Рефералы", callback_data="menu_referrals")],
        ]
    )


def get_business_menu() -> InlineKeyboardMarkup:
    """Меню бизнеса"""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🍋 Лимонадная ($1)", callback_data="create_lemonade"
                )
            ],
            [InlineKeyboardButton(text="🌾 Ферма ($5)", callback_data="create_farm")],
            [
                InlineKeyboardButton(
                    text="⬆️ Апгрейд бизнеса", callback_data="upgrade_select"
                )
            ],
            [
                InlineKeyboardButton(
                    text="⬆️ Мгновенный апгрейд (⭐3)",
                    callback_data="instant_upgrade_select",
                )
            ],
            [InlineKeyboardButton(text="🔙 Назад", callback_data="menu_main")],
        ]
    )


def get_shop_menu() -> InlineKeyboardMarkup:
    """Меню магазина"""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="⭐ VIP на 7 дней (⭐5)", callback_data="buy_vip"
                )
            ],
            [InlineKeyboardButton(text="🛡️ Щит (⭐2)", callback_data="buy_shield")],
            [
                InlineKeyboardButton(
                    text="🎰 Лотерея (⭐1)", callback_data="buy_lottery"
                )
            ],
            [InlineKeyboardButton(text="🔙 Назад", callback_data="menu_main")],
        ]
    )


def get_upgrade_keyboard(businesses) -> InlineKeyboardMarkup:
    """Кнопки для выбора бизнеса при апгрейде"""
    buttons = []
    for biz in businesses:
        cost = game_logic.get_upgrade_cost(biz["id"])
        text = f"{biz['name']} (Ур.{biz['level']}) - ${cost:.2f}"
        buttons.append(
            [InlineKeyboardButton(text=text, callback_data=f"upgrade_{biz['id']}")]
        )
    buttons.append(
        [InlineKeyboardButton(text="🔙 Назад", callback_data="menu_business")]
    )
    return InlineKeyboardMarkup(inline_keyboard=buttons)


# ============== ОБРАБОТЧИКИ КОМАНД ==============


@router.message(CommandStart())
async def cmd_start(message: Message):
    """Обработчик команды /start"""
    user_id = message.from_user.id
    username = message.from_user.username or message.from_user.first_name

    # Парсим реферальный ID из аргументов
    args = message.text.split()
    referral_id = None
    if len(args) > 1:
        try:
            referral_id = int(args[1])
        except ValueError:
            pass

    # Регистрируем пользователя
    db.create_user(user_id, username, referral_id)

    welcome_text = f"""
🎮 <b>Микрокапитализм: Жизнь на 1 доллар</b>

💵 Ваш стартовый капитал: $1.00

📈 Стройте бизнес, собирайте доход, 
   развивайтесь и становитесь богаче!

🎁 Приглашайте друзей и получайте бонусы!

Выберите действие:
"""

    await message.answer(welcome_text, reply_markup=get_main_menu())


@router.message(Command("menu"))
async def cmd_menu(message: Message):
    """Команда для быстрого возврата в меню"""
    await message.answer("📋 Главное меню:", reply_markup=get_main_menu())


# ============== ОБРАБОТЧИКИ МЕНЮ ==============


@router.callback_query(F.data == "menu_main")
async def menu_main(callback):
    """Главное меню"""
    await callback.message.edit_text("📋 Главное меню:", reply_markup=get_main_menu())
    await callback.answer()


@router.callback_query(F.data == "menu_balance")
async def menu_balance(callback):
    """Меню баланса"""
    user_id = callback.from_user.id
    text = formatter.format_balance(user_id)
    await callback.message.edit_text(text, reply_markup=get_main_menu())
    await callback.answer()


@router.callback_query(F.data == "menu_business")
async def menu_business(callback):
    """Меню бизнеса"""
    user_id = callback.from_user.id
    businesses = db.get_user_businesses(user_id)

    text = "💼 <b>Меню бизнеса</b>\n\n"

    if businesses:
        text += "📋 Ваши бизнесы:\n"
        for biz in businesses:
            income = db.get_business_income(biz["id"])
            text += f"• {biz['name']} (Ур.{biz['level']}) - ${income:.2f}\n"
    else:
        text += "📭 У вас пока нет бизнесов.\nСоздайте свой первый бизнес!"

    text += f"\n💰 Баланс: ${db.get_balance(user_id):.2f}"

    await callback.message.edit_text(text, reply_markup=get_business_menu())
    await callback.answer()


@router.callback_query(F.data == "menu_events")
async def menu_events(callback):
    """Меню событий дня"""
    user_id = callback.from_user.id
    today = db.get_last_event_date(user_id)

    text = f"""🎲 <b>События дня</b>

📅 Сегодня: {today or "ещё не обработано"}

"""

    # Показываем последние события
    events = db.get_user_events(user_id, 5)
    if events:
        text += "📜 Последние события:\n"
        for event in events:
            event_name = config.EVENTS.get(event["event_type"], {}).get(
                "name", event["event_type"]
            )
            effect = event["effect_value"]
            sign = "+" if effect > 0 else ""
            text += f"• {event_name} {sign}${effect:.2f}\n"
    else:
        text += "Пока нет событий."

    await callback.message.edit_text(text, reply_markup=get_main_menu())
    await callback.answer()


@router.callback_query(F.data == "menu_leaderboard")
async def menu_leaderboard(callback):
    """Лидерборд"""
    text = formatter.format_leaderboard()
    await callback.message.edit_text(text, reply_markup=get_main_menu())
    await callback.answer()


@router.callback_query(F.data == "menu_referrals")
async def menu_referrals(callback):
    """Меню рефералов"""
    user_id = callback.from_user.id
    text = formatter.format_referrals(user_id)
    await callback.message.edit_text(text, reply_markup=get_main_menu())
    await callback.answer()


@router.callback_query(F.data == "menu_shop")
async def menu_shop(callback):
    """Магазин"""
    user_id = callback.from_user.id
    balance = db.get_balance(user_id)
    is_vip = db.check_vip(user_id)

    vip_text = "⭐ VIP активен!" if is_vip else "⭐ VIP неактивен"

    text = f"""⭐ <b>Магазин</b>

{vip_text}
💰 Ваш баланс: ${balance:.2f}

🛒 Доступные покупки:
"""

    await callback.message.edit_text(text, reply_markup=get_shop_menu())
    await callback.answer()


# ============== СОЗДАНИЕ БИЗНЕСОВ ==============


@router.callback_query(F.data.in_(["create_lemonade", "create_farm"]))
async def create_business(callback):
    """Создание бизнеса"""
    user_id = callback.from_user.id

    # Определяем тип бизнеса
    if callback.data == "create_lemonade":
        biz_type = "lemonade"
        cost = config.BUSINESS_TYPES["lemonade"]["base_cost"]
    else:
        biz_type = "farm"
        cost = config.BUSINESS_TYPES["farm"]["base_cost"]

    balance = db.get_balance(user_id)

    if balance < cost:
        await callback.message.edit_text(
            f"❌ Недостаточно средств!\n💰 Нужно: ${cost:.2f}\n💵 У вас: ${balance:.2f}",
            reply_markup=get_business_menu(),
        )
        await callback.answer("❌ Недостаточно средств!", show_alert=True)
        return

    if db.create_business(user_id, biz_type):
        biz_name = config.BUSINESS_TYPES[biz_type]["name"]
        new_balance = db.get_balance(user_id)
        await callback.message.edit_text(
            f"✅ <b>Бизнес создан!</b>\n\n"
            f"🏢 {biz_name}\n"
            f"💵 Потрачено: ${cost:.2f}\n"
            f"💰 Новый баланс: ${new_balance:.2f}",
            reply_markup=get_business_menu(),
        )
        await callback.answer(f"✅ {biz_name} успешно создан!", show_alert=True)
    else:
        await callback.answer("❌ Ошибка при создании бизнеса!", show_alert=True)


# ============== АПГРЕЙД БИЗНЕСОВ ==============


@router.callback_query(F.data == "upgrade_select")
async def upgrade_select(callback):
    """Выбор бизнеса для апгрейда"""
    user_id = callback.from_user.id
    businesses = db.get_user_businesses(user_id)

    if not businesses:
        await callback.message.edit_text(
            "❌ У вас нет бизнесов для апгрейда!", reply_markup=get_business_menu()
        )
        await callback.answer("❌ Нет бизнесов!", show_alert=True)
        return

    await callback.message.edit_text(
        "⬆️ <b>Выберите бизнес для апгрейда:</b>",
        reply_markup=get_upgrade_keyboard(businesses),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("upgrade_"))
async def upgrade_business(callback):
    """Апгрейд выбранного бизнеса"""
    user_id = callback.from_user.id
    business_id = int(callback.data.split("_")[1])

    balance = db.get_balance(user_id)
    upgrade_cost = game_logic.get_upgrade_cost(business_id)

    if balance < upgrade_cost:
        await callback.answer(
            f"❌ Недостаточно средств!\n💰 Нужно: ${upgrade_cost:.2f}\n💵 У вас: ${balance:.2f}",
            show_alert=True,
        )
        return

    success, cost = db.upgrade_business(business_id)

    if success:
        biz = db.get_business(business_id)
        new_balance = db.get_balance(user_id)
        await callback.message.edit_text(
            f"✅ <b>Бизнес улучшен!</b>\n\n"
            f"🏢 {biz['name']}\n"
            f"📈 Новый уровень: {biz['level']}\n"
            f"💵 Потрачено: ${cost:.2f}\n"
            f"💰 Баланс: ${new_balance:.2f}",
            reply_markup=get_main_menu(),
        )
        await callback.answer("✅ Апгрейд успешен!", show_alert=True)
    else:
        await callback.answer("❌ Ошибка апгрейда!", show_alert=True)


# ============== МГНОВЕННЫЙ АПГРЕЙД ==============


@router.callback_query(F.data == "instant_upgrade_select")
async def instant_upgrade_select(callback):
    """Выбор бизнеса для мгновенного апгрейда (Stars)"""
    user_id = callback.from_user.id
    businesses = db.get_user_businesses(user_id)

    if not businesses:
        await callback.message.edit_text(
            "❌ У вас нет бизнесов!", reply_markup=get_business_menu()
        )
        await callback.answer("❌ Нет бизнесов!", show_alert=True)
        return

    text = f"⬆️ <b>Мгновенный апгрейд (⭐{config.INSTANT_UPGRADE_COST_STARS})</b>\n\nВыберите бизнес:"

    buttons = []
    for biz in businesses:
        text_btn = f"{biz['name']} (Ур.{biz['level']})"
        buttons.append(
            [InlineKeyboardButton(text=text_btn, callback_data=f"instant_{biz['id']}")]
        )
    buttons.append(
        [InlineKeyboardButton(text="🔙 Назад", callback_data="menu_business")]
    )

    await callback.message.edit_text(
        text, reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons)
    )
    await callback.answer()


@router.callback_query(F.data.startswith("instant_"))
async def instant_upgrade(callback):
    """Мгновенный апгрейд за Stars"""
    user_id = callback.from_user.id
    business_id = int(callback.data.split("_")[1])

    # В реальной реализации здесь должна быть проверка Stars
    # Для MVP просто используем баланс
    cost_stars = config.INSTANT_UPGRADE_COST_STARS

    # Проверяем виртуальный баланс Stars (для демо)
    # В реальном боте используйте Telegram Payments API

    if db.instant_upgrade_business(business_id):
        biz = db.get_business(business_id)
        new_balance = db.get_balance(user_id)
        await callback.message.edit_text(
            f"⚡ <b>Мгновенный апгрейд!</b>\n\n"
            f"🏢 {biz['name']}\n"
            f"📈 Новый уровень: {biz['level']}\n"
            f"⭐ Потрачено Stars: {cost_stars}\n"
            f"💰 Баланс: ${new_balance:.2f}",
            reply_markup=get_main_menu(),
        )
        await callback.answer("⚡ Апгрейд выполнен!", show_alert=True)
    else:
        await callback.answer("❌ Ошибка!", show_alert=True)


# ============== ПОКУПКИ В МАГАЗИНЕ ==============


@router.callback_query(F.data == "buy_vip")
async def buy_vip(callback):
    """Покупка VIP"""
    user_id = callback.from_user.id

    cost = config.VIP_COST_STARS

    # В реальности - оплата Stars через Telegram Payments
    # Для MVP просто активируем VIP

    if db.check_vip(user_id):
        await callback.answer("⭐ VIP уже активен!", show_alert=True)
        return

    if db.set_vip(user_id, config.VIP_DURATION_DAYS):
        await callback.message.edit_text(
            f"✅ <b>VIP активирован!</b>\n\n"
            f"⭐ Статус: VIP на {config.VIP_DURATION_DAYS} дней\n"
            f"💰 Ежедневный бонус: ${config.VIP_DAILY_BONUS}\n"
            f"🛡️ Защита от негативных событий\n"
            f"⭐ Потрачено Stars: {cost}",
            reply_markup=get_main_menu(),
        )
        await callback.answer("✅ VIP активирован!", show_alert=True)
    else:
        await callback.answer("❌ Ошибка покупки!", show_alert=True)


@router.callback_query(F.data == "buy_shield")
async def buy_shield(callback):
    """Покупка щита"""
    user_id = callback.from_user.id
    cost = config.SHIELD_COST_STARS

    balance = db.get_balance(user_id)

    if balance < cost:
        await callback.answer(
            f"❌ Недостаточно средств! Нужно ${cost}", show_alert=True
        )
        return

    db.update_balance(user_id, -cost)
    db.add_resource(user_id, "shield", 1)
    new_balance = db.get_balance(user_id)

    shields = db.get_resource(user_id, "shield")

    await callback.message.edit_text(
        f"🛡️ <b>Щит куплен!</b>\n\n"
        f"🛡️ Количество щитов: {shields}\n"
        f"💵 Потрачено: ${cost:.2f}\n"
        f"💰 Баланс: ${new_balance:.2f}",
        reply_markup=get_shop_menu(),
    )
    await callback.answer("🛡️ Щит куплен!", show_alert=True)


@router.callback_query(F.data == "buy_lottery")
async def buy_lottery(callback):
    """Покупка и участие в лотерее"""
    user_id = callback.from_user.id
    cost = config.LOTTERY_COST_STARS

    balance = db.get_balance(user_id)

    if balance < cost:
        await callback.message.edit_text(
            f"❌ Недостаточно средств!\n💵 Нужно: ${cost}\n💰 У вас: ${balance:.2f}",
            reply_markup=get_shop_menu(),
        )
        await callback.answer("❌ Недостаточно средств!", show_alert=True)
        return

    result = game_logic.play_lottery(user_id)

    new_balance = db.get_balance(user_id)

    await callback.message.edit_text(
        f"🎰 <b>ЛОТЕРЕЯ</b>\n\n"
        f"{result['message']}\n\n"
        f"💵 Потрачено: ${cost}\n"
        f"💰 Баланс: ${new_balance:.2f}",
        reply_markup=get_shop_menu(),
    )
    await callback.answer(result["message"], show_alert=True)


# ============== ОБРАБОТКА СОБЫТИЙ ДНЯ ==============


@router.callback_query(F.data == "process_event")
async def process_event(callback):
    """Обработка ежедневного события"""
    user_id = callback.from_user.id

    result = game_logic.process_daily_event(user_id)

    if not result["processed"]:
        await callback.answer(result["message"], show_alert=True)
        return

    text = f"🎲 <b>Событие дня</b>\n\n{result['message']}\n\n💰 Баланс: ${db.get_balance(user_id):.2f}"

    await callback.message.edit_text(text, reply_markup=get_main_menu())
    await callback.answer()


# ============== ЕЖЕДНЕВНЫЙ ВХОД ==============


@router.callback_query(F.data == "daily_claim")
async def daily_claim(callback):
    """Ежедневная награда за вход"""
    user_id = callback.from_user.id

    today = db.get_last_event_date(user_id)

    if today == date.today().isoformat():
        await callback.answer("⏰ Награда уже получена сегодня!", show_alert=True)
        return

    # Обрабатываем событие дня
    result = game_logic.process_daily_event(user_id)

    text = f"""🎉 <b>Добро пожаловать!</b>

📅 Дата: {date.today().strftime("%d.%m.%Y")}

"""

    if result["processed"]:
        text += f"{result['event_name']}\n"
        text += f"Эффект: {result['message']}\n\n"
        text += f"💰 Баланс: ${db.get_balance(user_id):.2f}"
    else:
        text += "⏰ Событие уже обработано сегодня!"

    await callback.message.edit_text(text, reply_markup=get_main_menu())
    await callback.answer()


# ============== ЗАПУСК БОТА ==============


async def main():
    """Главная функция запуска бота"""
    dp.include_router(router)

    logger.info("🚀 Бот запускается...")

    try:
        await dp.start_polling(bot)
    finally:
        await bot.session.close()


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
