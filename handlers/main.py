"""
Production handlers для бота "Микрокапитализм: Жизнь на 1 доллар"
С системой энергии и монетизацией
"""

import re
import logging
from aiogram import Router, F
from aiogram.filters import Command, CommandStart
from aiogram.types import (
    Message,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    CallbackQuery,
)
from aiogram.enums import ParseMode
from aiogram.client.bot import Bot

from config import config
from db import db
from services import EnergyService, MarketService, EventService

logger = logging.getLogger(__name__)
router = Router()


# ==================== КЛАВИАТУРЫ ====================


def get_main_menu() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🏠 Профиль", callback_data="menu_balance")],
            [InlineKeyboardButton(text="💼 Бизнесы", callback_data="menu_business")],
            [InlineKeyboardButton(text="📊 Рынок", callback_data="menu_market")],
            [InlineKeyboardButton(text="🎁 Магазин", callback_data="menu_shop")],
            [InlineKeyboardButton(text="🔝 Топ", callback_data="menu_top")],
            [InlineKeyboardButton(text="👥 Рефералы", callback_data="menu_referrals")],
        ]
    )


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
                    text=f"⚡ Буст x2 ({config.BOOST_1H_COST}⭐)",
                    callback_data="buy_boost",
                )
            ],
            [
                InlineKeyboardButton(
                    text=f"🛡️ Щит ({config.SHIELD_COST}⭐)", callback_data="buy_shield"
                )
            ],
            [
                InlineKeyboardButton(
                    text=f"🔮 Инсайдер ({config.INSIDER_COST}⭐)",
                    callback_data="buy_insider",
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
    await message.answer(welcome, reply_markup=get_main_menu())


# ==================== ПРОФИЛЬ (С ЭНЕРГИЕЙ) ====================


@router.callback_query(F.data == "menu_balance")
async def menu_balance(callback: CallbackQuery):
    user_id = callback.from_user.id
    user = db.get_user(user_id)

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

    # Если энергия кончилась - показываем меню покупки
    if energy_status["current"] < config.MIN_ENERGY_TO_WORK:
        await callback.message.edit_text(text, reply_markup=get_no_energy_menu())
    else:
        await callback.message.edit_text(text, reply_markup=get_main_menu())

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
        await callback.message.edit_text(
            f"⬆️ <b>Апгрейд!</b>\n\n"
            f"{biz_config.get('name', biz['business_type'])} → Ур.{biz['level']}\n"
            f"💵 Потрачено: ${cost:.2f}",
            reply_markup=get_main_menu(),
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
    vip = "⭐ Активен" if db.check_vip(user_id) else "❌ Неактивен"
    boost = "⚡ Активен" if db.check_boost(user_id) else "❌ Неактивен"
    shields = db.get_item(user_id, "shield")

    text = f"""🎁 <b>Магазин</b>

💰 Баланс: ${balance:.2f}
{vip} | {boost}
🛡️ Щитов: {shields}
"""

    await callback.message.edit_text(text, reply_markup=get_shop_menu())
    await callback.answer()


@router.callback_query(F.data == "buy_vip")
async def buy_vip(callback: CallbackQuery):
    user_id = callback.from_user.id

    if db.check_vip(user_id):
        await callback.answer("⭐ VIP уже активен!", show_alert=True)
        return

    # TODO: Telegram Stars интеграция
    db.set_vip(user_id, config.VIP_DURATION_DAYS)

    await callback.message.edit_text(
        f"⭐ <b>VIP активирован!</b>\n\n"
        f"⏱️ На {config.VIP_DURATION_DAYS} дней\n"
        f"📈 +{config.VIP_PRODUCTION_BONUS * 100}% к производству\n"
        f"⚡ -{config.VIP_ENERGY_DISCOUNT * 100}% к расходу энергии",
        reply_markup=get_shop_menu(),
    )
    await callback.answer("✅ VIP активирован!", show_alert=True)


@router.callback_query(F.data == "buy_boost")
async def buy_boost(callback: CallbackQuery):
    user_id = callback.from_user.id

    # TODO: Telegram Stars интеграция
    db.set_boost(user_id, 1)

    await callback.message.edit_text(
        "⚡ <b>Буст активирован!</b>\n\n📈 x2 к производству на 1 час",
        reply_markup=get_shop_menu(),
    )
    await callback.answer("✅ Буст активен!", show_alert=True)


@router.callback_query(F.data == "buy_shield")
async def buy_shield(callback: CallbackQuery):
    user_id = callback.from_user.id

    # TODO: Telegram Stars интеграция
    db.add_item(user_id, "shield", 1)
    shields = db.get_item(user_id, "shield")

    await callback.message.edit_text(
        f"🛡️ <b>Щит куплен!</b>\n\n🛡️ Количество: {shields}", reply_markup=get_shop_menu()
    )
    await callback.answer("🛡️ Щит куплен!", show_alert=True)


@router.callback_query(F.data == "buy_insider")
async def buy_insider(callback: CallbackQuery):
    user_id = callback.from_user.id

    # TODO: Telegram Stars интеграция
    preview = EventService.get_next_event_preview()

    await callback.message.edit_text(preview, reply_markup=get_shop_menu())
    await callback.answer("🔮 Инсайдерская информация!", show_alert=True)


# ==================== ЭНЕРГИЯ ====================


@router.callback_query(F.data == "buy_energy_20")
async def buy_energy_20(callback: CallbackQuery):
    user_id = callback.from_user.id

    # TODO: Telegram Stars интеграция
    EnergyService.add_energy(user_id, 20)
    energy = EnergyService.get_user_energy_status(user_id)

    await callback.message.edit_text(
        f"⚡ <b>Энергия восстановлена!</b>\n\n"
        f"⚡ {energy['current']:.0f}/{energy['max']}",
        reply_markup=get_main_menu(),
    )
    await callback.answer("✅ +20 энергии!", show_alert=True)


@router.callback_query(F.data == "buy_energy_50")
async def buy_energy_50(callback: CallbackQuery):
    user_id = callback.from_user.id

    # TODO: Telegram Stars интеграция
    EnergyService.add_energy(user_id, 50)
    energy = EnergyService.get_user_energy_status(user_id)

    await callback.message.edit_text(
        f"🔥 <b>Супер энергия!</b>\n\n⚡ {energy['current']:.0f}/{energy['max']}",
        reply_markup=get_main_menu(),
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

    await callback.message.edit_text(text, reply_markup=get_main_menu())
    await callback.answer()


@router.callback_query(F.data == "menu_referrals")
async def menu_referrals(callback: CallbackQuery):
    user_id = callback.from_user.id
    referrals = db.get_referrals(user_id)
    count = len(referrals)

    try:
        bot_username = (await callback.bot.get_me()).username
    except:
        bot_username = "YourBot"

    text = f"""👥 <b>Рефералы</b>

👥 Приглашено: {count}
💰 Бонус за друга: ${config.REFERRAL_BONUS}

📎 Ваша ссылка:
https://t.me/{bot_username}?start={user_id}
"""

    await callback.message.edit_text(text, reply_markup=get_main_menu())
    await callback.answer()


# ==================== ЧАТ-КОМАНДЫ ====================


@router.message(F.chat.type != "private", F.text.startswith("/мой_баланс"))
async def chat_balance(message: Message):
    user_id = message.from_user.id
    balance = db.get_balance(user_id)
    energy, max_e = db.get_energy(user_id)

    bar = EnergyService.get_energy_bar(energy, max_e)
    await message.reply(
        f"💰 {message.from_user.first_name}: ${balance:.2f}\n{bar} ⚡{energy:.0f}/{max_e}"
    )


@router.message(F.chat.type != "private", F.text.startswith("/мой_бизнес"))
async def chat_business(message: Message):
    user_id = message.from_user.id
    businesses = db.get_user_businesses(user_id)

    if not businesses:
        await message.reply("🏢 У вас нет бизнесов!")
        return

    text = "🏢 <b>Ваши бизнесы:</b>\n"
    for biz in businesses:
        biz_config = config.BUSINESSES.get(biz["business_type"], {})
        text += f"• {biz_config.get('name', biz['business_type'])} Ур.{biz['level']}\n"

    await message.reply(text)


@router.message(F.chat.type != "private", F.text.startswith("/рынок"))
async def chat_market(message: Message):
    text = MarketService.get_market_overview()
    await message.reply(text)


@router.message(F.chat.type != "private", F.text.startswith("/топ"))
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
    match = re.match(r"^/отправить\s*@?(\w+)\s*(\d+(?:\.\d+)?)", message.text)
    if not match:
        await message.reply("❌ Формат: /отправить @username сумма")
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

    success, result = db.transfer_money(from_user, to_user, amount, message.chat.id)

    if success:
        await message.reply(
            f"✅ {message.from_user.first_name} → @{username}: ${amount:.2f}"
        )
    else:
        await message.reply(f"❌ {result}")


# ==================== НАВИГАЦИЯ ====================


@router.callback_query(F.data == "menu_main")
async def menu_main(callback: CallbackQuery):
    await callback.message.edit_text(
        "📋 <b>Главное меню:</b>", reply_markup=get_main_menu()
    )
    await callback.answer()
