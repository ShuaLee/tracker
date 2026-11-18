from rest_framework.permissions import SAFE_METHODS, BasePermission

from . import access


class HasPortfolioRole(BasePermission):
    """Object-level role check (PLAN.md 1.4): reads need any role, writes need
    owner/manager, deletion needs owner.

    Only ever runs on objects the view already fetched through
    access.accessible_portfolios(), so "no access at all" has already become
    a 404 - this decides between "allowed" and 403 for users who can at
    least see the object.

    Works on a Portfolio (uses its `my_role` annotation) or, for the child
    models to come, on anything with a `portfolio` attribute. A view can
    raise the bar for custom actions with `required_role = {"action": role}`.
    """

    def _required_role(self, request, view):
        custom = getattr(view, "required_role", {}).get(getattr(view, "action", None))
        if custom:
            return custom
        if request.method in SAFE_METHODS:
            return access.READ
        if request.method == "DELETE":
            return access.OWN
        return access.EDIT

    def has_object_permission(self, request, view, obj):
        role = getattr(obj, "my_role", None)
        if role is None:
            portfolio = getattr(obj, "portfolio", obj)
            role = access.role_for(request.user, portfolio)
        return access.has_role(role, self._required_role(request, view))
