import os
import traceback
import asyncio

import concurrent.futures
from functools import partial

import multiprocessing
import telegram

from queue import Queue
from enum import Enum
from typing import Any, Callable, Coroutine, NoReturn, Optional, Tuple, Type
# Internal imports
from .custom_dataclass import JobResponse, ErrorInformation
from .custom_util import separate_result_list, separate_result_queue
from .send_method import broadcast_method_wrapper, BroadcastMethodTypeHint


class BroadcastStrategyType(Enum):
    """
    An enumeration class that stores the types of broadcast strategies.
    """
    ASYNCIO_SEQUENTIAL = "async_sequential"
    ASYNCIO_MULTIPROCESSING_POOL = "async_multiprocessing_pool"
    ASYNCIO_PROCESS_POOL = "async_process_pool"


def string_to_BroadcastStrategyType(enum_value: str):
    try:
        return BroadcastStrategyType[enum_value]
    except ValueError:
        raise


class BroadcastStrategy:
    """
    This is the base class for all broadcasting strategies.
    It provides a common interface for all strategies.
    Each subclass should override the execute method to implement the specific broadcasting strategy.
    """
    def __init__(self, verbose: bool = False):
        """
        Initialize the BroadcastStrategy class.

        Parameters:
        ----------
        verbose (bool, optional):
            If set to True, verbose output will be printed. Defaults to False.
        """
        self.verbose = verbose

    async def execute(
            self, subscribers: list[Tuple[int, str]], bot_token: str, method: BroadcastMethodTypeHint,
            content: str | list[str], caption: str | list[str],
            success_callback: Optional[Callable[[Any], Coroutine[Any, Any, NoReturn]]] = None,
            **configuration
    ) -> tuple[list[JobResponse], list[JobResponse]]:
        """
        Execute the broadcasting strategy. This method should be overridden by each subclass to implement the specific
        broadcasting strategy.

        Parameters:
        ----------
        subscribers (list[Tuple[int, str]]):
            A list of tuples containing the telegram_id and username of the subscribers.
        bot_token (str):
            The token of the Telegram bot.
        method (BroadcastMethod):
            The method to be called for sending the message.
        content (str | list[str]):
            The content of the message. If it's a string, it will be broadcast to all subscribers.
        caption (str | list[str]):
            The caption of the message. If it's a string, it will be used for all messages.
        success_callback (Optional[Callable[[Any], Coroutine[Any, Any, NoReturn]]]):
            An optional callback function to be called when a message is successfully sent to a subscriber.
        **configuration: Additional configuration parameters.

        Returns:
        -------
        tuple[list[JobResponse], list[JobResponse]]:
            A tuple containing two lists: the list of successfully sent messages and the list of failed messages.

        Raises:
        ------
        NotImplementedError: This method should be overridden in each subclass.
        """
        raise NotImplementedError


class AsyncSequential(BroadcastStrategy):
    """
    This class represents the asynchronous sequential broadcasting strategy. It is a subclass of the BroadcastStrategy
    class and overrides the execute method.

    In this strategy, messages are sent to subscribers one after the other in an
    asynchronous manner.
    """

    async def execute(
            self, subscribers: list[Tuple[int, str]], bot_token: str, method: BroadcastMethodTypeHint,
            content: str | list[str], caption: str | list[str],
            success_callback: Optional[Callable[[Any], Coroutine[Any, Any, NoReturn]]] = None,
            **configuration
    ) -> tuple[list[JobResponse], list[JobResponse]]:
        """
        Execute the broadcasting strategy.

        Parameters:
        ----------
        subscribers (list[Tuple[int, str]]):
            A list of tuples containing the telegram_id and username of the subscribers.
        bot_token (str):
            The token of the Telegram bot.
        method (BroadcastMethod):
            The method to be called for sending the message.
        content (str | list[str]):
            The content of the message. If it's a string, it will be broadcast to all subscribers.
        caption (str | list[str]):
            The caption of the message. If it's a string, it will be used for all messages.
        success_callback (Optional[Callable[[Any], Coroutine[Any, Any, NoReturn]]]):
            An optional callback function to be called when a message is successfully sent to a subscriber.
        **configuration: Additional configuration parameters.

        Returns:
        -------
        tuple[list[JobResponse], list[JobResponse]]:
            A tuple containing two lists: the list of successfully sent messages and the list of failed messages.

        Raises:
        ------
        Exception:
            If an error occurs during the execution of the strategy.
        """
        bot = telegram.Bot(token=bot_token)
        seconds: float = configuration.get("seconds", 0.0)  # Sleep for a short time to avoid overloading the CPU
        max_retry: int = configuration.get("max_retry", 5)

        # If content or caption is a string, convert it to a list of strings with the same length as subscribers
        if type(content) is str:
            content = [content] * len(subscribers)
        if type(caption) is str:
            caption = [caption] * len(subscribers)

        result_list: list[JobResponse] = []
        # Iterate over each subscriber and send the message
        for (telegram_id, username), _payload, _caption in zip(subscribers, content, caption):
            try:
                # Attempt to send the message
                send_result = await method(bot, telegram_id, _payload, _caption, seconds, 0, max_retry)
                # If successful, append the result to the result list
                result_list.append(JobResponse(telegram_id, username, _payload, send_result))
                # If a success callback is provided, call it
                if success_callback:
                    await success_callback(telegram_id)
            except Exception as error:
                # If an error occurs, append the error information to the result list
                error_info = ErrorInformation(type(error).__name__, str(error), traceback.format_exc())
                if self.verbose:
                    print(f"Error: {error_info}")
                result_list.append(JobResponse(telegram_id, username, _payload, error_info))

        # Group the results by success and failure
        sent_list, failed_list = separate_result_list(result_list)
        return sent_list, failed_list


