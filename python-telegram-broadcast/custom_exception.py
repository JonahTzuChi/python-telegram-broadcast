from telegram.error import TelegramError


class TelegramSendError(TelegramError):
    """Raised when an error occurs while sending a message.

    Attributes:
    ----------------------
    telegram_id: int
        The telegram id of the receiver.
    username : str
        The username of the receiver.
    payload : str
        The payload that was sent.
    error : str
        The error message that occurred.
    """
    __slots__ = ()

    def __init__(self, target_id: int, username: str, payload: str, error: str):
        error_message = (f'target_id: "{target_id}", "'
                         f'username: "{username}", '
                         f'payload: "{payload}", '
                         f'error: "{error}"')
        super().__init__("{" + error_message + "}")


class ExceedMaxRetriesError(TelegramError):
    """Raised when the maximum number of retries is exceeded.

    Attributes:
    ----------------------
    target_id : int
        The user id of the target.
    username : str
        The username of the receiver.
    payload : str
        The payload that was sent.
    max_retry : Optional[int]
        The maximum number of retries. Defaults to 5.
    """
    __slots__ = ()

    def __init__(self, target_id: int, username: str, payload: str, max_retry: int = 5):
        error_message = (f'target_id: "{target_id}", "'
                         f'username: "{username}", '
                         f'payload: "{payload}", '
                         f'max_retry: "{max_retry}"')
        super().__init__("{" + error_message + "}")
