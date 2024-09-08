from django.urls import path
from .views import FloorFreeSlotsView

urlpatterns = [
    path('floor/<int:floor_id>/free_hours/', FloorFreeSlotsView.as_view(), name='floor_free_slots'),
    ]