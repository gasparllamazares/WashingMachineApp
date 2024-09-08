from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .models import Room, Reservation, Floor
from datetime import datetime, timedelta, time
from django.utils import timezone

def get_free_time_intervals_for_floor(floor, date):
    """
    Get free time intervals for the entire floor on a specific date.
    A time interval is only considered free if all rooms on the floor are available.
    """
    start_time = time(6, 0)
    end_time = time(23, 0)
    interval_minutes = 40

    free_intervals = []
    current_time = datetime.combine(date, start_time)
    end_time_dt = datetime.combine(date, end_time)

    # Get all reservations for this floor on the specific date
    reservations = Reservation.objects.filter(room__floor=floor, reservation_time__date=date)

    reserved_slots = []
    for reservation in reservations:
        reserved_time = reservation.reservation_time
        reserved_end_time = reserved_time + reservation.duration
        slot_start = reserved_time
        while slot_start < reserved_end_time:
            reserved_slots.append(slot_start)
            slot_start += timedelta(minutes=interval_minutes)

    # Group free slots into intervals
    temp_interval_start = None
    while current_time + timedelta(minutes=interval_minutes) <= end_time_dt:
        if current_time not in reserved_slots:
            if temp_interval_start is None:
                temp_interval_start = current_time  # Start a new free interval
        else:
            if temp_interval_start is not None:
                free_intervals.append((temp_interval_start, current_time))  # End the interval
                temp_interval_start = None
        current_time += timedelta(minutes=interval_minutes)

    # If there's an ongoing free interval at the end of the day
    if temp_interval_start is not None:
        free_intervals.append((temp_interval_start, end_time_dt))

    return free_intervals


class FloorFreeSlotsView(APIView):
    def get(self, request, floor_id):
        try:
            today = timezone.now().date()
            floor = Floor.objects.get(id=floor_id)

            free_intervals = get_free_time_intervals_for_floor(floor, today)

            # Format free intervals as a list of dictionaries
            free_intervals_formatted = [{
                'start': interval[0].strftime('%H:%M'),
                'end': interval[1].strftime('%H:%M')
            } for interval in free_intervals]

            return Response({
                'floor': floor.floor_number,
                'free_intervals': free_intervals_formatted
            }, status=status.HTTP_200_OK)

        except Floor.DoesNotExist:
            return Response({'error': 'Floor not found.'}, status=status.HTTP_404_NOT_FOUND)
