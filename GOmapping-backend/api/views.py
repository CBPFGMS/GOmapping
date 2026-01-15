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
    # 取“每个 source_global_org 的最大 similarity_percent 对应那一行”
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




