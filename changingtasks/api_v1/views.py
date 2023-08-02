from rest_framework import views, viewsets, filters, status
from rest_framework.response import Response
from django.views.decorators.clickjacking import xframe_options_exempt
from django.shortcuts import render

import logging
import re
from time import sleep
import json
import datetime

from django.conf import settings


from . import service, bitrix24
from .service import MyException


logging.basicConfig(filename="./logs_api_v1/log_task.log", level=logging.ERROR,
                    format='[%(asctime)s] %(levelname).1s %(message)s', datefmt='%Y.%m.%d %H:%M:%S')

logger_success = logging.getLogger('success')
logger_success.setLevel(logging.INFO)

# fh_success = logging.FileHandler('log_success_task.log')
fh_success = logging.handlers.TimedRotatingFileHandler('./logs_api_v1/log_success_task.log', when='D', interval=1, encoding="cp1251", backupCount=10)

formatter = logging.Formatter('[%(asctime)s] %(levelname).1s %(message)s')
fh_success.setFormatter(formatter)
logger_success.addHandler(fh_success)

# логгер входные данные событий
logger_access = logging.getLogger('tasks_access')
logger_access.setLevel(logging.INFO)
fh_access = logging.handlers.TimedRotatingFileHandler('./logs_api_v1/access.log', when='D', interval=1, backupCount=10)
formatter_access = logging.Formatter('[%(asctime)s] %(levelname).1s %(message)s')
fh_access.setFormatter(formatter_access)
logger_access.addHandler(fh_access)

#
token_data = service.get_token()
APPLICATION_TOKEN = token_data.get("application_token", None)

obj_markers = {
  "phone":            '☎️',
  "closed":           '✅',
  "anchor":           '⚓',
  "cloud":            '☁️',
  "snowflake":        '❄️',
  "lightning":        '⚡',
  "pencil":           '✏️',
  "scissors":         '✂️',
  "tool":             '⚒️',
  "cogwheel":         '⚙️',
  "attention":        '⚠️',
  "danger":           '⛔',
  "right":            '➡️',
  "left":             '⬅️',
  "top":              '⬆️',
  "bottom":           '⬇️',
  "topright":         '↗️',
  "bottomright":      '↘️',
  "bottomleft":       '↙️',
  "topleft":          '↖️',
  "play":             '▶️',
  "pause":            '⏸️',
  "stop":             '⏹️',
  "play2":            '⏯️',
  "torus":            '⭕',
  "yellowsnowflake":  '✴️',
  "greensnowflake":   '✳️',
  "greensnowflake2":  '❇️',
  "greenclosed":      '❎',
  "greencheck":       '✅',
  "redsnowflake":     '✴️',
  "bluecheck":        '☑️',
  "zero":             '0️⃣',
  "one":              '1️⃣',
  "two":              '2️⃣',
  "three":            '3️⃣',
  "four":             '4️⃣',
  "five":             '5️⃣',
  "six":              '6️⃣',
  "seven":            '7️⃣',
  "eight":            '8️⃣',
  "nine":             '9️⃣',
  "check":            '✔️',
  "update":           '♻️',
}


# {'auth[access_token]': ['4e0515620059d2ca0054d65200000009000003e5f79877d42b56fbf2f78ec07f25a05e'],
#  'auth[expires]': ['1645544782'],
#  'auth[expires_in]': ['3600'],
#  'auth[scope]': ['crm,task'],
#  'auth[domain]': ['bits24.bitrix24.ru'],
#  'auth[server_endpoint]': ['https://oauth.bitrix.info/rest/'],
#  'auth[status]': ['L'],
#  'auth[client_endpoint]': ['https://bits24.bitrix24.ru/rest/'],
#  'auth[member_id]': ['e7ea7834c1e27b4e529de3a7eb8e8b3b'],
#  'auth[user_id]': ['9'],
#  'auth[refresh_token]': ['3e843c620059d2ca0054d65200000009000003bf278d206374421f4a41fdf61e490ccf'],
#  'auth[application_token]': ['3b44cc19db732645b92c7ba3c8d08c42']}>
#


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
        logging.info(request.query_params)
        logging.info(request.data)
        logging.info(data)
        service.write_app_data_to_file(data)
        return render(request, 'install.html')


class IndexApiView(views.APIView):
    @xframe_options_exempt
    def post(self, request):
        return render(request, 'index.html')

class TaskUpdateApiView(views.APIView):
    bx24 = bitrix24.Bitrix24()

    def post(self, request):
        logger_access.info(json.dumps({
            "url_path": "api/v1/task-update/",
            "handler": "TaskUpdateApiView",
            "query_params": request.query_params,
        }))
        task_id = request.query_params.get("id", "")
        marker = request.query_params.get("marker", None)
        position = request.query_params.get("position", None)
        request_token = request.query_params.get("request_token", None)

        if request_token != APPLICATION_TOKEN:
            return Response("Unverified event source", status=status.HTTP_400_BAD_REQUEST)

        if not task_id:
            return Response("Not transferred ID task", status=status.HTTP_400_BAD_REQUEST)

        if not marker:
            return Response("New emoji code not sent", status=status.HTTP_400_BAD_REQUEST)

        if position is None:
            return Response("The position of the emoji to replace was not passed", status=status.HTTP_400_BAD_REQUEST)

        result_task_data = self.bx24.callMethod("tasks.task.get", {
            "taskId": task_id,
            "select": ["ID", "TITLE"]
        })

        # старое название задачи
        title = result_task_data["result"]["task"]["title"]

        # новое название задачи
        new_title = get_new_title(title, marker, position)
        if new_title is None:
            return Response("Error changing emoji in task title", status=status.HTTP_400_BAD_REQUEST)

        result_task_update_title = self.bx24.callMethod("tasks.task.update", {
            "taskId": task_id,
            "fields": {"TITLE": new_title}
        })

        logger_success.info(json.dumps({
            "method": "task-update",
            "input data": {"id": task_id, "marker": marker, "position": position},
            "result": result_task_update_title.get("result", "")
        }))

        return Response("OK", status=status.HTTP_200_OK)


