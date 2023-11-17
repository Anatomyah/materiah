import json

from django.contrib.auth.models import User
from django.core.exceptions import ObjectDoesNotExist
from django.core.serializers import serialize
from rest_framework import status
from rest_framework import viewsets
from rest_framework.authtoken.models import Token
from rest_framework.authtoken.views import ObtainAuthToken
from rest_framework.decorators import action, permission_classes, throttle_classes, authentication_classes
from rest_framework.exceptions import ParseError
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import UserRateThrottle, AnonRateThrottle
from rest_framework.views import APIView

from ..models import OrderNotifications, SupplierUserProfile, UserProfile
from ..serializers.user_serializer import UserSerializer


class CheckUsernameRateThrottle(UserRateThrottle, AnonRateThrottle):
    scope = 'check_username'


class CheckEmailRateThrottle(UserRateThrottle, AnonRateThrottle):
    scope = 'check_email'


class CheckPhoneRateThrottle(UserRateThrottle, AnonRateThrottle):
    scope = 'check_phone'


class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [AllowAny, ]

    def get_permissions(self):
        if self.action == 'create':
            self.permission_classes = [AllowAny, ]
        return [permission() for permission in self.permission_classes]

    @action(detail=False, methods=['GET'], permission_classes=[IsAuthenticated])
    def validate_token(self, request):
        """
        Validate the user's authentication token.
        """
        try:
            return Response({'valid': True}, status=status.HTTP_200_OK)

        except Exception as e:
            return Response({'valid': False, 'error': str(e)}, status=status.HTTP_401_UNAUTHORIZED)

    @action(detail=False, methods=['GET'], permission_classes=[AllowAny], authentication_classes=[],
            throttle_classes=[UserRateThrottle])
    def check_username(self, request):
        try:
            entered_username = request.query_params.get('value', None)
            exists = User.objects.filter(username=entered_username).exists()
            if exists:
                return Response({"unique": False, "message": "Username already exists"},
                                status=status.HTTP_200_OK)
            else:
                return Response({"unique": True, "message": "Username is available"}, status=status.HTTP_200_OK)

        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=False, methods=['GET'], permission_classes=[AllowAny], authentication_classes=[],
            throttle_classes=[CheckEmailRateThrottle])
    def check_email(self, request):
        try:
            entered_email = request.query_params.get('value', None)
            exists = User.objects.filter(email__iexact=entered_email).exists()
            if exists:
                return Response({"unique": False, "message": "Email already exists"},
                                status=status.HTTP_200_OK)
            else:
                return Response({"unique": True, "message": "Email is available"}, status=status.HTTP_200_OK)

        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=False, methods=['GET'], permission_classes=[AllowAny], authentication_classes=[],
            throttle_classes=[CheckPhoneRateThrottle])
    def check_phone(self, request):
        try:
            entered_phone_prefix = request.query_params.get('prefix', None)
            entered_phone_suffix = request.query_params.get('suffix', None)
            exists_supplier_profile = SupplierUserProfile.objects.filter(
                contact_phone_prefix=entered_phone_prefix,
                contact_phone_suffix=entered_phone_suffix
            ).exists()

            exists_user_profile = UserProfile.objects.filter(
                phone_prefix=entered_phone_prefix,
                phone_suffix=entered_phone_suffix
            ).exists()

            if exists_user_profile or exists_supplier_profile:
                return Response({"unique": False, "message": "Phone already exists"},
                                status=status.HTTP_200_OK)
            else:
                return Response({"unique": True, "message": "Phone is available"}, status=status.HTTP_200_OK)

        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=False, methods=['GET'])
    def check_username_auth_required(self, request):
        try:
            entered_username = request.query_params.get('value', None)
            exists = User.objects.filter(username=entered_username).exists()
            if exists:
                return Response({"unique": False, "message": "Username already exists"},
                                status=status.HTTP_200_OK)
            else:
                return Response({"unique": True, "message": "Username is available"}, status=status.HTTP_200_OK)

        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=False, methods=['GET'])
    def check_email_auth_required(self, request):
        try:
            entered_email = request.query_params.get('value', None)
            exists = User.objects.filter(email__iexact=entered_email).exists()
            if exists:
                return Response({"unique": False, "message": "Email already exists"},
                                status=status.HTTP_200_OK)
            else:
                return Response({"unique": True, "message": "Email is available"}, status=status.HTTP_200_OK)

        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=False, methods=['GET'])
    def check_phone_auth_required(self, request):
        try:
            entered_phone_prefix = request.query_params.get('prefix', None)
            entered_phone_suffix = request.query_params.get('suffix', None)
            exists_supplier_profile = SupplierUserProfile.objects.filter(
                contact_phone_prefix=entered_phone_prefix,
                contact_phone_suffix=entered_phone_suffix
            ).exists()

            exists_user_profile = UserProfile.objects.filter(
                phone_prefix=entered_phone_prefix,
                phone_suffix=entered_phone_suffix
            ).exists()

            if exists_user_profile or exists_supplier_profile:
                return Response({"unique": False, "message": "Phone already exists"},
                                status=status.HTTP_200_OK)
            else:
                return Response({"unique": True, "message": "Phone is available"}, status=status.HTTP_200_OK)

        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class CustomObtainAuthToken(ObtainAuthToken):
    def post(self, request, *args, **kwargs):
        try:
            response = super().post(request, *args, **kwargs)
            token = Token.objects.get(key=response.data['token'])
            user = token.user
            user_details = {
                'user_id': token.user.id,
                'username': token.user.username,
                'first_name': token.user.first_name,
                'last_name': token.user.last_name,
                'email': token.user.email
            }

            try:
                profile = user.userprofile
                user_details['phone_prefix'] = profile.phone_prefix
                user_details['phone_suffix'] = profile.phone_suffix
            except ObjectDoesNotExist:
                pass

            try:
                supplier_profile = user.supplieruserprofile
                user_details['supplier_id'] = supplier_profile.supplier.id
                user_details['supplier_name'] = supplier_profile.supplier.name
                user_details['supplier_phone_prefix'] = supplier_profile.supplier.phone_prefix
                user_details['supplier_phone_suffix'] = supplier_profile.supplier.phone_suffix
                user_details['supplier_email'] = supplier_profile.supplier.email
                user_details['supplier_website'] = supplier_profile.supplier.website
                user_details['phone_prefix'] = supplier_profile.contact_phone_prefix
                user_details['phone_suffix'] = supplier_profile.contact_phone_suffix
                user_details['is_supplier'] = True
            except ObjectDoesNotExist:
                pass

            notifications = OrderNotifications.objects.all()
            response_data = {
                'token': token.key,
                'user_details': user_details,
            }

            if notifications.exists():
                notifications = json.loads(serialize('json', OrderNotifications.objects.all()))
                for item in notifications:
                    item.pop('model', None)
                response_data['notifications'] = notifications

            return Response(response_data)

        except ParseError as e:
            return Response(e.detail, status=400)
        except Token.DoesNotExist:
            return Response("Invalid token", status=400)
        except Exception as e:
            return Response(str(e), status=400)


class LogoutAPIView(APIView):

    def post(self, request):
        try:
            if request.user.is_authenticated:
                request.user.auth_token.delete()
                return Response({"message": "Successfully logged out."}, status=status.HTTP_200_OK)
            else:
                return Response({"error": "You are not logged in."}, status=status.HTTP_401_UNAUTHORIZED)

        except Exception as e:
            return Response({"error": str(e)},
                            status=status.HTTP_500_INTERNAL_SERVER_ERROR)
