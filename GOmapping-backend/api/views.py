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
    from django.db.models import Count
    from organization_knowledge_base import get_recommendation_score
    
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
    
    # Set usage_count to 0 for GOs with no mappings
    go_ids_with_mappings = set(item['global_org_id'] for item in usage_counts)
    all_go_ids = set(GlobalOrganization.objects.values_list('global_org_id', flat=True))
    go_ids_without_mappings = all_go_ids - go_ids_with_mappings
    
    if go_ids_without_mappings:
        GlobalOrganization.objects.filter(
            global_org_id__in=go_ids_without_mappings
        ).update(usage_count=0)
    
    # Build grouped data structure - Real-time similarity calculation
    from difflib import SequenceMatcher
    import re
    
    SIMILARITY_THRESHOLD = 60.0  # Lowered to catch more potential duplicates
    
    # Get all GOs for comparison
    all_gos_for_comparison = GlobalOrganization.objects.all()
    
    def normalize_name(name):
        """Normalize name: lowercase, remove special chars, remove stop words"""
        if not name:
            return ""
        name = name.lower()
        name = re.sub(r'[^\w\s]', ' ', name)
        name = re.sub(r'\s+', ' ', name).strip()
        stop_words = {'the', 'of', 'for', 'and', 'in', 'to', 'a', 'an', 'at', 'on'}
        words = [w for w in name.split() if w not in stop_words]
        return ' '.join(words)
    
    def calculate_similarity(go1, go2):
        """Calculate similarity between two GOs"""
        name1 = go1.global_org_name or ""
        name2 = go2.global_org_name or ""
        
        # Exact match (case-insensitive)
        if name1.lower() == name2.lower():
            return 100.0
        
        # Normalize names
        norm1 = normalize_name(name1)
        norm2 = normalize_name(name2)
        
        if not norm1 or not norm2:
            return 0.0
        
        # Sequence similarity
        seq_sim = SequenceMatcher(None, norm1, norm2).ratio() * 100
        
        # Token similarity (Jaccard)
        tokens1 = set(norm1.split())
        tokens2 = set(norm2.split())
        if tokens1 and tokens2:
            intersection = tokens1.intersection(tokens2)
            union = tokens1.union(tokens2)
            token_sim = (len(intersection) / len(union)) * 100 if union else 0
        else:
            token_sim = 0
        
        # Acronym matching
        acronym1 = (go1.global_acronym or "").upper()
        acronym2 = (go2.global_acronym or "").upper()
        acronym_sim = 100.0 if (acronym1 and acronym2 and acronym1 == acronym2) else 0
        
        # Weighted combination
        if acronym_sim == 100.0:
            # Perfect acronym match - high base score
            final_sim = 75.0 + (seq_sim * 0.15) + (token_sim * 0.10)
        else:
            final_sim = (seq_sim * 0.5) + (token_sim * 0.3) + (acronym_sim * 0.2)
        
        return min(final_sim, 100.0)
    
    # Calculate similarities and group
    go_groups = {}  # {go_id: group_id}
    groups = {}     # {group_id: set of go_ids}
    next_group_id = 1
    
    go_list = list(all_gos_for_comparison)
    for i, go1 in enumerate(go_list):
        for go2 in go_list[i + 1:]:
            similarity = calculate_similarity(go1, go2)
            
            if similarity >= SIMILARITY_THRESHOLD:
                source_id = go1.global_org_id
                target_id = go2.global_org_id
                
                source_group = go_groups.get(source_id)
                target_group = go_groups.get(target_id)
                
                if source_group is None and target_group is None:
                    go_groups[source_id] = next_group_id
                    go_groups[target_id] = next_group_id
                    groups[next_group_id] = {source_id, target_id}
                    next_group_id += 1
                elif source_group is None:
                    go_groups[source_id] = target_group
                    groups[target_group].add(source_id)
                elif target_group is None:
                    go_groups[target_id] = source_group
                    groups[source_group].add(target_id)
                elif source_group != target_group:
                    for go_id in groups[target_group]:
                        go_groups[go_id] = source_group
                        groups[source_group].add(go_id)
                    del groups[target_group]
    
    # Merge groups with same base name (case-insensitive)
    # This prevents duplicate groups like "Save The Children" and "Save the Children"
    name_to_groups = {}  # {normalized_name: [group_ids]}
    
    for group_id, go_ids in groups.items():
        if len(go_ids) < 2:
            continue
        # Get representative name
        sample_go = GlobalOrganization.objects.filter(global_org_id__in=list(go_ids)[:1]).first()
        if sample_go:
            base_name = normalize_name(sample_go.global_org_name)
            # Extract core name (remove country/location)
            core_name = base_name
            for suffix in ['international', 'uk', 'jordan', 'yemen', 'foundation', 'somalia', 'ethiopia', 'pakistan', 'syria', 'lebanon', 'iraq', 'afghanistan', 'sudan']:
                if core_name.endswith(' ' + suffix):
                    core_name = core_name[:-len(' ' + suffix)]
                    break
            
            if core_name not in name_to_groups:
                name_to_groups[core_name] = []
            name_to_groups[core_name].append(group_id)
    
    # Merge groups with same core name
    final_groups = {}
    next_final_group_id = 1
    for core_name, group_ids_list in name_to_groups.items():
        if len(group_ids_list) == 1:
            # Single group
            final_groups[next_final_group_id] = groups[group_ids_list[0]]
        else:
            # Multiple groups with same core name - merge them
            merged_ids = set()
            for gid in group_ids_list:
                merged_ids.update(groups[gid])
            final_groups[next_final_group_id] = merged_ids
        next_final_group_id += 1
    
    # Build duplicate groups
    duplicate_groups = []
    for group_id, go_ids in final_groups.items():
        if len(go_ids) < 2:
            continue
            
        go_list = GlobalOrganization.objects.filter(global_org_id__in=go_ids)
        
        # Calculate max similarity within group
        max_similarity = 0
        go_objs = list(go_list)
        for i, g1 in enumerate(go_objs):
            if g1.global_org_id not in go_ids:
                continue
            for g2 in go_objs[i + 1:]:
                if g2.global_org_id not in go_ids:
                    continue
                sim = calculate_similarity(g1, g2)
                if sim > max_similarity:
                    max_similarity = sim
        
        members = []
        total_instances = 0
        
        for go in go_list:
            usage = go.usage_count or 0
            total_instances += usage
            members.append({
                "global_org_id": go.global_org_id,
                "global_org_name": go.global_org_name,
                "usage_count": usage,
                "name_length": len(go.global_org_name) if go.global_org_name else 0
            })
        
        # Recommend master using knowledge base + usage count + name length
        for member in members:
            rec_info = get_recommendation_score(member["global_org_name"], member["usage_count"])
            member["recommendation_score"] = rec_info['score']
            member["kb_match"] = rec_info['kb_match']
            member["kb_standard_name"] = rec_info.get('standard_name')
        
        # Recommend based on combined score
        recommended = max(members, key=lambda x: x["recommendation_score"])
        
        for member in members:
            member["is_recommended"] = (member["global_org_id"] == recommended["global_org_id"])
        
        # Sort: recommended first, then by usage count
        members.sort(key=lambda x: (not x["is_recommended"], -x["usage_count"]))
        
        # Generate group name from recommended master - normalize for consistency
        group_name = recommended["global_org_name"]
        
        # Title case for consistency
        group_name = ' '.join(word.capitalize() for word in group_name.split())
        
        # Simplify name (remove country/location suffixes)
        for suffix in [' International', ' Uk', ' Jordan', ' Yemen', ' Foundation', ' Somalia', ' Ethiopia', ' Pakistan', ' Syria', ' Lebanon', ' Iraq', ' Afghanistan', ' Sudan']:
            if group_name.endswith(suffix):
                group_name = group_name[:-len(suffix)]
                break
        
        duplicate_groups.append({
            "group_id": group_id,
            "group_name": group_name + " Group",
            "max_similarity": max_similarity,
            "total_members": len(members),
            "total_instances": total_instances,
            "recommended_master": {
                "global_org_id": recommended["global_org_id"],
                "global_org_name": recommended["global_org_name"],
                "usage_count": recommended["usage_count"]
            },
            "members": members
        })
    
    # Sort groups by similarity (highest first)
    duplicate_groups.sort(key=lambda x: -x["max_similarity"])
    
    # Get unique organizations (not in any group)
    grouped_go_ids = set()
    for group in duplicate_groups:
        grouped_go_ids.update(m["global_org_id"] for m in group["members"])
    
    unique_organizations = []
    all_gos = GlobalOrganization.objects.all()
    
    for go in all_gos:
        if go.global_org_id not in grouped_go_ids:
            unique_organizations.append({
                "global_org_id": go.global_org_id,
                "global_org_name": go.global_org_name,
                "usage_count": go.usage_count or 0
            })
    
    # Sort unique by usage count
    unique_organizations.sort(key=lambda x: -x["usage_count"])
    
    return Response({
        "duplicate_groups": duplicate_groups,
        "unique_organizations": unique_organizations,
        "summary": {
            "total_organizations": len(all_gos),
            "duplicate_groups_count": len(duplicate_groups),
            "unique_count": len(unique_organizations)
        }
    })


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
    Returns mapping data for a specific Global Organization (same structure as Mapping Dashboard)
    {
      "go_info": {"global_org_id": 1, "global_org_name": "xxx", "global_acronym": "XXX"},
      "mappings": [...]
    }
    """
    go = get_object_or_404(GlobalOrganization, global_org_id=go_id)

    mappings_qs = OrgMapping.objects.filter(global_org_id=go_id).order_by("id")
    
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

    return Response(
        {
            "go_info": {
                "global_org_id": go.global_org_id,
                "global_org_name": go.global_org_name,
                "global_acronym": go.global_acronym,
            },
            "mappings": mappings,
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
        
        # Include ALL GOs, even those without mappings
        result.append({
            "global_org_id": go.global_org_id,
            "global_org_name": go.global_org_name,
            "global_acronym": go.global_acronym,
            "mappings": mappings,  # Will be empty list if no mappings
        })
    
    return Response(result)




