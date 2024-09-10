from rest_framework import serializers
from django.utils import timezone
from datetime import timedelta, time
import pytz
from .models import Floor, Room, Individual, WashingMachineRoom, Reservation
from rest_framework.exceptions import PermissionDenied

class FloorSerializer(serializers.ModelSerializer):
    class Meta:
        model = Floor
        fields = '__all__'


class RoomSerializer(serializers.ModelSerializer):
    floor = FloorSerializer(read_only=True)

    class Meta:
        model = Room
        fields = '__all__'


class IndividualSerializer(serializers.ModelSerializer):
    class Meta:
        model = Individual
        fields = ['id', 'username', 'first_name', 'last_name', 'national_id', 'room', 'country']


class WashingMachineRoomSerializer(serializers.ModelSerializer):
    floor = FloorSerializer(read_only=True)

    class Meta:
        model = WashingMachineRoom
        fields = '__all__'


class ReservationSerializer(serializers.ModelSerializer):
    individual_name = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = Reservation
        fields = ['reservation_time', 'duration', 'created_at', 'individual_name', 'id']
        read_only_fields = ['created_at', 'individual_name', 'id']

    def get_individual_name(self, obj):
        return f"{obj.individual.first_name} {obj.individual.last_name}"

    def validate(self, data):
        """
        Perform all the validations previously in the model's clean() method.
        """
        user = self.context['request'].user
        room = user.room

        # Ensure the user has a room assigned
        if not room:
            raise serializers.ValidationError("User must be assigned to a room to make a reservation.")

        reservation_time = data.get('reservation_time')
        duration = data.get('duration')


        # Validation: Ensure only the owner can update their reservation
        if self.instance and self.instance.individual != user:
            raise PermissionDenied("You do not have permission to update this reservation.")

        # Validation 1: Ensure the duration is between 40 minutes and 4 hours
        if duration < timedelta(minutes=40):
            raise serializers.ValidationError("Reservations must be at least 40 minutes long.")
        if duration > timedelta(hours=4):
            raise serializers.ValidationError("Reservations cannot exceed 4 hours (240 minutes).")

        # Validation 2: Check for overlapping reservations on the same floor
        reservation_end_time = reservation_time + duration
        overlapping_reservations = Reservation.objects.filter(
            room__floor=room.floor,
            reservation_time__lt=reservation_end_time,
            reservation_time__gt=reservation_time - duration
        )

        # Exclude the instance if it's an update operation
        if self.instance:
            overlapping_reservations = overlapping_reservations.exclude(pk=self.instance.pk)

        if overlapping_reservations.exists():
            raise serializers.ValidationError(
                f"Another room on floor {room.floor.floor_number} already has a reservation during this time."
            )

        # Validation 3: Ensure the room doesn't exceed 4 hours of reservations per week
        week_start = reservation_time - timedelta(days=reservation_time.weekday())
        week_end = week_start + timedelta(days=7)
        weekly_reservations = Reservation.objects.filter(
            room=room,
            reservation_time__gte=week_start,
            reservation_time__lt=week_end
        )

        # Exclude the instance if it's an update operation
        if self.instance:
            weekly_reservations = weekly_reservations.exclude(pk=self.instance.pk)

        total_reserved_time = sum([res.duration for res in weekly_reservations], timedelta())
        total_reserved_time += duration

        if total_reserved_time > timedelta(hours=4):
            raise serializers.ValidationError(
                f"Room {room.room_number} cannot have more than 4 hours of reservations per week.")

        # Validation 4: No reservations in the past
        if reservation_time < timezone.now():
            raise serializers.ValidationError("Reservations cannot be made in the past.")

        # Validation 5: No reservations on Sundays
        if reservation_time.weekday() == 6:
            raise serializers.ValidationError("Reservations cannot be made on Sundays.")

        # Validation 6: Ensure reservation is within working hours (7:00 AM to 11:00 PM)
        reservation_start_time = reservation_time.time()
        reservation_end_time_time = (reservation_time + duration).time()

        start_of_day = time(7, 0)  # 7:00 AM
        end_of_day = time(23, 0)  # 11:00 PM

        if not (start_of_day <= reservation_start_time <= end_of_day):
            raise serializers.ValidationError("Reservations can only start between 7:00 AM and 11:00 PM.")
        if not (start_of_day <= reservation_end_time_time <= end_of_day):
            raise serializers.ValidationError("Reservations must end by 11:00 PM.")

        # Validation 7: Ensure reservation is within this week or next week
        bucharest_tz = pytz.timezone('Europe/Bucharest')
        now_in_bucharest = timezone.now().astimezone(bucharest_tz)
        start_of_this_week = now_in_bucharest - timedelta(days=now_in_bucharest.weekday())
        start_of_this_week = start_of_this_week.replace(hour=0, minute=0, second=0, microsecond=0)
        end_of_next_week = start_of_this_week + timedelta(days=13)
        end_of_next_week = end_of_next_week.replace(hour=23, minute=59, second=59, microsecond=999999)

        if not (start_of_this_week <= reservation_time.astimezone(bucharest_tz) <= end_of_next_week):
            raise serializers.ValidationError("Reservations can only be made within the current and next week.")

        return data