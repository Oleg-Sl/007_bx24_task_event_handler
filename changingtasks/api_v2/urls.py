from django.urls import include, path
from rest_framework import routers


from .views import (
    InstallApiView,
    TaskCreateApiView,
    TaskUpdateApiView,
    TaskDeleteApiView,
    TaskChangeStatusApiView,
    TaskDataApiView,
    TaskChangeDeadlineApiView,
    TaskCommentCreateApiView,

)


app_name = 'api_v2'
router = routers.DefaultRouter()


urlpatterns = [
    path('', include(router.urls)),
    path('install/', InstallApiView.as_view()),                         # установка приложения
    # path('task-create/', TaskCreateApiView.as_view()),                  # создание задачи
    # path('task-update/', TaskUpdateApiView.as_view()),                  # изменение задачи
    # path('task-delete/', TaskDeleteApiView.as_view()),                  # удаление задачи
    path('task-comment-create/', TaskCommentCreateApiView.as_view()),   # добавление комментария к задаче

    # Методы для работы браузерного расширения
    path('task-change-status/', TaskChangeStatusApiView.as_view()),     # изменение статуса задачи (смена 1-го эмоджи)
    path('task-data/', TaskDataApiView.as_view()),                      # получить данные задачи
    path('task-change-deadline/', TaskChangeDeadlineApiView.as_view()), # изменение дедлайна задачи
]

urlpatterns += router.urls


