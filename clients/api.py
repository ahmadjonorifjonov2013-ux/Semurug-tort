from django.contrib.auth import authenticate
from rest_framework import status, viewsets
from rest_framework.authtoken.models import Token
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Client
from .serializers import (ClientCreateSerializer, ClientSerializer,
                          LoginSerializer)


class ClientViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = ClientSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.is_staff:
            return Client.objects.select_related('user').all()
        return Client.objects.filter(user=user)

    @action(detail=False, methods=['get', 'put', 'patch'])
    def me(self, request):
        client = getattr(request.user, 'client', None)
        if client is None:
            return Response({'detail': "Profil topilmadi"},
                            status=status.HTTP_404_NOT_FOUND)

        if request.method == 'GET':
            return Response(ClientSerializer(client).data)

        serializer = ClientSerializer(client, data=request.data,
                                      partial=request.method == 'PATCH')
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)


class RegisterView(APIView):
    permission_classes = [AllowAny]
    throttle_scope = 'register'

    def post(self, request):
        serializer = ClientCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        client = serializer.save()
        token, _ = Token.objects.get_or_create(user=client.user)
        return Response({
            'token': token.key,
            'client': ClientSerializer(client).data,
        }, status=status.HTTP_201_CREATED)


class LoginView(APIView):
    permission_classes = [AllowAny]
    throttle_scope = 'login'

    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = authenticate(
            request,
            username=serializer.validated_data['username'],
            password=serializer.validated_data['password'],
        )
        if user is None:
            return Response({'detail': "Login yoki parol xato"},
                            status=status.HTTP_400_BAD_REQUEST)

        token, _ = Token.objects.get_or_create(user=user)
        client = getattr(user, 'client', None)
        return Response({
            'token': token.key,
            'client': ClientSerializer(client).data if client else None,
        })