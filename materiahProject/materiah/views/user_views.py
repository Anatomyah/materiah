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

from ..models import OrderNotifications, SupplierUserProfile, UserProfile, ExpiryNotifications
from ..serializers.user_serializer import UserSerializer


class CheckUsernameRateThrottle(UserRateThrottle, AnonRateThrottle):
    """
    Throttling class that limits the number of requests for checking a username.

    Inherits from UserRateThrottle and AnonRateThrottle.

    Attributes:
        scope (str): The scope of the throttling rate limit. Defaults to 'check_username'.

    """
    scope = 'check_username'


class CheckEmailRateThrottle(UserRateThrottle, AnonRateThrottle):
    """This class is used for rate throttling the email checking functionality.
    It is a combination of two other rate throttling classes, UserRateThrottle
    and AnonRateThrottle.

    Attributes:
        scope (str): The scope of the rate throttle, which is set to 'check_email'.
    """
    scope = 'check_email'


class CheckPhoneRateThrottle(UserRateThrottle, AnonRateThrottle):
    """
    Throttles the number of requests based on the user's phone number.

    Inherits from UserRateThrottle and AnonRateThrottle classes.

    This throttle is specific to the 'check_phone' scope.

    Attributes:
        scope (str): The throttle scope which is set to 'check_phone'.
    """
    scope = 'check_phone'


