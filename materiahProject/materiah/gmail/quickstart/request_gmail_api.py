# Document

import base64
import os.path
import re
from email.utils import parsedate_to_datetime

from django.conf import settings
from django.core.cache import cache
from django.contrib.auth.models import User
from django.utils.timezone import is_aware, make_naive, utc, make_aware, get_default_timezone
from google.auth.exceptions import RefreshError

from ...models import GoogleCredentials
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# If modifying these scopes, delete the file token.json.
SCOPES = [
    'https://www.googleapis.com/auth/gmail.modify',
]
CREDENTIALS_FILE_PATH = os.path.join(os.path.dirname(__file__), 'credentials.json')
USER_ID = "me"


def check_email_label(label_ids):
    """
    Checks if an email is from the Inbox or Sent items.

    Args:
        label_ids: the email label_ids.

    Returns:
        A string indicating the label of the email ("Inbox", "Sent").
    """
    try:
        if 'INBOX' in label_ids:
            return "Inbox"
        elif 'SENT' in label_ids:
            return "Sent"

    except Exception as error:
        print(f"An error occurred: {error}")
        return "Error"


def parse_sender_from_header(header):
    """
    Parses the sender's name and email address from the 'From' header.

    Args:
        header (str): The 'From' header value, e.g., "Sender Name <sender_email@example.com>".

    Returns:
        tuple: A tuple containing the sender's name and email address. If the 'From' header does not match the expected format, returns (None, None).
    """
    match = re.match(r'(?:"?([^"]*)"?\s)?(?:<?([\w.-]+@[\w.-]+)>?)', header)
    if match:
        sender_name, sender_email = match.groups()
        return sender_name, sender_email
    return None, None


def parse_recipients_from_header(headers):
    """
    Parses the CC'd names and email addresses from the 'Cc' header, including names and email addresses within brackets.

    Args:
        headers (list): List of header dictionaries.

    Returns:
        list: A list of strings, each containing the name (if present) and email address in brackets. Returns an empty list if no 'Cc' header is found or if there are no CC'd addresses.
    """
    to_header = next((header['value'] for header in headers if header['name'].lower() == "to"), "")
    if '"' in to_header:
        to_header = to_header.replace('"', '')
    to_formatted = to_header.split(', ')
    # Format matches back into the standard "Name <email>" format if a name is present, otherwise just "email"
    return to_formatted


def parse_cc_from_header(headers):
    """
    Parses the CC'd names and email addresses from the 'Cc' header, including names and email addresses within brackets.

    Args:
        headers (list): List of header dictionaries.

    Returns:
        list: A list of strings, each containing the name (if present) and email address in brackets. Returns an empty list if no 'Cc' header is found or if there are no CC'd addresses.
    """
    cc_header = next((header['value'] for header in headers if header['name'].lower() == "cc"), "")
    if cc_header:
        cc_formatted = cc_header.split(', ')
    else:
        cc_formatted = []
    # Format matches back into the standard "Name <email>" format if a name is present, otherwise just "email"
    return cc_formatted


def parse_email_header(headers, header_name):
    """
    Parses the specified header's value from the message headers.

    Args:
        headers (list): List of header dictionaries.
        header_name (str): The name of the header to parse.

    Returns:
        str: The value of the specified header, or an empty string if not found.
    """
    header_value = next((header['value'] for header in headers if
                         header['name'] == header_name or header['name'] == header_name.lower()), "")
    return header_value


def get_message_content_and_attachments(service, message_id):
    """
    Fetches the content of an email message and its attachments.

    Args:
        service: Authorized Gmail API service instance.
        message_id: The ID of the email message to fetch.

    Returns:
        A tuple containing:
        - The text content of the message.
        - A list of attachments, where each attachment is a tuple of (filename, data).
    """
    try:
        message = service.users().messages().get(userId=USER_ID, id=message_id, format='full').execute()
        parts = message['payload'].get('parts', [])
        html_content = ''
        attachments = []

        if parts:
            for part in parts:
                if part['mimeType'] == 'text/html' and 'data' in part['body']:
                    html_content = base64.urlsafe_b64decode(part['body']['data']).decode('utf-8')
                    break  # Stop looking for HTML content once found
                elif part['mimeType'] == 'text/plain' and 'data' in part['body'] and not html_content:
                    html_content = base64.urlsafe_b64decode(part['body']['data']).decode('utf-8')
                if 'filename' in part and part['filename']:
                    if 'attachmentId' in part['body']:
                        # Just store attachment metadata here instead of fetching the content
                        attachments.append({
                            'filename': part['filename'],
                            'part_id': part.get('partId'),
                            'attachment_id': part['body']['attachmentId'],
                            'mime_type': part['mimeType']
                        })

            if not parts and 'data' in message['payload']['body']:
                html_content += base64.urlsafe_b64decode(message['payload']['body']['data']).decode('utf-8')

        else:
            body = message['payload']['body']
            if 'data' in body:
                data = base64.urlsafe_b64decode(body['data']).decode('utf-8')
                html_content = data if message['payload']['mimeType'] == 'text/html' else html_content

        return html_content, attachments

    except HttpError as error:
        print(f"An error occurred: {error}")
    return "", []


def run_installed_app_flow():
    """Runs the InstalledAppFlow and returns the credentials."""
    flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_FILE_PATH, SCOPES)
    creds = flow.run_local_server(port=8080)
    return creds


