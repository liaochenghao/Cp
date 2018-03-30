import datetime
from django.db import transaction
from django.db.models import Q
from rest_framework import mixins, viewsets, serializers
from rest_framework.decorators import list_route
from rest_framework.response import Response
from authentication.models import User
from common.ComputeNewCorn import NewCornCompute
from invitation.models import Invitation
from invitation.serializer import InvitationSerializer
import logging
from common.execute_sql import execute_custom_sql
from register.models import RegisterInfo
from register.serializer import RegisterInfoSerializer

logger = logging.getLogger('django')


class InvitationView(mixins.CreateModelMixin, viewsets.GenericViewSet, mixins.ListModelMixin,
                     mixins.RetrieveModelMixin, mixins.UpdateModelMixin):
    queryset = Invitation.objects.all()
    serializer_class = InvitationSerializer

    def list(self, request, *args, **kwargs):
        inviter = self.request.query_params.get('inviter')
        invitee = self.request.query_params.get('invitee')
        if inviter:
            sql = """select B.*, C.nickname, C.avatar_url,C.sex from invitation B, register_info C 
                     where  B.inviter=C.user_id AND B.inviter='%s'""" % inviter
        if invitee:
            sql = """select B.*, C.nickname, C.avatar_url,C.sex from invitation B, register_info C 
                     where  B.invitee=C.user_id AND B.invitee='%s'""" % invitee
        datas = execute_custom_sql(sql)
        logger.info(datas)
        result = self._wrapper_data(datas)
        return Response(result)

    def _wrapper_data(self, datas):
        data_list = []
        for data in datas:
            temp = dict()
            temp['id'] = data[0]
            temp['inviter'] = data[1]
            temp['invitee'] = data[2]
            temp['status'] = data[3]
            temp['create_time'] = data[4]
            temp['update_at'] = data[5]
            temp['expire_at'] = data[6]
            temp['nickname'] = data[7]
            temp['avatar_url'] = data[8]
            temp['sex'] = data[9]
            data_list.append(temp)
        return data_list

    @transaction.atomic
    def create(self, request, *args, **kwargs):
        params = request.data
        user = request.user_info
        if not params.get('invitee'):
            raise serializers.ValidationError('参数 invitee 不能为空')
        super().create(request, *args, **kwargs)
        NewCornCompute.compute_new_corn(user.get('open_id'), 1)
        return Response()

    @transaction.atomic
    def update(self, request, *args, **kwargs):
        pk = kwargs.get('pk')
        inviter = kwargs.get('inviter')
        logger.info('===========================================')
        logger.info(inviter)
        logger.info('===========================================')
        user = request.user_info
        status = request.data.get('status')
        if not status or status not in (0, 1, 2):
            logger.info('InvitationView update (status=%s)' % status)
            raise serializers.ValidationError('参数 invitee 有误')
        invitation = Invitation.objects.get(id=pk)
        invitation.status = status
        invitation.save()
        if status == 1:
            # 接收邀请，CP匹配成功
            NewCornCompute.compute_new_corn(user.get('open_id'), 5)
            # 同时更新User，将当前用户与inviter的cp_user_id进行更新
            now = datetime.datetime.now()
            User.objects.filter(open_id=user.get('open_id')).update(cp_user_id=inviter, cp_time=now)
            User.objects.filter(open_id=inviter).update(cp_user_id=user.get('open_id'), cp_time=now)
        return Response()

    @list_route(methods=['get'])
    def cp(self, request):
        user = request.user_info
        result = Invitation.objects.filter(Q(inviter=user.get('open_id')) | Q(invitee=user.get('open_id')), status=1)
        if not result:
            raise serializers.ValidationError('该用户暂不存在CP')
        # 在cp列表中，当前用户可能是邀请人也有可能是被邀请人
        cp_id = result[0].inviter if user.get('open_id') == result[0].invitee else result[0].invitee
        data = RegisterInfo.objects.filter(user_id=cp_id)
        if not data:
            raise serializers.ValidationError('该用户CP无注册信息，请检查数据库')
        data = data.first()
        temp = RegisterInfoSerializer(data).data
        temp['update_at'] = result[0].update_at
        return Response(temp)

    @list_route(methods=['get'])
    def check_inviter(self, request):
        user = request.user_info
        data = Invitation.objects.filter(inviter=user.get('open_id'), status=1)
        return Response(True if data else False)

    @list_route(methods=['get'])
    def check_invitee(self, request):
        user = request.user_info
        data = Invitation.objects.filter(invitee=user.get('open_id'), status=0, expire_at__gt=datetime.datetime.now())
        return Response(True if data else False)

    @list_route(methods=['get'])
    def cp_god(self, request):
        user = request.user_info
        result = list()
        pageNum = request.query_params.get('pageNum', 1)
        pageSize = request.query_params.get('pageSize', 10)
        start = pageSize * (pageNum - 1)
        end = pageSize * pageNum
        sql1 = """SELECT invitee,COUNT(*) as number from invitation GROUP BY invitee ORDER BY number desc
                limit %s, %s""" % (start, end)
        datas = execute_custom_sql(sql1)
        id_list = list()
        temp_dict = dict()
        for data in datas:
            id_list.append(data[0])
            temp_dict[data[0]] = data[1]
        register_info = RegisterInfo.objects.filter(user_id__in=id_list)
        for temp in register_info:
            data_temp = dict()
            data_temp['avatar_url'] = temp.avatar_url
            data_temp['nickname'] = temp.nickname
            data_temp['sex'] = temp.sex
            data_temp['total'] = temp_dict.get(temp.user_id)
            data_temp['user_id'] = temp.user_id
            result.append(data_temp)
        temp = Invitation.objects.filter(invitee=user.get('open_id'), inviter__in=id_list, status=0).values('invitee')
        for info in result:
            info['invite'] = 1 if info['user_id'] in list(temp) else 0
        return Response(result)

    @list_route(methods=['get'])
    def code(self, request):
        params = request.query_params
        # 获取邀请码
        code = params.get('code')
        # 获取邀请类型
        type = params.get('type', 0)
        other_open_id = params.get('other_open_id')
        nickname = params.get('nickname')
        if not code:
            raise serializers.ValidationError('参数 code 不能为空')
        if not other_open_id:
            raise serializers.ValidationError('参数 other_open_id 不能为空')
        if not nickname:
            raise serializers.ValidationError('参数 nickname 不能为空')
        inviter = User.objects.filter(code=code)
        if not inviter:
            raise serializers.ValidationError('参数 code 无效')
        NewCornCompute.compute_new_corn(inviter[0].open_id, type, other_open_id, nickname)
        return Response()
