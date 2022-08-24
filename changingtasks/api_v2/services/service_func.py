# from mainapp.models import Deal, Stage
# from api_v1.serializers import DealSerializer
import logging


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
            "select": ["UF_CRM_TASK", "STATUS", "TITLE"]
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
    logger_error.error({
        "event": "ТЕКСТ КОММЕНТАРИЯ",
        "id_task": task['id'],
        "text_comment": text_comment
    })
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








# def get_deal(id_task):
#     response = bx24.bath({
#         "halt": 0,
#         "cmd": {
#             "zamer": f"crm.deal.list?filter[UF_CRM_1661089690]={id_task},
#             "zamer": "crm.deal.list?filter[UF_CRM_1661089717]=",
#             "task": "tasks.task.get"
#
#         }
#     })
    # 'tasks.task.get',
# "crm.deal.list",
#     {
#         order: { "STAGE_ID": "ASC" },
#         filter: { ">PROBABILITY": 50 },
#         select: [ "ID", "TITLE", "STAGE_ID", "PROBABILITY", "OPPORTUNITY", "CURRENCY_ID" ]
#     },

# {taskId: 1, select: ['ID', 'TITLE']},
# response_deal = bx24.call(
#         "crm.deal.get",
#         {
#             "id": id_deal
#         }
#     )



# def create_or_update(id_deal):
#     """ Сохранение компании из BX24 """
#     response_deal = bx24.call(
#         "crm.deal.get",
#         {
#             "id": id_deal
#         }
#     )
#
#     if not response_deal or "result" not in response_deal:
#         return response_deal
#
#     direction = response_deal["result"]["CATEGORY_ID"]
#     if direction in [43, "43"]:
#         direction = response_deal["result"]["UF_CRM_1610523951"]
#
#     stage_abbrev = response_deal["result"]["STAGE_ID"]
#     stage = Stage.objects.get(abbrev=stage_abbrev)
#
#     deal = {
#         "id_bx": response_deal["result"]["ID"],
#         "title": response_deal["result"]["TITLE"],
#         "date_create": response_deal["result"]["DATE_CREATE"],
#         "date_modify": response_deal["result"]["DATE_MODIFY"],
#         "date_closed": response_deal["result"]["CLOSEDATE"] or None,
#         "closed": True if response_deal["result"]["CLOSED"] == "Y" else False,
#         "opportunity": response_deal["result"]["OPPORTUNITY"],
#         "balance_on_payments": editing_numb(response_deal["result"]["UF_CRM_1575629957086"]),
#         "amount_paid": editing_numb(response_deal["result"]["UF_CRM_1575375338"]),
#         "company": response_deal["result"]["COMPANY_ID"],
#         "direction": direction,
#         "stage": stage.pk,
#     }
#
#     exist_deal = Deal.objects.filter(id_bx=deal["id_bx"]).first()
#     if not exist_deal:
#         # при создании
#         serializer = DealSerializer(data=deal)
#     else:
#         # при обновлении
#         serializer = DealSerializer(exist_deal, data=deal)
#
#     if serializer.is_valid():
#         serializer.save()
#         return serializer.data
#
#     return serializer.errors
#
#
# def editing_numb(numb):
#     """ Преобразует денежное значение из BX24 в число """
#     numb = numb.split("|")[0] or "0"
#     if numb:
#         return f"{float(numb):.2f}"
#     else:
#         return None