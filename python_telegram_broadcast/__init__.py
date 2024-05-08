"""
MIT License

Copyright (c) 2024 Jonah Whaler

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
"""

__title__ = "python-telegram-broadcast"
__author__ = "Jonah Whaler"
__license__ = "MIT"
__copyright__ = "Copyright (c) 2024 Jonah Whaler"

import asyncio
from typing import Tuple
from .main import handle_broadcast, get_file_id
from .send_method import BroadcastMethodType, select_broadcast_method, string_to_BroadcastMethodType
from .strategy import BroadcastStrategyType, select_broadcast_strategy, string_to_BroadcastStrategyType
from .custom_util import write_sent_result, evaluate_broadcast_stats
from .custom_dataclass import JobResponse, BroadcastStats, ErrorInformation

__all__ = [
    "handle_broadcast", "get_file_id",
    "select_broadcast_method", "BroadcastMethodType", "string_to_BroadcastMethodType",
    "select_broadcast_strategy", "BroadcastStrategyType", "string_to_BroadcastStrategyType",
    "write_sent_result", "evaluate_broadcast_stats",
    "JobResponse", "BroadcastStats", "ErrorInformation"
]


def wrapper(token, method, target_id, payload):
    caption = ""
    seconds = 0.0  # 0.0 means no timeout
    max_retry = 5  # Maximum retry

    loop = asyncio.get_event_loop()
    return loop.run_until_complete(
        get_file_id(
            token, method, target_id, payload, caption, seconds, max_retry
        )
    )


def broadcast_wrapper(token, method, stg, slist, payload):
    loop = asyncio.get_event_loop()
    return loop.run_until_complete(
        handle_broadcast(
            slist, token, method, stg, payload, "...",
            use_multiproc=False, use_nproc=1, seconds=0.0, max_retry=5
        )
    )


# CLI: python3 -m python_telegram_broadcast.__init__
if __name__ == "__main__":
    bot_token: str = ""                             # << Change to your bot token
    user_telegram_id: int = 12345678                # << Change to your telegram id
    file_path: str = "./asset/sample_photo.jpeg"    # << Change to your file path or the URL of your file

    broadcast_method = select_broadcast_method(BroadcastMethodType.PHOTO)

    file_id = wrapper(bot_token, broadcast_method, user_telegram_id, file_path)

    # Use bot_token, broadcast_method, file_path from the previous example!!!
    export_path = "./asset"
    broadcast_strategy = select_broadcast_strategy(BroadcastStrategyType.ASYNCIO_SEQUENTIAL)
    # Read subscriber list from file, but you can also read from database of your choice
    subscriber_list: list[Tuple[int, str]] = []
    with open("./asset/subscriber.txt", "r") as file:
        header = file.readline()
        while True:
            line = file.readline()
            if not line:
                break
            telegram_id, username = line.strip().split(",")
            subscriber_list.append((int(telegram_id), username))

    s, f = broadcast_wrapper(
        bot_token, broadcast_method, broadcast_strategy,
        subscriber_list,
        file_id
    )
    for S in s:
        print(f"Success: {s}")

    for F in f:
        print(f"Failed: {f}")

    if len(f) > 0:
        write_sent_result(f"{export_path}/result_{file_path}.txt", f, file_path)
