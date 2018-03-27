# coding: utf-8
import datetime

from rest_framework import exceptions

from register.models import NewCornRecord
import logging
import uuid

logger = logging.getLogger('django')
OPTION_CHOICE = (
    (0, '关注留学新青年'),
    (1, '邀请用户'),
    (2, '注册成功'),
    (3, '每日登陆'),
    (4, '活动报名'),
    (5, '接受用户邀请'),
    (6, '切换用户'),
)


class NewCornCompute:
    @staticmethod
    def compute_new_corn(user_id, operation):
        # 新关注公众号与注册成功的new币计算规则一致，都是要判断用户是否是首次，且不允许重复
        if operation == 0 or operation == 2:
            record = NewCornRecord.objects.filter(user_id=user_id)
            corn = 3 if operation == 0 else 20
            extra = '关注留学新青年' if operation == 0 else '注册成功'
            if not record:
                NewCornRecord.objects.create(id=str(uuid.uuid4()), user_id=user_id, operation=operation, balance=corn,
                                             corn=corn, extra=extra)
            else:
                temp = NewCornRecord.objects.filter(user_id=user_id, operation=operation)
                # 判断是否是首次关注
                if not temp:
                    balance = record[0].balance
                    NewCornRecord.objects.create(id=str(uuid.uuid4()), user_id=user_id, operation=operation,
                                                 balance=corn + balance,
                                                 corn=corn,
                                                 extra=extra)
        # 每日登陆的逻辑处理
        if operation == 3:
            start_date = datetime.datetime.now()
            record = NewCornRecord.objects.filter(user_id=user_id, operation=operation,
                                                  create_at__day=start_date.day, create_at__month=start_date.month)
            if not record:
                record = NewCornRecord.objects.filter(user_id=user_id)
                if not record:
                    NewCornRecord.objects.create(id=str(uuid.uuid4()), user_id=user_id, operation=operation, balance=1,
                                                 corn=1,
                                                 extra='每日登陆')
                else:
                    balance = record[0].balance
                    # 查询最新记录添加记录
                    NewCornRecord.objects.create(id=str(uuid.uuid4()), user_id=user_id, operation=operation,
                                                 balance=1 + balance, corn=1,
                                                 extra='每日登陆')
        else:
            record = NewCornRecord.objects.filter(id=str(uuid.uuid4()), user_id=user_id).first()
            balance = record.balance
            corn = 0
            extra = None
            if operation == 1:
                corn = 3
                if balance < corn:
                    logger.info('compute_new_corn operation=%s,balance=%s' % (str(operation), str(balance)))
                    raise exceptions.ValidationError('账户余额不足')
                balance -= corn
                extra = '邀请用户'
            elif operation == 4:
                corn = 3
                balance += corn
                extra = '活动报名'
            elif operation == 5:
                corn = 2
                if balance < corn:
                    logger.info('compute_new_corn operation=%s,balance=%s' % (str(operation), str(balance)))
                    raise exceptions.ValidationError('账户余额不足')
                balance -= corn
                extra = '接受用户邀请'
            elif operation == 6:
                corn = 1
                if balance < corn:
                    logger.info('compute_new_corn operation=%s,balance=%s' % (str(operation), str(balance)))
                    raise exceptions.ValidationError('账户余额不足')
                balance -= corn
                extra = '切换用户'
            NewCornRecord.objects.create(id=str(uuid.uuid4()), user_id=user_id, operation=operation, balance=balance,
                                         corn=corn, extra=extra)
        return "success"
