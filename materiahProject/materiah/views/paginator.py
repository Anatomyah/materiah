from rest_framework import pagination
from rest_framework.response import Response


class MateriahPagination(pagination.PageNumberPagination):
    page_size = 2
    max_page_size = 4
    page_query_param = "page_num"

    def get_paginated_response(self, data):
        return Response({
            'next': self.get_next_link(),
            'results': data
        })
