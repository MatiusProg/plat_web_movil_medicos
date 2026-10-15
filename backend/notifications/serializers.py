from rest_framework import serializers

from .models import DeviceToken


class DeviceTokenSerializer(serializers.Serializer):
    token = serializers.CharField(max_length=4096)
    platform = serializers.ChoiceField(
        choices=DeviceToken.Platform.choices, default=DeviceToken.Platform.ANDROID,
    )


class ForgetDeviceSerializer(serializers.Serializer):
    token = serializers.CharField(max_length=4096)
