from rest_framework.decorators import api_view
from rest_framework.response import Response
from django.conf import settings
import os


@api_view(['GET'])
def fetch_email_signature(request):
    """
    Fetches the email signature HTML content.

    :param request: The HTTP request object.
    :return: The HTTP response containing the email signature content as 'signature' if successful, or an error message as 'error' if an exception occurs.
    """
    # Set the signature.html file path
    signature_path = os.path.join(settings.BASE_DIR, 'materiah', 'templates', 'signature.html')

    # Open, read and return the file content
    try:
        with open(signature_path, 'r', encoding='utf-8') as file:
            signature_content = file.read()
        return Response({'signature': signature_content}, status=200)
    except Exception as e:
        return Response({'error': str(e)}, status=500)


@api_view(['POST'])
def update_email_signature(request):
    """
    Update the email signature template.

    :param request: The request object.
    :type request: rest_framework.request.Request
    :return: A response indicating if the signature was updated successfully or an error message.
    :rtype: rest_framework.response.Response
    """
    # Fetch the new signature HTML content
    signature_content = request.data.get('template')

    # Set the default HTML case code
    static_html_template = """
    <!DOCTYPE html>
    <html lang="he" dir="rtl">
    <head>
        <meta charset="UTF-8">
        <title>Title</title>
    </head>
    <body>
    {content}
    </body>
    </html>
    """

    # Insert the new signature in the {content} brackets
    full_html_content = static_html_template.format(content=signature_content)
    # Set the signature file path
    signature_path = os.path.join(settings.BASE_DIR, 'materiah', 'templates', 'signature.html')

    # Write the new content into the file
    try:
        with open(signature_path, 'w', encoding='utf-8') as file:
            file.write(full_html_content)
        return Response({'message': 'Signature updated successfully'}, status=200)
    except Exception as e:
        return Response({'error': str(e)}, status=500)
