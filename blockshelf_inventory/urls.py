from django.contrib import admin
from django.urls import path, include
from django.views.generic import RedirectView
from django.contrib.auth import views as auth_views
from inventory.views.auth import custom_login

urlpatterns = [
    path('admin/', admin.site.urls),
    # Auth routes (with rate limiting)
    path('login/', custom_login, name='login'),
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),
    # allauth for social login
    path('accounts/', include('allauth.urls')),
    # App
    path('', RedirectView.as_view(pattern_name='inventory:list', permanent=False)),
    path('inventory/', include('inventory.urls')),
]

handler404 = "inventory.views.error_404"
handler500 = "inventory.views.error_500"