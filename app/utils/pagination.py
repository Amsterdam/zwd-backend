from rest_framework.pagination import PageNumberPagination


class CustomPagination(PageNumberPagination):
    page_size = 10  # Default page size
    page_size_query_param = "page_size"  # Allows clients to set page size
    max_page_size = 1000  # Maximum limit to prevent overload
