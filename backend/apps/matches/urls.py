from rest_framework.routers import DefaultRouter

from .views import MatchViewSet, RefereeViewSet, StadiumViewSet

router = DefaultRouter()
router.register("matches", MatchViewSet, basename="match")
router.register("referees", RefereeViewSet, basename="referee")
router.register("stadiums", StadiumViewSet, basename="stadium")

urlpatterns = router.urls
