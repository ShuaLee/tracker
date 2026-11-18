from rest_framework.routers import DefaultRouter

from . import views

router = DefaultRouter(trailing_slash=True)
router.register("portfolios", views.PortfolioViewSet, basename="portfolio")

urlpatterns = router.urls
