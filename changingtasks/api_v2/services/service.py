import pip
import time
import os
import json
import datetime

from django.conf import settings
# from changingtasks.api_v2 import bitrix24


path_secret_file = os.path.join(settings.BASE_DIR, 'secrets.json')
path_settings_file = os.path.join(settings.BASE_DIR, 'settings_app_bx24.json')


class MyException(Exception):
    def __init__(self, message):
        super().__init__(message)


# запись настроек приложения в фаил
def write_app_data_to_file(data):
    lifetime_token = data.get("expires_in", 3600)    # время жизни access токена
    data["expires_in"] = time.time() + float(lifetime_token) - 5 * 60   # время по истечении которого обновляется токен

    # сохранение данных авторизации в файл
    with open(path_secret_file, 'w') as secrets_file:
        json.dump(data, secrets_file)


# обновление токенов в файле
def update_tokens_in_file(auth_token, expires_in, refresh_token):
    # expires_in = time.time() + float(lifetime_token) - 5 * 60  # время по истечении которого обновляется токен

    with open(path_secret_file) as secrets_file:
        data = json.load(secrets_file)

    data["auth_token"] = auth_token
    data["expires_in"] = expires_in
    data["refresh_token"] = refresh_token

    with open(path_secret_file, 'w') as secrets_file:
        json.dump(data, secrets_file)


# возвращает токен приложения
def get_app_sid():
    if not os.path.exists(path_secret_file):
        return

    with open(path_secret_file) as secrets_file:
        token_app = json.load(secrets_file)

    return token_app.get("application_token", "")


# возвращает все токены из файла
def get_token():
    if not os.path.exists(path_secret_file):
        return {}

    with open(path_secret_file) as secrets_file:
        token_app = json.load(secrets_file)

    return token_app


# возвращает все токены из файла
def get_settings_app():
    if not os.path.exists(path_settings_file):
        return {}

    with open(path_settings_file) as secrets_file:
        settings_app = json.load(secrets_file)

    return settings_app


# преобразование даты к виду для сохранения в БД
def convert_date_to_obj(date):
    if date:
        return datetime.datetime.strptime(date, "%Y-%m-%dT%H:%M:%S%z")













