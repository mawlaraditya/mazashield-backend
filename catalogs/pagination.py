from rest_framework.pagination import PageNumberPagination


class CatalogPagination(PageNumberPagination):
    """
    Pagination for public-facing catalog endpoints (Mazdafarm, Mazdaging, Invest).
    Uses page_size=12 so the grid (3-col) fills evenly with 4 rows.
    Does NOT override the global PAGE_SIZE used by internal admin views.
    """
    page_size = 12
    page_size_query_param = 'page_size'
    max_page_size = 50
