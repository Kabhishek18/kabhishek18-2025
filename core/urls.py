from django.urls import path
from .views import PageRequest, custom_404

handler404 = 'core.views.custom_404'

urlpatterns = [
    path('', PageRequest.as_view(), name="home_page"),  # Home page
    path('<slug:slug>/', PageRequest.as_view(), name="generic_page"),  # Catch all other pages
]