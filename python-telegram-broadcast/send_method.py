import asyncio
import time
import traceback
from enum import Enum

import telegram
from telegram import Message, PhotoSize, Document, Video
from telegram.constants import ParseMode
from telegram.error import TelegramError, RetryAfter, TimedOut, Forbidden, BadRequest

from .custom_exception import ExceedMaxRetriesError, TelegramSendError
from .custom_dataclass import ErrorInformation
from typing import Any, Callable, Coroutine, Union

BroadcastMethodReturnTypeHint = Union[
    telegram.Message, telegram.PhotoSize, telegram.Document, telegram.Video, ErrorInformation
]
BroadcastMethodTypeHint = Callable[
    [telegram.Bot, int, str, str, float, int, int],
    Coroutine[Any, Any, Message | PhotoSize | Document | Video | ErrorInformation]
]


class BroadcastMethodType(Enum):
    """
    An enumeration class that stores the types of broadcast methods.
    """
    TEXT = "Text"
    PHOTO = "Photo"
    DOCUMENT = "Document"
    VIDEO = "Video"


def string_to_BroadcastMethodType(enum_value: str):
    try:
        return BroadcastMethodType[enum_value]
    except ValueError:
        raise


async def sendMessage(
        bot: telegram.Bot, target_id: int, message: str, caption: str | None = None,
        seconds: float = 0.0, n_retry: int = 0, max_retry: int = 5
) -> Message:
    """
    Sends a message to a target ID using the given Telegram bot.

    Parameters:
    - bot (telegram.Bot): The Telegram bot instance.
    - target_id (int): The ID of the target user or chat.
    - message (str): The message to be sent.
    - caption (str | None): The caption for the message (optional).
    - seconds (float): The delay in seconds before sending the message (optional, default: 0.0).
    - n_retry (int): The number of retries performed (optional, default: 0).
    - max_retry (int): The maximum number of retries allowed (optional, default: 5).

    Returns:
    - Message: Sent `telegram.Message` object.

    Raises:
    - ExceedMaxRetriesError: If the maximum number of retries is exceeded.
    - TelegramSendError: If there is an error sending the message.
    - Forbidden: If the bot is forbidden from sending messages to the target.
    - TimedOut: If the message sending times out.
    - Exception: If there is an unexpected error.

    Notes:
    - The `caption` parameter is not used in this function and will be ignored.
    """
    t1 = time.time()
    try:
        res = await bot.sendMessage(
            chat_id=target_id, text=message, parse_mode=ParseMode.HTML, disable_web_page_preview=False,
        )
        t2 = time.time()
        sent_time = t2 - t1
        if sent_time < seconds:
            await asyncio.sleep(seconds - sent_time)
        return res
    except RetryAfter as ra_err:
        n_retry += 1
        if n_retry < max_retry:
            delay = max(ra_err.retry_after, int(seconds) + 1)
            if delay > 0.0:
                await asyncio.sleep(delay)
            return await sendMessage(bot, target_id, message, caption, seconds, n_retry, max_retry)
        raise ExceedMaxRetriesError(target_id, "NA", message, max_retry)
    except TimedOut:
        t2 = time.time()
        sent_time = t2 - t1
        error_message = (f'telegram_id: "{target_id}", '
                         f'username: "NA", payload: '
                         f'payload: "{message}", '
                         f'elapsed_seconds: "{sent_time}"')
        raise TimedOut("{" + error_message + "}")
    except BadRequest as bad_request_err:
        raise TelegramSendError(target_id, "NA", message, str(bad_request_err))
    except Forbidden as _:
        raise Forbidden(str(target_id))
    except TelegramError as tg_err:
        raise TelegramSendError(target_id, "NA", message, str(tg_err))
    except Exception as err:
        raise TelegramSendError(target_id, "NA", message, str(err))


