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

from queue import Queue
from typing import NoReturn

from .custom_dataclass import JobResponse, BroadcastStats, ErrorInformation


def write_sent_result(
        log_sheet_path: str, job_response_list: list[JobResponse], payload: str
) -> NoReturn:
    """
    Writes the result of sent jobs to a log file. It iterates over a list of JobResponse objects,
    which contain information about each job that was sent.
    For each job, it writes the job's information to the log file.

    Parameters:
    ----------
    log_sheet_path : str
        The path to the log file where the job information will be written.
    job_response_list : list[JobResponse]
        A list of JobResponse objects, each representing a job that was sent.
    payload : str
        The payload that was expected to be sent in each job.

    Returns:
    -------
    NoReturn
    """
    with open(log_sheet_path, "a") as file:
        file.write(f"Payload: {payload}\n")
        for jr in job_response_list:
            file.write(f"{jr.dump()}\n")


def separate_result_queue(result_queue: Queue[JobResponse]) -> tuple[list[JobResponse], list[JobResponse]]:
    sent_list, failed_list = list(), list()
    while result_queue.qsize():
        item = result_queue.get()
        sid, uname, payload, result = item.to_tuple()
        if isinstance(result, ErrorInformation):
            failed_list.append(item)
        else:
            sent_list.append(item)
    return sent_list, failed_list


def separate_result_list(result_list: list[JobResponse]) -> tuple[list[JobResponse], list[JobResponse]]:
    sent_list, failed_list = list(), list()
    for job_result in result_list:
        _, _, _, result = job_result.to_tuple()
        if isinstance(result, ErrorInformation):
            failed_list.append(job_result)
        else:
            sent_list.append(job_result)
    return sent_list, failed_list


def evaluate_broadcast_stats(
        sent_list: list[JobResponse], failed_list: list[JobResponse]
) -> BroadcastStats:
    n_job = len(sent_list) + len(failed_list)
    n_success = len(sent_list)
    n_failure = len(failed_list)
    return BroadcastStats(n_job, n_success, n_failure)
