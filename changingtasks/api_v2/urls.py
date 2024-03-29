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
    TaskBusinessTripApiView,
    TaskCommentCreateApiView,
    ChangeDeadlineForOverdueTasksApiView,
    ChangeCountDaysInTaskTitleApiView,
)


app_name = 'api_v2'
router = routers.DefaultRouter()


urlpatterns = [
    path('', include(router.urls)),
    path('install/', InstallApiView.as_view()),                             # установка приложения
    # path('task-create/', TaskCreateApiView.as_view()),                  # создание задачи
    # path('task-update/', TaskUpdateApiView.as_view()),                  # изменение задачи
    # path('task-delete/', TaskDeleteApiView.as_view()),                  # удаление задачи
    path('task-comment-create/', TaskCommentCreateApiView.as_view()),                           # добавление комментария к задаче
    path('change-deadline-all-overdue_tasks/', ChangeDeadlineForOverdueTasksApiView.as_view()), # изменение крайнего срока в просроченных задачах
    path('task-change-days-in-title/', ChangeCountDaysInTaskTitleApiView.as_view()),            # изменение кол-во дней в названии задачи

    # Методы для работы браузерного расширения
    path('task-change-status/', TaskChangeStatusApiView.as_view()),     # изменение статуса задачи (смена 1-го эмоджи)
    path('task-data/', TaskDataApiView.as_view()),                      # получить данные задачи
    path('task-change-deadline/', TaskChangeDeadlineApiView.as_view()), # изменение дедлайна задачи
    path('task-business-trip/', TaskBusinessTripApiView.as_view()),     # командировка есть/нет

]

urlpatterns += router.urls


