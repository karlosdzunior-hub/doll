"""
Production handlers для бота "Микрокапитализм: Жизнь на 1 доллар"
С системой энергии и монетизацией
"""

import re
import uuid
import logging
from typing import Callable, Dict, Any, Awaitable
from aiogram import Router, F, BaseMiddleware
from aiogram.filters import Command, CommandStart
from aiogram.types import (
    Message,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    CallbackQuery,
    PreCheckoutQuery,
    SuccessfulPayment,
    LabeledPrice,
    InlineKeyboardButton,
)
from aiogram.enums import ParseMode, Currency
from aiogram.client.bot import Bot

from config import config
from db import db
from services import EnergyService, MarketService, EventService

logger = logging.getLogger(__name__)
router = Router()


class AutoJoinMiddleware(BaseMiddleware):
    """Автоматически регистрирует пользователя и чат при каждом сообщении в группе."""
    async def __call__(
        self,
        handler: Callable[[Message, Dict[str, Any]], Awaitable[Any]],
        event: Message,
        data: Dict[str, Any],
    ) -> Any:
        if event.chat.type != "private" and event.from_user:
            chat_id = event.chat.id
            user_id = event.from_user.id
            username = event.from_user.username or event.from_user.first_name
            db.create_user(user_id, username)
            db.create_or_update_chat(chat_id, event.chat.type, event.chat.title)
            db.add_user_to_chat(chat_id, user_id)
            db.add_chat_xp(chat_id, config.XP_PER_COMMAND)
            db.log_action(user_id, "chat_command", f"Used command in chat {chat_id}")
        return await handler(event, data)


router.message.middleware(AutoJoinMiddleware())

# Провайдер токена для Telegram Stars (пустой для Stars)
TELEGRAM_STARS_PROVIDER_TOKEN = ""


# ==================== КЛАВИАТУРЫ ====================


async def get_bot_username(bot: Bot) -> str:
    """Получить username бота"""
    try:
        bot_info = await bot.get_me()
        return bot_info.username
    except:
        return ""


def get_main_menu(bot_username: str = None) -> InlineKeyboardMarkup:
    keyboard = [
        [InlineKeyboardButton(text="🏠 Профиль", callback_data="menu_balance")],
        [InlineKeyboardButton(text="💼 Бизнесы", callback_data="menu_business")],
        [InlineKeyboardButton(text="📊 Рынок", callback_data="menu_market")],
        [InlineKeyboardButton(text="🎁 Магазин", callback_data="menu_shop")],
        [InlineKeyboardButton(text="🔝 Топ", callback_data="menu_top")],
        [InlineKeyboardButton(text="👥 Рефералы", callback_data="menu_referrals")],
    ]
    
    # Добавляем кнопку добавления бота в чат
    if bot_username:
        keyboard.append(
            [InlineKeyboardButton(
                text="➕ Добавить бота в чат",
                url=f"https://t.me/{bot_username}?startgroup=true"
            )]
        )
    
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def get_energy_menu() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=f"⚡ +20 энергии ({config.ENERGY_20_COST}⭐)",
                    callback_data="buy_energy_20",
                )
            ],
            [
                InlineKeyboardButton(
                    text=f"🔥 +50 энергии ({config.ENERGY_50_COST}⭐)",
                    callback_data="buy_energy_50",
                )
            ],
            [InlineKeyboardButton(text="🔙 Назад", callback_data="menu_balance")],
        ]
    )


def get_business_menu() -> InlineKeyboardMarkup:
    buttons = []
    for biz_type, biz in config.BUSINESSES.items():
        energy_cost = biz.get("energy_cost", 0)
        energy_gen = biz.get("energy_gen", 0)
        if energy_gen > 0:
            info = f"+{energy_gen * biz['production_rate']:.0f}⚡"
        else:
            info = f"-{energy_cost:.0f}⚡"
        buttons.append(
            [
                InlineKeyboardButton(
                    text=f"{biz['name']} (${biz['base_cost']}) {info}",
                    callback_data=f"buy_biz_{biz_type}",
                )
            ]
        )
    buttons.append(
        [InlineKeyboardButton(text="⬆️ Апгрейд", callback_data="upgrade_select")]
    )
    buttons.append([InlineKeyboardButton(text="🔙 Назад", callback_data="menu_main")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_market_menu() -> InlineKeyboardMarkup:
    buttons = []
    for resource_type, data in config.RESOURCES.items():
        buttons.append(
            [
                InlineKeyboardButton(
                    text=f"📥 Купить {data['name']}",
                    callback_data=f"buy_res_{resource_type}",
                ),
                InlineKeyboardButton(
                    text=f"📤 Продать {data['name']}",
                    callback_data=f"sell_res_{resource_type}",
                ),
            ]
        )
    buttons.append([InlineKeyboardButton(text="🔙 Назад", callback_data="menu_main")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_shop_menu() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=f"⭐ VIP ({config.VIP_COST_STARS}⭐)", callback_data="buy_vip"
                )
            ],
            [
                InlineKeyboardButton(
                    text=f"⚡ +20 Энергии (5⭐)", callback_data="buy_energy_20"
                )
            ],
            [
                InlineKeyboardButton(
                    text=f"🔥 +50 Энергии (10⭐)", callback_data="buy_energy_50"
                )
            ],
            [
                InlineKeyboardButton(
                    text=f"⚡ Буст x2 (10⭐)", callback_data="buy_boost_1h"
                )
            ],
            [InlineKeyboardButton(text=f"🛡️ Щит (5⭐)", callback_data="buy_shield")],
            [
                InlineKeyboardButton(
                    text=f"🎰 Лотерея Премиум (2⭐)",
                    callback_data="buy_lottery_premium",
                )
            ],
            [InlineKeyboardButton(text="🔙 Назад", callback_data="menu_main")],
        ]
    )