class UserViewSet(viewsets.ModelViewSet):
    """
    UserViewSet

    A ViewSet for interacting with User objects.

    Attributes:
    - queryset (QuerySet): Queryset containing all User objects.
    - serializer_class (Serializer): Serializer class to use for serializing User objects.
    - permission_classes (list): List of permission classes to apply to view.

    Methods:
    - get_permissions: Get the list of permissions to apply to the current request's action.
    - validate_token: Validate the user's authentication token.
    - check_username: Check if a username is available or already exists.
    - check_email: Check if an email is available or already exists.
    - check_phone: Check if a phone number is available or already exists.
    - check_username_auth_required: Check if a username is available or already exists, authentication required.
    - check_email_auth_required: Check if an email is available or already exists, authentication required.
    - check_phone_auth_required: Check if a phone number is available or already exists, authentication required.
    """
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [AllowAny, ]

    def get_permissions(self):
        """
        Retrieve a list of permission classes based on the specified action.

        :return: A list of instantiated permission classes.
        """
        # If the action is 'create', set the permission_classes attribute to only include AllowAny
        # This means that any authenticated or unauthenticated user can access this endpoint
        if self.action == 'create':
            self.permission_classes = [AllowAny, ]

        # Instantiate and return the list of permissions that this view requires
        # As done by calling is_valid() on each permission
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
        """
            Check if a given username already exists in the User model.

            :param request: The request object.
            :return: A Response object with a JSON body indicating whether the username is unique or not.
            """
        try:
            # Extract the username value from the 'value' query parameter in the incoming request
            entered_username = request.query_params.get('value', None)

            # Check if a user instance with the extracted username already exists or not in the DB
            exists = User.objects.filter(username=entered_username).exists()

            # If such instance does exist
            if exists:
                # Return an HTTP response with a JSON payload indicating that the username is not unique,
                # along with a corresponding message
                return Response({"unique": False, "message": "Username already exists"},
                                status=status.HTTP_200_OK)
            # If there's no such instance
            else:
                # Return an HTTP response with a JSON payload indicating that the username is unique,
                # along with a corresponding message
                return Response({"unique": True, "message": "Username is available"}, status=status.HTTP_200_OK)
        except Exception as e:  # If there's an error during the execution
            # Return an error HTTP response with the status code of 500 (Internal Server Error)
            # and a JSON payload containing the error message
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=False, methods=['GET'], permission_classes=[AllowAny], authentication_classes=[],
            throttle_classes=[CheckEmailRateThrottle])
    def check_email(self, request):
        """
            Check if a given email already exists in the User model.

            :param request: The request object.
            :return: A Response object with a JSON body indicating whether the email is unique or not.
            """
        try:
            # Extract the email value from the 'value' query parameter in the incoming request
            entered_email = request.query_params.get('value', None)

            # Check if a user instance with the same email (ignoring case) already exists in the DB
            exists = User.objects.filter(email__iexact=entered_email).exists()

            # If such instance does exist
            if exists:
                # Return an HTTP response with a JSON payload indicating that the email is not unique,
                # along with a corresponding message
                return Response({"unique": False, "message": "Email already exists"},
                                status=status.HTTP_200_OK)
            # If there's no such instance
            else:
                # Return an HTTP response with a JSON payload indicating that the email is unique,
                # along with a corresponding message
                return Response({"unique": True, "message": "Email is available"}, status=status.HTTP_200_OK)
        except Exception as e:  # If there's an error during execution
            # Return an error HTTP response with the status code of 500 (Internal Server Error)
            # and a JSON payload containing the error message
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=False, methods=['GET'], permission_classes=[AllowAny], authentication_classes=[],
            throttle_classes=[CheckPhoneRateThrottle])
    def check_phone(self, request):
        """
            Check if a given phone number already exists in the SupplierUserProfile or UserProfile model.

            :param request: The request object.
            :return: A Response object with a JSON body indicating whether the phone number is unique or not.
            """
        try:
            # Extract the phone number's prefix and suffix from the 'prefix' and 'suffix' query parameters in
            # the incoming request.
            entered_phone_prefix = request.query_params.get('prefix', None)
            entered_phone_suffix = request.query_params.get('suffix', None)

            # Check whether a SupplierUserProfile exists in the database that has the same phone prefix and suffix.
            exists_supplier_profile = SupplierUserProfile.objects.filter(
                contact_phone_prefix=entered_phone_prefix,
                contact_phone_suffix=entered_phone_suffix
            ).exists()

            # Check whether a UserProfile exists in the database that has the same phone prefix and suffix
            exists_user_profile = UserProfile.objects.filter(
                phone_prefix=entered_phone_prefix,
                phone_suffix=entered_phone_suffix
            ).exists()

            # If a SupplierUserProfile or a UserProfile with the same phone number exists
            if exists_user_profile or exists_supplier_profile:
                # Return an HTTP response with a JSON payload indicating that the phone number is not unique,
                # along with a corresponding message
                return Response({"unique": False, "message": "Phone already exists"},
                                status=status.HTTP_200_OK)
            # If there's no such instance
            else:
                # Return an HTTP response with a JSON payload indicating that the phone number is unique,
                # along with a corresponding message
                return Response({"unique": True, "message": "Phone is available"},
                                status=status.HTTP_200_OK)

        except Exception as e:  # If there's an error during execution
            # Return an error HTTP Response with the status code of 500 (Internal Server Error)
            # and a JSON payload containing the error message
            return Response({"error": str(e)},
                            status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=False, methods=['GET'])
    def check_username_auth_required(self, request):
        """
            Check if a given username already exists in the User model.

            :param request: The request object.
            :return: A Response object with a JSON body indicating whether the username is unique or not.
            """
        try:
            # Extract the username value from the 'value' query parameter in the incoming request
            entered_username = request.query_params.get('value', None)

            # Check if a user instance with the extracted username already exists or not in the DB
            exists = User.objects.filter(username=entered_username).exists()

            # If such instance does exist
            if exists:
                # Return an HTTP response with a JSON payload indicating that the username is not unique,
                # along with a corresponding message
                return Response({"unique": False, "message": "Username already exists"},
                                status=status.HTTP_200_OK)
            # If there's no such instance
            else:
                # Return an HTTP response with a JSON payload indicating that the username is unique,
                # along with a corresponding message
                return Response({"unique": True, "message": "Username is available"}, status=status.HTTP_200_OK)
        except Exception as e:  # If there's an error during execution
            # Return an error HTTP response with the status code of 500 (Internal Server Error)
            # and a JSON payload containing the error message
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=False, methods=['GET'])
    def check_email_auth_required(self, request):
        """
            Check if a given email exists in the User model. This requires the user to be authenticated.

            :param request: The request object.
            :return: A Response object with a JSON body indicating whether the email is unique or not.
            """
        try:
            # Extract the email value from the 'value' query parameter in the incoming request
            entered_email = request.query_params.get('value', None)

            # Check if a user instance with the same email (ignoring case) already exists in the DB
            exists = User.objects.filter(email__iexact=entered_email).exists()

            # If such instance does exist
            if exists:
                # Return an HTTP response with a JSON payload indicating that the email is not unique,
                # along with a corresponding message
                return Response({"unique": False, "message": "Email already exists"},
                                status=status.HTTP_200_OK)
            # If there's no such instance
            else:
                # Return an HTTP response with a JSON payload indicating that the email is unique,
                # along with a corresponding message
                return Response({"unique": True, "message": "Email is available"},
                                status=status.HTTP_200_OK)
        except Exception as e:  # If there's an error during execution
            # Return an error HTTP response with the status code of 500 (Internal Server Error)
            # and a JSON payload containing the error message
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=False, methods=['GET'])
    def check_phone_auth_required(self, request):
        """
           Check if a given phone number already exists in the SupplierUserProfile or UserProfile model.
           Note: This method requires user authentication.

           :param request: The request object.
           :return: A Response object with a JSON body indicating whether the phone number is unique or not.
           """
        try:
            # Extract the phone number's prefix and suffix from the 'prefix' and 'suffix' query parameters in
            # the incoming request.
            entered_phone_prefix = request.query_params.get('prefix', None)
            entered_phone_suffix = request.query_params.get('suffix', None)

            # Check whether a SupplierUserProfile exists in the database that has
            # the same phone prefix and suffix.
            exists_supplier_profile = SupplierUserProfile.objects.filter(
                contact_phone_prefix=entered_phone_prefix,
                contact_phone_suffix=entered_phone_suffix
            ).exists()

            # Check whether a UserProfile exists in the database that has
            # the same phone prefix and suffix.
            exists_user_profile = UserProfile.objects.filter(
                phone_prefix=entered_phone_prefix,
                phone_suffix=entered_phone_suffix
            ).exists()

            # If a SupplierUserProfile or a UserProfile with the same phone number exists:
            if exists_user_profile or exists_supplier_profile:
                # Return an HTTP response with a JSON payload indicating that the phone number is not unique,
                # along with a corresponding message
                return Response({"unique": False, "message": "Phone already exists"},
                                status=status.HTTP_200_OK)
                # If there's no such instance
            else:
                # Return an HTTP response with a JSON payload indicating that the phone number is unique,
                # along with a corresponding message
                return Response({"unique": True, "message": "Phone is available"},
                                status=status.HTTP_200_OK)

        except Exception as e:  # If there's an error during execution
            # Return an error HTTP response with the status code of 500 (Internal Server Error)
            # and a JSON payload containing the error message
            return Response({"error": str(e)},
                            status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class CustomObtainAuthToken(ObtainAuthToken):
    """
    Custom class for obtaining authentication token.

    Overrides the post method to provide additional user details along with the token response.

    """

    def post(self, request, *args, **kwargs):
        """
                Post method to authenticate the user and provide the token.

                :param request: The request object.
                :param args: Additional arguments.
                :param kwargs: Additional keyword arguments.
                :return: A Response object with a JSON containing the user's authentication token and user details.
                """
        try:
            # Call to ObtainAuthToken.post can help us fetch the token generated for the
            # given username/password using the Django Rest Framework's inbuilt mechanism.
            response = super().post(request, *args, **kwargs)

            # Retrive the User's token generated by Django Rest Framework's Token Authentication.
            token = Token.objects.get(key=response.data['token'])

            # Fetch the User associated with the retrived Token
            user = token.user

            # User details dictionary. These details will be returned in the response.
            user_details = {
                'user_id': token.user.id,
                'username': token.user.username,
                'first_name': token.user.first_name,
                'last_name': token.user.last_name,
                'email': token.user.email
            }

            # Try and except block to check if UserProfile exists for the user. If yes,
            # then add the phone prefix and suffix to the user_details.
            try:
                profile = user.userprofile
                user_details['phone_prefix'] = profile.phone_prefix
                user_details['phone_suffix'] = profile.phone_suffix
            except ObjectDoesNotExist:
                pass

            # Try and except block to check if SupplierUserProfile exists for the user. If yes,
            # then add the supplier details to the user_details.
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

            # Set the response data dictionary
            response_data = {
                'token': token.key,
                'user_details': user_details,
            }

            # Check for order or expiry notifications
            order_notifications_exist = OrderNotifications.objects.exists()
            expiry_notifications_exist = ExpiryNotifications.objects.exists()

            # If there exists any notifications, add a boolean indicating this to the frontend
            if order_notifications_exist or expiry_notifications_exist:
                notifications = {}
                if order_notifications_exist:
                    notifications['order_notifications'] = order_notifications_exist.notifications
                if expiry_notifications_exist:
                    notifications['expiry_notifications'] = expiry_notifications_exist
                response_data['notifications'] = notifications

            return Response(response_data)

        # Handle all exceptions and return respective error messages as response.
        except ParseError as e:
            return Response(e.detail, status=400)
        except Token.DoesNotExist:
            return Response("Invalid token", status=400)
        except Exception as e:
            return Response(str(e), status=400)


class LogoutAPIView(APIView):
    """

    LogoutAPIView
    =============

    API view class for logging out a user.

    Methods
    -------

    post(request)
        Logs out a user.
    """

    def post(self, request):
        try:
            # Check if the user making the request is authenticated
            if request.user.is_authenticated:
                # If authenticated, delete the user's authentication token
                request.user.auth_token.delete()

                # Return a success response indicating that the user was successfully logged out
                return Response({"message": "Successfully logged out."}, status=status.HTTP_200_OK)

            else:
                # If the user is not authenticated, return an error response indicating that
                # the user is not logged in
                return Response({"error": "You are not logged in."}, status=status.HTTP_401_UNAUTHORIZED)

        except Exception as e:  # If there's an error during the execution
            # Return an error HTTP response with the status code of 500 (Internal Server Error)
            # and a JSON payload containing the error message
            return Response({"error": str(e)},
                            status=status.HTTP_500_INTERNAL_SERVER_ERROR)
