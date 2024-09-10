from rest_framework import viewsets
from django.core.exceptions import ValidationError
from .models import Floor, Room, Individual, WashingMachineRoom, Reservation
from rest_framework import serializers
from .serializers import FloorSerializer, RoomSerializer, IndividualSerializer, WashingMachineRoomSerializer, ReservationSerializer
from rest_framework.permissions import IsAuthenticated


class FloorViewSet(viewsets.ModelViewSet):
    queryset = Floor.objects.all()
    serializer_class = FloorSerializer
    permission_classes = [IsAuthenticated]


class RoomViewSet(viewsets.ModelViewSet):
    queryset = Room.objects.all()
    serializer_class = RoomSerializer
    permission_classes = [IsAuthenticated]


class IndividualViewSet(viewsets.ModelViewSet):
    queryset = Individual.objects.all()
    serializer_class = IndividualSerializer
    permission_classes = [IsAuthenticated]


class WashingMachineRoomViewSet(viewsets.ModelViewSet):
    queryset = WashingMachineRoom.objects.all()
    serializer_class = WashingMachineRoomSerializer
    permission_classes = [IsAuthenticated]



class ReservationViewSet(viewsets.ModelViewSet):
    serializer_class = ReservationSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user

        if not user.room:
            return Reservation.objects.none()

        # If the user is staff, return all reservations
        if user.is_staff:
            return Reservation.objects.all()

        # Otherwise, return reservations on the user's floor
        return Reservation.objects.filter(room__floor=user.room.floor)

    def perform_create(self, serializer):
        # Automatically assign the current user and their room to the reservation
        serializer.save(individual=self.request.user, room=self.request.user.room)
