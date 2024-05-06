from dataclasses import dataclass
from typing import Union, Callable, Coroutine, Any
import telegram


@dataclass
class BroadcastStats:
    """
    A data class that stores statistics about a broadcast operation.

    Attributes:
    -----------
    n_job : int
        The number of jobs that are expected to be sent, default to 0.
    n_success : int
        The number of jobs that are successfully sent, default to 0.
    n_failure : int
        The number of jobs that are failed, default to 0.
    """

    n_job: int = 0
    n_success: int = 0
    n_failure: int = 0

    def __add__(self, other: "BroadcastStats") -> "BroadcastStats":
        return BroadcastStats(
            n_job=self.n_job + other.n_job,
            n_success=self.n_success + other.n_success,
            n_failure=self.n_failure + other.n_failure,
        )

    def __str__(self) -> str:
        return (f"Expect to send {self.n_job} jobs, "
                f"{self.n_success} jobs are successful, "
                f"{self.n_failure} jobs are failed.")


@dataclass
class ErrorInformation:
    """
    A data class that stores information about an error that occurred.

    Attributes:
    -----------
    error_type: str
        The type of the error that occurred.
    error_message: str
        The message of the error that occurred.
    traceback: str
        The traceback of the error that occurred.
    """

    error_type: str
    error_message: str
    traceback: str


BroadcastMethodArgumentType = [
    telegram.Bot, int, str, str, float, int, int
]

BroadcastMethodReturnType = Union[
    telegram.Message, telegram.PhotoSize, telegram.Document, telegram.Video, ErrorInformation
]
BroadcastMethod = Callable[
    [*BroadcastMethodArgumentType],
    Coroutine[Any, Any, BroadcastMethodReturnType]
]


@dataclass
class JobResponse:
    """
    A data class that stores information about a job that is sent.

    Attributes:
    -----------
    telegram_id : int
        The telegram id of the receiver.
    username : str
        The username of the receiver.
    payload : str
        The payload that is sent to the receiver.
    result : Union[Message, PhotoSize, Document, Video, ErrorInformation]
        The result of the job that is sent.

    Notes:
    ------
    - If successful, result is either a Message, PhotoSize, Document, or Video object.
    - If failed, result is a ErrorInformation object.
    """

    telegram_id: int
    username: str
    payload: str
    result: Union[
        telegram.Message, telegram.PhotoSize, telegram.Document, telegram.Video, ErrorInformation
    ]

    def to_tuple(
            self
    ) -> tuple[
        int, str, str, Union[
            telegram.Message, telegram.PhotoSize, telegram.Document, telegram.Video, ErrorInformation
        ]
    ]:
        return self.telegram_id, self.username, self.payload, self.result

    def dump(self) -> str:
        template: str = '"telegram_id": "{tid}", "username": "{uname}", "payload": "{pld}", "result": "{res}"'
        content_string = template.format(
            tid=self.telegram_id, uname=self.username, pld=self.payload, res=str(self.result)
        )
        return "{" + content_string + "}"
