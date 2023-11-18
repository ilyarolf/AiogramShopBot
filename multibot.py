from aiogram import Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage

multibot_dispatcher = Dispatcher(storage=MemoryStorage())
