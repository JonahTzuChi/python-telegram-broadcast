import asyncio
from .main import handle_broadcast, get_file_id
from .send_method import BroadcastMethodType, select_broadcast_method
from .strategy import BroadcastStrategyType, select_broadcast_strategy
from .custom_util import write_sent_result, evaluate_broadcast_stats
from .custom_dataclass import JobResponse, BroadcastStats, ErrorInformation

__all__ = [
    "handle_broadcast", "get_file_id",
    "select_broadcast_method", "BroadcastMethodType",
    "select_broadcast_strategy", "BroadcastStrategyType",
    "write_sent_result", "evaluate_broadcast_stats",
    "JobResponse", "BroadcastStats", "ErrorInformation"
]


def wrapper(bt, bm, user, payload):
    loop = asyncio.get_event_loop()
    return loop.run_until_complete(
        get_file_id(
            bt, bm, user, payload, "...", 0.0, 5
        )
    )


def broadcast_wrapper(bt, bm, bs, sl, payload):
    loop = asyncio.get_event_loop()
    return loop.run_until_complete(
        handle_broadcast(
            sl, bt, bm, bs, payload, "...", use_multiproc=False, use_nproc=1, seconds=0.0, max_retry=5
        )
    )


# CLI: python3 -m python-telegram-broadcast.__init__
if __name__ == "__main__":
    bot_token: str
    with open("./asset/token.txt", "r") as file:
        bot_token = file.readline().strip()
    print(bot_token)
    broadcast_method = select_broadcast_method(BroadcastMethodType.PHOTO)
    broadcast_strategy = select_broadcast_strategy(BroadcastStrategyType.ASYNCIO_SEQUENTIAL)

    with open("./asset/subscriber.txt", "r") as file:
        header = file.readline()
        while True:
            line = file.readline()
            if not line:
                break
            telegram_id, username = line.strip().split(",")
            print(telegram_id, username)

    file_id = wrapper(bot_token, broadcast_method, int(telegram_id), open("./asset/sample_photo.jpeg", "rb"))
    print(file_id)

    subscriber_list = []
    with open("./asset/subscriber.txt", "r") as file:
        header = file.readline()
        while True:
            line = file.readline()
            if not line:
                break
            telegram_id, username = line.strip().split(",")
            print(telegram_id, username)

            subscriber_list.append((int(telegram_id), username))

    for tid, uname in subscriber_list:
        print(tid, uname)

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
        write_sent_result(f"./asset/result_sample_photo.txt", f, "sample_photo.jpeg")
