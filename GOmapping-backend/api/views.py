from django.db.models import OuterRef, Subquery, DecimalField, CharField
from django.shortcuts import get_object_or_404
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
import os
import sys
import requests
import json


from orgnizations.models import GlobalOrganization, GoSimilarity, OrgMapping, DataSyncLog, MergeDecision
from .serializers import GlobalOrganizationSerializer
from .sync_service import SmartDataSyncService

@api_view(['GET'])
def go_list(request):
    gos = GlobalOrganization.objects.all().order_by("global_org_id")
    serializer = GlobalOrganizationSerializer(gos, many=True)
    return Response(serializer.data)


@api_view(["GET"])
def go_summary(request):
    from django.core.cache import cache
    from django.db.models import Count
    from organization_knowledge_base import get_recommendation_score
    import subprocess
    import os
    
    # Check if force refresh is requested
    force_refresh = request.GET.get('refresh', '').lower() == 'true'

    # Similarity threshold — defaults to 70, can be overridden via ?threshold=XX
    try:
        threshold = float(request.GET.get('threshold', 70))
        threshold = max(0.0, min(100.0, threshold))
    except (ValueError, TypeError):
        threshold = 70.0
    
    # Try to get cached result (only if NOT force refresh)
    cache_key = 'go_summary_data'
    if not force_refresh:
        cached_data = cache.get(cache_key)
        if cached_data:
            return Response(cached_data)
    
    # Only update usage_count and recalculate similarities when force_refresh=true
    if force_refresh:
        # Also invalidate mapping dashboard cache
        cache.delete('mapping_dashboard_data')
        
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
        
        # Run similarity calculation and wait for completion
        try:
            # Get the directory of manage.py
            manage_py_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            
            # Run the command synchronously so response only returns after calculation is done
            env = os.environ.copy()
            env['PYTHONUTF8'] = '1'
            # the threshold here will influence directly
            completed = subprocess.run(
                [sys.executable, 'manage.py', 'calculate_similarity', '--clear', '--threshold', str(threshold)],
                cwd=manage_py_dir,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                check=False,
                env=env,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
            )

            if completed.returncode != 0:
                print(f"Warning: Similarity calculation failed with code {completed.returncode}")
                if completed.stderr:
                    print(f"stderr: {completed.stderr[-2000:]}")
        except Exception as e:
            # Log the error but don't fail the request
            print(f"Warning: Could not start similarity calculation: {e}")
    
    # Build grouped data structure - Read from pre-calculated go_similarity table
    # Fetch all similarities from database
    all_similarities = GoSimilarity.objects.select_related(
        'source_global_org', 'target_global_org'
    ).all()
    
    # Build similarity graph using Union-Find
    go_groups = {}  # {go_id: group_id}
    groups = {}     # {group_id: set of go_ids}
    next_group_id = 1
    
    for similarity in all_similarities:
        source_id = similarity.source_global_org_id
        target_id = similarity.target_global_org_id
        
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
            # Merge groups
            for go_id in groups[target_group]:
                go_groups[go_id] = source_group
                groups[source_group].add(go_id)
            del groups[target_group]
    
    # Build duplicate groups
    duplicate_groups = []
    for group_id, go_ids in groups.items():
        if len(go_ids) < 2:
            continue
        
        go_list = GlobalOrganization.objects.filter(global_org_id__in=go_ids)
        
        # Get max similarity within group from database
        max_similarity = 0
        for go_id in go_ids:
            similarities_in_group = GoSimilarity.objects.filter(
                source_global_org_id=go_id,
                target_global_org_id__in=go_ids
            ).values_list('similarity_percent', flat=True)
            if similarities_in_group:
                group_max = max(float(s) for s in similarities_in_group if s is not None)
                if group_max > max_similarity:
                    max_similarity = group_max
        
        members = []
        total_instances = 0
        
        for go in go_list:
            usage = go.usage_count or 0
            total_instances += usage
            
            # Get instance organizations for this GO
            instance_orgs = OrgMapping.objects.filter(
                global_org_id=go.global_org_id
            ).values(
                'instance_org_id',
                'instance_org_name',
                'instance_org_acronym',
                'instance_org_type',
                'fund_name',
                'match_percent'
            )[:20]  # Limit to 20 for performance
            
            members.append({
                "global_org_id": go.global_org_id,
                "global_org_name": go.global_org_name,
                "global_org_acronym": go.global_acronym or "",
                "usage_count": usage,
                "name_length": len(go.global_org_name) if go.global_org_name else 0,
                "instance_organizations": list(instance_orgs)
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
                "global_org_acronym": recommended.get("global_org_acronym", ""),
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
            # Get instance organizations for this unique GO
            instance_orgs = OrgMapping.objects.filter(
                global_org_id=go.global_org_id
            ).values(
                'instance_org_id',
                'instance_org_name',
                'instance_org_acronym',
                'instance_org_type',
                'fund_name',
                'match_percent'
            )[:20]  # Limit to 20 for performance
            
            unique_organizations.append({
                "global_org_id": go.global_org_id,
                "global_org_name": go.global_org_name,
                "global_org_acronym": go.global_acronym or "",
                "usage_count": go.usage_count or 0,
                "instance_organizations": list(instance_orgs)
            })
    
    # Sort unique by usage count
    unique_organizations.sort(key=lambda x: -x["usage_count"])
    
    response_data = {
        "duplicate_groups": duplicate_groups,
        "unique_organizations": unique_organizations,
        "summary": {
            "total_organizations": len(all_gos),
            "duplicate_groups_count": len(duplicate_groups),
            "unique_count": len(unique_organizations)
        }
    }
    
    # Cache the result for 1 hour (3600 seconds)
    # Only refresh when user explicitly clicks "Refresh Data" button
    cache.set(cache_key, response_data, 3600)
    
    return Response(response_data)


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
            "instance_org_type": mapping.instance_org_type,
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
    返回 Scenario 2 的完整数据结构（优化版：2 次查询代替 N+1）
    """
    from django.core.cache import cache
    from collections import defaultdict
    
    cache_key = 'mapping_dashboard_data'
    cached = cache.get(cache_key)
    if cached:
        return Response(cached)
    
    # Query 1: all mappings in one go, grouped by global_org_id
    all_mappings = OrgMapping.objects.all().order_by("global_org_id", "id").values(
        'global_org_id',
        'instance_org_id',
        'instance_org_name',
        'instance_org_acronym',
        'instance_org_type',
        'parent_instance_org_id',
        'fund_id',
        'fund_name',
        'match_percent',
        'risk_level',
        'status',
    )
    
    mappings_by_go = defaultdict(list)
    for m in all_mappings:
        go_id = m.pop('global_org_id')
        if m['match_percent'] is not None:
            m['match_percent'] = float(m['match_percent'])
        mappings_by_go[go_id].append(m)
    
    # Query 2: all global orgs
    global_orgs = GlobalOrganization.objects.all().order_by("global_org_id").values(
        'global_org_id', 'global_org_name', 'global_acronym'
    )
    
    result = []
    for go in global_orgs:
        result.append({
            "global_org_id": go['global_org_id'],
            "global_org_name": go['global_org_name'],
            "global_acronym": go['global_acronym'],
            "mappings": mappings_by_go.get(go['global_org_id'], []),
        })
    
    cache.set(cache_key, result, 3600)
    return Response(result)


@api_view(["POST"])
def ai_recommendation(request):
    """
    AI-powered recommendation for which Global Organization to keep in a duplicate group.
    
    Request body:
    {
        "group_id": 1,
        "group_name": "Save the Children Group",
        "members": [
            {
                "global_org_id": 123,
                "global_org_name": "Save the Children International",
                "usage_count": 50,
                "is_recommended": true,
                "kb_match": true
            },
            ...
        ]
    }
    
    Response:
    {
        "recommended_id": 123,
        "recommended_name": "Save the Children International",
        "reasoning": ["Higher usage count", "Matches knowledge base", ...],
        "analysis": "Detailed explanation..."
    }
    """
    try:
        # Get API key from environment variable
        # Prefer ZHIPUAI_API_KEY; allow fallback for existing setups
        api_key = "c4d74482a5e64890a44fd5cd2e6af2c3.LouAL40edi1tZss8"
        # Get request data
        group_id = request.data.get('group_id')
        group_name = request.data.get('group_name')
        members = request.data.get('members', [])
        
        if not members:
            return Response(
                {"error": "No members provided in the group"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Build prompt for DeepSeek
        members_info = "\n".join([
            f"- ID: {m['global_org_id']}, Name: {m['global_org_name']}, "
            f"Usage: {m['usage_count']} instances, "
            f"KB Match: {'Yes' if m.get('kb_match') else 'No'}, "
            f"Current System Recommendation: {'KEEP' if m.get('is_recommended') else 'MERGE'}"
            for m in members
        ])
        
        prompt = f"""You are a data quality expert analyzing duplicate Global Organizations in a humanitarian aid management system.

Group: {group_name}
Members in this duplicate group:
{members_info}

Your task is to recommend which ONE Global Organization should be KEPT as the master record, while others should be merged into it.

Consider these factors (in order of importance):
1. **Standardization**: Which name follows the most standard, official format?
2. **Usage frequency**: Higher usage indicates more established/trusted
3. **Knowledge base match**: Organizations in our knowledge base are verified and standardized
4. **Name completeness**: Full official names are better than abbreviated versions or regional variants
5. **Geographic scope**: International/global variants are preferred over country-specific ones

Please respond in the following JSON format:
{{
    "recommended_id": <ID of the organization to keep>,
    "recommended_name": "<Name of the organization to keep>",
    "reasoning": [
        "<Concise reason 1>",
        "<Concise reason 2>",
        "<Concise reason 3>"
    ],
    "analysis": "<2-3 sentence detailed explanation of your recommendation>"
}}

Be decisive and provide a clear recommendation.
Return JSON only. Do not include markdown code fences."""

        # Call ZhipuAI via official Python SDK
        try:
            from zhipuai import ZhipuAI
        except Exception as e:
            return Response(
                {
                    "error": (
                        "ZhipuAI SDK not installed. Install it in backend env: "
                        "`pip install zhipuai`. "
                        f"Import error: {str(e)}"
                    )
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

        client = ZhipuAI(api_key=api_key)

        import time

        response_text = ""
        max_attempts = 3
        last_empty_reason = "unknown"

        for attempt in range(1, max_attempts + 1):
            completion = client.chat.completions.create(
                model="glm-4.7-flash",
                messages=[
                    {"role": "system", "content": "You are a data quality expert. Always respond with valid JSON only, no extra text."},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.3,
                max_tokens=2048,
            )

            choice = completion.choices[0] if getattr(completion, "choices", None) else None
            message = getattr(choice, "message", None)
            finish_reason = getattr(choice, "finish_reason", None)
            content = getattr(message, "content", None) if message else None

            if isinstance(content, list):
                parts = []
                for item in content:
                    if isinstance(item, dict):
                        parts.append(item.get("text", ""))
                    else:
                        text_val = getattr(item, "text", None)
                        if text_val:
                            parts.append(text_val)
                response_text = "".join(parts).strip()
            elif content is None:
                response_text = ""
            else:
                response_text = str(content).strip()

            print(f"[DEBUG] AI attempt={attempt}, finish_reason={finish_reason}, response_length={len(response_text)}")
            print(f"[DEBUG] AI raw response preview: {response_text[:500]}")

            if finish_reason == "length":
                print(f"[DEBUG] Response truncated (finish_reason=length), retrying...")
                last_empty_reason = f"truncated (finish_reason=length, got {len(response_text)} chars)"
                response_text = ""
                if attempt < max_attempts:
                    time.sleep(1.5 * attempt)
                continue

            if response_text:
                break

            last_empty_reason = f"empty_content (finish_reason={finish_reason})"
            if attempt < max_attempts:
                time.sleep(1.2 * attempt)

        if not response_text:
            return Response(
                {
                    "error": "AI returned empty response after retries.",
                    "hint": "Please try again in a few seconds. Upstream model may be temporarily unstable.",
                    "detail": last_empty_reason,
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        
        # Try to extract/parse JSON from response (with tolerant fallback)
        import re
        import ast

        candidates = []

        # 1) Code fence JSON block
        fenced_match = re.search(r'```(?:json)?\s*(.*?)\s*```', response_text, re.DOTALL | re.IGNORECASE)
        if fenced_match:
            candidates.append(fenced_match.group(1).strip())

        # 2) Largest JSON-like object between first '{' and last '}'
        first_brace = response_text.find('{')
        last_brace = response_text.rfind('}')
        if first_brace != -1 and last_brace != -1 and first_brace < last_brace:
            candidates.append(response_text[first_brace:last_brace + 1].strip())

        # 3) Full response as a last resort
        candidates.append(response_text.strip())

        # Deduplicate while preserving order
        seen = set()
        unique_candidates = []
        for item in candidates:
            if item and item not in seen:
                unique_candidates.append(item)
                seen.add(item)

        ai_result = None
        parse_error = None
        chosen_payload = None

        for payload in unique_candidates:
            # First try strict JSON
            try:
                parsed = json.loads(payload)
                if isinstance(parsed, dict):
                    ai_result = parsed
                    chosen_payload = payload
                    break
            except Exception as e:
                parse_error = e

            # Then try Python-literal style dict (single quotes, etc.)
            try:
                parsed = ast.literal_eval(payload)
                if isinstance(parsed, dict):
                    ai_result = parsed
                    chosen_payload = payload
                    break
            except Exception as e:
                parse_error = e

        if not ai_result:
            return Response(
                {
                    "error": f"Failed to parse AI response as JSON: {str(parse_error)}",
                    "raw_response": response_text[:800],
                    "hint": "Model returned non-standard format. Please retry.",
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

        print(f"[DEBUG] AI parsed payload length: {len(chosen_payload or '')}")
        
        reasoning = ai_result.get("reasoning", [])
        if isinstance(reasoning, str):
            reasoning = [reasoning]
        elif not isinstance(reasoning, list):
            reasoning = [str(reasoning)]

        return Response({
            "recommended_id": ai_result.get("recommended_id"),
            "recommended_name": ai_result.get("recommended_name"),
            "reasoning": reasoning,
            "analysis": ai_result.get("analysis", "")
        })
    except Exception as e:
        # Log full error for debugging
        import traceback
        print(f"[ERROR] ZhipuAI API error: {str(e)}")
        print(f"[ERROR] Traceback: {traceback.format_exc()}")
        return Response(
            {"error": f"ZhipuAI API error: {str(e)}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


# ============================================
# 数据同步 API
# ============================================

@api_view(['GET'])
def sync_status(request):
    """
    获取数据同步状态
    GET /api/sync-status/
    GET /api/sync-status/?sync_type=org_mapping
    """
    sync_type = request.GET.get('sync_type', None)
    
    service = SmartDataSyncService()
    status_info = service.get_sync_status(sync_type)
    
    return Response(status_info)


@api_view(['GET'])
def sync_history(request):
    """
    获取同步历史记录
    GET /api/sync-history/
    GET /api/sync-history/?limit=10&sync_type=org_mapping
    """
    limit = int(request.GET.get('limit', 20))
    sync_type = request.GET.get('sync_type', None)
    
    service = SmartDataSyncService()
    history = service.get_sync_history(limit=limit, sync_type=sync_type)
    
    return Response({
        'history': history,
        'total': len(history)
    })


@api_view(['POST'])
def trigger_sync(request):
    """
    手动触发数据同步
    
    POST /api/trigger-sync/
    
    Request body:
    {
        "sync_type": "full",  # "full" / "global_org" / "org_mapping"
        "force": false  # 是否强制同步（忽略时间和指纹检查）
    }
    
    Response:
    {
        "success": true,
        "message": "Sync completed successfully",
        "results": {...}
    }
    """
    try:
        sync_type = request.data.get('sync_type', 'full')
        force = request.data.get('force', False)
        
        service = SmartDataSyncService()
        
        if sync_type == 'full':
            results = service.sync_all(triggered_by='manual', force=force)
        elif sync_type == 'global_org':
            results = service.sync_global_orgs(triggered_by='manual', force=force)
        elif sync_type == 'org_mapping':
            results = service.sync_org_mappings(triggered_by='manual', force=force)
        else:
            return Response(
                {"error": "Invalid sync_type. Must be 'full', 'global_org', or 'org_mapping'"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        sync_errors = {}
        for sync_key in ['global_org', 'org_mapping']:
            sync_result = results.get(sync_key)
            if sync_result and sync_result.get('error'):
                sync_errors[sync_key] = sync_result['error']

        if sync_errors:
            return Response({
                "success": False,
                "message": "Sync completed with errors",
                "errors": sync_errors,
                "results": results
            }, status=status.HTTP_200_OK)

        return Response({
            "success": True,
            "message": results.get('message', 'Sync completed'),
            "results": results
        })
        
    except Exception as e:
        import traceback
        print(f"[ERROR] Sync failed: {str(e)}")
        print(f"[ERROR] Traceback: {traceback.format_exc()}")
        
        return Response(
            {
                "success": False,
                "error": str(e),
                "message": "Sync failed. Please check server logs."
            },
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
def check_for_updates(request):
    """
    快速检查是否有数据更新（不执行同步）
    
    GET /api/check-for-updates/
    
    Response:
    {
        "has_updates": true,
        "reason": "should_sync",
        "last_sync_time": "2026-01-30T10:00:00Z",
        "message": "Updates available"
    }
    """
    sync_type = request.GET.get('sync_type', 'org_mapping')
    
    service = SmartDataSyncService()
    should_sync, reason, last_sync = service.should_sync(sync_type, force=False)
    
    return Response({
        "has_updates": should_sync,
        "reason": reason,
        "last_sync_time": last_sync.completed_at if last_sync else None,
        "last_sync_status": last_sync.status if last_sync else None,
        "message": "Updates available" if should_sync else "No updates needed"
    })


# ==================== Merge Decision APIs ====================

@api_view(['POST'])
def create_merge_decision(request):
    """
    创建映射变更决策记录
    
    POST /api/merge-decisions/create/
    Body: {
        "instance_org_id": 123,
        "instance_org_name": "Organization A",
        "original_global_org_id": 456,
        "original_global_org_name": "Original Global Org",
        "target_global_org_id": 789,
        "target_global_org_name": "Target Global Org",
        "decision_type": "remap",  // optional: 'remap', 'merge', 'review_later'
        "confidence": "high",  // optional: 'high', 'medium', 'low'
        "similarity_score": 0.95,  // optional
        "notes": "Reason for remapping",  // optional
        "decided_by": "admin"  // optional
    }
    """
    try:
        data = request.data
        
        # 验证必需字段
        required_fields = [
            'instance_org_id', 'instance_org_name',
            'original_global_org_id', 'original_global_org_name',
            'target_global_org_id', 'target_global_org_name'
        ]
        missing_fields = [field for field in required_fields if field not in data]
        if missing_fields:
            return Response({
                'error': f'Missing required fields: {", ".join(missing_fields)}'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # 冲突检查：同一个 Instance Org 只能有一个 pending 决策，避免冲突
        existing_any_pending = MergeDecision.objects.filter(
            instance_org_id=data['instance_org_id'],
            execution_status='pending'
        ).first()

        if existing_any_pending:
            if existing_any_pending.target_global_org_id == data['target_global_org_id']:
                return Response({
                    'error': 'A pending decision already exists for this mapping change',
                    'existing_decision_id': existing_any_pending.decision_id
                }, status=status.HTTP_409_CONFLICT)

            return Response({
                'error': (
                    'Conflict: this instance organization already has another pending '
                    'decision to a different target global organization'
                ),
                'existing_decision_id': existing_any_pending.decision_id,
                'existing_target_global_org_id': existing_any_pending.target_global_org_id,
                'existing_target_global_org_name': existing_any_pending.target_global_org_name,
            }, status=status.HTTP_409_CONFLICT)
        
        # 创建决策记录
        decision = MergeDecision.objects.create(
            instance_org_id=data['instance_org_id'],
            instance_org_name=data['instance_org_name'],
            original_global_org_id=data['original_global_org_id'],
            original_global_org_name=data['original_global_org_name'],
            target_global_org_id=data['target_global_org_id'],
            target_global_org_name=data['target_global_org_name'],
            decision_type=data.get('decision_type', 'remap'),
            confidence=data.get('confidence'),
            similarity_score=data.get('similarity_score'),
            notes=data.get('notes', ''),
            decided_by=data.get('decided_by', 'admin')
        )
        
        return Response({
            'success': True,
            'decision_id': decision.decision_id,
            'message': 'Mapping change decision recorded successfully',
            'decision': {
                'decision_id': decision.decision_id,
                'instance_org_id': decision.instance_org_id,
                'instance_org_name': decision.instance_org_name,
                'original_global_org_id': decision.original_global_org_id,
                'original_global_org_name': decision.original_global_org_name,
                'target_global_org_id': decision.target_global_org_id,
                'target_global_org_name': decision.target_global_org_name,
                'decision_type': decision.decision_type,
                'confidence': decision.confidence,
                'similarity_score': str(decision.similarity_score) if decision.similarity_score else None,
                'notes': decision.notes,
                'decided_by': decision.decided_by,
                'decided_at': decision.decided_at,
                'execution_status': decision.execution_status
            }
        }, status=status.HTTP_201_CREATED)
        
    except Exception as e:
        return Response({
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
def list_merge_decisions(request):
    """
    获取映射变更决策列表
    
    GET /api/merge-decisions/
    Query params:
        - status: filter by execution_status (pending/executed/cancelled)
        - instance_org_id: filter by instance organization
        - original_global_org_id: filter by original global organization
        - target_global_org_id: filter by target global organization
    """
    try:
        decisions = MergeDecision.objects.all()
        
        # 过滤
        exec_status = request.GET.get('status')
        if exec_status:
            decisions = decisions.filter(execution_status=exec_status)
        
        instance_org_id = request.GET.get('instance_org_id')
        if instance_org_id:
            decisions = decisions.filter(instance_org_id=instance_org_id)
        
        original_global_org_id = request.GET.get('original_global_org_id')
        if original_global_org_id:
            decisions = decisions.filter(original_global_org_id=original_global_org_id)
        
        target_global_org_id = request.GET.get('target_global_org_id')
        if target_global_org_id:
            decisions = decisions.filter(target_global_org_id=target_global_org_id)
        
        # 序列化
        decisions_data = [{
            'decision_id': d.decision_id,
            'instance_org_id': d.instance_org_id,
            'instance_org_name': d.instance_org_name,
            'original_global_org_id': d.original_global_org_id,
            'original_global_org_name': d.original_global_org_name,
            'target_global_org_id': d.target_global_org_id,
            'target_global_org_name': d.target_global_org_name,
            'decision_type': d.decision_type,
            'confidence': d.confidence,
            'similarity_score': str(d.similarity_score) if d.similarity_score else None,
            'notes': d.notes,
            'decided_by': d.decided_by,
            'decided_at': d.decided_at,
            'execution_status': d.execution_status,
            'executed_at': d.executed_at,
            'executed_by': d.executed_by,
            'execution_notes': d.execution_notes
        } for d in decisions]
        
        return Response({
            'count': len(decisions_data),
            'decisions': decisions_data
        })
        
    except Exception as e:
        return Response({
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['DELETE'])
def delete_merge_decision(request, decision_id):
    """
    删除合并决策记录
    
    DELETE /api/merge-decisions/<decision_id>/
    """
    try:
        decision = get_object_or_404(MergeDecision, decision_id=decision_id)
        
        # 只允许删除 pending 状态的决策
        if decision.execution_status != 'pending':
            return Response({
                'error': f'Cannot delete decision with status: {decision.execution_status}'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        decision_info = {
            'decision_id': decision.decision_id,
            'instance_org_name': decision.instance_org_name,
            'target_global_org_name': decision.target_global_org_name
        }
        
        decision.delete()
        
        return Response({
            'success': True,
            'message': 'Decision deleted successfully',
            'deleted_decision': decision_info
        })
        
    except Exception as e:
        return Response({
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['PATCH'])
def update_merge_decision_status(request, decision_id):
    """
    更新决策执行状态
    
    PATCH /api/merge-decisions/<decision_id>/status/
    Body: {
        "execution_status": "executed",  // 'executed', 'cancelled', 'pending'
        "executed_by": "admin",  // optional
        "execution_notes": "Manually executed in source system"  // optional
    }
    """
    try:
        decision = get_object_or_404(MergeDecision, decision_id=decision_id)
        
        new_status = request.data.get('execution_status')
        if not new_status:
            return Response({
                'error': 'execution_status is required'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        if new_status not in ['executed', 'cancelled', 'pending']:
            return Response({
                'error': 'Invalid execution_status'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        from django.utils import timezone
        decision.execution_status = new_status
        
        mapping_updated = False
        if new_status == 'executed':
            decision.executed_at = timezone.now()
            decision.executed_by = request.data.get('executed_by', 'admin')
            decision.execution_notes = request.data.get('execution_notes', '')
            
            # Actually remap the instance org in org_mapping table
            updated_count = OrgMapping.objects.filter(
                instance_org_id=decision.instance_org_id,
                global_org_id=decision.original_global_org_id
            ).update(
                global_org_id=decision.target_global_org_id,
                updated_at=timezone.now()
            )
            mapping_updated = updated_count > 0
            if mapping_updated:
                from django.core.cache import cache
                cache.delete('mapping_dashboard_data')
            
        elif new_status == 'cancelled':
            decision.execution_notes = request.data.get('execution_notes', 'Cancelled by user')
        
        decision.save()
        
        return Response({
            'success': True,
            'message': f'Decision status updated to {new_status}',
            'mapping_updated': mapping_updated,
            'decision': {
                'decision_id': decision.decision_id,
                'execution_status': decision.execution_status,
                'executed_at': decision.executed_at,
                'executed_by': decision.executed_by,
                'execution_notes': decision.execution_notes
            }
        })
        
    except Exception as e:
        return Response({
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


