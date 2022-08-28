# from mainapp.models import Deal, Stage
# from api_v1.serializers import DealSerializer
import logging
import datetime


from . import bitrix24
from ..models import Task

logger_success = logging.getLogger('success')
logger_success.setLevel(logging.INFO)
fh_success = logging.handlers.TimedRotatingFileHandler('./logs/success.log', when='D', interval=1, backupCount=14)
formatter_success = logging.Formatter('[%(asctime)s] %(levelname).1s %(message)s')
fh_success.setFormatter(formatter_success)
logger_success.addHandler(fh_success)

logger_error = logging.getLogger('error')
logger_error.setLevel(logging.ERROR)
fh_error = logging.handlers.TimedRotatingFileHandler('./logs/error.log', when='D', interval=1, backupCount=14)
formatter_error = logging.Formatter('[%(asctime)s] %(levelname).1s %(message)s')
fh_error.setFormatter(formatter_error)
logger_error.addHandler(fh_error)

USER_OPEN_TASK = 255
FIELD_DEAL__TASK_ORDER_TRANSFER = 'UF_CRM_1661089895'

# объект выполнения запросов к Битрикс
bx24 = bitrix24.Bitrix24()


#
# FIELD_DEAL_TASK = {
#     # "measuring": "UF_CRM_1661089690",               # ID задачи на замер
#     # "production": "UF_CRM_1661089717",              # ID задачи на производство
#     # "pospechat": "UF_CRM_1661089736",               # ID задачи на поспечать
#     # "montage": "UF_CRM_1661089762",                 # ID задачи на монтаж
#     # "closing_doc": "UF_CRM_1661089782",             # ID задачи на закрывающие документы
#     # "invoice": "UF_CRM_1661089811",                 # ID задачи на счет
#     # "order_transfer": "UF_CRM_1661089895",          # ID задачи "Передача заказа"
#     # "design": "UF_CRM_1661089657",                  # ID задачи на дизайн
#     # "invoice_payment": "UF_CRM_1661253202",         # ID задачи счет на предоплату/постоплату
# }
#
# STATUS_TASK = {
#     "2": "Ждет выполнения",
#     "3": "Выполняется",
#     "4": "Ожидает контроля",
#     "5": "Завершена",
#     "6": "Отложена"
# }


# получение общего имени задачи
def get_task_name(deal, id_task):
    if (deal.get("UF_CRM_1661089690") == id_task):
        return 'задача на замер'
    elif (deal.get("UF_CRM_1661089717") == id_task):
        return 'задача на производство'
    elif (deal.get("UF_CRM_1661089736") == id_task):
        return 'задача на поспечать'
    elif (deal.get("UF_CRM_1661089762") == id_task):
        return 'задача на монтаж'
    elif (deal.get("UF_CRM_1661089782") == id_task):
        return 'задача на закрывающие документы'
    elif (deal.get("UF_CRM_1661089811") == id_task):
        return 'задача на счет'
    elif (deal.get("UF_CRM_1661089895") == id_task):
        return 'задача на передачу заказа'
    elif (deal.get("UF_CRM_1661089657") == id_task):
        return 'задача на дизайн'
    elif (deal.get("UF_CRM_1661253202") == id_task):
        return 'задача счет на предоплату/постоплату'


# получение текста комментария задачи
def get_comment_task(status, task_name):
    if status == '2':
        desc = f'Создана "{task_name}"'
    elif status == '3':
        desc = f'"{task_name}" выполняется'
    elif status == '4':
        desc = f'"{task_name}" ожидает контроля'
    elif status == '5':
        desc = f'"{task_name}" завершена'
    elif status == '6':
        desc = f'"{task_name}" отложена'
    return desc


# получение ссылки на задачу
def get_link_task(id_task, title_task):
    return f"<a href='/company/personal/user/{USER_OPEN_TASK}/tasks/task/view/{id_task}/'>{title_task}</a>"


# получение данных о задаче из Битрикс
def get_task_data(id_task):
    response = bx24.call(
        "tasks.task.get",
        {
            "taskId": id_task,
            "select": ["UF_CRM_TASK", "STATUS", "TITLE", "DEADLINE"]
        }
    )
    return response


