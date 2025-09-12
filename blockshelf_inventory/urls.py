from django.contrib import admin
from django.urls import path, include
from django.views.generic import RedirectView
from django.contrib.auth import views as auth_views

urlpatterns = [
    path('admin/', admin.site.urls),
    # Auth routes
    path('login/', auth_views.LoginView.as_view(template_name='registration/login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),
    # allauth for social login
    path('accounts/', include('allauth.urls')),
    # App
    path('', RedirectView.as_view(pattern_name='inventory:list', permanent=False)),
    path('inventory/', include('inventory.urls')),
]

handler404 = "inventory.views.error_404"
handler500 = "inventory.views.error_500"