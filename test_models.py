import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from django.conf import settings
from google import genai

client = genai.Client(api_key=settings.GEMINI_API_KEY)

print("=== MODELOS DISPONÍVEIS ===")

for model in client.models.list():
    print(model.name)