async def sendPhoto(
        bot: telegram.Bot, target_id: int, filename_or_url: str, caption: str = "",
        seconds: float = 0.0, n_retry: int = 0, max_retry: int = 5
) -> PhotoSize:
    """
    Asynchronously sends a photo file to a specified target using a Telegram bot.

    Parameters:
    - bot (telegram.Bot): An instance of the Telegram Bot used to send the photo.
    - target_id (str): The Telegram chat_id where the photo will be sent.
    - filename_or_url (str): The photo to be sent. Can be a URL or a local file name.
    - caption (str, optional): The caption for the photo. Defaults to an empty string.
    - seconds (float, optional): A delay in seconds before sending the photo. Defaults to 0.0, meaning no delay.
    - n_retry (int, optional): The number of retries. Defaults to 0.
    - max_retry (int, optional): The maximum number of retries. Defaults to 5.

    Returns:
    - PhotoSize: The `PhotoSize` object of sent photo.

    Raises:
    - FileNotFoundError: If the photo could not be found locally.
    - RetryAfter: If the sending process encounters a RetryAfter error.
    - ExceedMaxRetriesError: If the maximum number of retries is exceeded.
    - TimedOut: If a timeout occurs during the sending process.
    - BadRequest: If a bad request error occurs during the sending process.
    - Forbidden: If the target_id is forbidden.
    - TelegramError: If any other Telegram-related error occurs during the sending process.
    - Exception: If any other error occurs during the sending process.

    Notes:
    - If the `sent_time` is < `seconds`, the function will sleep for `seconds - sent_time` seconds.
    - Return the last element of the `message.photo` list, the highest resolution photo.
    - Default timeout is 60 seconds.
    """
    timeout = 60
    t1 = time.time()
    try:
        res = await bot.sendPhoto(
            chat_id=target_id, photo=filename_or_url, caption=caption,
            allow_sending_without_reply=True, protect_content=False,
            read_timeout=timeout, write_timeout=timeout, connect_timeout=timeout, pool_timeout=timeout,
            parse_mode=ParseMode.HTML,
        )
        t2 = time.time()
        sent_time = t2 - t1
        if sent_time < seconds:
            await asyncio.sleep(seconds - sent_time)
        print(f"sendPhoto: {round(sent_time, 2)} seconds.")

        return res.photo[-1]
    except FileNotFoundError as _:
        raise FileNotFoundError(f"payload: {filename_or_url}")
    except RetryAfter as ra_err:
        n_retry += 1
        if n_retry < max_retry:
            delay = max(ra_err.retry_after, int(seconds) + 1)
            if delay > 0.0:
                await asyncio.sleep(delay)
            return await sendPhoto(bot, target_id, filename_or_url, caption, seconds, n_retry, max_retry)
        raise ExceedMaxRetriesError(target_id, "NA", filename_or_url, max_retry)
    except TimedOut:
        sent_time = time.time() - t1
        error_message = (f'telegram_id: "{target_id}", '
                         f'username: "NA", payload: '
                         f'payload: "{filename_or_url}", '
                         f'elapsed_seconds: "{sent_time}"')
        raise TimedOut("{" + error_message + "}")
    except BadRequest as bad_request_err:
        raise TelegramSendError(target_id, "NA", filename_or_url, str(bad_request_err))
    except Forbidden as _:
        raise Forbidden(str(target_id))
    except TelegramError as tg_err:
        raise TelegramSendError(target_id, "NA", filename_or_url, str(tg_err))
    except Exception as err:
        raise TelegramSendError(target_id, "NA", filename_or_url, str(err))


async def sendVideo(
        bot: telegram.Bot, target_id: int, filename_or_url: str, caption: str = "",
        seconds: float = 0.0, n_retry: int = 0, max_retry: int = 5
) -> Video:
    """
    Asynchronously sends a video file to a specified target using a Telegram bot.

    Parameters:
        bot (telegram.Bot): The Telegram bot instance.
        target_id (int): The ID of the target user or group.
        filename_or_url (str): The filename or URL of the video to send.
        caption (str, optional): The caption for the video message. Defaults to "".
        seconds (float, optional): The minimum duration to wait before sending the video. Defaults to 0.0.
        n_retry (int, optional): The number of retries performed. Defaults to 0.
        max_retry (int, optional): The maximum number of retries allowed. Defaults to 5.

    Returns:
        Video: The `Video` object of sent video.

    Raises:
        FileNotFoundError: If the video file is not found.
        RetryAfter: If the request is rate-limited and needs to be retried after a delay.
        ExceedMaxRetriesError: If the maximum number of retries is exceeded.
        TimedOut: If the request times out.
        BadRequest: If the request is invalid.
        Forbidden: If the bot is forbidden from performing the action.
        TelegramError: If there is an error sending the video message.
        Exception: If there is an unexpected error.

    Notes:
    - If the `sent_time` is < `seconds`, the function will sleep for `seconds - sent_time` seconds.
    - Default timeout is 300 seconds.
    """
    timeout = 300
    t1 = time.time()
    try:
        res = await bot.sendVideo(
            chat_id=target_id, video=filename_or_url, caption=caption,
            allow_sending_without_reply=True, protect_content=False,
            read_timeout=timeout, write_timeout=timeout, connect_timeout=timeout, pool_timeout=timeout,
        )
        t2 = time.time()
        sent_time = t2 - t1
        if sent_time < seconds:
            await asyncio.sleep(seconds - sent_time)
        return res.video
    except FileNotFoundError as _:
        raise FileNotFoundError(f"payload: {filename_or_url}")
    except RetryAfter as ra_err:
        n_retry += 1
        if n_retry < max_retry:
            delay = max(ra_err.retry_after, int(seconds) + 1)
            if delay > 0.0:
                await asyncio.sleep(delay)
            return await sendVideo(bot, target_id, filename_or_url, caption, seconds, n_retry, max_retry)
        raise ExceedMaxRetriesError(target_id, "NA", filename_or_url, max_retry)
    except TimedOut:
        sent_time = time.time() - t1
        error_message = (f'telegram_id: "{target_id}", '
                         f'username: "NA", payload: '
                         f'payload: "{filename_or_url}", '
                         f'elapsed_seconds: "{sent_time}"')
        raise TimedOut("{" + error_message + "}")
    except BadRequest as bad_request_err:
        raise TelegramSendError(target_id, "NA", filename_or_url, str(bad_request_err))
    except Forbidden as _:
        raise Forbidden(str(target_id))
    except TelegramError as tg_err:
        raise TelegramSendError(target_id, "NA", filename_or_url, str(tg_err))
    except Exception as err:
        raise TelegramSendError(target_id, "NA", filename_or_url, str(err))


