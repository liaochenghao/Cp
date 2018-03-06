from django.db import models
from authentication.models import User


class Ticket(models.Model):
    user = models.ForeignKey(User)
    ticket = models.CharField('用户ticket', max_length=100, unique=True)
    create_time = models.DateTimeField('创建时间', auto_now=True)
    expired_time = models.DateTimeField('过期时间')

    class Meta:
        db_table = "ticket"
