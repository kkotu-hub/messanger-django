import os
from django.core.asgi import get_asgi_application

# Установите переменную окружения ДО импорта приложений Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'messenger.settings')

# Получите Django ASGI application
django_application = get_asgi_application()

from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack
import chat.routing

application = ProtocolTypeRouter({
    "http": django_application,
    "websocket": AuthMiddlewareStack(
        URLRouter(
            chat.routing.websocket_urlpatterns
        )
    ),
})