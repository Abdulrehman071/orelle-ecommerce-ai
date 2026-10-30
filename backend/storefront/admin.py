from django.contrib import admin
from .models import NewsletterSubscriber, Notification, StoreLocation

admin.site.register(NewsletterSubscriber)
admin.site.register(Notification)
admin.site.register(StoreLocation)
