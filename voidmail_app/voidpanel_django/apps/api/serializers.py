from rest_framework import serializers
from apps.mail_engine.models import VirtualDomain, VirtualMailbox
from .models import ApiKey

class VirtualDomainSerializer(serializers.ModelSerializer):
    class Meta:
        model = VirtualDomain
        fields = ['id', 'name', 'is_verified', 'created_at']

class VirtualMailboxSerializer(serializers.ModelSerializer):
    class Meta:
        model = VirtualMailbox
        fields = ['id', 'domain', 'username', 'email', 'quota_mb', 'used_mb', 'is_active', 'created_at']
        read_only_fields = ['email', 'used_mb']

class SendEmailSerializer(serializers.Serializer):
    to = serializers.EmailField()
    from_email = serializers.EmailField(required=False)
    subject = serializers.CharField(max_length=255)
    html = serializers.CharField(required=False)
    text = serializers.CharField(required=False)
