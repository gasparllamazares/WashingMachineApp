from django.contrib import admin
from .models import Floor, Room, Individual, WashingMachineRoom, Reservation
from django import forms


from django import forms
from django.contrib import admin
from .models import Room, Individual
from django.utils.safestring import mark_safe
# Custom form to select existing individuals for a room
from django import forms
from django.contrib import admin
from .models import Room, Individual
from django_countries import countries
from django.core.exceptions import ValidationError
from datetime import timedelta

 # Change the admin site title
admin.site.site_header = 'Laundry Room Management'

# Custom form to allow selecting individuals for a room
class RoomForm(forms.ModelForm):
    individuals = forms.ModelMultipleChoiceField(
        queryset=Individual.objects.filter(room__isnull=True),  # Only show individuals without a room
        widget=admin.widgets.FilteredSelectMultiple('Individuals', is_stacked=False),
        required=False,
        label='Assigned Individuals',
    )

    class Meta:
        model = Room
        fields = ['room_number', 'floor', 'max_occupants', 'individuals']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance.pk:
            # Prepopulate the field with users already assigned to this room
            # Keep the already assigned individuals in the current room available for selection
            self.fields['individuals'].queryset = Individual.objects.filter(room__isnull=True) | Individual.objects.filter(room=self.instance)
            self.fields['individuals'].initial = Individual.objects.filter(room=self.instance)

    def clean_individuals(self):
        individuals = self.cleaned_data['individuals']
        max_occupants = self.instance.max_occupants

        # Check if adding these individuals would exceed the maximum occupants
        if individuals.count() > max_occupants:
            raise ValidationError(f"No more than {max_occupants} occupants can be assigned to this room.")

        return individuals


    def save(self, commit=True):
        instance = super().save(commit=False)
        instance.save()

        # Get the selected individuals from the form
        individuals = self.cleaned_data['individuals']

        # Assign selected individuals to this room
        individuals.update(room=instance)

        # Unassign individuals that were previously assigned but are now unchecked
        Individual.objects.filter(room=instance).exclude(id__in=individuals).update(room=None)

        return instance
# Custom admin class to display additional information about rooms
class RoomAdmin(admin.ModelAdmin):
    form = RoomForm  # Use the custom form for multi-select with search
    readonly_fields = ('room_number', 'floor', 'max_occupants')
    list_display = ('room_number', 'floor', 'get_assigned_individuals')

    # Allow searching by room number and by individual name (through individual_set)
    search_fields = ['room_number', 'individual__username']



    def has_add_permission(self, request):
        return False
    # Add filter to filter rooms by floor
    list_filter = ('floor',)

    def has_delete_permission(self, request, obj=None):
        # Prevent delete button from appearing
        return False

    # Custom method to display assigned individuals in the list view
    def get_assigned_individuals(self, obj):
        individuals = Individual.objects.filter(room=obj)
        return ", ".join([individual.username for individual in individuals])

    get_assigned_individuals.short_description = 'Assigned Individuals'

# Custom admin class to display additional information about floors
class FloorAdmin(admin.ModelAdmin):
    list_display = ('floor_number', 'room_count', 'occupied_rooms', 'total_individuals', 'washing_machine_room_status')
    readonly_fields = ('floor_number',)

    # Custom method to display the total number of rooms on the floor
    def room_count(self, obj):
        return Room.objects.filter(floor=obj).count()
    room_count.short_description = 'Total Rooms'

    # Custom method to display the number of occupied rooms on the floor
    def occupied_rooms(self, obj):
        return Room.objects.filter(floor=obj, individual__isnull=False).distinct().count()
    occupied_rooms.short_description = 'Occupied Rooms'

    # Custom method to display the total number of individuals on the floor
    def total_individuals(self, obj):
        return Individual.objects.filter(room__floor=obj).count()
    total_individuals.short_description = 'Total Individuals'

    # Custom method to display the status of the washing machine room
    def washing_machine_room_status(self, obj):
        washing_room = WashingMachineRoom.objects.get(floor=obj)
        current_reservations = Reservation.objects.filter(washing_machine_room=washing_room).exists()
        return "Reserved" if current_reservations else "Available"
    washing_machine_room_status.short_description = 'Washing Machine Room Status'

# Custom admin class to disable add, edit, and delete actions for washing machine rooms
class WashingMachineRoomAdmin(admin.ModelAdmin):
    # Disable add, edit, and delete actions
    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    # Make the list view display washing machine rooms but disable editing
    list_display = ('floor',)
    readonly_fields = ('floor',)

# Custom method to display the status of the washing machine room
class IndividualAdmin(admin.ModelAdmin):
    # Specify the field order and place national_id and country after last_name
    fields = ['username', 'first_name', 'last_name', 'national_id', 'country', 'email', 'room']

    list_display = ('username', 'email', 'first_name', 'last_name', 'national_id', 'country', 'room')
    search_fields = ('username', 'email', 'national_id')  # Enable search by national ID


class ReservationForm(forms.ModelForm):
    class Meta:
        model = Reservation
        fields = ['room', 'reservation_time', 'duration']

    def clean_duration(self):
        duration = self.cleaned_data['duration']

        # Ensure reservation is in 40-minute intervals
        if duration.total_seconds() % 2400 != 0:
            raise ValidationError("Reservations must be in 40-minute intervals.")

        # Ensure reservation does not exceed 4 hours
        if duration > timedelta(hours=4):
            raise ValidationError("Reservations cannot exceed 4 hours.")

        return duration

    def clean(self):
        cleaned_data = super().clean()
        room = cleaned_data.get('room')
        reservation_time = cleaned_data.get('reservation_time')
        duration = cleaned_data.get('duration')

        # Ensure room doesn't exceed 4 hours per week
        if room and reservation_time and duration:
            week_start = reservation_time - timedelta(days=reservation_time.weekday())
            week_end = week_start + timedelta(days=7)

            # Get all reservations for this room in the current week
            weekly_reservations = Reservation.objects.filter(
                room=room,
                reservation_time__gte=week_start,
                reservation_time__lt=week_end
            )

            total_reserved_time = sum([res.duration for res in weekly_reservations], timedelta())

            # Add current reservation duration to the total
            total_reserved_time += duration

            if total_reserved_time > timedelta(hours=4):
                raise ValidationError(f"Room {room.room_number} cannot exceed 4 hours of reservations in a week.")

        return cleaned_data

admin.site.register(Individual, IndividualAdmin)
admin.site.register(Floor, FloorAdmin)
admin.site.unregister(Floor)
admin.site.register(Room, RoomAdmin)
admin.site.register(WashingMachineRoom, WashingMachineRoomAdmin)
admin.site.register(Reservation)
