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
EMOJI_FORWARD_COMMENT__MONTAGE = "⏩"
EMOJI_FORWARD_COMMENT__ORDER_CLOSE = "❌"
EMOJI_FORWARD_COMMENT__ORDER_WARM = ":f09f9aa8:"


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

    ids_task_bind = {
        "montage": deal["UF_CRM_1661089762"],     # монтаж
        "print": deal["UF_CRM_1661089736"],       # поспечать
        "order": deal["UF_CRM_1661089895"],       # передача заказа (заказ)
        "product": deal["UF_CRM_1661089717"]      # производство
    }
    # если комментарий добавлен к задаче - монтаж
    if task_id == ids_task_bind["montage"]:
        comment_added_to_task_montage(bx24, ids_task_bind, comment)

    # если комментарий добавлен к задаче - заказ
    if task_id == ids_task_bind["order"]:
        comment_added_to_task_order(bx24, ids_task_bind, comment)


# комментарий добавлен к задаче на монтаж:
# Коммент в задаче Монтаж,  с символом "⏩" и текст после символа, будет автоматом оставлять сообщение в комментах задач Заказ и Поспечать
def comment_added_to_task_montage(bx24, ids_task_bind, comment):
    # Проверка, что комментарий нужно переслать
    comment_msg = comment.get("POST_MESSAGE").strip()
    author_id = comment.get("AUTHOR_ID")
    files_ids = get_files_data(comment.get("ATTACHED_OBJECTS", {}))
    if not is_forward_comment(comment_msg, EMOJI_FORWARD_COMMENT__MONTAGE):
        return

    file_data = "&".join([f"fields[UF_FORUM_MESSAGE_DOC][]={file_id}" for file_id in files_ids])
    # Добавление комментария в задачу поспечать и передача заказа
    response = bx24.callMethod("batch", {
        "halt": 0,
        "cmd": {
            "1": f"task.commentitem.add?taskId={ids_task_bind['print']}&fields[AUTHOR_ID]={author_id}&fields[POST_MESSAGE]={comment.get('POST_MESSAGE')}&{file_data}",
            "2": f"task.commentitem.add?taskId={ids_task_bind['order']}&fields[AUTHOR_ID]={author_id}&fields[POST_MESSAGE]={comment.get('POST_MESSAGE')}&{file_data}"
        }
    })
    logger_fc.info({
        "stage": 11,
        "task_id": ids_task_bind['montage'],
        "response": response,
    })

    if not response or "result" not in response or "result" not in response["result"]:
        logger_fc.error({
            "errors": f"Не удалось добавить комментарий к задаче {ids_task_bind['print']}, {ids_task_bind['order']} из задачи {ids_task_bind['montage']}",
            "id_task_from": ids_task_bind['montage'],
            "ids_tasks_to": [ids_task_bind['print'], ids_task_bind['order']],
            "text_message": comment.get("POST_MESSAGE"),
            "response": response
        })


# Коммент в задаче Заказ, с символом "❌" и текст после символа, будет ставить автоматом задачу на "отложена" и
# оставлять сообщение в комментах задач производство и монтаж
# Коммент в задаче Заказ,  с символом "🚨" и текст после символа, будет автоматом оставлять сообщение в комментах
# задач Производство, Поспечать, Монтаж (например важно сообщить всем о новых сроках, или новых вводных и тд.)
def comment_added_to_task_order(bx24, ids_task_bind, comment):
    # Проверка, что комментарий нужно переслать
    comment_msg = comment.get("POST_MESSAGE").strip()
    author_id = comment.get("AUTHOR_ID")
    files_ids = get_files_data(comment.get("ATTACHED_OBJECTS", {}))
    file_data = "&".join([f"fields[UF_FORUM_MESSAGE_DOC][]={file_id}" for file_id in files_ids])

    logger_fc.info({
        "task": "ORDER",
        "stage": 10,
        "task_id": ids_task_bind['order'],
        "comment_msg": comment_msg,
    })

    if is_forward_comment(comment_msg, EMOJI_FORWARD_COMMENT__ORDER_CLOSE):
        cmd = {
            "1": f"tasks.task.defer?taskId={ids_task_bind['order']}",
            "2": f"task.commentitem.add?taskId={ids_task_bind['product']}&fields[AUTHOR_ID]={author_id}&fields[POST_MESSAGE]={comment.get('POST_MESSAGE')}&{file_data}",
            "3": f"task.commentitem.add?taskId={ids_task_bind['montage']}&fields[AUTHOR_ID]={author_id}&fields[POST_MESSAGE]={comment.get('POST_MESSAGE')}&{file_data}"
        }
    elif is_forward_comment(comment_msg, EMOJI_FORWARD_COMMENT__ORDER_WARM):
        cmd = {
            "1": f"task.commentitem.add?taskId={ids_task_bind['product']}&fields[AUTHOR_ID]={author_id}&fields[POST_MESSAGE]={comment.get('POST_MESSAGE')}&{file_data}",
            "2": f"task.commentitem.add?taskId={ids_task_bind['print']}&fields[AUTHOR_ID]={author_id}&fields[POST_MESSAGE]={comment.get('POST_MESSAGE')}&{file_data}",
            "3": f"task.commentitem.add?taskId={ids_task_bind['montage']}&fields[AUTHOR_ID]={author_id}&fields[POST_MESSAGE]={comment.get('POST_MESSAGE')}&{file_data}"
        }
    else:
        return

    response = bx24.callMethod("batch", {"halt": 0, "cmd": cmd})

    logger_fc.info({
        "stage": 11,
        "task_id": ids_task_bind['order'],
        "response": response,
    })

    if not response or "result" not in response or "result" not in response["result"]:
        logger_fc.error({
            "errors": f"Не удалось добавить комментарий к задачам",
            "id_task_from": ids_task_bind['order'],
            "ids_tasks_to": [ids_task_bind['product'], ids_task_bind['print'], ids_task_bind['montage']],
            "text_message": comment.get("POST_MESSAGE"),
            "response": response
        })



def get_id_from_binding(arr_binding, prefix):
    if not isinstance(arr_binding, list) or not arr_binding:
        return

    for binding in arr_binding:
        arr_entity_data_ = binding.split("_")
        if len(arr_entity_data_) == 2 and arr_entity_data_[0] == prefix:
            return arr_entity_data_[1]


def is_forward_comment(comment, emoji_starting):
    match = re.match(r"(\[.+\].+\[.+\])?(.+)", comment)
    if not match or len(match.groups()) != 2:
        return
    if match.group(2).strip().startswith(emoji_starting):
        return True


def get_files_data(files_):
    files_ids = []
    for _, f_data in files_.items():
        f_id = f_data.get("FILE_ID")
        files_ids.append(f"n{f_id}")
    return files_ids
