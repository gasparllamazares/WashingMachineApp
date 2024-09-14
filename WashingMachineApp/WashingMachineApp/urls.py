from django.contrib import admin
from django.urls import path, include
from reservations.views import IndividualRegisterView  # Absolute import
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
    TokenBlacklistView,
)

urlpatterns = [
    path('admin/', admin.site.urls),

    # Authentication Endpoints (better placed in the main project URLs)
    path('auth/login/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('auth/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('auth/logout/', TokenBlacklistView.as_view(), name='token_blacklist'),
    path('auth/register/', IndividualRegisterView.as_view(), name='register'),


    # API endpoints for reservations (delegated to the app)
    path('api/', include('reservations.urls')),
]