async def sendDocument(
        bot: telegram.Bot, target_id: int, filename_or_url: str, caption: str = "",
        seconds: float = 0.0, n_retry: int = 0, max_retry: int = 5
) -> Document:
    """
    Asynchronously sends a file to a specified target using a Telegram bot.

    Parameters:
    -------
    - bot (telegram.Bot): The Telegram bot instance.
    - target_id (int): The ID of the target user or chat.
    - filename_or_url (str): The filename or URL of the document to send.
    - caption (str, optional): The caption for the document. Defaults to "".
    - seconds (float, optional): The minimum time to wait before sending the document. Defaults to 0.0.
    - n_retry (int, optional): The number of retries performed. Defaults to 0.
    - max_retry (int, optional): The maximum number of retries allowed. Defaults to 5.

    Returns:
    -------
    Document: The `Document` object of sent document.

    Raises:
    -------
    - FileNotFoundError: If the specified file or URL is not found.
    - RetryAfter: If the request is rate-limited and needs to be retried after a delay.
    - ExceedMaxRetriesError: If the maximum number of retries is exceeded.
    - TimedOut: If the request times out.
    - BadRequest: If the request is invalid.
    - Forbidden: If the request is forbidden.
    - TelegramError: If there is an error sending the document.
    - Exception: If there is an unexpected error.

    Notes:
    -------
    - If the `sent_time` is < `seconds`, the function will sleep for `seconds - sent_time` seconds.
    - Default timeout is 120 seconds.
    """
    timeout = 120
    t1 = time.time()
    try:
        res = await bot.sendDocument(
            chat_id=target_id,
            document=filename_or_url, caption=caption,
            allow_sending_without_reply=True, protect_content=False,
            read_timeout=timeout, write_timeout=timeout, connect_timeout=timeout, pool_timeout=timeout,
        )
        t2 = time.time()
        sent_time = t2 - t1
        if sent_time < seconds:
            await asyncio.sleep(seconds < sent_time)
        return res.document
    except FileNotFoundError as _:
        raise FileNotFoundError(f"payload: {filename_or_url}")
    except RetryAfter as ra_err:
        n_retry += 1
        if n_retry < max_retry:
            delay = max(ra_err.retry_after, int(seconds) + 1)
            if delay > 0.0:
                await asyncio.sleep(delay)
            return await sendDocument(bot, target_id, filename_or_url, caption, seconds, n_retry, max_retry)
        raise ExceedMaxRetriesError(target_id, "NA", filename_or_url, max_retry)
    except TimedOut:
        sent_time = time.time() - t1
        error_message = (f'telegram_id: "{target_id}", '
                         f'username: "NA", payload: '
                         f'payload: "{filename_or_url}", '
                         f'elapsed_seconds: "{sent_time}"')
        raise TimedOut("{" + error_message + "}")
    except BadRequest as bad_request_err:
        raise TelegramSendError(target_id, "NA", filename_or_url, str(bad_request_err))
    except Forbidden as _:
        raise Forbidden(str(target_id))
    except TelegramError as tg_err:
        raise TelegramSendError(target_id, "NA", filename_or_url, str(tg_err))
    except Exception as err:
        raise TelegramSendError(target_id, "NA", filename_or_url, str(err))


def select_broadcast_method(
    dtype: BroadcastMethodType = BroadcastMethodType.TEXT
) -> BroadcastMethodTypeHint:
    """
    Selects the appropriate broadcast method based on the given dtype.

    Parameters:
    -------
    - dtype (BroadcastMethodType): The type of broadcast message.

    Returns:
    -------
    - BroadcastMethodType: The selected broadcast method.

    Raises:
    -------
    ValueError: If an invalid dtype is provided.

    Notes:
    -------
    - Default dtype is TEXT.
    """
    if dtype == BroadcastMethodType.PHOTO:
        return sendPhoto
    if dtype == BroadcastMethodType.DOCUMENT:
        return sendDocument
    if dtype == BroadcastMethodType.VIDEO:
        return sendVideo
    if dtype == BroadcastMethodType.TEXT:
        return sendMessage
    raise ValueError(f"Invalid dtype: {dtype}")


def broadcast_method_wrapper(
        method: BroadcastMethodTypeHint,
        bot_token: str, target_id: int, payload: str, caption: str,
        seconds: float, max_retry: int
) -> BroadcastMethodReturnTypeHint:
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
