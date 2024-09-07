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


 # Change the admin site title
admin.site.site_header = 'Laundry Room Management'

# Custom form to allow selecting individuals for a room
class RoomForm(forms.ModelForm):
    individuals = forms.ModelMultipleChoiceField(
        queryset=Individual.objects.all(),
        widget=admin.widgets.FilteredSelectMultiple('Individuals', is_stacked=False),  # Dual list box with search
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
            self.fields['individuals'].initial = Individual.objects.filter(room=self.instance)

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


admin.site.register(Individual, IndividualAdmin)
admin.site.register(Floor, FloorAdmin)
admin.site.register(Room, RoomAdmin)
admin.site.register(WashingMachineRoom, WashingMachineRoomAdmin)
admin.site.register(Reservation)