def get_upgrade_menu(user_id: int) -> InlineKeyboardMarkup:
    businesses = db.get_user_businesses(user_id)
    buttons = []
    for biz in businesses:
        biz_config = config.BUSINESSES.get(biz["business_type"], {})
        new_level = biz["level"] + 1
        cost = biz_config.get("base_cost", 1) * (new_level**1.5)
        text = f"{biz_config.get('name', biz['business_type'])} Ур.{biz['level']}→{new_level} (${cost:.0f})"
        buttons.append(
            [InlineKeyboardButton(text=text, callback_data=f"upgrade_{biz['id']}")]
        )
    buttons.append(
        [InlineKeyboardButton(text="🔙 Назад", callback_data="menu_business")]
    )
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_no_energy_menu() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=f"⚡ +20 энергии ({config.ENERGY_20_COST}⭐)",
                    callback_data="buy_energy_20",
                )
            ],
            [
                InlineKeyboardButton(
                    text=f"🔥 +50 энергии ({config.ENERGY_50_COST}⭐)",
                    callback_data="buy_energy_50",
                )
            ],
            [
                InlineKeyboardButton(
                    text="💤 Ждать восстановления", callback_data="menu_balance"
                )
            ],
        ]
    )


# ==================== КОМАНДЫ ====================


@router.message(CommandStart())
async def cmd_start(message: Message):
    user_id = message.from_user.id
    username = message.from_user.username or message.from_user.first_name

    args = message.text.split()
    referral_id = None
    if len(args) > 1:
        try:
            referral_id = int(args[1])
        except ValueError:
            pass

    db.create_user(user_id, username, referral_id)

    welcome = f"""
🎮 <b>Микрокапитализм</b>

💵 Старт: $1
⚡ Энергия: {config.MAX_ENERGY}

📈 Развивай бизнесы, торгуй на рынке!
⚠️ Без энергии бизнесы не работают!

👥 Рефералы → бонусы!
"""
    bot_username = await get_bot_username(message.bot)
    await message.answer(welcome, reply_markup=get_main_menu(bot_username))


# ==================== ПРОФИЛЬ (С ЭНЕРГИЕЙ) ====================


@router.callback_query(F.data == "menu_balance")
async def menu_balance(callback: CallbackQuery):
    user_id = callback.from_user.id
    username = callback.from_user.username or callback.from_user.first_name
    db.create_user(user_id, username)
    user = db.get_user(user_id)

    if not user:
        await callback.answer("❌ Сначала напишите /start боту в личных сообщениях!", show_alert=True)
        return

    balance = user["balance"]
    energy_status = EnergyService.get_user_energy_status(user_id)

    # Проверяем VIP и буст
    vip = "⭐ VIP" if db.check_vip(user_id) else ""
    boost = "⚡ x2" if db.check_boost(user_id) else ""

    # Бизнесы
    businesses = db.get_user_businesses(user_id)

    # Ресурсы
    resources = db.get_user_resources(user_id)

    # Производство
    production = db.get_total_production(user_id)

    # Статус энергии
    energy_bar = EnergyService.get_energy_bar(
        energy_status["current"], energy_status["max"]
    )

    text = f"""🏠 <b>Профиль</b>

💰 Баланс: ${balance:.2f} {vip} {boost}

{energy_bar}
⚡ {energy_status["current"]:.0f}/{energy_status["max"]} энергии
📉 Расход: -{energy_status["consumption_per_hour"]:.1f}/час
📈 Приход: +{energy_status["generation_per_hour"]:.1f}/час
"""

    # Предупреждение если энергия кончилась
    if energy_status["is_depleted"]:
        text += "\n⚠️ <b>Энергия слишком низкая!</b>\nБизнесы остановлены.\n"

    text += f"\n🏢 <b>Бизнесов:</b> {len(businesses)}\n"

    # Активные события
    active_events = EventService.get_active_events_list()
    if active_events:
        text += "\n🌍 <b>События:</b>\n"
        for event in active_events[:2]:
            text += f"• {event['name']}\n"

    # Получаем username бота для кнопки
    try:
        bot_info = await callback.bot.get_me()
        bot_username = bot_info.username
    except:
        bot_username = None

    # Если энергия кончилась - показываем меню покупки
    if energy_status["current"] < config.MIN_ENERGY_TO_WORK:
        await callback.message.edit_text(text, reply_markup=get_no_energy_menu())
    else:
        await callback.message.edit_text(text, reply_markup=get_main_menu(bot_username))

    await callback.answer()


# ==================== БИЗНЕСЫ ====================


@router.callback_query(F.data == "menu_business")
async def menu_business(callback: CallbackQuery):
    user_id = callback.from_user.id
    balance = db.get_balance(user_id)
    businesses = db.get_user_businesses(user_id)
    energy_status = EnergyService.get_user_energy_status(user_id)

    text = f"""💼 <b>Бизнесы</b>

💰 Баланс: ${balance:.2f}
⚡ Энергия: {energy_status["current"]:.0f}/{energy_status["max"]}
🏢 У вас: {len(businesses)}

"""

    if businesses:
        text += "<b>Ваши бизнесы:</b>\n"
        production = db.get_total_production(user_id)
        for biz in businesses:
            biz_config = config.BUSINESSES.get(biz["business_type"], {})
            resource = biz_config.get("resource", "")
            rate = production.get(resource, 0)
            energy_cost = biz_config.get("energy_cost", 0) * biz["level"]
            active = (
                "🟢" if energy_status["current"] >= config.MIN_ENERGY_TO_WORK else "🔴"
            )
            text += f"{active} {biz_config.get('name', biz['business_type'])} Ур.{biz['level']} (+{rate:.1f}/час, -{energy_cost:.0f}⚡)\n"

    text += "\n<b>Купить бизнес:</b>"

    await callback.message.edit_text(text, reply_markup=get_business_menu())
    await callback.answer()


