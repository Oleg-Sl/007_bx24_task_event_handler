from rest_framework import views, status
from rest_framework.response import Response
from django.shortcuts import render
from django.views.decorators.clickjacking import xframe_options_exempt
import logging
import datetime
from threading import Thread

from . import bitrix24
from .services import service
from .services import service_func, tokens
from .tasks import forward_comment, change_deadline_for_overdue_tasks, change_days_in_title_task

logger_error = logging.getLogger('error')
logger_error.setLevel(logging.INFO)
fh_error = logging.handlers.TimedRotatingFileHandler('./logs/error.log', when='D', interval=1, backupCount=10)
formatter_error = logging.Formatter('[%(asctime)s] %(levelname).1s %(message)s')
fh_error.setFormatter(formatter_error)
logger_error.addHandler(fh_error)

# логгер входные данные событий
logger_access = logging.getLogger('api_v2_access')
logger_access.setLevel(logging.INFO)
fh_access = logging.handlers.TimedRotatingFileHandler('./logs/access.log', when='D', interval=1, backupCount=10)
formatter_access = logging.Formatter('[%(asctime)s] %(levelname).1s %(message)s')
fh_access.setFormatter(formatter_access)
logger_access.addHandler(fh_access)

token_data = service.get_token()
APPLICATION_TOKEN = token_data.get("application_token", None)


class InstallApiView(views.APIView):
    @xframe_options_exempt
    def post(self, request):
        data = {
            "domain": request.data.get("auth[domain]", "atonlab.bitrix24.ru"),
            "auth_token": request.data.get("auth[access_token]", ""),
            "expires_in": request.data.get("auth[expires_in]", 3600),
            "refresh_token": request.data.get("auth[refresh_token]", ""),
            "application_token": request.data.get("auth[application_token]", ""),   # используется для проверки достоверности событий Битрикс24
            'client_endpoint': f'https://{request.data.get("auth[domain]", "atonlab.bitrix24.ru")}/rest/',
        }
        tokens.save_secrets(data)
        return render(request, 'install_2.html')


class TaskCreateApiView(views.APIView):
    def post(self, request):
        logger_access.info({
            "url_path": "api/v2/task-create/",
            "handler": "TaskCreateApiView",
            "query_params": request.data,
            "data[FIELDS_AFTER][ID]": request.data.get("data[FIELDS_AFTER][ID]", ""),
        })

        # task_id = request.query_params.get("data[FIELDS_AFTER][ID]", "")
        task_id = request.data.get("data[FIELDS_AFTER][ID]", "")
        application_token = request.data.get("auth[application_token]", None)

        # if application_token != APPLICATION_TOKEN:
        #     return Response("Unverified event source", status=status.HTTP_400_BAD_REQUEST)

        if not task_id:
            return Response("Not transferred ID task", status=status.HTTP_400_BAD_REQUEST)

        # получение данных сущности - задача
        result_task = service_func.get_task_data(task_id)
        if not result_task or "result" not in result_task or "task" not in result_task["result"]:
            logger_error.error({
                "event": "TaskUpdateApiView",
                "task_id": task_id,
                "response": result_task,
                "message": "Не удалось получить данные задачи",
            })
            return Response("No response from bitrix", status=status.HTTP_400_BAD_REQUEST)

        task = result_task["result"]["task"]
        if "ufCrmTask" not in task:
            logger_error.error({
                "event": "TaskUpdateApiView",
                "result_task": result_task["result"],
                "message": "Отсутствует поле с привязками задачи к CRM сущностям",
            })
            return Response("The task is not tied to the crm entity", status=status.HTTP_400_BAD_REQUEST)

        id_deal = service_func.get_id_deal_from_line_str(task["ufCrmTask"], "D")
        if not id_deal:
            logger_error.error({
                "event": "TaskUpdateApiView",
                "id_deal": task["ufCrmTask"],
                "message": "Отсутствует привязка задачи к сделке",
            })
            return Response("The task is not linked to the deal", status=status.HTTP_400_BAD_REQUEST)

        # получение данных сущности - сделка
        result_deal = service_func.get_deal_data(id_deal)
        if not result_deal or "result" not in result_deal:
            logger_error.error({
                "event": "TaskUpdateApiView",
                "id_deal": id_deal,
                "response": result_deal,
                "message": "Не удалось получить данные сделки",
            })
            return Response("No response from bitrix", status=status.HTTP_400_BAD_REQUEST)

        deal = result_deal["result"]

        # проброс комментариев в задачу
        service_func.throwing_comments(task, deal)
        # # изменение крайнего строка выполнения главной задачи
        # service_func.change_deadline(task, deal)

        return Response("OK", status=status.HTTP_200_OK)


