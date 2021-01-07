import asyncio
import traceback

from app import bot


loop = asyncio.get_event_loop()

try:
    loop.run_until_complete(bot.run())
except KeyboardInterrupt:
    pass
except Exception as e:
    raise e from e
finally:
    print("Bot logged out.")
