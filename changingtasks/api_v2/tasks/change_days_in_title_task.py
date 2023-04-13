import re
import logging
from .. import bitrix24


logger_change_days = logging.getLogger('change_days_in_title_task')
logger_change_days.setLevel(logging.INFO)
fh_change_days = logging.handlers.TimedRotatingFileHandler('./logs/change_days_in_title_task.log', when='D', interval=1, backupCount=10)
formatter_change_days = logging.Formatter('[%(asctime)s] %(levelname).1s %(message)s')
fh_change_days.setFormatter(formatter_change_days)
logger_change_days.addHandler(fh_change_days)




def run(task_id):
    bx24 = bitrix24.Bitrix24()

    # Получение задачи и комментария
    response = bx24.callMethod("tasks.task.get", {
        "taskId": task_id
    })
    logger_change_days.info({
        "stage": 0,
        "task_id": task_id,
        "response": response
    })
    if not response or "result" not in response or "task" not in response["result"]:
        logger_change_days.info({
            "errors": f"Не удалось получить данные задачи {task_id}",
            "id_task_from": task_id,
            "response": response
        })
        return

    task = response.get("result", {}).get("task", {})
    title = task.get("title")
    if task_id and title:
        new_title = get_new_title(title)
        if new_title:
            response = bx24.callMethod("tasks.task.update", {
                "taskId": task_id,
                "fields": {
                    "TITLE": new_title
                }
            })
            logger_change_days.info({
                "stage": 1,
                "task_id": task_id,
                "response": response,
            })
            return
    logger_change_days.info({
        "errors": f"Не удалось обновить название задачи {task_id}",
        "id_task_from": task_id,
        "response": response
    })


def get_new_title(title_old):
    title_new = None
    days_math = re.search("\((\d+)\)", title_old)
    if days_math:
        days = int(days_math.group(1)) + 1
        title_new = re.sub("\(\d+\)", f"({days})", title_old)

    return title_new


