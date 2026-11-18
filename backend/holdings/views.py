from rest_framework import mixins, viewsets
from rest_framework.permissions import IsAuthenticated

from . import access
from .permissions import HasPortfolioRole
from .serializers import PortfolioSerializer


class PortfolioViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.UpdateModelMixin,
    viewsets.GenericViewSet,
):
    """/api/portfolios/ - the portfolios the caller has access to.

    For now every user has exactly one: created at signup (holdings/signals.py)
    and living as long as the account. So there is no create or delete here.
    Update (rename, base currency) needs owner or manager.
    """

    serializer_class = PortfolioSerializer
    permission_classes = [IsAuthenticated, HasPortfolioRole]
    http_method_names = ["get", "patch", "head", "options"]

    def get_queryset(self):
        # Anything not in here is a 404 for this user, by construction.
        return access.accessible_portfolios(self.request.user)
