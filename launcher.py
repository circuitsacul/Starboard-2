import asyncio

from app import main


loop = asyncio.get_event_loop()

try:
    loop.run_until_complete(main.run())
except KeyboardInterrupt:
    pass
except Exception as e:
    raise e from e
finally:
    print("Bot logged out.")
