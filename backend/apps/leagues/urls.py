from rest_framework.routers import DefaultRouter

from .views import LeagueViewSet, TeamViewSet

router = DefaultRouter()
router.register("leagues", LeagueViewSet, basename="league")
router.register("teams", TeamViewSet, basename="team")

urlpatterns = router.urls
