""" Production Telegram бот "Микрокапитализм: Жизнь на 1 доллар" v2.0 — система удержания, джекпот, кредиты, уведомления """
import logging
import asyncio
from datetime import datetime
from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
from aiogram.types import BotCommand, BotCommandScopeAllPrivateChats, BotCommandScopeAllGroupChats
from config import config
from handlers import router
from services import (
    EnergyService, MarketService, EventService, JackpotService,
    CreditService, NotificationService, init_activity_manager, start_activity_tasks
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

bot = Bot(token=config.TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher()
dp.include_router(router)
shutdown_event = asyncio.Event()

def process_production_tick():
    """Начисление дохода от бизнесов каждые 5 минут."""
    from db import db as _db
    users = _db.get_all_users_energy()
    total_users = 0
    total_income = 0
    for user_data in users:
        user_id = user_data["user_id"]
        energy = user_data["energy"]
        if energy < config.MIN_ENERGY_TO_WORK:
            continue
        businesses = _db.get_user_businesses(user_id)
        if not businesses:
            continue
        income_5min = 0.0
        for biz in businesses:
            biz_type = biz["business_type"]
            if biz_type in config.BUSINESSES:
                biz_cfg = config.BUSINESSES[biz_type]
                # Доход за 5 минут = доход/час / 12
                income_5min += biz_cfg["income_per_hour"] / 12
        if income_5min > 0:
            _db.update_balance(user_id, income_5min)
            total_income += income_5min
            total_users += 1
    return {"users_produced": total_users, "total_income": round(total_income, 2)}

async def jackpot_draw_task():
    """Розыгрыш джекпота каждые 6 часов."""
    from db import db as _db
    logger.info("🎰 Задача джекпота запущена")
    interval = config.JACKPOT_INTERVAL_HOURS * 3600
    while not shutdown_event.is_set():
        try:
            await asyncio.sleep(60)  # проверяем каждую минуту
            if shutdown_event.is_set():
                break
            next_draw = JackpotService.get_next_draw_time(_db)
            if datetime.now() >= next_draw:
                result = JackpotService.run_draw(_db)
                if result:
                    logger.info(f"🎰 Джекпот! Победитель: {result['winner_id']}, приз: ${result['prize']:.2f}")
                    # Уведомляем всех участников
                    participants = _db.get_jackpot_participants()
                    try:
                        # Победителю
                        await bot.send_message(result["winner_id"], result["message"])
                    except Exception as e:
                        logger.warning(f"Не удалось отправить уведомление победителю: {e}")
                else:
                    logger.info("🎰 Розыгрыш: нет участников, пропуск")
        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.error(f"❌ Ошибка задачи джекпота: {e}")

async def debt_check_task():
    """Проверка долгов и начисление пеней каждый час."""
    from db import db as _db
    logger.info("💳 Задача долгов запущена")
    while not shutdown_event.is_set():
        try:
            await asyncio.sleep(config.DEBT_CHECK_INTERVAL)
            if shutdown_event.is_set():
                break
            # Начисляем пени за просроченные кредиты
            count = CreditService.apply_interest(_db)
            if count > 0:
                logger.info(f"💳 Начислены пени: {count} должников")
            # Уведомляем должников
            debtors = _db.get_users_with_overdue_credits()
            bank = _db.get_jackpot_bank()
            time_left = JackpotService.time_until_draw(_db)
            for user_id in debtors:
                credit = _db.get_active_credit(user_id)
                if credit:
                    debt = credit["repay_amount"] - credit["paid_amount"]
                    try:
                        msg = NotificationService.format_debt_critical(debt, bank) if debt > 500 \
                            else NotificationService.format_debt_warning(debt)
                        await bot.send_message(user_id, msg)
                    except Exception:
                        pass
            # Уведомляем о росте банка джекпота (если > $50)
            if bank > 50:
                logger.info(f"🎰 Банк джекпота: ${bank:.2f}, до розыгрыша: {time_left}")
        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.error(f"❌ Ошибка задачи долгов: {e}")

async def background_tasks():
    """
    Фоновые задачи:
    - Энергия каждые 5 минут
    - Доход от бизнесов каждые 5 минут
    - Рынок + NPC
    - Случайные события
    """
    logger.info("🔄 Фоновые задачи запущены")
    tick_count = 0
    while not shutdown_event.is_set():
        try:
            await asyncio.sleep(config.TICK_INTERVAL)
            if shutdown_event.is_set():
                break
            tick_count += 1
            logger.info(f"📊 Тик #{tick_count} ({datetime.now().strftime('%H:%M')})")
            
            # Каждые 5 мин: энергия
            energy_stats = EnergyService.process_energy_tick()
            logger.info(f"⚡ Энергия: {energy_stats['users_processed']} игроков")
            
            # Каждые 5 мин: денежный доход от бизнесов (старая логика)
            prod_stats = process_production_tick()
            logger.info(f"💰 Доход: {prod_stats['users_produced']} игроков, +${prod_stats['total_income']}")
            
            # Каждый час (12 тиков): производство ресурсов
            if tick_count % 12 == 0:
                from db import db as _db
                res_stats = _db.produce_resources_tick()
                logger.info(f"📦 Ресурсы: {res_stats['users']} игроков, {res_stats['produced']} ед.")
            
            # Каждые 30 мин (6 тиков): обновление NPC-цен
            if tick_count % 6 == 0:
                from db import db as _db
                _db.update_npc_prices()
                market_stats = MarketService.process_market_tick()
                logger.info(f"📊 Рынок: цены обновлены, {market_stats['npc_trades']} NPC-сделок")
            
            # Каждые ~90 мин (18 тиков): рыночное событие
            if tick_count % 18 == 0:
                import random
                if random.random() < 0.7:  # 70% шанс события
                    event = EventService.trigger_random_event()
                    logger.info(f"🌍 Событие: {event['name']}")
                    # Уведомляем активных игроков
                    try:
                        from db import db as _db
                        all_users = _db.get_all_users_energy()
                        notified = 0
                        for u in all_users[:50]:  # не более 50 уведомлений
                            try:
                                await bot.send_message(u["user_id"], f"🌍 Рыночное событие!\n\n{event['message']}\n\n"
                                                                    f"📊 Проверьте /рынок для актуальных цен")
                                notified += 1
                            except Exception:
                                pass
                        logger.info(f"🌍 Уведомлено {notified} игроков")
                    except Exception as e:
                        logger.warning(f"Ошибка уведомления о событии: {e}")
        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.error(f"❌ Ошибка в фоновых задачах: {e}")
    logger.info("🛑 Фоновые задачи завершены")

async def activity_tasks():
    """Запуск задач активности чатов."""
    logger.info("📢 Задачи активности чатов запущены")
    
    # Инициализируем менеджер активности
    init_activity_manager(bot)
    
    # Запускаем задачи
    await start_activity_tasks()

async def on_startup():
    """Действия при запуске"""
    logger.info("🚀 Бот запускается...")
    try:
        me = await bot.get_me()
        logger.info(f"✅ Бот: @{me.username}")
    except Exception as e:
        logger.error(f"❌ Ошибка получения info бота: {e}")
    
    private_commands = [
        BotCommand(command="start", description="🎮 Начать игру"),
        BotCommand(command="balance", description="💰 Мой баланс"),
        BotCommand(command="warehouse", description="📦 Мой склад"),
        BotCommand(command="market", description="📊 Рынок ресурсов"),
        BotCommand(command="sell", description="💸 Продать ресурс NPC"),
        BotCommand(command="buy", description="🛍️ Купить ресурс у NPC"),
        BotCommand(command="order", description="📋 Создать P2P ордер"),
        BotCommand(command="jackpot", description="🎰 Джекпот"),
        BotCommand(command="lottery", description="🎲 Лотерея"),
        BotCommand(command="credit", description="💳 Взять кредит"),
        BotCommand(command="repay", description="💸 Погасить кредит"),
        BotCommand(command="bankrupt", description="🏳️ Объявить банкротство"),
        BotCommand(command="top", description="🏆 Таблица лидеров"),
        BotCommand(command="help", description="❓ Помощь"),
    ]
    
    group_commands = [
        BotCommand(command="balance", description="💰 Мой баланс"),
        BotCommand(command="top", description="🏆 Топ игроков"),
        BotCommand(command="market", description="📊 Рынок"),
        BotCommand(command="jackpot", description="🎰 Джекпот"),
        BotCommand(command="lottery", description="🎲 Лотерея"),
        BotCommand(command="chat", description="📊 Статистика чата"),
        BotCommand(command="topchats", description="🏆 Топ чатов"),
    ]
    
    try:
        await bot.set_my_commands(private_commands, scope=BotCommandScopeAllPrivateChats())
        await bot.set_my_commands(group_commands, scope=BotCommandScopeAllGroupChats())
        logger.info("✅ Команды зарегистрированы")
    except Exception as e:
        logger.error(f"❌ Ошибка регистрации команд: {e}")
    
    # Запускаем фоновые задачи
    asyncio.create_task(background_tasks())
    asyncio.create_task(jackpot_draw_task())
    asyncio.create_task(debt_check_task())
    asyncio.create_task(activity_tasks())
    logger.info("✅ Все фоновые задачи запущены")

async def on_shutdown():
    """Действия при остановке"""
    logger.info("🛑 Бот останавливается...")
    shutdown_event.set()
    await asyncio.sleep(1)
    await bot.session.close()
    logger.info("✅ Бот остановлен")

async def main():
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
║ 🎮 МИКРОКАПИТАЛИЗМ: ЖИЗНЬ НА 1 ДОЛЛАР        ║
║                                              ║
║ 💰 Старт: $100 + 20 энергии + 1 билет        ║
║ 🎰 Джекпот каждые 6 часов                    ║
║ 💳 Система кредитов с пенями                 ║
║ ⚡ Балансированная экономика                 ║
║ 📢 АВТО-СООБЩЕНИЯ В ЧАТАХ                    ║
║ 🏆 УРОВНИ ЧАТОВ С БОНУСАМИ                   ║
╚══════════════════════════════════════════════╝
    """)
    asyncio.run(main())
