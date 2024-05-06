import os
import asyncio
import traceback

import concurrent.futures
from functools import partial

from queue import Queue
from typing import Any, Callable, Coroutine, NoReturn, Optional, Tuple

import telegram

from .custom_dataclass import JobResponse, BroadcastMethodReturnType, BroadcastMethod, ErrorInformation
from .custom_util import group_by_result_list, group_by_result
from .send_method import select_broadcast_method


def broadcast_method_wrapper(
    method: BroadcastMethod,
    bot_token: str, target_id: int, payload: str, caption: str,
    seconds: float, max_retry: int
) -> BroadcastMethodReturnType:
    """
    This function is a wrapper for the broadcast method.
    It creates a new event loop, sets it as the current event loop,
    and then runs the broadcast method until it completes.
    The broadcast method is expected to be a coroutine function.

    Parameters:
    ----------
    - method (BroadcastMethod): Broadcast method to be called.
    - bot_token (str): The token of the Telegram bot.
    - target_id (int): The ID of the target to which the message will be sent.
    - payload (str): The payload to be sent.
    - caption (str): The caption for the payload.
    - seconds (float): The number of seconds to wait before sending the message.
    - max_retry (int): The maximum number of times to retry sending the message in case of failure.

    Returns:
    -------
    - BroadcastMethodReturnType: The return value of the broadcast method.

    Notes:
    ------
    - Unpack the exception object to get the ErrorInformation.
    """
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        my_bot = telegram.Bot(token=bot_token)
        return loop.run_until_complete(
            method(my_bot, target_id, payload, caption, seconds, 0, max_retry)
        )
    except Exception as error:
        return ErrorInformation(type(error).__name__, str(error), traceback.format_exc())


async def async_broadcast_sequentially(
        subscribers: list[Tuple[int, str]], bot_token: str, method: BroadcastMethod,
        content: str, caption: str,
        success_callback: Optional[Callable[[Any], Coroutine[Any, Any, NoReturn]]] = None,
        **configuration
) -> tuple[list[JobResponse], list[JobResponse]]:
    bot = telegram.Bot(token=bot_token)
    seconds: float = configuration.get("seconds", 0.0)
    max_retry: int = configuration.get("max_retry", 5)
    res_list: list[JobResponse] = []
    for telegram_id, username in subscribers:
        try:
            send_result = await method(
                bot, telegram_id, content, caption, seconds, 0, max_retry
            )
            res_list.append(JobResponse(telegram_id, username, content, send_result))
            if success_callback:
                await success_callback(telegram_id)
            if seconds > 0:
                await asyncio.sleep(seconds)  # Sleep for a short time to avoid overloading the CPU
        except Exception as error:
            error_info = ErrorInformation(
                type(error).__name__, str(error), traceback.format_exc()
            )
            res_list.append(JobResponse(telegram_id, username, content, error_info))

    sent_list, failed_list = group_by_result_list(res_list, is_apply_result=False)
    return sent_list, failed_list


async def async_broadcast_with_multiprocessing(
        subscribers: list[Tuple[int, str]], bot_token: str, method: Callable[..., Coroutine],
        content: str, caption: str,
        success_callback: Optional[Callable[[int], Coroutine[Any, Any, NoReturn]]] = None,
        **configuration
) -> tuple[list[JobResponse], list[JobResponse]]:
    """
    Broadcasts a message to multiple subscribers using multiple processes.

    Args:
        subscribers (list[Tuple[int, str]]): A list of tuples containing the telegram_id and username of the subscribers.
        bot_token (str): The token of the Telegram bot.
        method (Callable[..., Coroutine]): The method to be called for sending the message.
        content (str): The content of the message.
        caption (str): The caption of the message.
        success_callback (Optional[Callable[[int], Coroutine[Any, Any, NoReturn]]]): An optional callback function to be
            called when a message is successfully sent to a subscriber. Defaults to None.
        **configuration: Additional configuration parameters.

    Returns:
        tuple[list[JobResponse], list[JobResponse]]: A tuple containing two lists: the list of successfully
        sent messages and the list of failed messages.

    """
    use_nproc: int = configuration.get("use_nproc", os.cpu_count())
    seconds: float = configuration.get("seconds", 0.0)
    max_retry: int = configuration.get("max_retry", 5)

    res_list: Queue[JobResponse] = Queue()
    with concurrent.futures.ProcessPoolExecutor(max_workers=use_nproc) as executor:
        loop = asyncio.get_event_loop()
        futures = []
        lst = []
        for telegram_id, username in subscribers:
            try:
                future = loop.run_in_executor(
                    executor,
                    partial(broadcast_method_wrapper, method, bot_token, telegram_id, content, caption, 0, max_retry)
                )
                futures.append(future)
                lst.append((telegram_id, username))
                if seconds > 0:
                    await asyncio.sleep(seconds)  # Sleep for a short time to avoid overloading the CPU
            except Exception as error:
                error_info = ErrorInformation(
                    type(error).__name__, str(error), traceback.format_exc()
                )
                res_list.put(JobResponse(telegram_id, username, content, error_info))

        for future, (telegram_id, username) in zip(futures, subscribers):
            try:
                result = await future
                res_list.put(JobResponse(telegram_id, username, content, result))

                if isinstance(result, dict):
                    continue

                if success_callback:
                    await success_callback(telegram_id)
            except Exception as error:
                error_info = ErrorInformation(
                    type(error).__name__, str(error), traceback.format_exc()
                )
                res_list.put(JobResponse(telegram_id, username, content, error_info))

    sent_list, failed_list = group_by_result(res_list, is_apply_result=False)
    return sent_list, failed_list


async def handle_broadcast(
        subscribers: list[Tuple[int, str]], bot_token: str, dtype: str,
        content: str, caption: str, **configuration
) -> tuple[list[JobResponse], list[JobResponse]]:
    use_multiproc = configuration.get("use_multiproc", False)
    use_nproc = configuration.get("use_nproc", os.cpu_count())
    seconds = configuration.get("seconds", 0.0)
    max_retry = configuration.get("max_retry", 5)
    dummy_user = configuration.get("dummy_user", 0)
    async_callback: Optional[Callable[[int], Coroutine[Any, Any, None]]] = configuration.get("async_callback", None)
    broadcast_method = select_broadcast_method(dtype)

    if dummy_user != 0:
        try:
            my_bot = telegram.Bot(token=bot_token)
            res = await broadcast_method(my_bot, dummy_user, content, caption, seconds, 0, max_retry)
            file_id = getattr(res, "file_id", None)
            if file_id:
                content = file_id
                print(f"file_id: {file_id}")
        except Exception:
            raise

    try:
        if use_multiproc:
            return await async_broadcast_with_multiprocessing(
                subscribers, bot_token, broadcast_method, content, caption,
                use_nproc=use_nproc, seconds=seconds, max_retry=max_retry,
                success_callback=async_callback
            )
        return await async_broadcast_sequentially(
            subscribers, bot_token, broadcast_method, content, caption,
            seconds=seconds, max_retry=max_retry,
            success_callback=async_callback
        )
    except Exception:
        raise
