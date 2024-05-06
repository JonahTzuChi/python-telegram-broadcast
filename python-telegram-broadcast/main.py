import os
import asyncio

from typing import Any, Callable, Coroutine, Optional, Tuple, Union

import telegram

from .custom_dataclass import JobResponse
from .send_method import select_broadcast_method, BroadcastMethodType, BroadcastMethodTypeHint
from .strategy import select_broadcast_strategy, BroadcastStrategyType


async def get_file_id(
        bot_token: str, broadcast_method: BroadcastMethodTypeHint, dummy_user: int,
        content: str, caption: str, seconds: float, max_retry: int
) -> str:
    try:
        bot = telegram.Bot(token=bot_token)
        res: Union[telegram.Document, telegram.PhotoSize, telegram.Video] = await broadcast_method(
            bot, dummy_user, content, caption, seconds, seconds, max_retry
        )
        if seconds > 0:
            await asyncio.sleep(seconds)
        return res.file_id
    except Exception:
        raise


async def handle_broadcast(
        subscribers: list[Tuple[int, str]], bot_token: str, broadcast_method: BroadcastMethodType | BroadcastMethodTypeHint,
        broadcast_strategy: BroadcastStrategyType | Callable[
            [...], Coroutine[Any, Any, Tuple[list[JobResponse], list[JobResponse]]]
        ],
        content: str, caption: str, **configuration
) -> tuple[list[JobResponse], list[JobResponse]]:
    use_multiproc = configuration.get("use_multiproc", False)
    use_nproc = configuration.get("use_nproc", os.cpu_count())
    seconds = configuration.get("seconds", 0.0)
    max_retry = configuration.get("max_retry", 5)
    async_callback: Optional[Callable[[int], Coroutine[Any, Any, None]]] = configuration.get("async_callback", None)
    try:
        # Pick the appropriate broadcast method
        if type(broadcast_method) is BroadcastMethodType:
            broadcast_method = select_broadcast_method(broadcast_method)
        # Pick the appropriate broadcast strategy
        if type(broadcast_strategy) is BroadcastStrategyType:
            broadcast_strategy = select_broadcast_strategy(broadcast_strategy)
        return await broadcast_strategy().execute(
            subscribers=subscribers, bot_token=bot_token, method=broadcast_method, content=content, caption=caption,
            success_callback=async_callback, use_multiproc=use_multiproc, use_nproc=use_nproc,
            seconds=seconds, max_retry=max_retry
        )
    except Exception:
        raise