class TaskUpdateApiView(views.APIView):

    def post(self, request):
        logger_access.info({
            "url_path": "api/v2/task-update/",
            "handler": "TaskUpdateApiView",
            "query_params": request.data,
            "data[FIELDS_AFTER][ID]": request.data.get("data[FIELDS_AFTER][ID]", ""),
        })

        task_id = request.data.get("data[FIELDS_AFTER][ID]", "")
        application_token = request.data.get("auth[application_token]", None)

        if not task_id:
            logger_error.error("Not transferred ID task")
            return Response("Not transferred ID task", status=status.HTTP_400_BAD_REQUEST)

        # получение данных сущности - задача
        result_task = service_func.get_task_data(task_id)
        if not result_task or "result" not in result_task or "task" not in result_task["result"]:
            logger_error.error({
                "event": "TaskUpdateApiView",
                "task_id": task_id,
                "response": result_task,
                "message": "Не удалось получить данные задачи",
            })
            return Response("No response from bitrix", status=status.HTTP_400_BAD_REQUEST)

        task = result_task["result"]["task"]
        if "ufCrmTask" not in task:
            logger_error.error({
                "event": "TaskUpdateApiView",
                "result_task": result_task["result"],
                "message": "Отсутствует поле с привязками задачи к CRM сущностям",
            })
            return Response("The task is not tied to the crm entity", status=status.HTTP_400_BAD_REQUEST)

        id_deal = service_func.get_id_deal_from_line_str(task["ufCrmTask"], "D")
        if not id_deal:
            logger_error.error({
                "event": "TaskUpdateApiView",
                "id_deal": task["ufCrmTask"],
                "message": "Отсутствует привязка задачи к сделке",
            })
            return Response("The task is not linked to the deal", status=status.HTTP_400_BAD_REQUEST)


        # получение данных сущности - сделка
        result_deal = service_func.get_deal_data(id_deal)
        if not result_deal or "result" not in result_deal:
            logger_error.error({
                "event": "TaskUpdateApiView",
                "id_deal": id_deal,
                "response": result_deal,
                "message": "Не удалось получить данные сделки",
            })
            return Response("No response from bitrix", status=status.HTTP_400_BAD_REQUEST)

        deal = result_deal["result"]

        # проброс комментариев в главную задачу
        service_func.throwing_comments(task, deal)
        # # изменение крайнего строка выполнения главной задачи
        # service_func.change_deadline(task, deal)
        # Отслеживание изменения названия задачи на монтаж и проброс ее крайнего срока в комментарии задач на поспечать и производство
        service_func.add_deadline_task_montage_in_taskpospechat_and_prod(task, deal)

        return Response("OK", status=status.HTTP_200_OK)


class TaskDeleteApiView(views.APIView):
    pass


class TaskChangeStatusApiView(views.APIView):
    def post(self, request):
        logger_access.info({
            "url_path": "api/v2/task-change-status/",
            "handler": "TaskChangeStatusApiView",
            "query_params": request.data,
        })
        task_id = request.data.get("task_id", "")
        emoji = request.data.get("emoji", None)
        application_token = request.data.get("application_token", None)

        # logger_error.info({
        #     "task_id": task_id,
        #     "request.data": request.data
        # })

        if application_token != APPLICATION_TOKEN:
            return Response("Unverified event source", status=status.HTTP_400_BAD_REQUEST)

        if not task_id:
            return Response("Not transferred ID task", status=status.HTTP_400_BAD_REQUEST)

        if not emoji:
            return Response("Not transferred new emoji", status=status.HTTP_400_BAD_REQUEST)

        # получение данных сущности - задача
        result_task = service_func.get_task_data(task_id)
        if not result_task or "result" not in result_task or "task" not in result_task["result"]:
            logger_error.error({
                "event": "TaskChangeStatusApiView",
                "task_id": task_id,
                "response": result_task,
                "message": "Не удалось получить данные задачи",
            })
            return Response("No response from bitrix", status=status.HTTP_400_BAD_REQUEST)

        task = result_task["result"]["task"]

        # изменение первого смайлика в названии задачи
        res = service_func.change_smile_in_title_task(task, emoji)

        return Response(res, status=status.HTTP_200_OK)


