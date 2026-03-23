"""
Production Telegram бот "Микрокапитализм: Жизнь на 1 доллар"
Система энергии, фоновые задачи, монетизация
"""

import logging
import asyncio
from datetime import datetime

from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
from aiogram.types import BotCommand, BotCommandScopeAllPrivateChats, BotCommandScopeAllGroupChats

from config import config
from handlers import router
from services import EnergyService, MarketService, EventService

# Логирование
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Инициализация бота
bot = Bot(token=config.TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))

# Диспетчер с роутерами
dp = Dispatcher()

# Подключение обработчиков
dp.include_router(router)

# Глобальные переменные для задач
shutdown_event = asyncio.Event()


def process_production_tick():
    """
    Начисление ресурсов от бизнесов каждые 5 минут.
    Бизнесы работают только если энергия >= MIN_ENERGY_TO_WORK.
    """
    from db import db as _db

    users = _db.get_all_users_energy()
    total_users = 0
    total_resources = 0

    for user_data in users:
        user_id = user_data["user_id"]
        energy = user_data["energy"]

        # Бизнесы работают только при достаточной энергии
        if energy < config.MIN_ENERGY_TO_WORK:
            continue

        production = _db.get_total_production(user_id)
        if not production:
            continue

        # Производство за 5 минут = ставка_в_час / 12
        for resource_type, rate_per_hour in production.items():
            amount = rate_per_hour / 12
            if amount > 0:
                _db.update_user_resource(user_id, resource_type, amount)
                total_resources += amount

        total_users += 1

    return {"users_produced": total_users, "total_resources": round(total_resources, 2)}


async def background_tasks():
    """
    Фоновые задачи:
    - Обновление энергии каждые 5 минут
    - Начисление ресурсов от бизнесов каждые 5 минут
    - Обновление рынка + NPC
    - Случайные события
    """
    logger.info("🔄 Фоновые задачи запущены")

    tick_count = 0

    while not shutdown_event.is_set():
        try:
            # Ожидаем интервал
            await asyncio.sleep(config.TICK_INTERVAL)

            if shutdown_event.is_set():
                break

            tick_count += 1
            logger.info(f"📊 Тик #{tick_count} ({datetime.now().strftime('%H:%M')})")

            # 1. Обновление энергии
            energy_stats = EnergyService.process_energy_tick()
            logger.info(
                f"⚡ Энергия: {energy_stats['users_processed']} игроков, "
                f"{energy_stats['out_of_energy']} с 0 энергии"
            )

            # 2. Начисление ресурсов от бизнесов
            prod_stats = process_production_tick()
            logger.info(
                f"🏭 Производство: {prod_stats['users_produced']} игроков, "
                f"+{prod_stats['total_resources']} ресурсов"
            )

            # 3. Обновление рынка + NPC
            market_stats = MarketService.process_market_tick()
            logger.info(f"📊 Рынок: NPC совершил {market_stats['npc_trades']} сделок")

            # 4. События (каждые 6 тиков = 30 минут)
            if tick_count % 6 == 0:
                event = EventService.trigger_random_event()
                logger.info(f"🌍 Событие: {event['name']} - {event['message']}")

            logger.info(f"✅ Тик #{tick_count} завершён")

        except asyncio.CancelledError:
            logger.info("⏹️ Фоновые задачи остановлены")
            break
        except Exception as e:
            logger.error(f"❌ Ошибка в фоновых задачах: {e}")

    logger.info("🛑 Фоновые задачи завершены")


async def on_startup():
    """Действия при запуске"""
    logger.info("🚀 Бот запускается...")

    try:
        me = await bot.get_me()
        logger.info(f"✅ Бот @{me.username} (ID: {me.id}) запущен!")
    except Exception as e:
        logger.error(f"❌ Не удалось получить информацию о боте: {e}")

    # Команды для личных чатов
    private_commands = [
        BotCommand(command="start", description="🎮 Открыть главное меню"),
    ]

    # Команды для групповых чатов (только латиница — требование Telegram)
    group_commands = [
        BotCommand(command="balance", description="💰 Мой баланс"),
        BotCommand(command="business", description="🏭 Мои бизнесы"),
        BotCommand(command="market", description="📊 Рынок ресурсов"),
        BotCommand(command="top", description="🏆 Топ игроков"),
        BotCommand(command="chatlevel", description="⭐ Уровень чата"),
        BotCommand(command="topchats", description="🌍 Топ чатов"),
        BotCommand(command="lottery", description="🎰 Лотерея"),
        BotCommand(command="jackpot", description="💎 Джекпот чата"),
        BotCommand(command="send", description="💸 Перевод (напр: /send @user 10)"),
    ]

    try:
        await bot.set_my_commands(private_commands, scope=BotCommandScopeAllPrivateChats())
        await bot.set_my_commands(group_commands, scope=BotCommandScopeAllGroupChats())
        logger.info("✅ Команды зарегистрированы")
    except Exception as e:
        logger.error(f"❌ Ошибка регистрации команд: {e}")

    # Запускаем фоновые задачи
    asyncio.create_task(background_tasks())


async def on_shutdown():
    """Действия при остановке"""
    logger.info("🛑 Бот останавливается...")
    shutdown_event.set()
    await asyncio.sleep(1)  # Даём время задачам завершиться
    await bot.session.close()
    logger.info("✅ Бот остановлен")


async def main():
    """Главная функция"""
    dp.startup.register(on_startup)
    dp.shutdown.register(on_shutdown)

    try:
        logger.info("📡 Запуск polling...")
        await dp.start_polling(bot)
    except KeyboardInterrupt:
        logger.info("⛔ Прервано пользователем")
    except Exception as e:
        logger.error(f"❌ Критическая ошибка: {e}")
    finally:
        shutdown_event.set()
        await bot.session.close()


if __name__ == "__main__":
    print("""
╔══════════════════════════════════════════════╗
║   🎮 МИКРОКАПИТАЛИЗМ: ЖИЗНЬ НА 1 ДОЛЛАР   ║
║                                              ║
║   ⚡ Система энергии                         ║
║   📊 Динамический рынок                      ║
║   ⭐ Монетизация через Stars                  ║
║   🌍 Глобальные события                       ║
╚══════════════════════════════════════════════╝
    """)
    asyncio.run(main())
