from rest_framework.routers import DefaultRouter

from .views import CoachViewSet, LeagueViewSet, PlayerViewSet, TeamViewSet

router = DefaultRouter()
router.register("leagues", LeagueViewSet, basename="league")
router.register("teams", TeamViewSet, basename="team")
router.register("coaches", CoachViewSet, basename="coach")
router.register("players", PlayerViewSet, basename="player")

urlpatterns = router.urls
