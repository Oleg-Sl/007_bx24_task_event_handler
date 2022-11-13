from django.db import models


class Task(models.Model):
    id_bx = models.PositiveIntegerField(primary_key=True, verbose_name='ID задачи в BX24', db_index=True)
    status = models.CharField(verbose_name='Название направления', max_length=50)

    def __str__(self):
        return f"ID={self.id_bx}, STATUS={self.status}"

    class Meta:
        verbose_name = 'Последний статус задачи'
        verbose_name_plural = 'Последние статусы задач'


class TaskTitle(models.Model):
    id_bx = models.PositiveIntegerField(primary_key=True, verbose_name='ID задачи в BX24', db_index=True)
    first_emoji = models.CharField(verbose_name='Первый эмоджи в названии задачи', max_length=5)

    def __str__(self):
        return f"ID={self.id_bx}, STATUS={self.first_emoji}"

    class Meta:
        verbose_name = 'Первый эмоджи в последнем изменении задачи'
        verbose_name_plural = 'Первый эмоджи в последних изменениях задачи'


