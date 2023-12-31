from django.urls import path, include
from rest_framework import routers

from airport.views import (
    CrewViewSet,
    AirplaneTypeViewSet,
    AirplaneViewSet,
    AirportViewSet,
    FlightViewSet,
    RouteViewSet,
    OrderViewSet,
    CountryViewSet,
    CityViewSet,
)

router = routers.DefaultRouter()
router.register("crews", CrewViewSet)
router.register("airplane_types", AirplaneTypeViewSet)
router.register("airplanes", AirplaneViewSet)
router.register("airports", AirportViewSet)
router.register("routes", RouteViewSet)
router.register("flights", FlightViewSet)
router.register("orders", OrderViewSet)
router.register("cities", CityViewSet)
router.register("countries", CountryViewSet)

urlpatterns = [
    path("", include(router.urls))
]

app_name = "airport"
