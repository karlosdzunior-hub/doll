"""
Production Telegram бот "Микрокапитализм: Жизнь на 1 доллар"
v2.0 — система удержания, джекпот, кредиты, уведомления
"""

import logging
import asyncio
from datetime import datetime

from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
from aiogram.types import BotCommand, BotCommandScopeAllPrivateChats, BotCommandScopeAllGroupChats, ErrorEvent
from aiogram.exceptions import TelegramBadRequest

from config import config
from handlers import router
from services import EnergyService, MarketService, EventService, JackpotService, CreditService, NotificationService

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

bot = Bot(token=config.TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher()
dp.include_router(router)


@dp.errors()
async def global_error_handler(event: ErrorEvent):
    exc = event.exception
    if isinstance(exc, TelegramBadRequest):
        msg = str(exc).lower()
        if any(x in msg for x in [
            "query is too old",
            "query id is invalid",
            "message is not modified",
            "message to edit not found",
            "message can't be deleted",
        ]):
            return True
    logger.error(f"Unhandled error: {exc}", exc_info=exc)
    return True

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
    """Розыгрыш джекпота каждые 6 часов + countdown уведомления."""
    from db import db as _db

    logger.info("🎰 Задача джекпота запущена")

    # Отслеживаем отправленные countdown-уведомления: ключ = (draw_time_iso, label)
    countdown_sent: set = set()

    while not shutdown_event.is_set():
        try:
            await asyncio.sleep(60)  # проверяем каждую минуту
            if shutdown_event.is_set():
                break

            next_draw = JackpotService.get_next_draw_time(_db)
            now = datetime.now()
            seconds_left = (next_draw - now).total_seconds()
            draw_key = next_draw.strftime("%Y%m%d%H%M")

            # --- Countdown уведомления участникам ---
            participants = _db.get_jackpot_participants()
            bank = _db.get_jackpot_bank()

            for threshold, label, emoji in [
                (600, "10min", "⏰"),
                (120, "2min", "⚡"),
                (30,  "30sec", "🚨"),
            ]:
                key = (draw_key, label)
                if 0 < seconds_left <= threshold and key not in countdown_sent:
                    countdown_sent.add(key)
                    time_str = JackpotService.time_until_draw(_db)
                    text = (
                        f"{emoji} <b>Джекпот через {time_str}!</b>\n\n"
                        f"💰 Банк: <b>${bank:.2f}</b>\n"
                        f"🎫 У вас есть билеты — удача ждёт!\n\n"
                        f"Ещё билеты: /джекпот"
                    )
                    for p in participants:
                        try:
                            await bot.send_message(p["user_id"], text)
                        except Exception:
                            pass

            # --- Розыгрыш ---
            if now >= next_draw:
                result = JackpotService.run_draw(_db)
                if result:
                    logger.info(f"🎰 Джекпот! Победитель: {result['winner_id']}, приз: ${result['prize']:.2f}")

                    winner_id = result["winner_id"]
                    prize = result["prize"]
                    winner_name = result["winner_name"]
                    total_tickets = result["total_tickets"]

                    # Победителю — победное сообщение
                    try:
                        await bot.send_message(
                            winner_id,
                            f"🏆 <b>ВЫ ВЫИГРАЛИ ДЖЕКПОТ!</b>\n\n"
                            f"💰 Выигрыш: <b>${prize:.2f}</b>!\n"
                            f"🎉 Поздравляем! Вы лучший капиталист!\n\n"
                            f"💵 Деньги уже на балансе: /баланс"
                        )
                    except Exception:
                        pass

                    # Остальным — "почти выиграл" / проигрыш
                    for p in participants:
                        uid = p["user_id"]
                        if uid == winner_id:
                            continue
                        tickets = p["tickets"]
                        chance_pct = round(tickets / total_tickets * 100, 1) if total_tickets > 0 else 0
                        if chance_pct >= 10:
                            near_miss_text = (
                                f"😱 <b>Почти!</b>\n\n"
                                f"Победил @{winner_name} с ${prize:.0f}...\n"
                                f"Вы были в {chance_pct}% от выигрыша!\n\n"
                                f"🎫 Следующий розыгрыш — через 6 часов\n"
                                f"Купи больше билетов: /джекпот"
                            )
                        else:
                            near_miss_text = (
                                f"🎰 Розыгрыш завершён!\n\n"
                                f"Победил @{winner_name} — ${prize:.0f}\n"
                                f"🎫 Следующий через 6ч — участвуй: /джекпот"
                            )
                        try:
                            await bot.send_message(uid, near_miss_text)
                        except Exception:
                            pass
                else:
                    logger.info("🎰 Розыгрыш: нет участников, пропуск")

                # Чистим старые countdown-ключи
                countdown_sent = {k for k in countdown_sent if k[0] != draw_key}

        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.error(f"❌ Ошибка задачи джекпота: {e}")


async def debt_check_task():
    """Проверка долгов и начисление пеней каждый час."""
    from db import db as _db

    logger.info("💳 Задача долгов запущена")

    # Отслеживаем порог банка для уведомлений ($50, $100, $150 ...)
    last_notified_bank_threshold = 0

    while not shutdown_event.is_set():
        try:
            await asyncio.sleep(config.DEBT_CHECK_INTERVAL)
            if shutdown_event.is_set():
                break

            # Начисляем пени за просроченные кредиты
            count = CreditService.apply_interest(_db)
            if count > 0:
                logger.info(f"💳 Начислены пени: {count} должников")

            bank = _db.get_jackpot_bank()
            time_left = JackpotService.time_until_draw(_db)

            # --- Уведомляем должников ---
            debtors = _db.get_users_with_overdue_credits()
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

            # --- Уведомляем о отрицательном балансе ---
            all_users = _db.get_all_users_energy()
            for u in all_users:
                uid = u["user_id"]
                balance = _db.get_balance(uid)
                if balance < 0:
                    try:
                        msg = NotificationService.format_negative_balance(balance)
                        await bot.send_message(uid, msg)
                    except Exception:
                        pass

            # --- Уведомляем участников о росте банка ---
            current_threshold = int(bank // 50) * 50
            if bank > 50 and current_threshold > last_notified_bank_threshold:
                last_notified_bank_threshold = current_threshold
                participants = _db.get_jackpot_participants()
                if participants:
                    grow_text = NotificationService.format_jackpot_growing(
                        bank, time_left, config.JACKPOT_TICKET_COST
                    )
                    for p in participants:
                        try:
                            await bot.send_message(p["user_id"], grow_text)
                        except Exception:
                            pass
                    logger.info(f"🎰 Уведомление о росте банка ${bank:.2f} отправлено {len(participants)} участникам")

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

            energy_stats = EnergyService.process_energy_tick()
            logger.info(f"⚡ Энергия: {energy_stats['users_processed']} игроков")

            prod_stats = process_production_tick()
            logger.info(f"💰 Доход: {prod_stats['users_produced']} игроков, +${prod_stats['total_income']}")

            market_stats = MarketService.process_market_tick()
            logger.info(f"📊 Рынок: {market_stats['npc_trades']} NPC-сделок")

            if tick_count % 6 == 0:
                event = EventService.trigger_random_event()
                logger.info(f"🌍 Событие: {event['name']}")

        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.error(f"❌ Ошибка в фоновых задачах: {e}")

    logger.info("🛑 Фоновые задачи завершены")


async def onboarding_reminder_task():
    """Отправляет напоминание о пассивном доходе через 10 минут после регистрации."""
    from handlers.main import NEW_USERS
    from db import db as _db

    logger.info("📩 Задача онбординг-напоминаний запущена")

    while not shutdown_event.is_set():
        try:
            await asyncio.sleep(60)
            if shutdown_event.is_set():
                break

            now = datetime.now()
            to_notify = [
                uid for uid, joined_at in list(NEW_USERS.items())
                if (now - joined_at).total_seconds() >= 600
            ]

            for user_id in to_notify:
                NEW_USERS.pop(user_id, None)
                user = _db.get_user(user_id)
                businesses = _db.get_user_businesses(user_id)
                balance = _db.get_balance(user_id)

                if businesses:
                    income_per_hour = sum(
                        config.BUSINESSES[b["business_type"]]["income_per_hour"]
                        for b in businesses
                        if b["business_type"] in config.BUSINESSES
                    )
                    text = (
                        f"💰 <b>Пассивный доход работает!</b>\n\n"
                        f"За 10 минут ваши бизнесы принесли доход!\n"
                        f"📈 Доход: <b>${income_per_hour / 6:.2f}</b> за эти 10 минут\n"
                        f"💵 Баланс сейчас: <b>${balance:.2f}</b>\n\n"
                        f"🚀 Покупай ещё бизнесы → /магазин\n"
                        f"🎰 Джекпот ждёт тебя → /джекпот"
                    )
                else:
                    text = (
                        f"💡 <b>Подсказка!</b>\n\n"
                        f"Ты ещё не купил бизнес.\n"
                        f"Купи Лимонадную за $50 и деньги начнут работать сами!\n\n"
                        f"🍋 Купить бизнес → /магазин\n"
                        f"💵 Баланс: <b>${balance:.2f}</b>"
                    )
                try:
                    await bot.send_message(user_id, text)
                except Exception:
                    pass

        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.error(f"❌ Ошибка онбординг-задачи: {e}")

    logger.info("🛑 Онбординг-задача завершена")


async def on_startup():
    """Действия при запуске"""
    logger.info("🚀 Бот запускается...")

    try:
        me = await bot.get_me()
        logger.info(f"✅ Бот: @{me.username}")
    except Exception as e:
        logger.error(f"❌ Ошибка получения info бота: {e}")

    private_commands = [
        BotCommand(command="start",      description="🎮 Начать игру"),
        BotCommand(command="balance",    description="💰 Мой баланс"),
        BotCommand(command="business",   description="🏭 Мои бизнесы"),
        BotCommand(command="shop",       description="🛒 Купить бизнес/энергию"),
        BotCommand(command="jackpot",    description="🎰 Джекпот"),
        BotCommand(command="lottery",    description="🎲 Лотерея"),
        BotCommand(command="credit",     description="💳 Взять кредит"),
        BotCommand(command="repay",      description="💸 Погасить кредит"),
        BotCommand(command="bankrupt",   description="🏳️ Объявить банкротство"),
        BotCommand(command="profile",    description="👤 Мой профиль"),
        BotCommand(command="top",        description="🏆 Таблица лидеров"),
        BotCommand(command="help",       description="❓ Помощь"),
    ]

    group_commands = [
        BotCommand(command="balance",   description="💰 Мой баланс"),
        BotCommand(command="business",  description="🏭 Мои бизнесы"),
        BotCommand(command="market",    description="📊 Рынок"),
        BotCommand(command="jackpot",   description="🎰 Джекпот"),
        BotCommand(command="lottery",   description="🎲 Лотерея"),
        BotCommand(command="top",       description="🏆 Топ игроков"),
        BotCommand(command="send",      description="💸 Отправить деньги"),
        BotCommand(command="chatlevel", description="📈 Уровень чата"),
        BotCommand(command="topchats",  description="🏆 Топ чатов"),
    ]

    try:
        await bot.set_my_commands(private_commands, scope=BotCommandScopeAllPrivateChats())
        await bot.set_my_commands(group_commands, scope=BotCommandScopeAllGroupChats())
        logger.info("✅ Команды зарегистрированы")
    except Exception as e:
        logger.error(f"❌ Ошибка регистрации команд: {e}")

    asyncio.create_task(background_tasks())
    asyncio.create_task(jackpot_draw_task())
    asyncio.create_task(debt_check_task())
    asyncio.create_task(onboarding_reminder_task())
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
║   🎮 МИКРОКАПИТАЛИЗМ: ЖИЗНЬ НА 1 ДОЛЛАР   ║
║                                              ║
║   💰 Старт: $100 + 20 энергии + 1 билет    ║
║   🎰 Джекпот каждые 6 часов                 ║
║   💳 Система кредитов с пенями              ║
║   ⚡ Балансированная экономика              ║
╚══════════════════════════════════════════════╝
    """)
    asyncio.run(main())
