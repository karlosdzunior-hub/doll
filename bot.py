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


async def background_tasks():
    """
    Фоновые задачи:
    - Обновление энергии каждые 5 минут
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

            # 2. Обновление рынка + NPC
            market_stats = MarketService.process_market_tick()
            logger.info(f"📊 Рынок: NPC совершил {market_stats['npc_trades']} сделок")

            # 3. События (каждые 6 тиков = 30 минут)
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
