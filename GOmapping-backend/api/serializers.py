from rest_framework import serializers

from orgnizations.models import *

class GOSummarySerializer(serializers.Serializer):
    global_org_id = serializers.IntegerField()
    global_org_name = serializers.CharField()
    usage_count = serializers.IntegerField()
    most_similar_go = serializers.CharField(allow_null=True, required=False)
    similarity_percent = serializers.DecimalField(max_digits=5, decimal_places=2, allow_null=True, required=False)


class GlobalOrganizationSerializer(serializers.ModelSerializer):
    class Meta:
        model = GlobalOrganization
        fields = '__all__'


class OrgMappingSerializer(serializers.ModelSerializer):
    global_org = GlobalOrganizationSerializer(read_only=True)
    
    class Meta:
        model = OrgMapping
        fields = '__all__'


class GoSimilaritySerializer(serializers.ModelSerializer):
    source_org = GlobalOrganizationSerializer(source='source_global_org', read_only=True)
    target_org = GlobalOrganizationSerializer(source='target_global_org', read_only=True)
    
    class Meta:
        model = GoSimilarity
        fields = '__all__'