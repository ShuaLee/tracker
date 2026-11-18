from rest_framework import mixins, viewsets
from rest_framework.permissions import IsAuthenticated

from . import access
from .serializers import PortfolioSerializer


class PortfolioViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.UpdateModelMixin,
    viewsets.GenericViewSet,
):
    """/api/portfolios/ - the caller's portfolio.

    Every user has exactly one: created at signup (holdings/signals.py) and
    living as long as the account. So there is no create or delete here, only
    read and update (rename, base currency). Someone else's portfolio is a
    404 because it's simply not in the queryset.
    """

    serializer_class = PortfolioSerializer
    permission_classes = [IsAuthenticated]
    http_method_names = ["get", "patch", "head", "options"]

    def get_queryset(self):
        return access.accessible_portfolios(self.request.user)
