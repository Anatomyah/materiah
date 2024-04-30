import base64
import json
from datetime import datetime
from email import encoders
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from django.core.cache import cache

from django.http import HttpResponse, JsonResponse
from googleapiclient.errors import HttpError
from rest_framework import status
from rest_framework.decorators import api_view, parser_classes, permission_classes
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from ..gmail.quickstart.request_gmail_api import get_emails_with_thread_messages, get_google_service


# add documentation


def find_part_with_id(parts, part_id):
    """Recursively searches for the part with the specified partId."""
    for part in parts:
        if part.get('partId') == part_id:
            return part
        # If this part has nested parts, search them too
        if 'parts' in part:
            nested_part = find_part_with_id(part['parts'], part_id)
            if nested_part is not None:
                return nested_part
    return None


def get_attachment_details(service, user_id, message_id, part_id):
    """Fetches filename and MIME type for an attachment by partId."""
    try:
        message = service.users().messages().get(userId=user_id, id=message_id, format='full').execute()
        parts = message['payload'].get('parts', [])

        # Use the recursive function to find the part
        part = find_part_with_id(parts, part_id)

        if part:
            filename = part.get('filename')
            mime_type = part.get('mimeType', "application/octet-stream")  # Default MIME type
            attachment_id = part['body'].get('attachmentId')
            return filename, mime_type, attachment_id
        else:
            print(f"No part found with partId: {part_id}")
            return None, "application/octet-stream", None
    except Exception as e:
        print(f"An error occurred: {e}")
        return None, "application/octet-stream", None


@api_view(['GET'])
def get_messages(request):
    try:
        now = datetime.now()
        next_page_token = request.GET.get('page_token', '')
        print(request.user.id)
        messages = get_emails_with_thread_messages(user_id=request.user.id, next_page_token=next_page_token,
                                                   result_amount=50)
        after = datetime.now()
        duration = after - now

        print(duration)
        return Response(messages, status=200)
    except Exception as e:
        return Response({'error': str(e)}, status=500)


@api_view(['GET'])
def get_attachment(request):
    try:
        message_id = request.GET.get('message_id')
        part_id = request.GET.get('part_id')
        service = get_google_service(request.user.id)

        filename, mime_type, attachment_id = get_attachment_details(service, "me", message_id, part_id)
        if not filename:
            return Response({'error': 'Attachment not found.'}, status=404)

        # Correctly use the attachment_id to fetch the attachment
        attachment = service.users().messages().attachments().get(userId="me", messageId=message_id,
                                                                  id=attachment_id).execute()
        attachment_data = base64.urlsafe_b64decode(attachment['data'].encode('UTF-8'))

        response = HttpResponse(attachment_data, content_type=mime_type)  # Use mime_type for the content_type
        content_dispostion = f'attachment; filename="{filename}"'
        response['Content-Disposition'] = content_dispostion
        return response
    except Exception as e:
        print(f"An error occurred: {e}")
        return Response({'error': str(e)}, status=500)


@api_view(['POST'])
@parser_classes([MultiPartParser, FormParser])
def send_message(request):
    if not request.data.get('to'):
        return JsonResponse({'error': 'Must provide a recipient address'}, status=400)

    to = request.data.get('to')
    cc = request.data.get('cc', '')
    subject = request.data.get('subject', '')
    message_body = request.data.get('message', '')
    original_message_id = request.data.get('original_message_id', '')
    thread_id = request.data.get('thread_id', '')  # ID of the thread for the conversation

    service = get_google_service(request.user.id)
    profile = service.users().getProfile(userId='me').execute()
    sender_email = profile['emailAddress']

    message = MIMEMultipart('mixed')
    message['from'] = sender_email
    message['to'] = to
    if subject: message['subject'] = subject
    if cc: message['cc'] = cc
    if message_body: message.attach(MIMEText(message_body, 'html'))

    if original_message_id:
        message['In-Reply-To'] = original_message_id
        message['References'] = original_message_id

    files = request.FILES.getlist('files')
    for file in files:
        file_part = MIMEBase('application', 'octet-stream')
        file_part.set_payload(file.read())
        encoders.encode_base64(file_part)
        file_part.add_header('Content-Disposition', f'attachment; filename={file.name}')
        message.attach(file_part)

    raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode()
    if thread_id:
        body = {'raw': raw_message, 'threadId': thread_id}
    else:
        body = {'raw': raw_message}

    try:
        send_message = service.users().messages().send(userId='ME', body=body).execute()
        return JsonResponse({'message': 'Message sent successfully', 'messageId': send_message['id']}, status=200)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@api_view(['POST'])