class AsyncProcessPool(BroadcastStrategy):
    """
    This class represents the asynchronous process pool broadcasting strategy. It is a subclass of the BroadcastStrategy
    class and overrides the execute method.

    In this strategy, messages are sent to subscribers using multiple processes.
    """

    async def execute(
            self, subscribers: list[Tuple[int, str]], bot_token: str, method: BroadcastMethodTypeHint,
            content: str | list[str], caption: str | list[str],
            success_callback: Optional[Callable[[int], Coroutine[Any, Any, NoReturn]]] = None,
            **configuration
    ) -> tuple[list[JobResponse], list[JobResponse]]:
        """
        Execute the broadcasting strategy.

        Parameters:
        ----------
        subscribers (list[Tuple[int, str]]):
            A list of tuples containing the telegram_id and username of the subscribers.
        bot_token (str):
            The token of the Telegram bot.
        method (BroadcastMethod):
            The method to be called for sending the message.
        content (str | list[str]):
            The content of the message. If it's a string, it will be broadcast to all subscribers.
        caption (str | list[str]):
            The caption of the message. If it's a string, it will be used for all messages.
        success_callback (Optional[Callable[[int], Coroutine[Any, Any, NoReturn]]]):
            An optional callback function to be called when a message is successfully sent to a subscriber.
        **configuration: Additional configuration parameters.

        Returns:
        -------
        tuple[list[JobResponse], list[JobResponse]]:
            A tuple containing two lists: the list of successfully sent messages and the list of failed messages.

        Raises:
        ------
        Exception:
            If an error occurs during the execution of the strategy.
        """
        use_nproc: int = configuration.get("use_nproc", os.cpu_count())  # Number of processes to use
        seconds: float = configuration.get("seconds", 0.0)  # Sleep for a short time to avoid overloading the CPU
        max_retry: int = configuration.get("max_retry", 5)  # Maximum number of retries

        if use_nproc > os.cpu_count():
            if self.verbose:
                print(f"Number of processes exceeds the number of CPUs. Using {os.cpu_count()} processes instead.")
            use_nproc = os.cpu_count()

        # If content or caption is a string, convert it to a list of strings with the same length as subscribers
        if type(content) is str:
            content = [content] * len(subscribers)
        if type(caption) is str:
            caption = [caption] * len(subscribers)

        res_list: Queue[JobResponse] = Queue()  # Queue to store the results
        # Use a process pool executor to send messages concurrently
        with concurrent.futures.ProcessPoolExecutor(max_workers=use_nproc) as executor:
            loop = asyncio.get_event_loop()
            futures = []
            # Iterate over each subscriber and send the message
            for (telegram_id, username), _payload, _caption in zip(subscribers, content, caption):
                try:
                    # Attempt to send the message
                    future = loop.run_in_executor(
                        executor,
                        partial(broadcast_method_wrapper, method, bot_token, telegram_id, _payload, _caption, 0,
                                max_retry)
                    )
                    futures.append(future)
                    if seconds > 0:
                        await asyncio.sleep(seconds)  # Sleep for a short time to avoid overloading the CPU
                except Exception as error:
                    # If an error occurs, append the error information to the result list
                    error_info = ErrorInformation(type(error).__name__, str(error), traceback.format_exc())
                    res_list.put(JobResponse(telegram_id, username, _payload, error_info))

            # Process the results
            for future, (telegram_id, username), _payload in zip(futures, subscribers, content):
                try:
                    result = await future
                    res_list.put(JobResponse(telegram_id, username, content, result))

                    if isinstance(result, ErrorInformation):
                        continue

                    if success_callback:
                        await success_callback(telegram_id)
                except Exception as error:
                    error_info = ErrorInformation(type(error).__name__, str(error), traceback.format_exc())
                    res_list.put(JobResponse(telegram_id, username, _payload, error_info))

        # Group the results by success and failure
        sent_list, failed_list = separate_result_queue(res_list)
        return sent_list, failed_list


