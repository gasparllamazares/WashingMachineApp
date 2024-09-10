from rest_framework import viewsets
from django.core.exceptions import ValidationError
from .models import Floor, Room, Individual, WashingMachineRoom, Reservation
from rest_framework import serializers
from .serializers import FloorSerializer, RoomSerializer, IndividualSerializer, WashingMachineRoomSerializer, ReservationSerializer
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from rest_framework.exceptions import PermissionDenied
from django.utils import timezone


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

    def perform_update(self, serializer):
        # Custom logic for updating (if needed), otherwise just save
        serializer.save()

    def destroy(self, request, *args, **kwargs):
        # Get the reservation instance
        reservation = self.get_object()

        # Check if the current user is the one who created the reservation
        if reservation.individual != request.user:
            raise PermissionDenied("You do not have permission to delete this reservation.")

        if reservation.reservation_time <= timezone.now():
            raise ValidationError("You cannot delete a reservation that has already started or is in the past.")

        # If the user is authorized, proceed with the deletion
        self.perform_destroy(reservation)
        return Response(status=status.HTTP_204_NO_CONTENT)

    def perform_destroy(self, instance):
        instance.delete()