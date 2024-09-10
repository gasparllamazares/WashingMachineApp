from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import FloorViewSet, RoomViewSet, IndividualViewSet, WashingMachineRoomViewSet, ReservationViewSet



router = DefaultRouter()
router.register(r'floors', FloorViewSet)
router.register(r'rooms', RoomViewSet)
router.register(r'individuals', IndividualViewSet)
router.register(r'washingmachinerooms', WashingMachineRoomViewSet)
router.register(r'reservations', ReservationViewSet, basename='reservation')

urlpatterns = [
    path('', include(router.urls)),
    # Auth endpoints
]
