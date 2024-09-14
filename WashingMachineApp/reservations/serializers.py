import pytz
from rest_framework import serializers
from django.utils import timezone
from datetime import timedelta, time
from .models import Floor, Room, Individual, WashingMachineRoom, Reservation
from rest_framework.exceptions import PermissionDenied
from django.contrib.auth import get_user_model
from django.db.utils import IntegrityError
from rest_framework.exceptions import ValidationError
from rest_framework import serializers
from .models import Individual, Room

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


# Use the custom Individual model
Individual = get_user_model()




class IndividualRegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)
    confirm_password = serializers.CharField(write_only=True)
    room_number = serializers.IntegerField(write_only=True)
    username = serializers.CharField()
    email = serializers.EmailField()
    national_id = serializers.CharField()

    class Meta:
        model = Individual
        fields = [
            'username', 'first_name', 'last_name', 'email', 'password',
            'confirm_password', 'national_id', 'country', 'room_number'
        ]
        extra_kwargs = {
            'username': {'validators': []},
            'email': {'validators': []},
            'national_id': {'validators': []},
        }

    def validate_email(self, value):
        email_domain = value.lower().split('@')[-1]
        if not email_domain.endswith('.upt.ro'):
            if not email_domain.endswith('.ro'):
                raise serializers.ValidationError("Please use your UPT email address ending with '.upt.ro'.")
            else:
                raise serializers.ValidationError(
                    "Only email addresses from the 'upt.ro' domain or its subdomains are allowed. "
                    "If you are a UPT student or staff, please use your institutional email."
                )
        return value

    def validate(self, data):
        # Password and confirm password validation
        if data['password'] != data['confirm_password']:
            raise serializers.ValidationError({"detail": "Passwords do not match."})

        # Check if the email already exists (highest priority)
        if Individual.objects.filter(email=data['email']).exists():
            raise serializers.ValidationError({"detail": "The email is already registered."})

        # Check if the username already exists
        if Individual.objects.filter(username=data['username']).exists():
            raise serializers.ValidationError({"detail": "The username already exists."})

        # Check if the national ID already exists
        if Individual.objects.filter(national_id=data['national_id']).exists():
            raise serializers.ValidationError({"detail": "The national ID is already registered."})

        # Validate that the room number exists
        room_number = data.get('room_number')
        room = Room.objects.filter(room_number=room_number).first()

        if not room:
            raise serializers.ValidationError({"detail": "The room number does not exist. Please contact administration."})

        # Check if the room is full
        if room.individual_set.count() >= room.max_occupants:
            raise serializers.ValidationError({"detail": "The room is full. Please contact administration."})

        return data

    def create(self, validated_data):
        # Remove 'confirm_password' and 'room_number' since they're not model fields
        validated_data.pop('confirm_password', None)
        room_number = validated_data.pop('room_number', None)

        # Get the Room instance
        try:
            room = Room.objects.get(room_number=room_number)
        except Room.DoesNotExist:
            raise serializers.ValidationError({'room_number': 'Room does not exist. Please contact administration.'})

        # Assign the room to the user
        validated_data['room'] = room

        # Extract and remove the password from validated_data
        password = validated_data.pop('password')

        # Create the user instance without saving to the database yet
        user = Individual(**validated_data)
        user.set_password(password)  # Hash the password

        # Set is_active to False
        user.is_active = False

        user.save()  # Save the user to the database

        return user

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