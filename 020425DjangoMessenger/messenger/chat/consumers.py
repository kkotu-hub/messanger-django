import json
from channels.generic.websocket import AsyncWebsocketConsumer
from django.contrib.auth.models import AnonymousUser
from django.contrib.auth import get_user_model
from .models import Message, ChatRoom, UserProfile
from channels.db import database_sync_to_async
from django.utils import timezone

User = get_user_model()

class ChatConsumer(AsyncWebsocketConsumer):
    
    async def connect(self):
        self.room_id = self.scope['url_route']['kwargs']['room_id']
        self.room_group_name = f'chat_{self.room_id}'
        
        if isinstance(self.scope["user"], AnonymousUser):
            await self.close()
            return

        # Проверка существования комнаты
        if not await self.room_exists():
            await self.close()
            return

        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )
        await self.accept()

    @database_sync_to_async
    def room_exists(self):
        return ChatRoom.objects.filter(id=self.room_id).exists()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )

    async def receive(self, text_data):
        try:
            data = json.loads(text_data)
            message = data.get('content')
            
            if not message:
                raise ValueError("Message content is required")
            
            # Сохраняем сообщение в БД
            message_obj = await self.save_message(message)
            
            # Получаем URL аватарки отправителя
            avatar_url = await self.get_user_avatar_url(message_obj.sender)
            
            # Отправляем сообщение в группу
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'chat_message',
                    'message_id': message_obj.id,
                    'sender': message_obj.sender.username,
                    'content': message_obj.content,
                    'timestamp': message_obj.timestamp.isoformat(),
                    'avatar_url': avatar_url,
                }
            )
        except Exception as e:
            await self.send(text_data=json.dumps({
                'error': str(e)
            }))

    @database_sync_to_async
    def save_message(self, content):
        return Message.objects.create(
            room_id=self.room_id,
            sender=self.scope['user'],
            content=content
        )
    
    @database_sync_to_async
    def get_user_avatar_url(self, user):
        try:
            profile = UserProfile.objects.get(user=user)
            if profile.avatar:
                return profile.avatar.url
        except UserProfile.DoesNotExist:
            pass
        return '/static/chat/img/default_avatar.png'

    async def chat_message(self, event):
        await self.send(text_data=json.dumps({
            'type': 'message',
            'message_id': event['message_id'],
            'sender': event['sender'],
            'content': event['content'],
            'timestamp': event['timestamp'],
            'avatar_url': event['avatar_url'],
        }))