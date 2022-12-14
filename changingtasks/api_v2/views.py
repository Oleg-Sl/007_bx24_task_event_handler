from rest_framework import views, status
from rest_framework.response import Response
from django.shortcuts import render
from django.views.decorators.clickjacking import xframe_options_exempt
import logging

from . import bitrix24
from .services import service
from .services import service_func, tokens

logger_error = logging.getLogger('error')
logger_error.setLevel(logging.INFO)
fh_error = logging.handlers.TimedRotatingFileHandler('./logs/error.log', when='D', interval=1, backupCount=14)
formatter_error = logging.Formatter('[%(asctime)s] %(levelname).1s %(message)s')
fh_error.setFormatter(formatter_error)
logger_error.addHandler(fh_error)

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
        logger_error.info({
            "auth[application_token]": request.data.get("auth[application_token]", None),
            "data[FIELDS_AFTER][ID]": request.data.get("data[FIELDS_AFTER][ID]", ""),
            "request.data": request.data
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
        logger_error.info({
            "data[FIELDS_AFTER][ID]": request.data.get("data[FIELDS_AFTER][ID]", ""),
            "request.data": request.data
        })
        task_id = request.data.get("data[FIELDS_AFTER][ID]", "")
        application_token = request.data.get("auth[application_token]", None)

        # if application_token != APPLICATION_TOKEN:
        #     logger_error.error("Unverified event source")
        #     return Response("Unverified event source", status=status.HTTP_400_BAD_REQUEST)

        if not task_id:
            logger_error.error("Not transferred ID task")
            return Response("Not transferred ID task", status=status.HTTP_400_BAD_REQUEST)

        # получение данных сущности - задача
        result_task = service_func.get_task_data(task_id)
        # logger_error.error({
        #     "event": "ПОЛУЧИЛИ ДАННЫЕ ЗАДАЧИ",
        #     "result_task": result_task
        # })
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
        # logger_error.error({
        #     "event": "ПОЛУЧИЛИ ДАННЫЕ СДЕЛКИ",
        #     "result_deal": result_deal
        # })
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
        task_id = request.data.get("task_id", "")
        emoji = request.data.get("emoji", None)
        application_token = request.data.get("application_token", None)

        logger_error.info({
            "task_id": task_id,
            "request.data": request.data
        })

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
        task_id = request.data.get("task_id", "")
        application_token = request.data.get("application_token", None)

        logger_error.info({
            "task_id": task_id,
            "request.data": request.data
        })

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
        task_id = request.data.get("task_id", "")
        deadline = request.data.get("deadline", "")
        application_token = request.data.get("application_token", None)

        logger_error.info({
            "task_id": task_id,
            "request.data": request.data
        })

        if application_token != APPLICATION_TOKEN:
            return Response("Unverified event source", status=status.HTTP_400_BAD_REQUEST)

        if not task_id:
            return Response("Not transferred ID task", status=status.HTTP_400_BAD_REQUEST)

        if not deadline:
            return Response("Not transferred deadline task", status=status.HTTP_400_BAD_REQUEST)

        # изменение дедлайна задачи
        res = service_func.change_deadline_task(task_id, deadline)

        return Response(res, status=status.HTTP_200_OK)















