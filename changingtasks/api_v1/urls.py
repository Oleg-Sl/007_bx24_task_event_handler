from django.urls import include, path
from rest_framework import routers


from .views import (InstallApiView, TaskUpdateApiView, TaskCommentApiView, TaskCompleteApiView, TaskStartApiView, TaskDateUpdateApiView)


app_name = 'api_v1'
router = routers.DefaultRouter()


urlpatterns = [
    path('', include(router.urls)),
    path('install/', InstallApiView.as_view()),                     # установка приложения
    path('index/', IndexApiView.as_view()),                     # установка приложения
    path('task-update/', TaskUpdateApiView.as_view()),              # изменение названия задачи
    path('task-comment/', TaskCommentApiView.as_view()),            # добавление комментария к задаче
    path('task-complete/', TaskCompleteApiView.as_view()),          # закрытие задачи
    path('task-start/', TaskStartApiView.as_view()),                # начать выполнение задачи
    path('task-date-update/', TaskDateUpdateApiView.as_view()),     # изменение крайнего срока задачи
]

urlpatterns += router.urls


