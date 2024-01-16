import os

from rest_framework import pagination
from rest_framework.response import Response


class MateriahPagination(pagination.PageNumberPagination):
    """MateriahPagination

    A class that inherits from `pagination.PageNumberPagination` to provide pagination functionality specifically for Materiah API.

    Attributes:
        page_size (int): The number of items to be displayed per page. Default is 12.
        max_page_size (int): The maximum number of items to be displayed per page. Default is 16.
        page_query_param (str): The query parameter used for page navigation. Default is "page_num".

    Methods:
        get_paginated_response(data):
            Retrieves the paginated response.

    Example usage:

    ```python
    pagination_class = MateriahPagination()

    # Retrieve paginated response
    response = pagination_class.get_paginated_response(data)
    print(response)
    ```
    """
    page_size = 4
    max_page_size = 4
    page_query_param = "page_num"

    def get_paginated_response(self, data):
        """
        :param data: A list or queryset of data to be paginated.
        :return: A `Response` object containing the paginated data with the following structure:
            - 'next': A link to the next page, if available, as returned by `get_next_link()` method of the current view.
            - 'results': The paginated data, represented by the `data` parameter.
        """
        return Response({
            'next': self.get_next_link(),
            'results': data
        })

    def get_next_link(self):
        link = super().get_next_link()
        # Check if the USE_HTTPS environment variable is set to 'True'
        if os.environ.get('DJANGO_SETTINGS_MODULE') == 'materiahProject.settings.production':
            if link:
                link = link.replace('http://', 'https://')
        return link
