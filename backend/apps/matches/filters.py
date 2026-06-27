import django_filters

from .models import Match


class MatchFilter(django_filters.FilterSet):
    date = django_filters.DateFilter(field_name="kickoff", lookup_expr="date")
    date_from = django_filters.DateFilter(field_name="kickoff", lookup_expr="date__gte")
    date_to = django_filters.DateFilter(field_name="kickoff", lookup_expr="date__lte")

    class Meta:
        model = Match
        fields = ["league", "status", "matchday", "date", "date_from", "date_to"]
