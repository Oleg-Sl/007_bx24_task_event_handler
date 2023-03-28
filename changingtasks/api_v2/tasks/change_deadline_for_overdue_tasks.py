import logging
import datetime
import re

from .. import bitrix24


logger_change_deadline = logging.getLogger('change_deadline_for_overdue_tasks')
logger_change_deadline.setLevel(logging.INFO)
fh_change_deadline = logging.handlers.TimedRotatingFileHandler('./logs/change_deadline_for_overdue_tasks.log', when='D', interval=1, backupCount=10)
formatter_change_deadline = logging.Formatter('[%(asctime)s] %(levelname).1s %(message)s')
fh_change_deadline.setFormatter(formatter_change_deadline)
logger_change_deadline.addHandler(fh_change_deadline)


BATCH_SIZE = 25


def run(deadline):
    bx24 = bitrix24.Bitrix24()
    deadline_str = deadline.strftime("%Y-%m-%d")
    tasks = bx24.request_list("tasks.task.list", ["ID"], {"STATUS": -1})

    length = len(tasks)
    for i in range(0, length, BATCH_SIZE):
        cmd = {}
        for j in range(i, i + BATCH_SIZE):
            if j >= length:
                break
            task_id = tasks[j].get("id")
            cmd[task_id] = f"tasks.task.update?taskId={task_id}&fields[DEADLINE]={deadline_str}&fields[status]=2"
            logger_change_deadline.info({
                "task_id": task_id,
                "deadline": deadline_str,
                "length": len(tasks)
            })

        response = bx24.callMethod("batch", {"halt": 0, "cmd": cmd})

