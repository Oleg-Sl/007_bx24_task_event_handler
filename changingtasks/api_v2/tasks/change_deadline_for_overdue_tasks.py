import logging
import datetime
import re
import time

from .. import bitrix24


logger_change_deadline = logging.getLogger('change_deadline_for_overdue_tasks')
logger_change_deadline.setLevel(logging.INFO)
fh_change_deadline = logging.handlers.TimedRotatingFileHandler('./logs/change_deadline_for_overdue_tasks.log', when='D', interval=1, backupCount=10)
formatter_change_deadline = logging.Formatter('[%(asctime)s] %(levelname).1s %(message)s')
fh_change_deadline.setFormatter(formatter_change_deadline)
logger_change_deadline.addHandler(fh_change_deadline)


BATCH_SIZE = 15


def run(deadline):
    bx24 = bitrix24.Bitrix24()
    deadline_str = deadline.strftime("%Y-%m-%d") + "T23:00"
    new_deadline_str = deadline.strftime("%Y-%m-%d") + "T12:00"
    deadline_after = deadline - datetime.timedelta(days=1)
    tasks = bx24.request_list("tasks.task.list", ["ID"], {"STATUS": -1, "<DEADLINE": deadline_after.strftime("%Y-%m-%d")})
    logger_change_deadline.info({"tasks": tasks})
    length = len(tasks)
    for i in range(0, length, BATCH_SIZE):
        cmd = {}
        for j in range(i, i + BATCH_SIZE):
            if j >= length:
                break
            task_id = tasks[j].get("id")
            cmd[task_id] = f"tasks.task.update?taskId={task_id}&fields[DEADLINE]={new_deadline_str}&fields[status]=2"
            logger_change_deadline.info({
                "task_id": task_id,
                "deadline": deadline_str,
                "length": len(tasks),
                "requests": f"tasks.task.update?taskId={task_id}&fields[DEADLINE]={new_deadline_str}&fields[status]=2"
            })

        response = bx24.callMethod("batch", {"halt": 0, "cmd": cmd})
        time.sleep(5)

