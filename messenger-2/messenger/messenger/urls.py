from django.contrib import admin
from django.urls import path, include
from django.views.generic.base import RedirectView

urlpatterns = [
    path('admin/', admin.site.urls),
    path('chat/', include('chat.urls')), 
    path('accounts/', include('django.contrib.auth.urls')),

    path('', RedirectView.as_view(url='/chat/', permanent=True)),
]