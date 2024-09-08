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
from .models import Reservation, Room
import pytz

class FloorNonAvailableSlotsView(APIView):
    def get(self, request, floor_id):
        # Define Bucharest timezone
        bucharest_tz = pytz.timezone('Europe/Bucharest')
        now = timezone.now().astimezone(bucharest_tz)

        # Start of this week (Monday 00:00:00 Bucharest time)
        start_of_this_week = now - timedelta(days=now.weekday())
        start_of_this_week = start_of_this_week.replace(hour=0, minute=0, second=0, microsecond=0)

        # End of next week (Sunday 23:59:59 Bucharest time)
        end_of_next_week = start_of_this_week + timedelta(days=13)
        end_of_next_week = end_of_next_week.replace(hour=23, minute=59, second=59, microsecond=999999)

        # Initialize reserved slots for the entire floor
        reserved_slots = {}

        # Collect all reservations across all rooms on the floor
        reservations = Reservation.objects.filter(
            room__floor_id=floor_id,
            reservation_time__gte=start_of_this_week,
            reservation_time__lte=end_of_next_week
        ).order_by('reservation_time')

        # Loop through the days from the start of the current week to the end of next week
        for day in range(14):  # 14 days from this Monday to the next Sunday
            current_day = start_of_this_week + timedelta(days=day)
            reserved_slots_for_day = []

            # Filter reservations for the current day
            day_reservations = [res for res in reservations if res.reservation_time.date() == current_day.date()]

            for reservation in day_reservations:
                # Ensure reservation is in Bucharest timezone
                reservation_start = reservation.reservation_time.astimezone(bucharest_tz)
                reservation_end = reservation_start + reservation.duration

                # Add reserved slot for the day
                reserved_slots_for_day.append({
                    "start_time": reservation_start.strftime("%H:%M"),
                    "end_time": reservation_end.strftime("%H:%M"),
                    "room": reservation.room.room_number  # Optional: Include room number
                })

            # Add reserved slots for the day to the final response
            reserved_slots[str(current_day.date())] = reserved_slots_for_day

        return Response(reserved_slots)