from rest_framework import serializers

from .models import Portfolio


class PortfolioSerializer(serializers.ModelSerializer):
    owner_email = serializers.EmailField(source="owner.email", read_only=True)
    # From access.accessible_portfolios()'s annotation.
    my_role = serializers.CharField(read_only=True)

    class Meta:
        model = Portfolio
        fields = ["id", "name", "base_currency", "owner_email", "my_role", "created_at", "updated_at"]
        read_only_fields = ["id", "owner_email", "my_role", "created_at", "updated_at"]
