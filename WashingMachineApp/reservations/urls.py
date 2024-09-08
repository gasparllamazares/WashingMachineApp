from django.urls import path
from .views import FloorNonAvailableSlotsView

urlpatterns = [
    path('floor/<int:floor_id>/free_hours/', FloorNonAvailableSlotsView.as_view(), name='floor_free_slots'),
    ]