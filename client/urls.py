from django.urls import path
from django.contrib.auth import views as auth_views
from . import views
from .forms import SpanishAuthenticationForm

urlpatterns = [
    path('login/', auth_views.LoginView.as_view(template_name='login.html', authentication_form=SpanishAuthenticationForm), name='client-login'),
    path('logout/', views.logout_view, name='client-logout'),
    path('register/', views.register, name='client-register'),
]