@router.callback_query(F.data.startswith("buy_biz_"))
async def buy_business(callback: CallbackQuery):
    user_id = callback.from_user.id
    biz_type = callback.data.replace("buy_biz_", "")

    if biz_type not in config.BUSINESSES:
        await callback.answer("❌ Неизвестный бизнес!", show_alert=True)
        return

    biz = config.BUSINESSES[biz_type]
    cost = biz["base_cost"]

    if db.get_balance(user_id) < cost:
        await callback.answer(
            f"❌ Недостаточно средств! Нужно: ${cost}", show_alert=True
        )
        return

    if db.create_business(user_id, biz_type):
        await callback.message.edit_text(
            f"✅ <b>{biz['name']}</b> куплен!\n\n💵 Потрачено: ${cost}\n💰 Баланс: ${db.get_balance(user_id):.2f}",
            reply_markup=get_business_menu(),
        )
        await callback.answer(f"✅ {biz['name']} успешно куплен!", show_alert=True)
    else:
        await callback.answer("❌ Ошибка покупки!", show_alert=True)


@router.callback_query(F.data == "upgrade_select")
async def upgrade_select(callback: CallbackQuery):
    user_id = callback.from_user.id
    await callback.message.edit_text(
        "⬆️ <b>Выберите бизнес для апгрейда:</b>", reply_markup=get_upgrade_menu(user_id)
    )
    await callback.answer()


@router.callback_query(F.data.startswith("upgrade_"))
async def upgrade_business(callback: CallbackQuery):
    user_id = callback.from_user.id
    business_id = int(callback.data.replace("upgrade_", ""))

    success, cost = db.upgrade_business(business_id)

    if success:
        biz = db.get_business(business_id)
        biz_config = config.BUSINESSES.get(biz["business_type"], {})
        bot_username = await get_bot_username(callback.bot)
        await callback.message.edit_text(
            f"⬆️ <b>Апгрейд!</b>\n\n"
            f"{biz_config.get('name', biz['business_type'])} → Ур.{biz['level']}\n"
            f"💵 Потрачено: ${cost:.2f}",
            reply_markup=get_main_menu(bot_username),
        )
        await callback.answer("✅ Апгрейд выполнен!", show_alert=True)
    else:
        await callback.answer("❌ Недостаточно средств!", show_alert=True)


# ==================== РЫНОК ====================


@router.callback_query(F.data == "menu_market")
async def menu_market(callback: CallbackQuery):
    text = MarketService.get_market_overview()
    await callback.message.edit_text(text, reply_markup=get_market_menu())
    await callback.answer()


@router.callback_query(F.data.startswith("buy_res_"))
async def buy_resource(callback: CallbackQuery):
    user_id = callback.from_user.id
    resource_type = callback.data.replace("buy_res_", "")

    if resource_type not in config.RESOURCES:
        await callback.answer("❌ Ресурс не найден!", show_alert=True)
        return

    resources = db.get_user_resources(user_id)
    qty = resources.get(resource_type, 0)
    prices = db.get_market_prices()
    price = prices[resource_type]["current_price"]
    balance = db.get_balance(user_id)
    max_buy = min(balance / price, config.RESOURCE_MAX - qty)

    res_name = config.RESOURCES[resource_type]["name"]
    text = f"""📥 <b>Купить {res_name}</b>

💰 Баланс: ${balance:.2f}
💵 Цена: ${price:.2f}/ед
📊 Максимум: {max_buy:.1f} ед
📦 У вас: {qty:.1f} ед
"""

    await callback.message.edit_text(text, reply_markup=get_market_menu())
    await callback.answer()


@router.callback_query(F.data.startswith("sell_res_"))
async def sell_resource(callback: CallbackQuery):
    user_id = callback.from_user.id
    resource_type = callback.data.replace("sell_res_", "")

    if resource_type not in config.RESOURCES:
        await callback.answer("❌ Ресурс не найден!", show_alert=True)
        return

    resources = db.get_user_resources(user_id)
    qty = resources.get(resource_type, 0)
    prices = db.get_market_prices()
    price = prices[resource_type]["current_price"]

    if qty <= 0:
        await callback.answer("❌ Нет ресурсов для продажи!", show_alert=True)
        return

    earnings = db.sell_resource(user_id, resource_type, qty)

    if earnings > 0:
        await callback.message.edit_text(
            f"✅ Продано {qty:.1f} ед. за ${earnings:.2f}\n"
            f"(комиссия {config.MARKET_FEE * 100}%)",
            reply_markup=get_market_menu(),
        )
        await callback.answer(f"✅ Получено ${earnings:.2f}!", show_alert=True)
    else:
        await callback.answer("❌ Ошибка!", show_alert=True)


# ==================== МАГАЗИН ====================


