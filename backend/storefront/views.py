from rest_framework import viewsets, mixins, permissions
from .models import NewsletterSubscriber, StoreLocation, Notification
from .serializers import NewsletterSubscriberSerializer, StoreLocationSerializer, NotificationSerializer


class NewsletterSubscribeView(mixins.CreateModelMixin, viewsets.GenericViewSet):
    queryset = NewsletterSubscriber.objects.all()
    serializer_class = NewsletterSubscriberSerializer


class StoreLocationViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = StoreLocation.objects.all()
    serializer_class = StoreLocationSerializer
    filterset_fields = ['city']


class NotificationViewSet(mixins.ListModelMixin, viewsets.GenericViewSet):
    serializer_class = NotificationSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Notification.objects.filter(user=self.request.user)
