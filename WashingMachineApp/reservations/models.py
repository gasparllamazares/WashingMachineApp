from base64 import encode
import uuid
from django.contrib.auth.models import AbstractUser
from django.db import models
from django.core.exceptions import ValidationError
from django_countries.fields import CountryField
from datetime import timedelta, time
from django.utils import timezone
import pytz


class Floor(models.Model):
    floor_number = models.IntegerField(unique=True)

    def __str__(self):
        return f"Floor {self.floor_number}"


class Room(models.Model):
    floor = models.ForeignKey(Floor, on_delete=models.CASCADE)
    room_number = models.IntegerField()
    max_occupants = models.IntegerField(default=2)

    def clean(self):
        # Ensure that the floor exists to avoid NoneType errors
        if not self.floor:
            raise ValidationError("The room must be assigned to a floor.")

        # Convert room_number and floor_number to strings before slicing
        room_number_str = str(self.room_number).zfill(3)
        floor_number_str = str(self.floor.floor_number)

        # Ensure the room number starts with the correct floor number (fix for multiple digits)
        if not room_number_str.startswith(floor_number_str):
            raise ValidationError(f"Room number {room_number_str} does not match Floor {floor_number_str}.")

        # Pre-save check: Validate that the room doesn't exceed its max_occupants limit before saving
        if self.pk:  # Ensure that the room has been saved before checking occupants
            current_occupants_count = self.individual_set.count()

            if current_occupants_count > self.max_occupants:
                raise ValidationError(
                    f"Room {self.room_number} currently exceeds the maximum of {self.max_occupants} occupants.")


    def save(self, *args, **kwargs):
        # Pre-save check
        self.clean()

        # Save the room first
        super().save(*args, **kwargs)

        # Post-save check: Check that the number of occupants does not exceed the max after save
        current_occupants_count = self.individual_set.count()

        if current_occupants_count > self.max_occupants:
            raise ValidationError(
                f"Room {self.room_number} will exceed the maximum of {self.max_occupants} occupants after the save.")

    def __str__(self):
        return f"Room {self.room_number}"

    class Meta:
        unique_together = ('floor', 'room_number')


class Individual(AbstractUser):  # Extend Django's User model
    room = models.ForeignKey('Room', on_delete=models.SET_NULL, null=True, blank=True)
    country = CountryField(null=True, blank=True)  # Country field from django-countries
    national_id = models.CharField(max_length=50, unique=True, null=True, blank=True)  # National ID/Passport
    admin_floor = models.IntegerField(null=True, blank=True, help_text="The floor this user administers.")
    validated_email = models.BooleanField(default=False, help_text="Set to true when the user's email is verified")
    def clean(self):
        if self.room:
            room_number_str = str(self.room.room_number).zfill(3)
            floor_number_str = str(self.room.floor.floor_number)


            if room_number_str[:1] != floor_number_str:
                raise ValidationError(
                    f"The selected room {room_number_str} does not match the floor {floor_number_str}.")

        if self.room:
            # Ensure the room doesn't exceed its max occupants limit
            if self.room.individual_set.exclude(id=self.id).count() >= self.room.max_occupants:
                raise ValidationError(
                    f"Room {self.room.room_number} cannot have more than {self.room.max_occupants} occupants.")

    def __str__(self):
        return f'{self.first_name} {self.last_name}'  # Display username and national ID


class WashingMachineRoom(models.Model):
    floor = models.ForeignKey(Floor, on_delete=models.SET_NULL, null=True, blank=True)

    def __str__(self):
        return f"Washing Machine Room on {self.floor}"