def get_new_title(title, marker, position):
    start = 0
    length_emoji = 0

    for num in range(int(position)):
        len_emoji = from_what_emoji_begin_string(title[start:])
        if len_emoji is None:
            return None
        start += len_emoji
        length_emoji = len_emoji

    start -= length_emoji

    return title[:start] + obj_markers[marker] + title[start + length_emoji:]


def from_what_emoji_begin_string(string):
    emoji_list = obj_markers.values()

    for emoji in emoji_list:
        if string.startswith(emoji):
            return len(emoji)


class TaskCommentApiView(views.APIView):
    bx24 = bitrix24.Bitrix24()

    def post(self, request):
        logger_access.info(json.dumps({
            "url_path": "api/v1/task-comment/",
            "handler": "TaskCommentApiView",
            "query_params": request.query_params,
        }))
        task_ids = request.query_params.get("ids", None)
        comment = request.query_params.get("comment", None)
        request_token = request.query_params.get("request_token", None)

        if request_token != APPLICATION_TOKEN:
            return Response("Unverified event source", status=status.HTTP_400_BAD_REQUEST)

        if not task_ids:
            return Response("Not transferred ID task", status=status.HTTP_400_BAD_REQUEST)

        if not comment:
            return Response("Comment not sent", status=status.HTTP_400_BAD_REQUEST)

        for task_id in task_ids.split(","):
            if not task_id:
                continue

            result_task_comment = self.bx24.callMethod("task.commentitem.add", {
                "taskId": task_id,
                "fields": {"POST_MESSAGE": comment, "AUTHOR_ID": 217}
            })

            logger_success.info(json.dumps({
                "method": "task-comment",
                "input data": {"task_id": task_id, "comment": comment},
                "result": result_task_comment.get("result", "")
            }))

            sleep(0.5)

        return Response("OK", status=status.HTTP_200_OK)


class TaskCompleteApiView(views.APIView):
    bx24 = bitrix24.Bitrix24()

    def post(self, request):
        logger_access.info(json.dumps({
            "url_path": "api/v1/task-complete/",
            "handler": "TaskCompleteApiView",
            "query_params": request.query_params,
        }))
        task_id = request.query_params.get("id", None)
        request_token = request.query_params.get("request_token", None)

        if request_token != APPLICATION_TOKEN:
            return Response("Unverified event source", status=status.HTTP_400_BAD_REQUEST)

        if not task_id:
            return Response("Not transferred ID task", status=status.HTTP_400_BAD_REQUEST)

        result_task_complete = self.bx24.callMethod("tasks.task.complete", {
            "taskId": task_id,
        })

        logger_success.info(json.dumps({
            "method": "task-complete",
            "input data": {"task_id": task_id},
            "result": result_task_complete.get("result", "")
        }))

        return Response("OK", status=status.HTTP_200_OK)


class TaskStartApiView(views.APIView):
    bx24 = bitrix24.Bitrix24()

    def post(self, request):
        logger_access.info(json.dumps({
            "url_path": "api/v1/task-start/",
            "handler": "TaskStartApiView",
            "query_params": request.query_params,
        }))
        task_id = request.query_params.get("id", None)
        request_token = request.query_params.get("request_token", None)

        if request_token != APPLICATION_TOKEN:
            return Response("Unverified event source", status=status.HTTP_400_BAD_REQUEST)

        if not task_id:
            return Response("Not transferred ID task", status=status.HTTP_400_BAD_REQUEST)

        result_task_start = self.bx24.callMethod("tasks.task.start", {
            "taskId": task_id,
        })

        logger_success.info(json.dumps({
            "method": "task-start",
            "input data": {"task_id": task_id},
            "result": result_task_start.get("result", "")
        }))

        return Response("OK", status=status.HTTP_200_OK)


class TaskDateUpdateApiView(views.APIView):
    bx24 = bitrix24.Bitrix24()

    def post(self, request):
        logger_access.info(json.dumps({
            "url_path": "api/v1/task-date-update/",
            "handler": "TaskDateUpdateApiView",
            "query_params": request.query_params,
        }))
        task_id = request.query_params.get("id", "")
        date = request.query_params.get("date", "")
        finish_date = request.query_params.get("finish_date", "")

        if not task_id:
            return Response("Not transferred ID task", status=status.HTTP_400_BAD_REQUEST)

        if not date:
            return Response("Not transferred date", status=status.HTTP_400_BAD_REQUEST)

        date_new = datetime.datetime.strptime(date, "%d.%m.%Y %H:%M:%S") + datetime.timedelta(days=1)

        body = {
            "taskId": task_id,
            "fields": {"DEADLINE": date_new.isoformat()}
        }

        if finish_date:
            body["END_DATE_PLAN"] = finish_date

        result_task_update_date = self.bx24.callMethod("tasks.task.update", body)

        logger_success.info(json.dumps({
            "method": "task-update",
            "input data": {"id": task_id, "date": date, "finish_date": finish_date},
            "body": body,
            "result": result_task_update_date.get("result", "")
        }))

        return Response("OK", status=status.HTTP_200_OK)


