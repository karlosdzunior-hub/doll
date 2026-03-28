""" Handlers package - обработчики команд и событий """
from .main import router
from .chat_activity import router as chat_activity_router

# Подключаем роутер активности к основному
router.include_router(chat_activity_router)

__all__ = ["router"]
