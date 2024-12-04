import os
import django
from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack
from channels.layers import get_channel_layer
from games.routing import websocket_urlpatterns

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "AllGameZone.settings")
django.setup()

application = ProtocolTypeRouter({
    "http": get_asgi_application(),
    "websocket": AuthMiddlewareStack(
        URLRouter(
            websocket_urlpatterns
        )
    ),
})

# For Daphne to recognize the ASGI application
channel_layer = get_channel_layer()