class Reservation(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    room = models.ForeignKey(Room, on_delete=models.CASCADE)
    individual = models.ForeignKey(Individual, on_delete=models.CASCADE)  # The user making the reservation
    reservation_time = models.DateTimeField()
    duration = models.DurationField(default=timedelta(minutes=40))  # Default to 40-minute intervals
    created_at = models.DateTimeField(auto_now_add=True)  # Timestamp for when the reservation is created
    floor = models.ForeignKey(Floor, on_delete=models.SET_NULL, null=True, blank=True)

    def save(self, *args, **kwargs):
        # Auto-populate the floor field from the room
        if self.room and not self.floor:
            self.floor = self.room.floor
        super(Reservation, self).save(*args, **kwargs)

    '''def delete(self, user=None, *args, **kwargs):
        # Check if the reservation has already started
        if self.reservation_time <= timezone.now():
            if user == self.individual and not user.is_staff:
                raise ValidationError("You cannot delete a reservation that has already started.")
        super(Reservation, self).delete(*args, **kwargs)  # Actually delete the instance'''

    def clean(self):
        # Call the individual clean methods
        #self.clean_duration()
        self.clean_overlap()
        #self.clean_weekly_limit()
        #self.clean_past_reservation()
        #self.clean_sunday_reservation()
        #self.clean_working_hours()
        #self.clean_within_valid_weeks()

    def clean_duration(self):
        """Validate duration is at least 40 minutes and does not exceed 4 hours."""
        if self.duration < timedelta(minutes=40):
            raise ValidationError("Reservations must be at least 40 minutes long.")

        if self.duration > timedelta(hours=4):
            raise ValidationError("Reservations cannot exceed 4 hours (240 minutes).")

    def clean_overlap(self):
        """Check for overlapping reservations across all rooms on the same floor."""
        reservation_end_time = self.reservation_time + self.duration

        # Get all reservations on the same floor as the current room
        overlapping_reservations = Reservation.objects.filter(
            room__floor=self.room.floor,  # Filter by the same floor as the room
            reservation_time__lt=reservation_end_time,
            reservation_time__gt=self.reservation_time - self.duration
        ).exclude(pk=self.pk)

        if overlapping_reservations.exists():
            raise ValidationError(
                f"Another room on floor {self.room.floor.floor_number} already has a reservation during this time.")

    def clean_weekly_limit(self):
        """Ensure the room doesn't exceed 4 hours of reservations per week."""
        week_start = self.reservation_time - timedelta(days=self.reservation_time.weekday())  # Start of the week
        week_end = week_start + timedelta(days=7)
        weekly_reservations = Reservation.objects.filter(
            room=self.room,
            reservation_time__gte=week_start,
            reservation_time__lt=week_end
        ).exclude(pk=self.pk)
        total_reserved_time = sum([res.duration for res in weekly_reservations], timedelta())
        total_reserved_time += self.duration  # Add the current reservation to the total

        if total_reserved_time > timedelta(hours=4):
            raise ValidationError(
                f"Room {self.room.room_number} cannot have more than 4 hours of reservations per week.")

    def clean_past_reservation(self):
        """Check if the reservation is in the past."""
        if self.reservation_time < timezone.now():
            raise ValidationError("Reservations cannot be made in the past.")

    def clean_sunday_reservation(self):
        """Check if the reservation is on a Sunday."""
        if self.reservation_time.weekday() == 6:
            raise ValidationError("Reservations cannot be made on Sundays.")

    def clean_working_hours(self):
        """Check if the reservation is within working hours (7:00 AM to 11:00 PM)."""
        reservation_start_time = self.reservation_time.time()
        reservation_end_time = (self.reservation_time + self.duration).time()  # Calculate the end time

        start_of_day = time(7, 0)  # Start time (7:00 AM)
        end_of_day = time(23, 0)  # End time (11:00 PM)

        # Ensure both start time and end time are within working hours
        if not (start_of_day <= reservation_start_time <= end_of_day):
            raise ValidationError("Reservations can only start between 7:00 AM and 11:00 PM.")

        if not (start_of_day <= reservation_end_time <= end_of_day):
            raise ValidationError("Reservations must end by 11:00 PM.")


    def clean_within_valid_weeks(self):
        """Validate that the reservation is within this week or next week."""
        bucharest_tz = pytz.timezone('Europe/Bucharest')
        now_in_bucharest = timezone.now().astimezone(bucharest_tz)
        start_of_this_week = now_in_bucharest - timedelta(days=now_in_bucharest.weekday())
        start_of_this_week = start_of_this_week.replace(hour=0, minute=0, second=0, microsecond=0)
        end_of_next_week = start_of_this_week + timedelta(days=13)
        end_of_next_week = end_of_next_week.replace(hour=23, minute=59, second=59, microsecond=999999)

        if not (start_of_this_week <= self.reservation_time.astimezone(bucharest_tz) <= end_of_next_week):
            raise ValidationError("Reservations can only be made from Monday of this week to Sunday of next week.")

    def __str__(self):
        return f"Reservation by {self.individual} for Room {self.room} on {self.reservation_time}"

# Create your models here.