@router.callback_query(F.data == "menu_shop")
async def menu_shop(callback: CallbackQuery):
    user_id = callback.from_user.id
    balance = db.get_balance(user_id)
    is_vip = db.check_vip(user_id)
    is_boost = db.check_boost(user_id)
    shields = db.get_item(user_id, "shield")

    user = db.get_user(user_id)
    vip_expire = ""
    if is_vip and user and user.get("vip_expire"):
        from datetime import datetime
        expire_dt = datetime.fromisoformat(user["vip_expire"])
        days_left = (expire_dt - datetime.now()).days + 1
        vip_expire = f" (ещё {days_left} дн.)"

    vip_status = f"⭐ VIP активен{vip_expire}" if is_vip else "❌ VIP неактивен"
    boost_status = "⚡ Буст x2 активен" if is_boost else "❌ Буст неактивен"

    text = f"""🎁 <b>Магазин</b>

💰 Баланс: ${balance:.2f}
{vip_status}
{boost_status}
🛡️ Щитов: {shields}

⭐ <b>VIP даёт:</b>
• +20% к производству бизнесов
• -30% к расходу энергии
• Значок ⭐ в профиле
"""

    await callback.message.edit_text(text, reply_markup=get_shop_menu())
    await callback.answer()


@router.callback_query(F.data == "buy_vip")
async def buy_vip(callback: CallbackQuery, bot: Bot):
    user_id = callback.from_user.id

    if db.check_vip(user_id):
        await callback.answer("⭐ VIP уже активен!", show_alert=True)
        return

    success = await send_invoice_to_user(bot, user_id, "vip")
    if success:
        await callback.answer("💳 Отправляю счёт на оплату VIP...", show_alert=True)
    else:
        await callback.answer("❌ Ошибка отправки счёта!", show_alert=True)


@router.callback_query(F.data == "buy_boost_1h")
async def buy_boost(callback: CallbackQuery, bot: Bot):
    """Покупка буста за Stars"""
    success = await send_invoice_to_user(bot, callback.from_user.id, "boost_1h")
    if success:
        await callback.answer("💳 Отправляю счёт...", show_alert=True)
    else:
        await callback.answer("❌ Ошибка!", show_alert=True)


@router.callback_query(F.data == "buy_shield")
async def buy_shield(callback: CallbackQuery, bot: Bot):
    """Покупка щита за Stars"""
    success = await send_invoice_to_user(bot, callback.from_user.id, "shield")
    if success:
        await callback.answer("💳 Отправляю счёт...", show_alert=True)
    else:
        await callback.answer("❌ Ошибка!", show_alert=True)


@router.callback_query(F.data == "buy_insider")
async def buy_insider(callback: CallbackQuery):
    """Показать информацию о инсайдере"""
    preview = EventService.get_next_event_preview()
    await callback.message.edit_text(preview, reply_markup=get_shop_menu())
    await callback.answer("🔮 Инсайдерская информация!", show_alert=True)


# ==================== ЭНЕРГИЯ ====================


@router.callback_query(F.data == "buy_energy_20")
async def buy_energy_20(callback: CallbackQuery, bot: Bot):
    """Покупка энергии за Stars"""
    success = await send_invoice_to_user(bot, callback.from_user.id, "energy_20")
    if success:
        await callback.answer("💳 Отправляю счёт...", show_alert=True)
    else:
        await callback.answer("❌ Ошибка!", show_alert=True)


@router.callback_query(F.data == "buy_energy_50")
async def buy_energy_50(callback: CallbackQuery, bot: Bot):
    """Покупка энергии за Stars"""
    user_id = callback.from_user.id
    success = await send_invoice_to_user(bot, user_id, "energy_50")
    if success:
        await callback.answer("💳 Отправляю счёт...", show_alert=True)
    else:
        await callback.answer("❌ Ошибка!", show_alert=True)
        return
    
    bot_username = await get_bot_username(bot)
    energy = EnergyService.get_user_energy_status(user_id)

    await callback.message.edit_text(
        f"🔥 <b>Супер энергия!</b>\n\n⚡ {energy['current']:.0f}/{energy['max']}",
        reply_markup=get_main_menu(bot_username),
    )
    await callback.answer("✅ +50 энергии!", show_alert=True)


# ==================== ТОП И РЕФЕРАЛЫ ====================


@router.callback_query(F.data == "menu_top")
async def menu_top(callback: CallbackQuery):
    leaders = db.get_leaderboard(10)

    text = "🏆 <b>ТОП-10 ИГРОКОВ</b>\n\n"

    medals = ["🥇", "🥈", "🥉"]
    for i, player in enumerate(leaders, 1):
        medal = medals[i - 1] if i <= 3 else f"{i}."
        name = player["username"] or f"User{player['user_id']}"
        text += f"{medal} {name} — ${player['balance']:.2f}\n"

    bot_username = await get_bot_username(callback.bot)
    await callback.message.edit_text(text, reply_markup=get_main_menu(bot_username))
    await callback.answer()


@router.callback_query(F.data == "menu_referrals")
async def menu_referrals(callback: CallbackQuery):
    user_id = callback.from_user.id
    referrals = db.get_referrals(user_id)
    count = len(referrals)

    bot_username = await get_bot_username(callback.bot)

    text = f"""👥 <b>Рефералы</b>

👥 Приглашено: {count}
💰 Бонус за друга: ${config.REFERRAL_BONUS}

📎 Ваша ссылка:
https://t.me/{bot_username}?start={user_id}
"""

    await callback.message.edit_text(text, reply_markup=get_main_menu(bot_username))
    await callback.answer()


# ==================== НАВИГАЦИЯ ====================


@router.callback_query(F.data == "menu_main")
async def menu_main(callback: CallbackQuery):
    bot_username = await get_bot_username(callback.bot)
    await callback.message.edit_text(
        "📋 <b>Главное меню:</b>", reply_markup=get_main_menu(bot_username)
    )
    await callback.answer()


# ==================== ЧАТ-КОМАНДЫ ====================


