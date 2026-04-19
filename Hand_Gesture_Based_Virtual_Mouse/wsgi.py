"""
WSGI config for Hand_Gesture_Based_Virtual_Mouse project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/5.2/howto/deployment/wsgi/
"""

import os

from django.core.wsgi import get_wsgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Hand_Gesture_Based_Virtual_Mouse.settings')

application = get_wsgi_application()
