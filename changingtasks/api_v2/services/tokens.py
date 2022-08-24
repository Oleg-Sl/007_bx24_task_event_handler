import os
import json
from django.conf import settings


path_secret_file = os.path.join(settings.BASE_DIR, 'secrets.json')
path_settings_file = os.path.join(settings.BASE_DIR, 'settings_app_bx24.json')

with open(path_settings_file) as settings_file:
    settings = json.load(settings_file)


def save_secrets(data):
    """ Запись токенов доступа к BX24 в файл """
    with open(path_secret_file, 'w') as secrets_file:
        json.dump(data, secrets_file)


def update_secrets(auth_token, expires_in, refresh_token):
    """ Обновление токенов доступа к BX24 в файле """
    with open(path_secret_file) as secrets_file:
        data = json.load(secrets_file)

    data["auth_token"] = auth_token
    data["expires_in"] = expires_in
    data["refresh_token"] = refresh_token

    with open(path_secret_file, 'w') as secrets_file:
        json.dump(data, secrets_file)


def get_secret(key):
    """ Получение секрета BX24 по ключу """
    with open(path_secret_file) as secrets_file:
        data = json.load(secrets_file)

    return data.get(key)


def get_secrets_all():
    """ Получение секрета BX24 """
    with open(path_secret_file) as secrets_file:
        data = json.load(secrets_file)

    return data


def get_setting(key):
    """ Получение значения настройки BX24 по ключу """
    if settings:
        return settings.get(key)

    return None