@router.message(F.chat.type != "private", F.text == "/мой_баланс")
async def chat_balance(message: Message):
    user_id = message.from_user.id
    username = message.from_user.username or message.from_user.first_name
    db.create_user(user_id, username)
    balance = db.get_balance(user_id)
    energy, max_e = db.get_energy(user_id)

    bar = EnergyService.get_energy_bar(energy, max_e)

    await message.reply(
        f"💰 {message.from_user.first_name}:\n"
        f"Баланс: ${balance:.2f}\n"
        f"{bar} ⚡{energy:.0f}/{max_e}"
    )


@router.message(F.chat.type != "private", F.text == "/мой_бизнес")
async def chat_business(message: Message):
    user_id = message.from_user.id
    username = message.from_user.username or message.from_user.first_name
    db.create_user(user_id, username)
    businesses = db.get_user_businesses(user_id)

    if not businesses:
        await message.reply("🏢 У вас нет бизнесов!")
        return

    text = "🏢 <b>Ваши бизнесы:</b>\n"
    for biz in businesses:
        biz_config = config.BUSINESSES.get(biz["business_type"], {})
        text += f"• {biz_config.get('name', biz['business_type'])} Ур.{biz['level']}\n"

    await message.reply(text)


@router.message(F.chat.type != "private", F.text == "/рынок")
async def chat_market(message: Message):
    text = MarketService.get_market_overview()
    await message.reply(text)


@router.message(F.chat.type != "private", F.text == "/топ")
async def chat_top(message: Message):
    leaders = db.get_leaderboard(5)
    text = "🏆 <b>ТОП-5</b>\n"

    for i, player in enumerate(leaders, 1):
        text += f"{i}. ${player['balance']:.2f}\n"

    await message.reply(text)


@router.message(
    F.chat.type != "private", F.text.regexp(r"^/отправить\s*@?(\w+)\s*(\d+(?:\.\d+)?)")
)
async def chat_transfer(message: Message):
    user_id = message.from_user.id
    username = message.from_user.username or message.from_user.first_name
    db.create_user(user_id, username)
    match = re.match(r"^/отправить\s*@?(\w+)\s*(\d+(?:\.\d+)?)", message.text)
    if not match:
        await message.reply(
            "❌ Формат: /отправить @username сумма\n💡 Пример: /отправить @username 100"
        )
        return

    username = match.group(1)
    amount = float(match.group(2))

    with db.get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT user_id FROM users WHERE username = ?", (username,))
        row = cursor.fetchone()

    if not row:
        await message.reply(f"❌ Пользователь @{username} не найден")
        return

    to_user = row[0]
    from_user = message.from_user.id
    chat_id = message.chat.id

    success, result = db.transfer_money(from_user, to_user, amount, chat_id)

    if success:
        db.log_action(from_user, "chat_transfer", f"To @{username}: ${amount}")
        
        # Начисляем XP чату за перевод
        db.add_chat_xp(chat_id, config.XP_PER_TRANSFER)
        
        await message.reply(
            f"✅ {message.from_user.first_name} → @{username}: ${amount:.2f}\n"
            f"💰 Ваш баланс: ${db.get_balance(from_user):.2f}"
        )
    else:
        await message.reply(f"❌ {result}")


@router.message(F.chat.type != "private", F.text == "/лотерея")
async def chat_lottery(message: Message):
    user_id = message.from_user.id
    username = message.from_user.username or message.from_user.first_name
    db.create_user(user_id, username)
    balance = db.get_balance(user_id)

    text = f"""🎰 <b>ЛОТЕРЕЯ</b>

💰 Ваш баланс: ${balance:.2f}

🎫 <b>Обычная:</b> $10
   Шансы:
   • 70% — проигрыш
   • 25% — x1.5
   • 4% — x3
   • 1% — x10

⭐ <b>Премиум:</b> 2⭐
   Те же шансы, но оплата Stars!"""

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🎫 Играть ($10)", callback_data="lottery_regular"
                )
            ],
            [
                InlineKeyboardButton(
                    text="⭐ Премиум (2⭐)", callback_data="lottery_premium"
                )
            ],
        ]
    )

    await message.reply(text, reply_markup=keyboard)


@router.callback_query(F.data.in_(["lottery_regular", "lottery_premium"]))
async def lottery_play(callback: CallbackQuery):
    user_id = callback.from_user.id
    is_premium = callback.data == "lottery_premium"

    result = db.play_lottery(user_id, callback.message.chat.id, is_premium)

    if not result["won"] and result["won_amount"] == 0:
        # Проигрыш
        await callback.message.edit_text(
            result["message"],
            reply_markup=InlineKeyboardMarkup(
                inline_keyboard=[
                    [
                        InlineKeyboardButton(
                            text="🔄 Ещё раз", callback_data=callback.data
                        )
                    ],
                    [
                        InlineKeyboardButton(
                            text="❌ Закрыть", callback_data="lottery_close"
                        )
                    ],
                ]
            ),
        )
    else:
        # Выигрыш!
        await callback.message.edit_text(
            f"{result['message']}\n\n💰 Баланс: ${db.get_balance(user_id):.2f}",
            reply_markup=InlineKeyboardMarkup(
                inline_keyboard=[
                    [
                        InlineKeyboardButton(
                            text="🎰 Ещё раз!", callback_data=callback.data
                        )
                    ],
                    [
                        InlineKeyboardButton(
                            text="❌ Закрыть", callback_data="lottery_close"
                        )
                    ],
                ]
            ),
        )

    await callback.answer()


@router.callback_query(F.data == "lottery_close")
async def lottery_close(callback: CallbackQuery):
    await callback.message.delete()
    await callback.answer()


