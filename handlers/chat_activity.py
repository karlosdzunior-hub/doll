"""
Обработчики событий чата для системы активности.
Регистрация чатов, реакция на добавление бота, отслеживание активности.
"""
import logging
from aiogram import Router, F, Bot
from aiogram.types import ChatMemberUpdated, Message
from aiogram.enums import ChatType
from aiogram.filters import Command
from aiogram.filters.chat_member_updated import ChatMemberUpdatedFilter, IS_NOT_MEMBER, IS_MEMBER
from db import db
from services.activity import activity_tracker, ActivityService
from config import config

logger = logging.getLogger(__name__)
router = Router()


# ==================== РЕГИСТРАЦИЯ ЧАТОВ ====================

@router.my_chat_member(ChatMemberUpdatedFilter(IS_NOT_MEMBER >> IS_MEMBER))
async def bot_added_to_chat(event: ChatMemberUpdated, bot: Bot):
    """
    Обработчик добавления бота в чат.
    Срабатывает когда бот становится участником чата.
    """
    chat = event.chat
    from_user = event.from_user

    # Регистрируем чат в БД
    db.create_or_update_chat(
        chat_id=chat.id,
        chat_type=chat.type,
        title=chat.title,
        added_by=from_user.id if from_user else None
    )

    # Добавляем бота в чат-юзеры
    db.add_user_to_chat(chat.id, bot.id)

    # Записываем активность
    activity_tracker.record_activity(chat.id)

    logger.info(f"📢 Бот добавлен в чат: {chat.title} ({chat.id})")

    # Отправляем приветственное сообщение
    welcome_message = (
        f"👋 Привет! Я бот игры «Микрокапитализм: Жизнь на 1 доллар»!\n\n"
        f"🎮 Начните игру командой /start\n"
        f"📊 Команды для группы:\n"
        f"  /balance - ваш баланс\n"
        f"  /market - рынок ресурсов\n"
        f"  /jackpot - джекпот\n"
        f"  /lottery - лотерея\n"
        f"  /top - топ игроков\n\n"
        f"⚡ Чат получил +{config.ADD_BOT_ENERGY_BONUS} энергии и {config.ADD_BOT_LOTTERY_TICKET} билет джекпота!"
    )

    try:
        await bot.send_message(chat.id, welcome_message)
    except Exception as e:
        logger.warning(f"Не удалось отправить приветствие в чат {chat.id}: {e}")

    # Выдаём бонусы всем участникам чата
    await give_chat_bonus(chat.id, bot)


async def give_chat_bonus(chat_id: int, bot: Bot):
    """Выдать бонусы за добавление бота."""
    # Проверяем, не получал ли чат бонус
    if db.has_claimed_bonus(chat_id):
        return

    db.claim_chat_bonus(chat_id)

    # Выдаём энергию и билеты всем участникам
    chat_users = db.get_chat_users(chat_id)
    for user_row in chat_users:
        user_id = user_row["user_id"]
        if user_id == bot.id:
            continue

        # Добавляем энергию
        from services.energy import EnergyService
        EnergyService.add_energy(user_id, config.ADD_BOT_ENERGY_BONUS)

        # Добавляем билет джекпота
        db.add_jackpot_tickets(user_id, config.ADD_BOT_LOTTERY_TICKET)

        # Добавляем пользователя в чат
        db.add_user_to_chat(chat_id, user_id)


# ==================== ОТслеживание активности ====================

@router.message()
async def track_message_activity(message: Message):
    """
    Отслеживание активности в чате.
    Записывает каждое сообщение для системы активности.
    """
    chat = message.chat
    user = message.from_user

    # Работаем только в группах и супергруппах
    if chat.type not in (ChatType.GROUP, ChatType.SUPERGROUP):
        return

    # Игнорируем сообщения ботов
    if user.is_bot:
        return

    # Записываем активность
    activity_tracker.record_activity(chat.id, user.id)
    activity_tracker.record_message(chat.id)

    # Добавляем XP чату за активность
    from services.chat import ChatService
    leveled_up = False
    new_level = 0

    try:
        # Убедимся, что чат зарегистрирован
        if not db.get_chat(chat.id):
            db.create_or_update_chat(chat.id, chat.type, chat.title)

        # Добавляем пользователя в чат
        db.add_user_to_chat(chat.id, user.id)

        # Добавляем XP
        _, leveled_up, new_level = ChatService.add_xp_for_action(chat.id, "command")

    except Exception as e:
        logger.warning(f"Ошибка при добавлении XP чату {chat.id}: {e}")

    # Если чат повысил уровень — отправляем уведомление
    if leveled_up:
        await handle_chat_level_up(chat.id, new_level, bot)


# ==================== ПОВЫШЕНИЕ УРОВНЯ ЧАТА ====================

async def handle_chat_level_up(chat_id: int, new_level: int, bot: Bot):
    """Обработка повышения уровня чата."""
    chat = db.get_chat(chat_id)
    if not chat:
        return

    # Получаем бонусы
    bonuses = db.get_chat_bonus(chat_id)

    # Формируем сообщение
    message = ActivityService.get_level_up_message(
        new_level=new_level,
        energy_bonus=config.CHAT_LEVEL_UP_ENERGY_BONUS
    )

    try:
        await bot.send_message(chat_id, message)
        logger.info(f"🏆 Чат {chat_id} повысил уровень до {new_level}")
    except Exception as e:
        logger.warning(f"Не удалось отправить уведомление о уровне чата {chat_id}: {e}")


# ==================== КОМАНДЫ ЧАТА ====================

@router.message(Command("chat"))
async def chat_stats_command(message: Message):
    """Показать статистику чата."""
    chat = message.chat

    if chat.type not in (ChatType.GROUP, ChatType.SUPERGROUP):
        await message.answer("📊 Статистика чата доступна только в группах!")
        return

    stats = ChatService.get_chat_stats(chat.id)

    if not stats:
        await message.answer("❌ Чат не найден в базе данных!")
        return

    response = (
        f"📊 **Статистика чата**\n\n"
        f"📛 Название: {stats['title']}\n"
        f"🏆 Уровень: {stats['level']}\n"
        f"⭐ XP: {stats['xp']} / {stats['xp_needed']}\n"
        f"📈 Прогресс: {stats['progress']:.1f}%\n\n"
        f"🎁 **Бонусы:**\n"
        f"  • К доходу: +{stats['bonuses']['income_bonus']*100:.0f}%\n"
        f"  • К энергии: -{stats['bonuses']['energy_discount']*100:.0f}%\n"
        f"  • К джекпоту: +{stats['bonuses']['jackpot_chance_bonus']*100:.0f}%\n"
        f"  • Бесплатных билетов: {stats['bonuses']['free_tickets']}\n"
    )

    await message.answer(response)


@router.message(Command("topchats"))
async def top_chats_command(message: Message):
    """Показать топ чатов."""
    chats = db.get_top_chats(10)

    if not chats:
        await message.answer("❌ Пока нет активных чатов!")
        return

    response = "🏆 **Топ чатов по уровням**\n\n"

    for i, chat in enumerate(chats, 1):
        medal = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else f"{i}."
        response += f"{medal} {chat['title'] or 'Чат'} — ур. {chat['level']} ({chat['xp']} XP)\n"

    await message.answer(response)

