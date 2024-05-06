from queue import Queue
from typing import NoReturn

from .custom_data_class import JobSentInformation, BroadcastStats


def write_sent_result(
        log_sheet_path: str, job_information_list: list[JobSentInformation], content: str
) -> NoReturn:
    """
    Writes the result of sent jobs to a log file. It iterates over a list of JobSentInformation objects,
    which contain information about each job that was sent.
    For each job, it writes the job's information to the log file.

    Parameters:
    ----------
    log_sheet_path : str
        The path to the log file where the job information will be written.
    job_information_list : list[JobSentInformation]
        A list of JobSentInformation objects, each representing a job that was sent.
    content : str
        The content that was expected to be sent in each job.

    Returns:
    -------
    NoReturn

    Notes:
    ------
    - TODO: Handle situations where the result is ApplyResult.
    """
    with open(log_sheet_path, "a") as file:
        file.write(f"Content:{content}\n")
        for jsi in job_information_list:
            file.write(f"{jsi.dump()}\n")


def group_by_result(
        result_queue: Queue[JobSentInformation], is_apply_result: bool
) -> tuple[list[JobSentInformation], list[JobSentInformation]]:
    sent_list, failed_list = list(), list()
    while result_queue.qsize():
        item = result_queue.get()
        sid, uname, result = item.to_tuple()
        if is_apply_result:
            result = result.get()
        if isinstance(result, dict):
            failed_list.append(item)
        else:
            sent_list.append(item)
    return sent_list, failed_list


def group_by_result_list(
        result_list: list[JobSentInformation], is_apply_result: bool
) -> tuple[list[JobSentInformation], list[JobSentInformation]]:
    sent_list, failed_list = list(), list()
    for job_result in result_list:
        _, _, result = job_result.to_tuple()
        if is_apply_result:
            result = result.get()
        if isinstance(result, dict):
            failed_list.append(job_result)
        else:
            sent_list.append(job_result)
    return sent_list, failed_list


def evaluate_broadcast_stats(
        sent_list: list[JobSentInformation], failed_list: list[JobSentInformation]
) -> BroadcastStats:
    n_job = len(sent_list) + len(failed_list)
    n_success = len(sent_list)
    n_failure = len(failed_list)
    return BroadcastStats(n_job, n_success, n_failure)