@router.callback_query(F.data == "buy_lottery_premium")
async def buy_lottery_premium(callback: CallbackQuery, bot: Bot):
    """Покупка премиум лотереи за Stars"""
    success = await send_invoice_to_user(bot, callback.from_user.id, "lottery_premium")
    if success:
        await callback.answer("💳 Отправляю счёт...", show_alert=True)
    else:
        await callback.answer("❌ Ошибка!", show_alert=True)


@router.callback_query(F.data == "buy_jackpot_ticket")
async def buy_jackpot_ticket(callback: CallbackQuery, bot: Bot):
    """Покупка билета джекпота за Stars"""
    success = await send_invoice_to_user(bot, callback.from_user.id, "jackpot_ticket")
    if success:
        await callback.answer("💳 Отправляю счёт...", show_alert=True)
    else:
        await callback.answer("❌ Ошибка!", show_alert=True)


# ==================== ОБРАБОТКА ДОБАВЛЕНИЯ БОТА В ЧАТ ====================


@router.message(F.new_chat_members)
async def bot_added_to_chat(message: Message, bot: Bot):
    """Обработка когда бота добавляют в чат"""
    chat_id = message.chat.id
    bot_user_id = (await bot.get_me()).id

    # Проверяем что бота добавили
    for member in message.new_chat_members:
        if member.id == bot_user_id:
            # Бота добавили в чат
            added_by = message.from_user.id if message.from_user else None

            # Сохраняем чат
            db.create_or_update_chat(
                chat_id, message.chat.type, message.chat.title, added_by
            )

            # Проверяем права администратора
            try:
                member_status = await bot.get_chat_member(chat_id, bot_user_id)
                is_admin = member_status.status in ["administrator", "creator"]
            except:
                is_admin = False

            admin_msg = ""
            if not is_admin:
                admin_msg = "\n\n⚠️ <b>Дайте боту права администратора для корректной работы!</b>"

            # Выдаём бонус за добавление (только если первый раз)
            bonus_msg = ""
            if not db.has_claimed_bonus(chat_id) and added_by:
                db.claim_chat_bonus(chat_id)
                EnergyService.add_energy(added_by, config.ADD_BOT_ENERGY_BONUS)
                db.add_item(added_by, "lottery_ticket", config.ADD_BOT_LOTTERY_TICKET)
                bonus_msg = f"\n\n🎁 <b>Бонус за добавление!</b>\n⚡ +{config.ADD_BOT_ENERGY_BONUS} энергии\n🎫 +{config.ADD_BOT_LOTTERY_TICKET} билет джекпота"

            welcome = f"""👋 <b>Бот активирован!</b>

📊 Уровень чата: 1
💡 Используйте команды:
• /мой_баланс
• /рынок
• /лотерея
• /уровень_чата{admin_msg}{bonus_msg}"""

            await message.answer(welcome)

            # Логирование
            if added_by:
                db.log_action(added_by, "chat_added", f"Added bot to chat {chat_id}")


# ==================== КОМАНДЫ ЧАТА ====================


@router.message(F.chat.type != "private", F.text == "/уровень_чата")
async def chat_level(message: Message):
    """Показать уровень чата"""
    chat_id = message.chat.id
    chat = db.get_chat(chat_id)

    if not chat:
        await message.reply("❌ Этот чат не зарегистрирован!")
        return

    level = chat["level"]
    xp = chat["xp"]
    xp_needed = db.get_xp_needed_for_level(level)
    progress = (xp / xp_needed) * 100 if xp_needed > 0 else 0

    # Получаем бонусы уровня
    bonuses = db.get_chat_bonus(chat_id)
    
    # Проверяем VIP чата
    is_vip = db.is_chat_vip(chat_id)
    vip_text = "⭐ <b>VIP активен</b>" if is_vip else ""

    bonuses_text = ""
    if level >= 2:
        bonuses_text += f"\n• Level 2: +5% доход"
    if level >= 3:
        bonuses_text += f"\n• Level 3: +1 бесплатный билет/день"
    if level >= 4:
        bonuses_text += f"\n• Level 4: -10% расход энергии"
    if level >= 5:
        bonuses_text += f"\n• Level 5: +10% шанс в джекпоте"
    if is_vip:
        bonuses_text += f"\n• ⭐ VIP: +10% XP, +5% доход"

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="📈 Буст XP (+100) - 10⭐",
                    callback_data="buy_xp_boost_chat"
                )
            ],
            [
                InlineKeyboardButton(
                    text="⭐ VIP Чат (7 дней) - 50⭐",
                    callback_data="buy_vip_chat"
                )
            ],
        ]
    )

    text = f"""🏆 <b>Уровень чата</b> {vip_text}

📊 Уровень: {level}
⭐ XP: {xp}/{xp_needed}
📈 Прогресс: {progress:.1f}%

💡 Бонусы:{bonuses_text or "\n• Пока нет бонусов"}"""

    await message.reply(text, reply_markup=keyboard)


@router.message(F.chat.type != "private", F.text == "/топ_чаты")
async def top_chats(message: Message):
    """Показать топ чатов"""
    chats = db.get_top_chats(10)

    if not chats:
        await message.reply("❌ Нет зарегистрированных чатов!")
        return

    text = "🏆 <b>ТОП-10 ЧАТОВ</b>\n\n"

    medals = ["🥇", "🥈", "🥉"]
    for i, chat in enumerate(chats, 1):
        medal = medals[i - 1] if i <= 3 else f"{i}."
        title = chat["title"] or f"Chat {chat['chat_id']}"
        text += f"{medal} {title}\n   📊 Level {chat['level']} ({chat['xp']} XP)\n"

    await message.reply(text)