class TaskDataApiView(views.APIView):
    def post(self, request):
        logger_access.info({
            "url_path": "api/v2/task-data/",
            "handler": "TaskDataApiView",
            "query_params": request.data,
        })
        task_id = request.data.get("task_id", "")
        application_token = request.data.get("application_token", None)

        # logger_error.info({
        #     "task_id": task_id,
        #     "request.data": request.data
        # })

        if application_token != APPLICATION_TOKEN:
            return Response("Unverified event source", status=status.HTTP_400_BAD_REQUEST)

        if not task_id:
            return Response("Not transferred ID task", status=status.HTTP_400_BAD_REQUEST)

        # получение данных сущности - задача
        result_task = service_func.get_task_data(task_id)
        if not result_task or "result" not in result_task or "task" not in result_task["result"]:
            logger_error.error({
                "event": "TaskDataApiView",
                "task_id": task_id,
                "response": result_task,
                "message": "Не удалось получить данные задачи",
            })
            return Response("No response from bitrix", status=status.HTTP_400_BAD_REQUEST)

        task = result_task["result"]["task"]

        # # изменение первого смайлика в названии задачи
        # res = service_func.change_smile_in_title_task(task, emoji)

        return Response(task, status=status.HTTP_200_OK)


class TaskChangeDeadlineApiView(views.APIView):
    def post(self, request):
        logger_access.info({
            "url_path": "api/v2/task-change-deadline/",
            "handler": "TaskChangeDeadlineApiView",
            "query_params": request.data,
        })
        task_id = request.data.get("task_id", "")
        deadline = request.data.get("deadline", "")
        application_token = request.data.get("application_token", None)

        # logger_error.info({
        #     "task_id": task_id,
        #     "request.data": request.data
        # })

        if application_token != APPLICATION_TOKEN:
            return Response("Unverified event source", status=status.HTTP_400_BAD_REQUEST)

        if not task_id:
            return Response("Not transferred ID task", status=status.HTTP_400_BAD_REQUEST)

        if not deadline:
            return Response("Not transferred deadline task", status=status.HTTP_400_BAD_REQUEST)

        # изменение дедлайна задачи
        res = service_func.change_deadline_task(task_id, deadline)

        return Response(res, status=status.HTTP_200_OK)


class TaskCommentCreateApiView(views.APIView):
    def post(self, request):
        logger_access.info({
            "handler": "TaskCommentCreateApiView",
            "data": request.data,
            "query_params": request.query_params
        })
        task_id = request.data.get("data[FIELDS_AFTER][TASK_ID]", None)
        comment_id = request.data.get("data[FIELDS_AFTER][ID]", None)
        application_token = request.data.get("auth[application_token]", None)

        if not task_id:
            return Response("Not transferred ID task", status=status.HTTP_400_BAD_REQUEST)

        if not comment_id:
            return Response("Not transferred ID comment", status=status.HTTP_400_BAD_REQUEST)

        thr = Thread(target=forward_comment.run, args=(task_id, comment_id,))
        thr.start()

        return Response("Обновление списка сотрудников началось", status=status.HTTP_200_OK)


class ChangeDeadlineForOverdueTasksApiView(views.APIView):
    def post(self, request):
        logger_access.info({
            "handler": "ChangeDeadlineForOverdueTaskApiView",
            "data": request.data,
            "query_params": request.query_params
        })
        # deadline = request.query_params.get("deadline", datetime.datetime.now().strftime("%Y-%m-%d")) or datetime.datetime.now().strftime("%Y-%m-%d")
        application_token = request.query_params.get("application_token", None)
        if application_token != APPLICATION_TOKEN:
            return Response("Unverified event source", status=status.HTTP_400_BAD_REQUEST)

        deadline_str = request.query_params.get("deadline")
        if not deadline_str:
            return Response("Не передан параметр deadline, формат 29.03.2023", status=status.HTTP_400_BAD_REQUEST)

        deadline = datetime.datetime.strptime(deadline_str, "%d.%m.%Y")
        thr = Thread(target=change_deadline_for_overdue_tasks.run, args=(deadline,))
        thr.start()

        return Response("Обновление крайнего срока задач началось", status=status.HTTP_200_OK)


class ChangeCountDaysInTaskTitleApiView(views.APIView):
    def post(self, request):
        logger_access.info({
            "handler": "ChangeCountDaysInTaskTitleApiView",
            "data": request.data,
            "query_params": request.query_params
        })
        application_token = request.query_params.get("application_token", None)
        if application_token != APPLICATION_TOKEN:
            return Response("Unverified event source", status=status.HTTP_400_BAD_REQUEST)

        task_id = request.query_params.get("task_id")
        if not task_id:
            return Response("Не передан параметр task_id", status=status.HTTP_400_BAD_REQUEST)

        thr = Thread(target=change_days_in_title_task.run, args=(task_id,))
        thr.start()

        return Response("Изменение кол-во дней в названии задачи началось", status=status.HTTP_200_OK)