def get_google_service(user_id):
    try:
        user = User.objects.get(pk=user_id)
        google_creds = GoogleCredentials.objects.get(user=user)

        creds = Credentials(
            token=google_creds.access_token,
            refresh_token=google_creds.refresh_token,
            token_uri='https://oauth2.googleapis.com/token',
            client_id=settings.GOOGLE_OAUTH2_CLIENT_ID,
            client_secret=settings.GOOGLE_OAUTH2_CLIENT_SECRET,
            scopes=SCOPES,
            # Ensure the expiry is correctly handled as a naive UTC datetime
            expiry=make_naive(google_creds.token_expiry, utc) if is_aware(
                google_creds.token_expiry) else google_creds.token_expiry
        )

        # Attempt to refresh the token if it's expired
        if creds.expired:
            creds.refresh(Request())
    except (GoogleCredentials.DoesNotExist, RefreshError):
        # This block catches either the absence of credentials or a failed refresh due to expired/revoked tokens
        # Initiates the re-authorization flow to get a new token
        creds = run_installed_app_flow()

        # Save the new credentials back to your storage
        expiry_datetime = make_aware(creds.expiry, utc)
        GoogleCredentials.objects.update_or_create(
            user=user,
            defaults={
                'access_token': creds.token,
                'refresh_token': creds.refresh_token,
                'token_expiry': expiry_datetime
            }
        )

    return build('gmail', 'v1', credentials=creds)


def setup_gmail_watch(service):
    """
    Set up a watch on the Gmail inbox to send notifications to a specified Pub/Sub topic.

    Args:
        service: Authorized Gmail API service instance.
        user_id: User's email address or 'me' for the current authenticated user.
        topic_name: The full name of the Google Cloud Pub/Sub topic (e.g., projects/my-project/topics/my-topic).

    Returns:
        The API response containing the watch details.
    """
    try:
        request_body = {
            'labelIds': ['INBOX'],  # Specify which labels to watch, 'INBOX' for incoming emails
            'topicName': "projects/materiah-email-test/topics/materiah_gmail"  # Full name of your Pub/Sub topic
        }
        response = service.users().watch(userId="ME", body=request_body).execute()
        print("Watch set up successfully:", response)
        return response
    except HttpError as error:
        print(f"Failed to set up watch: {error}")
        return None


def get_thread_messages(service, thread_id):
    """
    Fetches all messages in a specific thread.

    Args:
        service: Authorized Gmail API service instance.
        thread_id: The ID of the thread to fetch.

    Returns:
        A list of dictionaries, each containing details of a message within the thread.
    """
    cache_key = f"thread_messages_{thread_id}"
    cached_data = cache.get(cache_key)
    if cached_data:
        return cached_data

    try:
        thread = service.users().threads().get(userId=USER_ID, id=thread_id, ).execute()
        messages = thread['messages']
        detailed_messages = []

        for msg in messages:
            headers = msg['payload']['headers']
            msg_id = msg['id']
            label_ids = msg.get('labelIds', [])
            label = check_email_label(label_ids)

            if 'SENT' in label_ids:
                email_role = "to"
                to_header = parse_email_header(headers, "To")
                name, email = parse_sender_from_header(to_header)
            else:
                from_header = parse_email_header(headers, "From")
                name, email = parse_sender_from_header(from_header)
                email_role = "from"

            to_header = parse_email_header(headers, "To")
            to_name, to_email = parse_sender_from_header(to_header)
            from_header = parse_email_header(headers, "From")
            from_name, from_email = parse_sender_from_header(from_header)

            cc_addresses = parse_cc_from_header(headers)
            to_addresses = parse_recipients_from_header(headers)
            reception_date = parsedate_to_datetime(parse_email_header(headers, 'Date'))
            subject = next((header['value'] for header in headers if header['name'].lower() == "subject"), "No Subject")
            # Extract text/plain or text/html content as per your requirement
            content, attachments = get_message_content_and_attachments(service, msg['id'])
            is_unread = 'UNREAD' in msg['labelIds']

            detailed_messages.append({
                "id": msg_id,
                "thread_id": thread_id,
                "reception_date": reception_date,
                "from1": {'name': from_name, 'email': from_email},
                "to1": {'name': to_name, 'email': to_email},
                email_role: {'name': name, 'email': email},
                'to_addresses': to_addresses,
                'cc_addresses': cc_addresses,
                "label": label,
                "subject": subject,
                "content": content,
                'attachments': attachments,
                'is_unread': is_unread
            })

        cache.set(cache_key, detailed_messages, timeout=660)
        return detailed_messages

    except HttpError as error:
        print(f"An error occurred: {error}")
        return []


def get_emails_with_thread_messages(user_id, next_page_token, result_amount, refresh_cache=False):
    """Enhanced function to fetch emails including all messages from their threads."""
    service = get_google_service(user_id)

    if service is None:
        print("Failed to get Google service.")
        return []

    try:
        # setup_gmail_watch(service)
        page_token = next_page_token
        all_thread_messages = []

        if page_token:
            response = service.users().threads().list(
                userId="ME",
                maxResults=result_amount,
                pageToken=page_token
            ).execute()
        else:
            response = service.users().threads().list(
                userId="ME",
                maxResults=result_amount,
            ).execute()

        threads = response.get("threads", [])
        for thread in threads:
            thread_id = thread['id']
            thread_messages = get_thread_messages(service, thread_id)
            all_thread_messages.append({'thread_id': thread_id, 'messages': thread_messages})

        page_token = response.get('nextPageToken')

        if not refresh_cache:
            return {'threads': all_thread_messages, "nextPageToken": page_token if page_token else None}

    except HttpError as error:
        print(f"An error occurred: {error}")
        return []