@router.message(F.chat.type != "private", F.text == "/джекпот")
async def jackpot_info(message: Message):
    """Информация о джекпоте"""
    user_id = message.from_user.id
    tickets = db.get_item(user_id, "lottery_ticket")

    text = f"""🎰 <b>ДЖЕКПОТ</b>

🎫 Ваши билеты: {tickets}

💡 Используйте билеты для участия в джекпоте!
⏰ Джекпот разыгрывается автоматически каждый час."""

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🎫 Купить билет (5⭐)", callback_data="buy_jackpot_ticket"
                )
            ]
        ]
    )

    await message.reply(text, reply_markup=keyboard)


# ==================== АНГЛИЙСКИЕ ПСЕВДОНИМЫ КОМАНД ====================

@router.message(F.chat.type != "private", Command("balance"))
async def cmd_balance(message: Message):
    await chat_balance(message)

@router.message(F.chat.type != "private", Command("business"))
async def cmd_business(message: Message):
    await chat_business(message)

@router.message(F.chat.type != "private", Command("market"))
async def cmd_market(message: Message):
    await chat_market(message)

@router.message(F.chat.type != "private", Command("top"))
async def cmd_top(message: Message):
    await chat_top(message)

@router.message(F.chat.type != "private", Command("chatlevel"))
async def cmd_chatlevel(message: Message):
    await chat_level(message)

@router.message(F.chat.type != "private", Command("topchats"))
async def cmd_topchats(message: Message):
    await top_chats(message)

@router.message(F.chat.type != "private", Command("lottery"))
async def cmd_lottery(message: Message):
    await chat_lottery(message)

@router.message(F.chat.type != "private", Command("jackpot"))
async def cmd_jackpot(message: Message):
    await jackpot_info(message)

@router.message(F.chat.type != "private", Command("send"))
async def cmd_send(message: Message):
    if not message.text:
        await message.reply("💸 Формат: /send @username сумма\n💡 Пример: /send @username 100")
        return
    # Подменяем текст чтобы переиспользовать логику русской команды
    match = re.match(r"^/send\s*@?(\w+)\s*(\d+(?:\.\d+)?)", message.text)
    if not match:
        await message.reply("💸 Формат: /send @username сумма\n💡 Пример: /send @username 100")
        return
    message.text = f"/отправить @{match.group(1)} {match.group(2)}"
    await chat_transfer(message)


# ==================== TELEGRAM STARS ПЛАТЕЖИ ====================

# Конфигурация товаров для покупки
ITEMS_CONFIG = {
    "energy_20": {
        "name": "⚡ +20 Энергии",
        "stars": 5,
        "description": "Мгновенное восстановление 20 единиц энергии",
        "reward": "⚡ +20 энергии зачислено на твой аккаунт!",
    },
    "energy_50": {
        "name": "🔥 +50 Энергии",
        "stars": 10,
        "description": "Мгновенное восстановление 50 единиц энергии",
        "reward": "🔥 +50 энергии зачислено на твой аккаунт!",
    },
    "boost_1h": {
        "name": "⚡ Буст x2 (1 час)",
        "stars": 10,
        "description": "Удвоение производства на 1 час",
        "reward": "⚡ Буст x2 активирован! Производство удвоено на 1 час.",
    },
    "shield": {
        "name": "🛡️ Щит",
        "stars": 5,
        "description": "Защита от одного негативного события",
        "reward": "🛡️ Щит активирован! Ты защищён от следующего негативного события.",
    },
    "lottery_premium": {
        "name": "🎰 Лотерея Премиум",
        "stars": 2,
        "description": "Билет в премиум лотерею с x10 джекпотом",
        "reward": "🎰 Премиум билет добавлен! Используй /лотерея чтобы сыграть.",
    },
    "vip": {
        "name": "⭐ VIP статус (7 дней)",
        "stars": 50,
        "description": "VIP статус на 7 дней: +20% к производству, -30% расход энергии",
        "reward": "⭐ VIP статус активирован на 7 дней!\n+20% к производству\n-30% к расходу энергии",
    },
    "xp_boost_chat": {
        "name": "📈 Буст XP чата (+100)",
        "stars": 10,
        "description": "Добавить 100 XP текущему чату",
        "reward": "📈 +100 XP добавлено текущему чату!",
    },
    "vip_chat": {
        "name": "⭐ VIP Чат (7 дней)",
        "stars": 50,
        "description": "VIP статус для чата на 7 дней с бонусами",
        "reward": "⭐ VIP статус чата активирован на 7 дней!",
    },
    "jackpot_ticket": {
        "name": "🎫 Билет Джекпота",
        "stars": 5,
        "description": "Билет для участия в часовом джекпоте",
        "reward": "🎫 Билет джекпота получен! Жди розыгрыша каждый час.",
    },
}


async def send_invoice_to_user(
    bot: Bot,
    user_id: int,
    item_key: str,
    chat_id: int = None,
):
    """Отправить инвойс пользователю через Telegram Stars"""
    if item_key not in ITEMS_CONFIG:
        return False

    item = ITEMS_CONFIG[item_key]

    # Генерируем уникальный payload (разделитель | чтобы не конфликтовал с _ в ключах)
    payload = f"{item_key}|{user_id}|{chat_id or 0}|{uuid.uuid4().hex[:8]}"

    # Создаём запись в БД
    payment_id = db.create_payment(user_id, item_key, item["stars"], chat_id)

    try:
        await bot.send_invoice(
            chat_id=user_id,
            title=item["name"],
            description=item["description"],
            payload=payload,
            provider_token=TELEGRAM_STARS_PROVIDER_TOKEN,
            currency="XTR",  # Telegram Stars
            prices=[LabeledPrice(label=item["name"], amount=item["stars"])],
        )
        return True
    except Exception as e:
        logger.error(f"Failed to send invoice: {e}")
        return False


