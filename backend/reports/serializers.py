from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers

from .models import Report


class ReportSerializer(serializers.ModelSerializer):
    type_label = serializers.CharField(source="get_type_display", read_only=True)
    generated_by_username = serializers.CharField(
        source="generated_by.username", read_only=True, default=None,
    )
    download_url = serializers.SerializerMethodField()

    class Meta:
        model = Report
        fields = "__all__"
        read_only_fields = ["id", "generated_by", "file_path", "created_at"]

    @extend_schema_field(OpenApiTypes.STR)
    def get_download_url(self, obj):
        if not obj.file_path or obj.pk is None:
            return None
        return f"/api/reports/{obj.pk}/download/"

    def validate(self, attrs):
        debut, fin = attrs.get("period_start"), attrs.get("period_end")
        if debut and fin and debut > fin:
            raise serializers.ValidationError({"period_end": "La fin de période doit être après le début."})
        return attrs
