from datetime import datetime

from django.db.models import F, Count
from drf_spectacular.utils import extend_schema, OpenApiParameter
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from rest_framework.response import Response

from airport.models import (
    Crew,
    AirplaneType,
    Airplane,
    Airport,
    Route,
    Flight,
    Order,
    Country,
    City
)
from airport.permissions import IsAdminOrIfAuthenticatedReadOnly, IsAdminOrReadOnly
from airport.serializers import (
    CrewSerializer,
    AirplaneTypeSerializer,
    AirplaneSerializer,
    RouteSerializer,
    AirportSerializer,
    FlightSerializer,
    AirplaneListSerializer,
    RouteListSerializer,
    OrderSerializer,
    OrderListSerializer,
    AirportListSerializer,
    CountrySerializer,
    CitySerializer,
    CityListSerializer,
    AirplaneImageSerializer,
    AirplaneDetailSerializer,
    FlightListDetailSerializer,
)


class CrewViewSet(viewsets.ModelViewSet):
    queryset = Crew.objects.all()
    serializer_class = CrewSerializer
    permission_classes = (IsAdminOrIfAuthenticatedReadOnly,)


class AirplaneTypeViewSet(viewsets.ModelViewSet):
    queryset = AirplaneType.objects.all()
    serializer_class = AirplaneTypeSerializer
    permission_classes = (IsAdminUser,)


class AirplaneViewSet(viewsets.ModelViewSet):
    queryset = Airplane.objects.select_related("airplane_type")
    serializer_class = AirplaneSerializer
    permission_classes = (IsAdminOrIfAuthenticatedReadOnly,)

    def get_serializer_class(self):
        serializer = self.serializer_class
        if self.action == "list":
            return AirplaneListSerializer

        if self.action == "retrieve":
            return AirplaneDetailSerializer

        if self.action == "upload_image":
            return AirplaneImageSerializer

        return serializer

    @action(methods=["POST"], detail=True, url_path="upload-image", )
    def upload_image(self, request, pk=None):
        item = self.get_object()
        serializer = self.get_serializer(item, data=request.data)

        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class AirportViewSet(viewsets.ModelViewSet):
    queryset = Airport.objects.select_related(
        "closest_big_city__country",
    )
    serializer_class = AirportSerializer
    permission_classes = (IsAdminOrReadOnly,)

    def get_queryset(self):
        queryset = self.queryset

        airport_name = self.request.query_params.get("airport_name")
        city = self.request.query_params.get("city")

        if airport_name:
            queryset = queryset.filter(name__icontains=airport_name)

        if city:
            queryset = queryset.filter(closest_big_city__name__icontains=city)

        return queryset.distinct()

    def get_serializer_class(self):
        if self.action in ("list", "retrieve"):
            return AirportListSerializer

        return self.serializer_class

    # only for documentation
    @extend_schema(
        parameters=[
            OpenApiParameter(
                "airport_name",
                type={"type": "list", "items": {"type": "str"}},
                description="Filter by airport name"
            ),
            OpenApiParameter(
                "city",
                type={"type": "list", "items": {"type": "str"}},
                description="Filter by city"
            ),
        ]
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)


def params_to_ints(queryset: str) -> list:
    """convert a list of string ids to a list of integer"""
    return [int(str_id) for str_id in queryset.split(",")]


class PaginationClass(PageNumberPagination):
    page_size = 5
    page_size_query_param = "page_size"
    max_page_size = 100


class RouteViewSet(viewsets.ModelViewSet):
    queryset = Route.objects.select_related(
        "source__closest_big_city__country",
        "destination__closest_big_city__country",
    )
    serializer_class = RouteSerializer
    pagination_class = PaginationClass
    permission_classes = (IsAdminOrReadOnly,)

    def get_queryset(self):
        queryset = self.queryset

        source = self.request.query_params.get("source")
        destination = self.request.query_params.get("destination")

        if source:
            source_ids = params_to_ints(source)
            queryset = queryset.filter(source__id__in=source_ids)

        if destination:
            destination_ids = params_to_ints(destination)
            queryset = queryset.filter(destination__id__in=destination_ids)

        return queryset

    def get_serializer_class(self):
        serializer = self.serializer_class
        if self.action in ("list", "retrieve"):
            return RouteListSerializer

        return serializer

    # only for documentation
    @extend_schema(
        parameters=[
            OpenApiParameter(
                "source",
                type={"type": "list", "items": {"type": "number"}},
                description="Filter by source id"
            ),
            OpenApiParameter(
                "destination",
                type={"type": "list", "items": {"type": "number"}},
                description="Filter by destination id"
            ),
        ]
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)


class FlightViewSet(viewsets.ModelViewSet):
    queryset = Flight.objects.select_related(
        "route__source__closest_big_city__country",
        "route__destination__closest_big_city__country",
        "airplane__airplane_type",
    ).prefetch_related("crew")
    serializer_class = FlightSerializer
    pagination_class = PaginationClass
    permission_classes = (IsAdminOrReadOnly,)

    def get_queryset(self):
        queryset = self.queryset

        route = self.request.query_params.get("route")
        departure_time = self.request.query_params.get("departure_time")

        if route:
            route_ids = params_to_ints(route)
            queryset = queryset.filter(route__id__in=route_ids)

        if departure_time:
            departure_time = datetime.strptime(departure_time, "%Y-%m-%d").date()
            queryset = queryset.filter(departure_time__date=departure_time)

        if self.action in ("list", "retrieve"):
            queryset = queryset.annotate(
                free_tickets_seat=F("airplane__rows") * F("airplane__seats_in_row") - Count("tickets")
            )
        return queryset

    def get_serializer_class(self):
        serializer = self.serializer_class

        if self.action in ("list", "retrieve"):
            return FlightListDetailSerializer

        return serializer

    # only for documentation
    @extend_schema(
        parameters=[
            OpenApiParameter(
                "route",
                type={"type": "list", "items": {"type": "number"}},
                description="Filter by route id"
            ),
            OpenApiParameter(
                "departure_time",
                type={
                    "type": "datetime.date",
                    "items": {"type": "datetime.date"}
                },
                description="Filter by departure time"
            ),
        ]
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)


class OrderViewSet(viewsets.ModelViewSet):
    queryset = Order.objects.prefetch_related(
        "tickets__flight__route__source__closest_big_city__country",
        "tickets__flight__route__destination__closest_big_city__country",
        "tickets__flight__crew",
        "tickets__flight__airplane__airplane_type"

    )
    serializer_class = OrderSerializer
    pagination_class = PaginationClass
    permission_classes = (IsAuthenticated,)

    def get_queryset(self):
        queryset = self.queryset
        queryset = queryset.filter(user=self.request.user).distinct()
        return queryset

    def get_serializer_class(self):
        if self.action in ("list", "retrieve"):
            return OrderListSerializer

        return OrderSerializer

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class CountryViewSet(viewsets.ModelViewSet):
    queryset = Country.objects.all()
    serializer_class = CountrySerializer
    permission_classes = (IsAdminUser,)


class CityViewSet(viewsets.ModelViewSet):
    queryset = City.objects.select_related("country")
    serializer_class = CitySerializer
    permission_classes = (IsAdminUser,)

    def get_serializer_class(self):
        if self.action in ("list", "retrieve"):
            return CityListSerializer

        return self.serializer_class
