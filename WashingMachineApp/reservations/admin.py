import pytz
from django.utils import timezone
from django.contrib import admin
from datetime import time
from django import forms
from django.core.exceptions import ValidationError
from django.db.models import F, ExpressionWrapper, DateTimeField
from .models import Floor, Room, Individual, WashingMachineRoom, Reservation
from django.contrib import messages
# Change the admin site title
admin.site.site_header = 'Laundry Room Management'


def activate_users(modeladmin, request, queryset):
    """Activate selected users."""
    queryset.update(is_active=True)
    messages.success(request, f"{queryset.count()} user(s) were successfully activated.")

activate_users.short_description = "Activate selected users"

def deactivate_users(modeladmin, request, queryset):
    """Deactivate selected users."""
    queryset.update(is_active=False)
    messages.success(request, f"{queryset.count()} user(s) were successfully deactivated.")

deactivate_users.short_description = "Deactivate selected users"


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
        fields = ['individuals']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['individuals'].queryset = Individual.objects.filter(room__isnull=True) | Individual.objects.filter(room=self.instance)
        if self.instance.pk:
            # Prepopulate the field with users already assigned to this room
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
    form = RoomForm
    readonly_fields = ('room_number', 'floor', 'max_occupants')
    list_display = ('room_number', 'floor', 'get_assigned_individuals')
    search_fields = ['room_number', 'individual__username']
    list_filter = ('floor',)

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def get_assigned_individuals(self, obj):
        individuals = Individual.objects.filter(room=obj)
        return ", ".join([individual.username for individual in individuals])
    get_assigned_individuals.short_description = 'Assigned Individuals'

    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        if request.user.groups.filter(name='Floor Admins').exists():
            admin_floor = request.user.admin_floor
            if admin_floor is not None:
                return queryset.filter(floor=admin_floor)
            else:
                return queryset.none()
        return queryset

# Custom admin class to display additional information about floors
class FloorAdmin(admin.ModelAdmin):
    list_display = ('floor_number', 'room_count', 'occupied_rooms', 'total_individuals', 'washing_machine_room_status')
    readonly_fields = ('floor_number',)


    def room_count(self, obj):
        return Room.objects.filter(floor=obj).count()
    room_count.short_description = 'Total Rooms'

    def occupied_rooms(self, obj):
        return Room.objects.filter(floor=obj).exclude(individual__isnull=True).distinct().count()
    occupied_rooms.short_description = 'Occupied Rooms'

    def total_individuals(self, obj):
        return Individual.objects.filter(room__floor=obj).count()
    total_individuals.short_description = 'Total Individuals'

    def washing_machine_room_status(self, obj):
        washing_room = WashingMachineRoom.objects.filter(floor=obj).first()
        if not washing_room:
            return "No Washing Machine Room"

        # Get current time in Bucharest timezone
        bucharest_tz = pytz.timezone('Europe/Bucharest')
        now_in_bucharest = timezone.now().astimezone(bucharest_tz)
        current_time = now_in_bucharest.time()

        # Operational hours
        start_of_day = time(7, 0)  # 7:00 AM
        end_of_day = time(23, 0)   # 11:00 PM

        # Check for current reservations
        from django.db.models.functions import Now

        # Annotate end_time as reservation_time + duration
        current_reservations = Reservation.objects.filter(
            floor=obj
        ).annotate(
            end_time=ExpressionWrapper(
                F('reservation_time') + F('duration'),
                output_field=DateTimeField()
            )
        ).filter(
            reservation_time__lte=now_in_bucharest,
            end_time__gte=now_in_bucharest
        )

        if current_reservations.exists():
            return "Occupied"

        # No current reservation
        if start_of_day <= current_time <= end_of_day:
            return "Available"
        else:
            return "Closed"

    washing_machine_room_status.short_description = 'Washing Machine Room Status'

    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        if request.user.groups.filter(name='Floor Admins').exists():
            admin_floor = request.user.admin_floor
            if admin_floor is not None:
                return queryset.filter(id=admin_floor)
            else:
                return queryset.none()
        return queryset

