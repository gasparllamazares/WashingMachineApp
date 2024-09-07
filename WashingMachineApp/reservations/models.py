from django.contrib.auth.models import AbstractUser
from django.db import models
from django.core.exceptions import ValidationError
from django_countries.fields import CountryField
class Floor(models.Model):
    floor_number = models.IntegerField(unique=True)

    def __str__(self):
        return f"Floor {self.floor_number}"


class Room(models.Model):
    floor = models.ForeignKey(Floor, on_delete=models.SET_NULL, null=True, blank=True)
    room_number = models.IntegerField()
    max_occupants = models.IntegerField(default=2)

    def clean(self):
        # Convert room_number and floor_number to strings before slicing
        room_number_str = str(self.room_number)
        floor_number_str = str(self.floor.floor_number)

        # Ensure the room number starts with the correct floor number
        if room_number_str[:1] != floor_number_str:
            raise ValidationError(f"Room number {room_number_str} does not match Floor {floor_number_str}.")

    def __str__(self):
        return f"Room {self.room_number} on {self.floor}"

    class Meta:
        unique_together = ('floor', 'room_number')


class Individual(AbstractUser):  # Extend Django's User model
    room = models.ForeignKey('Room', on_delete=models.SET_NULL, null=True, blank=True)
    country = CountryField(null=True, blank=True)  # Country field from django-countries
    national_id = models.CharField(max_length=50, unique=True, null=True, blank=True)  # National ID/Passport

    def clean(self):
        if self.room:
            room_number_str = str(self.room.room_number)
            floor_number_str = str(self.room.floor.floor_number)

            if room_number_str[:1] != floor_number_str:
                raise ValidationError(
                    f"The selected room {room_number_str} does not match the floor {floor_number_str}.")

    def __str__(self):
        return f'{self.username} ({self.national_id})'  # Display username and national ID

class WashingMachineRoom(models.Model):
    floor = models.ForeignKey(Floor, on_delete=models.SET_NULL, null=True, blank=True)

    def __str__(self):
        return f"Washing Machine Room on {self.floor}"


class Reservation(models.Model):
    washing_machine_room = models.ForeignKey(WashingMachineRoom, on_delete=models.CASCADE)
    room = models.ForeignKey(Room, on_delete=models.CASCADE)
    reservation_time = models.DateTimeField()

    def __str__(self):
        return f"Reservation for {self.room} at {self.reservation_time}"

    class Meta:
        unique_together = ('room', 'reservation_time')
from django.db import models

# Create your models here.
