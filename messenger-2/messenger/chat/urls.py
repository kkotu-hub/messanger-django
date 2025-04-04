from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

urlpatterns = [
    path('api/messages/', views.MessageList.as_view(), name='message-list'),
    
    path('', views.chat_rooms, name='chat_rooms'),
    path('room/<int:room_id>/', views.room_detail, name='room_detail'),
    path('create/', views.create_room, name='create_room'),
    
    # Аутентификация
    path('accounts/login/', auth_views.LoginView.as_view(template_name='registration/login.html'), name='login'),
    path('accounts/logout/', auth_views.LogoutView.as_view(), name='logout'),
    path('accounts/register/', views.register, name='register'),

    path('room/<int:room_id>/delete/', views.delete_room, name='delete_room'),
    path('room/<int:room_id>/manage/', views.manage_room, name='manage_room'),
]