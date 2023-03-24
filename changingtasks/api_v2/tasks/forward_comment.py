import re
import logging
from .. import bitrix24


logger_fc = logging.getLogger('forward_comment')
logger_fc.setLevel(logging.INFO)
fh_fc = logging.handlers.TimedRotatingFileHandler('./logs/forward_comment.log', when='D', interval=1, backupCount=10)
formatter_fc = logging.Formatter('[%(asctime)s] %(levelname).1s %(message)s')
fh_fc.setFormatter(formatter_fc)
logger_fc.addHandler(fh_fc)

# Комментарии начинающиеся с этого смайлика будут прокидываться в другую задачу
EMOJI_FORWARD_COMMENT = "⏩"


def run(task_id, comment_id):
    bx24 = bitrix24.Bitrix24()

    # Получение задачи и комментария
    response = bx24.callMethod("batch", {
        "halt": 0,
        "cmd": {
            "task": f"tasks.task.get?taskId={task_id}&select[]=UF_CRM_TASK",
            "comment": f"task.commentitem.get?taskId={task_id}&itemId={comment_id}"
        }
    })
    logger_fc.info({
        "stage": 0,
        "task_id": task_id,
        "response": response
    })
    if not response or "result" not in response or "result" not in response["result"]:
        logger_fc.info({
            "errors": f"Не удалось получить данные задачи {task_id} и комментария {comment_id}",
            "id_task_from": task_id,
            "comment_id": comment_id,
            "response": response
        })
        return

    task = response.get("result", {}).get("result", {}).get("task", {}).get("task", {})
    comment = response.get("result", {}).get("result", {}).get("comment", {})

    logger_fc.info({
        "stage": 1,
        "task_id": task_id,
        "task": task,
        "comment": comment
    })
    # Проверка, что комментарий нужно переслать
    comment_msg = comment.get("POST_MESSAGE").strip()
    author_id = comment.get("AUTHOR_ID")
    files_ids = get_files_data(comment.get("ATTACHED_OBJECTS", {}))
    if not is_forward_comment(comment_msg):
        return

    # Получение ID связанной с задачей сделки
    id_deal = get_id_from_binding(task["ufCrmTask"], "D")
    if not id_deal:
        return

    # Получение данных сделки
    deal = bx24.callMethod("crm.deal.get", {"id": id_deal}).get("result")
    logger_fc.info({
        "stage": 2,
        "task_id": task_id,
        "deal": deal
    })
    id_task_montage = deal["UF_CRM_1661089762"]     # монтаж
    id_task_print = deal["UF_CRM_1661089736"]       # поспечать
    id_task_order = deal["UF_CRM_1661089895"]       # передача заказа

    # если комментарий добавлен не в задачу на монтаж
    if task_id != id_task_montage:
        return

    # Добавление комментария в задачу поспечать и передача заказа
    # response = bx24.callMethod("batch", {
    #     "halt": 0,
    #     "cmd": {
    #         "1": f"task.commentitem.add?taskId={id_task_print}&fields[POST_MESSAGE]={comment.get('POST_MESSAGE')}",
    #         "2": f"task.commentitem.add?taskId={id_task_order}&fields[POST_MESSAGE]={comment.get('POST_MESSAGE')}"
    #     }
    # })
    response = bx24.call("task.commentitem.add", {
        "taskId": id_task_print,
        "fields": {
            "AUTHOR_ID": author_id,
            "POST_MESSAGE": comment_msg,
            "UF_FORUM_MESSAGE_DOC": files_ids
        }
    })
    logger_fc.info({
        "stage": 3,
        "task_id": task_id,
        "response": response
    })
    response = bx24.call("task.commentitem.add", {
        "taskId": id_task_order,
        "fields": {
            "AUTHOR_ID": author_id,
            "POST_MESSAGE": comment_msg,
            "UF_FORUM_MESSAGE_DOC": files_ids
        }
    })
    logger_fc.info({
        "stage": 4,
        "task_id": task_id,
        "response": response
    })
    # if not response or "result" not in response or "result" not in response["result"]:
    #     logger_fc.info({
    #         "errors": f"Не удалось добавить комментарий к задаче {id_task_print}, {id_task_order} из задачи {id_task_montage}",
    #         "id_task_from": id_task_montage,
    #         "ids_tasks_to": [id_task_print, id_task_order],
    #         "text_message": comment.get("POST_MESSAGE"),
    #         "response": response
    #     })


def get_id_from_binding(arr_binding, prefix):
    if not isinstance(arr_binding, list) or not arr_binding:
        return

    for binding in arr_binding:
        arr_entity_data_ = binding.split("_")
        if len(arr_entity_data_) == 2 and arr_entity_data_[0] == prefix:
            return arr_entity_data_[1]


def is_forward_comment(comment):
    match = re.match(r"(\[.+\].+\[.+\])?(.+)", comment)
    if not match or len(match.groups()) != 2:
        return
    if match.group(2).strip().startswith(EMOJI_FORWARD_COMMENT):
        return True


def get_files_data(files_):
    files_ids = []
    for _, f_data in files_.items():
        f_id = f_data.get("FILE_ID")
        files_ids.append(f"n{f_id}")
    return files_ids