class AsyncMultiProcessingPool(BroadcastStrategy):
    """
    This class represents the multiprocessing.Pool broadcasting strategy. It is a subclass of the BroadcastStrategy
    class and overrides the execute method.

    In this strategy, messages are sent to subscribers using multiple processes.
    """
    async def execute(
            self,
            subscribers: list[Tuple[int, str]], bot_token: str, method: Callable[..., Coroutine],
            content: str | list[str], caption: str | list[str],
            success_callback: Optional[Callable[[int], Coroutine[Any, Any, NoReturn]]] = None,
            **configuration
    ) -> Tuple[list[JobResponse], list[JobResponse]]:
        """
        Execute the broadcasting strategy.

        Parameters:
        ----------
        subscribers (list[Tuple[int, str]]):
            A list of tuples containing the telegram_id and username of the subscribers.
        bot_token (str):
            The token of the Telegram bot.
        method (BroadcastMethod):
            The method to be called for sending the message.
        content (str | list[str]):
            The content of the message. If it's a string, it will be broadcast to all subscribers.
        caption (str | list[str]):
            The caption of the message. If it's a string, it will be used for all messages.
        success_callback (Optional[Callable[[Any], Coroutine[Any, Any, NoReturn]]]):
            An optional callback function to be called when a message is successfully sent to a subscriber.
        **configuration: Additional configuration parameters.

        Returns:
        -------
        tuple[list[JobResponse], list[JobResponse]]:
            A tuple containing two lists: the list of successfully sent messages and the list of failed messages.

        Raises:
        ------
        Exception:
            If an error occurs during the execution of the strategy.
        """
        use_nproc: int = configuration.get("use_nproc", os.cpu_count())
        seconds: float = configuration.get("seconds", 0.0)
        max_retry: int = configuration.get("max_retry", 5)

        if use_nproc > os.cpu_count():
            if self.verbose:
                print(f"Number of processes exceeds the number of CPUs. Using {os.cpu_count()} processes instead.")
            use_nproc = os.cpu_count()

        # If content or caption is a string, convert it to a list of strings with the same length as subscribers
        if type(content) is str:
            content = [content] * len(subscribers)
        if type(caption) is str:
            caption = [caption] * len(subscribers)

        res_list: Queue[JobResponse] = Queue()
        with multiprocessing.Pool(processes=use_nproc) as pool:
            results = []
            for (telegram_id, username), _payload, _caption in zip(subscribers, content, caption):
                result = pool.apply_async(
                    broadcast_method_wrapper,
                    (method, bot_token, telegram_id, _payload, _caption, 0.0, max_retry)
                )
                results.append((result, telegram_id, username))
                if seconds > 0:
                    await asyncio.sleep(seconds)
            pool.close()
            pool.join()

        for (result, telegram_id, username), _payload in zip(results, content):
            try:
                send_result = result.get()
                res_list.put(JobResponse(telegram_id, username, _payload, send_result))

                if isinstance(send_result, ErrorInformation):
                    continue

                if success_callback:
                    await success_callback(telegram_id)
            except Exception as error:
                error_info = ErrorInformation(
                    type(error).__name__, str(error), traceback.format_exc()
                )
                res_list.put(JobResponse(telegram_id, username, _payload, error_info))

        sent_list, failed_list = separate_result_queue(res_list)
        return sent_list, failed_list


def select_broadcast_strategy(strategy: BroadcastStrategyType) -> Type[BroadcastStrategy]:
    """
    Selects the appropriate broadcasting strategy based on the provided strategy type.

    Args:
        strategy (BroadcastStrategyType): The type of the broadcasting strategy to be selected.

    Returns:
        Type[BroadcastStrategy]: The selected broadcasting strategy class.

    Raises:
        ValueError: If an invalid broadcasting strategy type is provided.
    """
    if strategy == BroadcastStrategyType.ASYNCIO_SEQUENTIAL:
        return AsyncSequential
    if strategy == BroadcastStrategyType.ASYNCIO_MULTIPROCESSING_POOL:
        return AsyncMultiProcessingPool
    if strategy == BroadcastStrategyType.ASYNCIO_PROCESS_POOL:
        return AsyncProcessPool
    raise ValueError("Invalid broadcast strategy")
