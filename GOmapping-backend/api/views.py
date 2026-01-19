from django.db.models import OuterRef, Subquery, DecimalField, CharField
from django.shortcuts import get_object_or_404
from rest_framework.decorators import api_view
from rest_framework.response import Response

from orgnizations.models import GlobalOrganization, GoSimilarity, OrgMapping
from .serializers import GlobalOrganizationSerializer

@api_view(['GET'])
def go_list(request):
    gos = GlobalOrganization.objects.all().order_by("global_org_id")
    serializer = GlobalOrganizationSerializer(gos, many=True)
    return Response(serializer.data)


@api_view(["GET"])
def go_summary(request):
    # Auto-update usage_count for all Global Organizations
    # Count how many instance organizations are mapped to each GO
    from django.db.models import Count
    
    # Calculate usage count for each GO from org_mapping table
    usage_counts = (
        OrgMapping.objects
        .values('global_org_id')
        .annotate(count=Count('id'))
    )
    
    # Update usage_count in global_organization table
    for item in usage_counts:
        GlobalOrganization.objects.filter(
            global_org_id=item['global_org_id']
        ).update(usage_count=item['count'])
    
    # Also set usage_count to 0 for GOs with no mappings
    # Get all GO IDs that have mappings
    go_ids_with_mappings = set(item['global_org_id'] for item in usage_counts)
    
    # Get all GO IDs
    all_go_ids = set(GlobalOrganization.objects.values_list('global_org_id', flat=True))
    
    # Find GOs with no mappings
    go_ids_without_mappings = all_go_ids - go_ids_with_mappings
    
    # Set their usage_count to 0
    if go_ids_without_mappings:
        GlobalOrganization.objects.filter(
            global_org_id__in=go_ids_without_mappings
        ).update(usage_count=0)
    
    # Now fetch the summary data with updated usage_count
    # Get best similarity for each GO
    best = (
        GoSimilarity.objects
        .filter(source_global_org_id=OuterRef("pk"))
        .order_by("-similarity_percent")
    )

    qs = (
        GlobalOrganization.objects
        .annotate(
            most_similar_go=Subquery(
                best.values("target_global_org__global_org_name")[:1],
                output_field=CharField(),
            ),
            similarity_percent=Subquery(
                best.values("similarity_percent")[:1],
                output_field=DecimalField(max_digits=5, decimal_places=2),
            ),
        )
        .values(
            "global_org_id",
            "global_org_name",
            "usage_count",
            "most_similar_go",
            "similarity_percent",
        )
        .order_by("global_org_id")
    )

    return Response(list(qs))


@api_view(["GET"])
def go_detail(request, go_id: int):
    """
    返回：
    {
      "go_info": {"id": 1, "name": "xxx"},
      "similar_gos": [{"go_id": 2, "go_name": "yyy", "similarity": 90.12, "mapping_count": 123}, ...]
    }
    """
    go = get_object_or_404(GlobalOrganization, global_org_id=go_id)

    similarities = (
        GoSimilarity.objects.filter(source_global_org_id=go_id)
        .select_related("target_global_org")
        .order_by("-similarity_percent", "target_global_org_id")
    )

    similar_gos = []
    for s in similarities:
        tgt = s.target_global_org
        similar_gos.append(
            {
                "go_id": tgt.global_org_id,
                "go_name": tgt.global_org_name,
                "similarity": float(s.similarity_percent) if s.similarity_percent is not None else None,
                # 前端展示“Mapping Count”，这里用 target GO 自带的 usage_count（与你 summary 页一致）
                "mapping_count": tgt.usage_count,
            }
        )

    return Response(
        {
            "go_info": {"id": go.global_org_id, "name": go.global_org_name},
            "similar_gos": similar_gos,
        }
    )


@api_view(["GET"])
def org_mapping(request, go_id: int):
    """
    返回：
    {
      "go_info": {"id": 1, "name": "xxx"},
      "organizations": [{"org_id": 10, "org_name": "...", "acronym": "...", "poolfund": "...", "similarity": 88.8}, ...]
    }
    """
    go = get_object_or_404(GlobalOrganization, global_org_id=go_id)

    qs = (
        OrgMapping.objects.filter(global_org_id=go_id)
        .values(
            "id",
            "instance_org_id",
            "instance_org_name",
            "instance_org_acronym",
            "fund_name",
            "match_percent",
        )
        .order_by("id")
    )

    organizations = []
    for row in qs:
        org_id = row["instance_org_id"] if row["instance_org_id"] is not None else row["id"]
        organizations.append(
            {
                "org_id": org_id,
                "org_name": row["instance_org_name"],
                "acronym": row["instance_org_acronym"],
                "poolfund": row["fund_name"],
                "similarity": float(row["match_percent"]) if row["match_percent"] is not None else None,
            }
        )

    return Response(
        {
            "go_info": {"id": go.global_org_id, "name": go.global_org_name},
            "organizations": organizations,
        }
    )


@api_view(["GET"])
def mapping_dashboard(request):
    """
    返回 Scenario 2 的完整数据结构
    [
      {
        "global_org_id": 206,
        "global_org_name": "Action For Development - South Sudan",
        "global_acronym": "AFOD",
        "mappings": [
          {
            "instance_org_id": 3611,
            "instance_org_name": "Action For Development",
            "instance_org_acronym": "AFOD-SS",
            "parent_instance_org_id": null,
            "fund_id": 20,
            "fund_name": "South Sudan",
            "match_percent": 62.00,
            "risk_level": "MEDIUM",
            "status": "Approved"
          },
          ...
        ]
      },
      ...
    ]
    """
    # 获取所有 GlobalOrganization 及其关联的 OrgMapping
    global_orgs = GlobalOrganization.objects.all().order_by("global_org_id")
    
    result = []
    for go in global_orgs:
        mappings_qs = OrgMapping.objects.filter(global_org_id=go.global_org_id).order_by("id")
        
        mappings = []
        for mapping in mappings_qs:
            mappings.append({
                "instance_org_id": mapping.instance_org_id,
                "instance_org_name": mapping.instance_org_name,
                "instance_org_acronym": mapping.instance_org_acronym,
                "parent_instance_org_id": mapping.parent_instance_org_id,
                "fund_id": mapping.fund_id,
                "fund_name": mapping.fund_name,
                "match_percent": float(mapping.match_percent) if mapping.match_percent is not None else None,
                "risk_level": mapping.risk_level,
                "status": mapping.status,
            })
        
        # 只包含有 mappings 的 GO
        if mappings:
            result.append({
                "global_org_id": go.global_org_id,
                "global_org_name": go.global_org_name,
                "global_acronym": go.global_acronym,
                "mappings": mappings,
            })
    
    return Response(result)




