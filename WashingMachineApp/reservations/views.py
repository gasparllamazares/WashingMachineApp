from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .models import Room, Reservation, Floor
from datetime import datetime, timedelta, time
from django.utils import timezone
import pytz


from django.utils import timezone
from datetime import timedelta, datetime, time
from rest_framework.views import APIView
from rest_framework.response import Response
from reservations.models import Reservation, Room
import pytz

class FloorFreeSlotsView(APIView):
    def get(self, request, floor_id):
        # Define Bucharest timezone
        bucharest_tz = pytz.timezone('Europe/Bucharest')

        # Get the current time in Bucharest
        now = timezone.now().astimezone(bucharest_tz)

        # Start of this week (Monday 00:00:00 Bucharest time)
        start_of_this_week = now - timedelta(days=now.weekday())
        start_of_this_week = start_of_this_week.replace(hour=0, minute=0, second=0, microsecond=0)

        # End of next week (Sunday 23:59:59 Bucharest time)
        end_of_next_week = start_of_this_week + timedelta(days=13)
        end_of_next_week = end_of_next_week.replace(hour=23, minute=59, second=59, microsecond=999999)

        # Initialize free slots for the entire floor
        free_slots = {}

        # Get all rooms on the selected floor
        rooms = Room.objects.filter(floor_id=floor_id)

        # Collect all reservations across all rooms on the floor
        reservations = Reservation.objects.filter(
            room__floor_id=floor_id,
            reservation_time__gte=start_of_this_week,
            reservation_time__lte=end_of_next_week
        ).order_by('reservation_time')

        # Define available hours in a day (6:00 AM to 11:00 PM)
        start_time = time(6, 0)
        end_time = time(23, 0)

        # Loop through the days from the start of the current week to the end of next week
        for day in range(14):  # 14 days from this Monday to the next Sunday
            current_day = start_of_this_week + timedelta(days=day)
            current_day_start = datetime.combine(current_day, start_time, tzinfo=bucharest_tz)
            current_day_end = datetime.combine(current_day, end_time, tzinfo=bucharest_tz)

            # Keep track of free slots for the entire floor for each day
            free_slots_for_day = []

            # Track the last end time of any reservation
            last_end_time = current_day_start

            for reservation in reservations:
                if reservation.reservation_time.date() == current_day.date():
                    # Calculate the free time before the reservation starts
                    if reservation.reservation_time > last_end_time:
                        free_slots_for_day.append(
                            (last_end_time, reservation.reservation_time)
                        )
                    last_end_time = reservation.reservation_time + reservation.duration

            # Check if there is free time after the last reservation of the day
            if last_end_time < current_day_end:
                free_slots_for_day.append(
                    (last_end_time, current_day_end)
                )

            # Convert datetime.date to string for JSON serialization
            free_slots[str(current_day.date())] = free_slots_for_day

        return Response(free_slots)