# Custom admin class to disable add, edit, and delete actions for washing machine rooms
class WashingMachineRoomAdmin(admin.ModelAdmin):
    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    list_display = ('floor',)
    readonly_fields = ('floor',)

    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        if request.user.groups.filter(name='Floor Admins').exists():
            admin_floor = request.user.admin_floor
            if admin_floor is not None:
                return queryset.filter(floor=admin_floor)
            else:
                return queryset.none()
        return queryset

class IndividualAdmin(admin.ModelAdmin):
    fields = ['username', 'first_name', 'last_name', 'national_id', 'country', 'email', 'room', 'groups', 'validated_email', 'is_active']
    list_display = ('username', 'email', 'first_name', 'last_name', 'national_id', 'country', 'room','validated_email', 'is_active')
    search_fields = ('username', 'email', 'national_id')
    filter_horizontal = ['groups']
    actions = [activate_users, deactivate_users]
    def get_readonly_fields(self, request, obj=None):
        readonly_fields = super().get_readonly_fields(request, obj)
        if obj is not None and request.user == obj and request.user.groups.filter(name='Floor Admins').exists():
            return readonly_fields + ('is_active', 'groups')
        if request.user.groups.filter(name='Floor Admins').exists():
            return readonly_fields + ('groups',)
        return readonly_fields

    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        if request.user.groups.filter(name='Floor Admins').exists():
            form.base_fields.pop('groups', None)
        return form

    def has_delete_permission(self, request, obj=None):
        if request.user.groups.filter(name='Floor Admins').exists():
            if obj and obj.room and obj.room.floor == request.user.admin_floor:
                return True
            return False
        return super().has_delete_permission(request, obj)

    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        if request.user.groups.filter(name='Floor Admins').exists():
            admin_floor = request.user.admin_floor
            if admin_floor is not None:
                return queryset.filter(room__floor=admin_floor)
            else:
                return queryset.none()
        return queryset

class ReservationForm(forms.ModelForm):
    class Meta:
        model = Reservation
        fields = ['room', 'individual', 'reservation_time', 'duration']

    def clean(self):
        cleaned_data = super().clean()
        room = cleaned_data.get('room')
        individual = cleaned_data.get('individual')

        # Ensure the individual belongs to the room they are trying to reserve
        if individual and room:
            if individual.room != room:
                raise ValidationError(f"Only individuals assigned to Room {room.room_number} can make reservations for this room.")

        return cleaned_data

class ReservationAdmin(admin.ModelAdmin):
    form = ReservationForm
    list_display = ['room', 'individual', 'get_floor', 'reservation_time', 'duration', 'created_at']
    list_filter = ['room__floor']
    search_fields = [
        'individual__username',
        'individual__first_name',
        'individual__last_name',
        'individual__email',
        'individual__national_id',
        'room__room_number',
        'reservation_time'
    ]

    def get_floor(self, obj):
        return obj.room.floor.floor_number
    get_floor.short_description = 'Floor'

    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        if request.user.groups.filter(name='Floor Admins').exists():
            admin_floor = request.user.admin_floor
            if admin_floor is not None:
                return queryset.filter(room__floor=admin_floor)
            else:
                return queryset.none()
        return queryset

    def has_delete_permission(self, request, obj=None):
        if obj and request.user.groups.filter(name='Floor Admins').exists():
            return obj.room.floor == request.user.admin_floor
        return super().has_delete_permission(request, obj)

admin.site.register(Individual, IndividualAdmin)
admin.site.register(Floor, FloorAdmin)
admin.site.register(Room, RoomAdmin)
admin.site.register(WashingMachineRoom, WashingMachineRoomAdmin)
admin.site.register(Reservation, ReservationAdmin)
