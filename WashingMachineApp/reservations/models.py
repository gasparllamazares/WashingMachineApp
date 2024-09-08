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
        # Ensure that the floor exists to avoid NoneType errors
        if not self.floor:
            raise ValidationError("The room must be assigned to a floor.")

        # Convert room_number and floor_number to strings before slicing
        room_number_str = str(self.room_number).zfill(3)
        floor_number_str = str(self.floor.floor_number)

        # Ensure the room number starts with the correct floor number (fix for multiple digits)
        if not room_number_str.startswith(floor_number_str):
            raise ValidationError(f"Room number {room_number_str} does not match Floor {floor_number_str}.")

        # Validate that the room doesn't exceed its max_occupants limit
        if self.pk:  # Ensure that the room has been saved before checking occupants
            if self.individual_set.count() > self.max_occupants:
                raise ValidationError(f"Room {self.room_number} cannot have more than {self.max_occupants} occupants.")

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
            room_number_str = str(self.room.room_number).zfill(3)
            floor_number_str = str(self.room.floor.floor_number)

            if room_number_str[:1] != floor_number_str:
                raise ValidationError(
                    f"The selected room {room_number_str} does not match the floor {floor_number_str}.")

        if self.room and self.room.individual_set.count() >= self.room.max_occupants:
            raise ValidationError(
                f"The room {self.room.room_number} cannot have more than {self.room.max_occupants} occupants.")

    def __str__(self):
        return f'{self.first_name} {self.last_name}'  # Display username and national ID

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
