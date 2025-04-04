from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.contrib.auth.models import User
from django.contrib.auth import login, authenticate
from django.contrib import messages
from .forms import MessageForm, RegisterForm, AddUserForm
from .models import ChatRoom, Message
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
from rest_framework.views import APIView
from rest_framework import status
from rest_framework.response import Response
from django.db.models import Q

class MessageList(APIView):
    def get(self, request):
        room_id = request.GET.get('room_id')
        if not room_id:
            return Response({'error': 'room_id parameter is required'}, status=400)
            
        messages = Message.objects.filter(room_id=room_id).order_by('timestamp')
        data = [
            {
                'message_id': msg.id,
                'sender': msg.sender.username,
                'content': msg.content,
                'timestamp': msg.timestamp.isoformat(),
            }
            for msg in messages
        ]
        return Response(data)

def register(request):
    if request.method == 'POST':
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect('chat_rooms')
    else:
        form = RegisterForm()
    return render(request, 'registration/register.html', {'form': form})

@login_required
def search_users(request):
    query = request.GET.get('q', '')
    room_id = request.GET.get('room_id')
    
    if not query:
        return JsonResponse({'users': []})
    
    try:
        room = ChatRoom.objects.get(id=room_id)
        # Исключаем уже добавленных пользователей и создателя
        excluded_ids = list(room.members.values_list('id', flat=True)) + [room.created_by.id]
        users = User.objects.filter(
            Q(username__icontains=query) |
            Q(first_name__icontains=query) |
            Q(last_name__icontains=query)
        ).exclude(id__in=excluded_ids)[:10]  # Ограничиваем результаты
        
        results = [{
            'id': user.id,
            'username': user.username,
            'full_name': f"{user.first_name} {user.last_name}".strip() or user.username
        } for user in users]
        
        return JsonResponse({'users': results})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)

@login_required
def remove_member(request, room_id, user_id):
    room = get_object_or_404(ChatRoom, id=room_id)
    if not room.is_creator(request.user):
        messages.error(request, "Только создатель может управлять комнатой")
        return redirect('room_detail', room_id=room.id)
    
    try:
        user = User.objects.get(id=user_id)
        room.remove_member(user)
        messages.success(request, f"{user.username} удален из комнаты")
    except User.DoesNotExist:
        messages.error(request, "Пользователь не найден")
    
    return redirect('manage_room', room_id=room.id)

@login_required
def delete_room(request, room_id):
    room = get_object_or_404(ChatRoom, id=room_id)
    
    # Проверяем, что пользователь - создатель комнаты
    if room.created_by != request.user:
        messages.error(request, "Вы не можете удалить эту комнату")
        return redirect('room_detail', room_id=room.id)
    
    if request.method == 'POST':
        room_name = room.name
        room.delete()
        messages.success(request, f"Комната '{room_name}' удалена")
        return redirect('chat_rooms')
    
    return redirect('room_detail', room_id=room.id)

@login_required
def manage_room(request, room_id):
    room = get_object_or_404(ChatRoom, id=room_id)
    
    # Проверяем, что пользователь - создатель комнаты
    if room.created_by != request.user:
        messages.error(request, "Вы не можете управлять этой комнатой")
        return redirect('room_detail', room_id=room.id)
    
    if request.method == 'POST':
        # Обработка добавления пользователя
        if 'add_user' in request.POST:
            username = request.POST.get('username')
            try:
                user = User.objects.get(username=username)
                if user not in room.members.all():
                    room.members.add(user)
                    messages.success(request, f"Пользователь {username} добавлен")
                    
                    # Если это AJAX-запрос, возвращаем только список участников
                    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                        current_members = room.members.exclude(id=room.created_by.id)
                        return render(request, 'chat/_members_list.html', {
                            'members': current_members
                        })
                else:
                    messages.warning(request, f"Пользователь {username} уже в комнате")
            except User.DoesNotExist:
                # Добавляем сообщение об ошибке
                error_message = f"Пользователь с именем '{username}' не найден"
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return JsonResponse({'error': error_message}, status=404)
                messages.error(request, error_message)
        
        # Обработка удаления пользователя
        elif 'remove_user' in request.POST:
            user_id = request.POST.get('user_id')
            try:
                user = User.objects.get(id=user_id)
                if user != request.user:  # Нельзя удалить себя
                    room.members.remove(user)
                    messages.success(request, f"Пользователь {user.username} удален")
                    
                    # Если это AJAX-запрос, возвращаем только список участников
                    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                        current_members = room.members.exclude(id=room.created_by.id)
                        return render(request, 'chat/_members_list.html', {
                            'members': current_members
                        })
                else:
                    messages.warning(request, "Вы не можете удалить себя из комнаты")
            except User.DoesNotExist:
                messages.error(request, "Пользователь не найден")
        
        return redirect('manage_room', room_id=room.id)
    
    current_members = room.members.exclude(id=room.created_by.id)
    
    return render(request, 'chat/manage_room.html', {
        'room': room,
        'members': current_members
    })
    
@login_required
def chat_rooms(request):
    rooms = request.user.chat_rooms.all()
    return render(request, 'chat/rooms.html', {'rooms': rooms})

@login_required
def room_detail(request, room_id):
    room = get_object_or_404(ChatRoom, id=room_id)
    if request.user not in room.members.all():
        return redirect('chat_rooms')
    
    # Убираем загрузку сообщений - они будут загружаться через API
    return render(request, 'chat/room.html', {
        'room': room,
        'form': MessageForm()
    })

@login_required
def create_room(request):
    if request.method == 'POST':
        room_name = request.POST.get('room_name')
        user_ids = request.POST.getlist('users')
        
        # Add created_by=request.user when creating the room
        room = ChatRoom.objects.create(name=room_name, created_by=request.user)
        room.members.add(request.user)
        for user_id in user_ids:
            user = User.objects.get(id=user_id)
            room.members.add(user)
        
        return redirect('room_detail', room_id=room.id)
    
    users = User.objects.exclude(id=request.user.id)
    return render(request, 'chat/create_room.html', {'users': users})