@permission_classes([AllowAny])
def pubsub_push(request):
    print("working")
    try:
        # Decode the incoming request to JSON
        envelope = request.data
        # The actual message is base64 encoded, so decode it
        message_str = base64.b64decode(envelope['message']['data']).decode('utf-8')
        message = json.loads(message_str)

        # Here, process the message as needed
        print("Received message:", message)

        # Respond with success status
        return Response({"status": "success"}, status=status.HTTP_200_OK)
    except KeyError:
        # If the request is malformed or missing data, return a bad request response
        return Response({"error": "Bad Request"}, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
def bulk_mark_email_as_read(request):
    """
    Marks an email as read by removing the 'UNREAD' label.

    Parameters:
    - service: Authorized Gmail API service instance.
    - user_id: User's email address or 'me' for the currently authenticated user.
    - message_id: The ID of the email message to mark as read.
    """
    try:
        user_id = request.user.id
        service = get_google_service(user_id)
        messages = request.data['messages']

        for msg in messages:
            message_id = msg['message_id']
            thread_id = msg['thread_id']

            service.users().messages().modify(
                userId="me",
                id=message_id,
                body={'removeLabelIds': ['UNREAD']}
            ).execute()

            # Invalidate cache for this thread
            cache_key = f"thread_messages_{thread_id}"
            cache.delete(cache_key)

        get_emails_with_thread_messages(user_id=request.user.id, next_page_token=None, result_amount=100,
                                        refresh_cache=True)

        print("Messages marked as read.")
        return Response({"status": "success"}, status=200)
    except HttpError as error:
        print(f'An error occurred: {error}')
        return Response({"status": "error", "message": str(error)}, status=500)


@api_view(['POST'])
def mark_email_as_read(request):
    """
    Marks an email as unread by adding the 'READ' label.

    Parameters:
    - service: Authorized Gmail API service instance.
    - user_id: User's email address or 'me' for the currently authenticated user.
    - message_id: The ID of the email message to mark as unread.
    """
    try:
        user_id = request.user.id
        service = get_google_service(user_id)
        message_id = request.data['message_id']
        thread_id = request.data['thread_id']

        service.users().messages().modify(
            userId="ME",
            id=message_id,
            body={'removeLabelIds': ['UNREAD']}
        ).execute()

        cache_key = f"thread_messages_{thread_id}"
        cache.delete(cache_key)
        get_emails_with_thread_messages(user_id=request.user.id, next_page_token=None, result_amount=100,
                                        refresh_cache=True)

        print(f"Message {message_id} marked as unread.")
        return Response({"status": "success"}, status=200)
    except HttpError as error:
        print(f'An error occurred: {error}')
        return Response({"status": "error"}, status=500)


@api_view(['POST'])
def mark_email_as_unread(request):
    """
    Marks an email as unread by adding the 'UNREAD' label.

    Parameters:
    - service: Authorized Gmail API service instance.
    - user_id: User's email address or 'me' for the currently authenticated user.
    - message_id: The ID of the email message to mark as unread.
    """
    try:
        user_id = request.user.id
        service = get_google_service(user_id)
        message_id = request.data['message_id']
        thread_id = request.data['thread_id']
        service.users().messages().modify(
            userId="ME",
            id=message_id,
            body={'addLabelIds': ['UNREAD']}
        ).execute()

        cache_key = f"thread_messages_{thread_id}"
        cache.delete(cache_key)
        get_emails_with_thread_messages(user_id=request.user.id, next_page_token=None, result_amount=100,
                                        refresh_cache=True)

        print(f"Message {message_id} marked as read.")
        return Response({"status": "success"}, status=200)
    except HttpError as error:
        print(f'An error occurred: {error}')
        return Response({"status": "error"}, status=500)


@api_view(['POST'])
def bulk_mark_email_as_unread(request):
    """
    Marks multiple emails as unread by adding the 'UNREAD' label.

    Parameters:
    - service: Authorized Gmail API service instance.
    - user_id: User's email address or 'me' for the currently authenticated user.
    - messages: A list of objects containing the message_id and thread_id of the emails to mark as unread.
    """
    try:
        user_id = request.user.id
        service = get_google_service(user_id)
        messages = request.data['messages']

        for msg in messages:
            message_id = msg['message_id']
            thread_id = msg['thread_id']

            service.users().messages().modify(
                userId="me",
                id=message_id,
                body={'addLabelIds': ['UNREAD']}
            ).execute()

            # Invalidate cache for this thread
            cache_key = f"thread_messages_{thread_id}"
            cache.delete(cache_key)

        # Refresh cache for all affected threads
        get_emails_with_thread_messages(user_id=request.user.id, next_page_token=None, result_amount=100,
                                        refresh_cache=True)
        print("Messages marked as unread.")
        return Response({"status": "success"}, status=200)
    except HttpError as error:
        print(f'An error occurred: {error}')
        return Response({"status": "error", "message": str(error)}, status=500)


@api_view(['POST'])
def bulk_delete_email(request):
    """
    Marks multiple emails as unread by adding the 'UNREAD' label.

    Parameters:
    - service: Authorized Gmail API service instance.
    - user_id: User's email address or 'me' for the currently authenticated user.
    - messages: A list of objects containing the message_id and thread_id of the emails to mark as unread.
    """
    try:
        user_id = request.user.id
        service = get_google_service(user_id)
        messages = request.data['messages']

        for msg in messages:
            message_id = msg['message_id']
            thread_id = msg['thread_id']

            service.users().messages().delete(userId='me', id=message_id).execute()

            # Invalidate cache for this thread
            cache_key = f"thread_messages_{thread_id}"
            cache.delete(cache_key)

        # Refresh cache for all affected threads
        get_emails_with_thread_messages(user_id=request.user.id, next_page_token=None, result_amount=100,
                                        refresh_cache=True)
        print("Messages deleted")
        return Response({"status": "success"}, status=200)
    except HttpError as error:
        print(f'An error occurred: {error}')
        return Response({"status": "error", "message": str(error)}, status=500)