# получение данных о сделке из Битрикс
def get_deal_data(id_deal):
    response = bx24.call(
        "crm.deal.get",
        {
            "id": id_deal
        }
    )
    return response


# добавление комментария к задаче
def send_comment(id_task_order_transfer, text_comment):
    response = bx24.call(
        "task.commentitem.add",
        {
            "taskId": id_task_order_transfer,
            "fields": {"POST_MESSAGE": text_comment}
        }
    )
    # response = ""
    return response


# обновление крайнего срока в главной задаче
def update_date(id_task, date):
    response = bx24.call(
        "tasks.task.update",
        {
            "taskId": id_task,
            "fields": {"DEADLINE": date.isoformat()}
        }
    )
    return response


# получение ID сделки из массива привязок к сущностям CRM
def get_id_deal_from_line_str(line, prefix):
    if not isinstance(line, list) or not line:
        return

    arr = line[0].split("_")
    if len(arr) == 2 and arr[0] == prefix:
        return arr[1]


# получение ID задачи из сделки по названию поля
def get_id_task_from_deal(deal, field_name):
    return deal.get(field_name)


# прокидывание комментариев в задачу "Передача заказа"
def throwing_comments(task, deal):
    # print("task = ", task)
    # print("deal = ", deal)

    exist_task = Task.objects.filter(id_bx=task["id"]).first()

    if exist_task and exist_task.status == task["status"]:
        logger_error.error({
            "event": "add comment",
            "exist_task.status": exist_task.status if exist_task else None,
            "status": task["status"],
            "message": f"Статус задачи с ID = {task['id']} не изменился",
        })
        return

    task_name_rus = get_task_name(deal, task["id"])

    if not task_name_rus:
        logger_error.error({
            "event": "add comment",
            "id_deal": deal["ID"],
            "message": f"Не удалось получить общее название задачи с ID = {task['id']}",
        })
        return

    text_comment = get_comment_task(task["status"], task_name_rus)
    text_comment += f": {get_link_task(task['id'], task['title'])}"

    id_task_recipient_comment = get_id_task_from_deal(deal, FIELD_DEAL__TASK_ORDER_TRANSFER)
    if id_task_recipient_comment == task['id']:
        return

    if not id_task_recipient_comment:
        logger_error.error({
            "event": "add comment",
            "id_deal": deal["ID"],
            "message": "В сделке отсутствует поле c ID задачи на передачу заказа",
        })
        return

    # отправка комментария
    send_comment(id_task_recipient_comment, text_comment)

    if exist_task:
        exist_task.status = task["status"]
    else:
        exist_task = Task(id_bx=task["id"], status=task["status"])
    exist_task.save()

    logger_success.info({
        "event": "add comment",
        "id_deal": deal["ID"],
        "id_task_recipient": id_task_recipient_comment,
        "comment": text_comment
    })


# изменение крайнего срока задачи "Передача заказа"
def change_deadline(task, deal):
    id_task_minor = task["id"]
    id_task_main = get_id_task_from_deal(deal, FIELD_DEAL__TASK_ORDER_TRANSFER)

    if id_task_main == id_task_minor:
        return

    if not id_task_main:
        logger_error.error({
            "event": "change deadline",
            "id_deal": deal["ID"],
            "message": "В сделке отсутствует поле c ID задачи на передачу заказа",
        })
        return

    # получение данных главной задачи
    result_task = get_task_data(id_task_main)
    if not result_task or "result" not in result_task or "task" not in result_task["result"]:
        logger_error.error({
            "event": "Change deadline",
            "task_id": id_task_main,
            "response": result_task,
            "message": "Не удалось получить данные задачи",
        })
        return

    # Крайние сроки главной и побочной задачи в виде строки
    deadline_str_main = result_task["result"]["task"]["deadline"]
    deadline_str_minor = task["deadline"]
    deadline_main = None
    deadline_minor = None

    if deadline_str_main:
        deadline_main = datetime.datetime.strptime(deadline_str_main, "%Y-%m-%dT%H:%M:%S%z")

    if deadline_str_minor:
        deadline_minor = datetime.datetime.strptime(deadline_str_minor, "%Y-%m-%dT%H:%M:%S%z")

    # обновление крайнего срока главной задачи
    if not deadline_main or deadline_main < deadline_minor:
        update_date(id_task_main, deadline_minor)


