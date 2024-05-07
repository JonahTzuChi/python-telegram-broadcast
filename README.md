![my-logo](https://jonahtzuchi.github.io/python-telegram-broadcast/logo-mini.jpg "Python-Telegram-Broadcast-Logo")

# Python Telegram Broadcast

This is a simple Python package that build on top of [python-telegram-bot](https://pypi.org/project/python-telegram-bot/) to make broadcasting easier.


## Features
- Broadcast message to multiple users
- Support media type:
  - Text
  - Photo
  - Document
  - Video
- Support broadcast strategy:
  - Asynchronous Sequentially
  - Asynchronous Process Pool
  - Asynchronous Multiprocessing Pool

## Dependencies
- [python-telegram-bot](https://pypi.org/project/python-telegram-bot/)=21.1.1
- [mypy](https://pypi.org/project/mypy/)

## Installation
  ```bash
  pip3 install python_telegram_broadcast
  ```

## Example

### Get File ID from Telegram
```python
import asyncio
from python_telegram_broadcast import (
    get_file_id, select_broadcast_method, BroadcastMethodType
)


def wrapper(token, method, target_id, payload):
  caption = ""
  seconds = 0.0 # 0.0 means no timeout
  max_retry = 5 # Maximum retry
  
  loop = asyncio.get_event_loop()
  return loop.run_until_complete(
      get_file_id(
          token, method, target_id, payload, caption, seconds, max_retry
      )
  )
  

if __name__ == "__main__":
  bot_token: str = "TELEGRAM_BOT_TOKEN"   # << Change to your bot token
  user_telegram_id: int = 123456789       # << Change to your telegram id
  file_path: str = ""                     # << Change to your file path or the URL of your file
  
  broadcast_method = select_broadcast_method(BroadcastMethodType.PHOTO)
  
  # If file_path is a URL
  if "://" in file_path:
    file_id = wrapper(bot_token, broadcast_method, user_telegram_id, file_path)
  else:  
    # Otherwise
    file_id = wrapper(bot_token, broadcast_method, user_telegram_id, open(file_path, "rb"))
  
  print(file_id)
```
    

### Broadcast Photo
```python
from typing import Tuple
from python_telegram_broadcast import (
    handle_broadcast,
    select_broadcast_strategy, BroadcastStrategyType,
    write_sent_result
)

def broadcast_wrapper(token, method, stg, slist, payload):
    loop = asyncio.get_event_loop()
    return loop.run_until_complete(
        handle_broadcast(
            slist, token, method, stg, payload, "...", 
            use_multiproc=False, use_nproc=1, seconds=0.0, max_retry=5
        )
    )

# Use bot_token, broadcast_method, file_path from the previous example!!!
export_path = ""
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

```

## Tests
TODO

## Source Code
- https://github.com/JonahTzuChi/python-telegram-broadcast