@router.callback_query(F.data.startswith("buy_"))
async def buy_with_stars(callback: CallbackQuery, bot: Bot):
    """Обработка кнопки покупки - отправка инвойса"""
    user_id = callback.from_user.id
    item_key = callback.data.replace("buy_", "")

    if item_key not in ITEMS_CONFIG:
        await callback.answer("❌ Неизвестный товар!", show_alert=True)
        return

    # Для XP буста и VIP чата нужен chat_id
    chat_id = None
    if item_key in ["xp_boost_chat", "vip_chat"]:
        if callback.message.chat.type == "private":
            await callback.answer("❌ Эта покупка только в чатах!", show_alert=True)
            return
        chat_id = callback.message.chat.id

    # Отправляем инвойс
    success = await send_invoice_to_user(bot, user_id, item_key, chat_id)

    if success:
        await callback.answer("💳 Отправляю счёт для оплаты...", show_alert=True)
    else:
        await callback.answer("❌ Ошибка отправки счёта!", show_alert=True)


# ==================== ОБРАБОТКА ПЛАТЕЖЕЙ STARS ====================


@router.pre_checkout_query()
async def pre_checkout(pre_checkout: PreCheckoutQuery):
    """Обработка предварительного запроса на оплату"""
    # Принимаем платёж
    await pre_checkout.answer(ok=True)


async def process_successful_payment(user_id: int, item_key: str, chat_id: int = None, bot: Bot = None):
    """Обработка успешного платежа - начисление товара"""
    item = ITEMS_CONFIG.get(item_key)
    if not item:
        return False, None

    # Начисляем товар в зависимости от типа
    if item_key == "energy_20":
        EnergyService.add_energy(user_id, 20)
    elif item_key == "energy_50":
        EnergyService.add_energy(user_id, 50)
    elif item_key == "boost_1h":
        db.set_boost(user_id, 1)
    elif item_key == "shield":
        db.add_item(user_id, "shield", 1)
    elif item_key == "lottery_premium":
        db.add_item(user_id, "lottery_premium_ticket", 1)
    elif item_key == "vip":
        db.set_vip(user_id, config.VIP_DURATION_DAYS)
    elif item_key == "jackpot_ticket":
        db.add_item(user_id, "lottery_ticket", 1)
    elif item_key == "xp_boost_chat":
        if chat_id:
            success, leveled_up, new_level = db.add_chat_xp(chat_id, 100)
            if leveled_up:
                return True, f"📈 Чат получил +100 XP и достиг уровня {new_level}!"
    elif item_key == "vip_chat":
        if chat_id:
            db.set_chat_vip(chat_id, 7)

    # Логирование
    db.log_action(
        user_id,
        "stars_payment_completed",
        f"Item: {item_key}, Stars: {item['stars']}, Chat: {chat_id}",
    )

    # Возвращаем описание награды из конфига
    return True, item.get("reward", "")


@router.message(F.successful_payment)
async def successful_payment(message: Message):
    """Обработка успешного платежа Telegram Stars"""
    user_id = message.from_user.id
    payment = message.successful_payment

    # Парсим payload (новый формат: item_key|user_id|chat_id|uuid)
    payload = payment.invoice_payload
    if "|" in payload:
        parts = payload.split("|")
        item_key = parts[0] if parts else None
        chat_id_raw = parts[2] if len(parts) > 2 else "0"
        chat_id = int(chat_id_raw) if chat_id_raw.lstrip("-").isdigit() and chat_id_raw != "0" else None
    else:
        # Обратная совместимость: старый формат item_key_userid_chatid_uuid
        # Ищем ключ товара по совпадению с началом payload
        item_key = None
        for key in ITEMS_CONFIG:
            if payload.startswith(key + "_"):
                item_key = key
                break
        rest = payload[len(item_key) + 1:].split("_") if item_key else []
        chat_id_raw = rest[1] if len(rest) > 1 else "0"
        chat_id = int(chat_id_raw) if chat_id_raw.lstrip("-").isdigit() and chat_id_raw != "0" else None

    item = ITEMS_CONFIG.get(item_key, {})

    # Обрабатываем платёж и начисляем товар
    success, reward_text = await process_successful_payment(user_id, item_key, chat_id, message.bot)

    item_name = item.get("name", "Товар")
    item_stars = item.get("stars", payment.total_amount)

    if success and reward_text:
        success_message = (
            f"✅ <b>Оплата прошла успешно!</b>\n\n"
            f"⭐ Потрачено: {item_stars}⭐\n"
            f"📦 Получено: {item_name}\n\n"
            f"{reward_text}\n\n"
            f"💪 Спасибо за покупку!"
        )
    else:
        success_message = (
            f"✅ <b>Оплата прошла успешно!</b>\n\n"
            f"⭐ Потрачено: {item_stars}⭐\n"
            f"📦 Получено: {item_name}\n\n"
            f"💪 Спасибо за покупку!"
        )

    await message.answer(success_message)


# ==================== КНОПКА ДОБАВЛЕНИЯ В ЧАТ ====================


def get_add_to_chat_button(bot_username: str) -> InlineKeyboardMarkup:
    """Кнопка для добавления бота в чат"""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="➕ Добавить бота в чат",
                    url=f"https://t.me/{bot_username}?startgroup=true",
                )
            ]
        ]
    )
