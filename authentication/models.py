# coding: utf-8
from django.db import models


class User(models.Model):
    id = models.CharField('序列号', max_length=64, primary_key=True)
    nick_name = models.CharField('微信昵称', max_length=100, null=True)
    GENDER = (
        (0, '未知'),
        (1, '男'),
        (2, '女')
    )
    gender = models.IntegerField('性别', choices=GENDER, default=0)
    head_img_url = models.CharField('用户头像', max_length=255, null=True)
    city = models.CharField('城市', max_length=64, null=True)
    country = models.CharField('国家', max_length=64, null=True)
    province = models.CharField('省份', max_length=64, null=True)
    session_key = models.CharField('微信session_key', max_length=255, null=True)  # 微信session key，对客户端不可见
    create_time = models.DateTimeField('创建时间', auto_now_add=True)
    is_active = models.BooleanField('是否有效', default=True)
    last_login = models.DateTimeField('最后登录时间', null=True)

    class Meta:
        db_table = "user"



