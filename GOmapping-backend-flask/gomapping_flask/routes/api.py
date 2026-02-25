import ast
import json
import re
from datetime import datetime

from flask import Blueprint, current_app, jsonify, request
from sqlalchemy import and_

from ..cache import cache
from ..extensions import db
from ..models import GlobalOrganization, GoSimilarity, MergeDecision, OrgMapping
from ..services.similarity import (
    build_go_summary_response,
    recalculate_similarity_table,
    refresh_usage_counts,
)
from ..services.sync_data import get_sync_service


api_bp = Blueprint("api", __name__)


def _json_error(message, code=400, **extra):
    payload = {"error": message}
    payload.update(extra)
    return jsonify(payload), code


@api_bp.get("/go-summary/")
def go_summary():
    force_refresh = request.args.get("refresh", "").lower() == "true"
    try:
        threshold = float(request.args.get("threshold", 70))
        threshold = max(0.0, min(100.0, threshold))
    except (TypeError, ValueError):
        threshold = 70.0

    cache_key = "go_summary_data"
    if not force_refresh:
        cached = cache.get(cache_key)
        if cached:
            return jsonify(cached)

    if force_refresh:
        refresh_usage_counts()
        recalculate_similarity_table(threshold=threshold)
        cache.delete("mapping_dashboard_data")

    data = build_go_summary_response()
    cache.set(cache_key, data, current_app.config["CACHE_TTL_SECONDS"])
    return jsonify(data)


@api_bp.get("/go-detail/<int:go_id>/")
def go_detail(go_id):
    go = GlobalOrganization.query.filter_by(global_org_id=go_id).first()
    if not go:
        return _json_error("Global organization not found", 404)

    similarities = (
        GoSimilarity.query.filter_by(source_global_org_id=go_id)
        .order_by(GoSimilarity.similarity_percent.desc(), GoSimilarity.target_global_org_id.asc())
        .all()
    )
    target_ids = [s.target_global_org_id for s in similarities]
    targets = {x.global_org_id: x for x in GlobalOrganization.query.filter(GlobalOrganization.global_org_id.in_(target_ids)).all()}

    similar_gos = []
    for s in similarities:
        tgt = targets.get(s.target_global_org_id)
        if not tgt:
            continue
        similar_gos.append(
            {
                "go_id": tgt.global_org_id,
                "go_name": tgt.global_org_name,
                "similarity": float(s.similarity_percent) if s.similarity_percent is not None else None,
                "mapping_count": tgt.usage_count,
            }
        )

    return jsonify({"go_info": {"id": go.global_org_id, "name": go.global_org_name}, "similar_gos": similar_gos})


@api_bp.get("/org-mappings/<int:go_id>/")
def org_mappings(go_id):
    go = GlobalOrganization.query.filter_by(global_org_id=go_id).first()
    if not go:
        return _json_error("Global organization not found", 404)
    mappings = OrgMapping.query.filter_by(global_org_id=go_id).order_by(OrgMapping.id.asc()).all()
    return jsonify(
        {
            "go_info": {
                "global_org_id": go.global_org_id,
                "global_org_name": go.global_org_name,
                "global_acronym": go.global_acronym,
            },
            "mappings": [
                {
                    "instance_org_id": m.instance_org_id,
                    "instance_org_name": m.instance_org_name,
                    "instance_org_acronym": m.instance_org_acronym,
                    "instance_org_type": m.instance_org_type,
                    "parent_instance_org_id": m.parent_instance_org_id,
                    "fund_id": m.fund_id,
                    "fund_name": m.fund_name,
                    "match_percent": float(m.match_percent) if m.match_percent is not None else None,
                    "risk_level": m.risk_level,
                    "status": m.status,
                }
                for m in mappings
            ],
        }
    )


@api_bp.get("/mapping-dashboard/")
def mapping_dashboard():
    cache_key = "mapping_dashboard_data"
    cached = cache.get(cache_key)
    if cached:
        return jsonify(cached)

    all_mappings = OrgMapping.query.order_by(OrgMapping.global_org_id.asc(), OrgMapping.id.asc()).all()
    grouped = {}
    for m in all_mappings:
        grouped.setdefault(m.global_org_id, []).append(
            {
                "instance_org_id": m.instance_org_id,
                "instance_org_name": m.instance_org_name,
                "instance_org_acronym": m.instance_org_acronym,
                "instance_org_type": m.instance_org_type,
                "parent_instance_org_id": m.parent_instance_org_id,
                "fund_id": m.fund_id,
                "fund_name": m.fund_name,
                "match_percent": float(m.match_percent) if m.match_percent is not None else None,
                "risk_level": m.risk_level,
                "status": m.status,
            }
        )

    result = []
    for go in GlobalOrganization.query.order_by(GlobalOrganization.global_org_id.asc()).all():
        result.append(
            {
                "global_org_id": go.global_org_id,
                "global_org_name": go.global_org_name,
                "global_acronym": go.global_acronym,
                "mappings": grouped.get(go.global_org_id, []),
            }
        )

    cache.set(cache_key, result, current_app.config["CACHE_TTL_SECONDS"])
    return jsonify(result)


@api_bp.post("/ai-recommendation/")
def ai_recommendation():
    payload = request.get_json(silent=True) or {}
    members = payload.get("members", [])
    if not members:
        return _json_error("No members provided in the group", 400)

    members_info = "\n".join(
        [
            f"- ID: {m['global_org_id']}, Name: {m['global_org_name']}, "
            f"Usage: {m['usage_count']} instances, "
            f"KB Match: {'Yes' if m.get('kb_match') else 'No'}, "
            f"Current System Recommendation: {'KEEP' if m.get('is_recommended') else 'MERGE'}"
            for m in members
        ]
    )
    prompt = f"""You are a data quality expert analyzing duplicate Global Organizations in a humanitarian aid management system.
Group: {payload.get('group_name', 'N/A')}
Members in this duplicate group:
{members_info}
Recommend ONE organization to keep as the master record.
Return strict JSON only:
{{
  "recommended_id": <int>,
  "recommended_name": "<string>",
  "reasoning": ["<reason1>", "<reason2>", "<reason3>"],
  "analysis": "<short explanation>"
}}"""
    try:
        from zhipuai import ZhipuAI

        client = ZhipuAI(api_key=current_app.config["ZHIPUAI_API_KEY"])
        completion = client.chat.completions.create(
            model="glm-4.7-flash",
            messages=[
                {"role": "system", "content": "Respond with valid JSON only."},
                {"role": "user", "content": prompt},
            ],
            temperature=0.3,
            max_tokens=1024,
        )

        content = completion.choices[0].message.content if completion.choices else ""
        response_text = content if isinstance(content, str) else json.dumps(content)

        candidates = []
        fenced = re.search(r"```(?:json)?\s*(.*?)\s*```", response_text, flags=re.DOTALL | re.IGNORECASE)
        if fenced:
            candidates.append(fenced.group(1).strip())
        first = response_text.find("{")
        last = response_text.rfind("}")
        if first != -1 and last != -1 and first < last:
            candidates.append(response_text[first : last + 1].strip())
        candidates.append(response_text.strip())

        parsed = None
        parse_error = None
        for item in candidates:
            try:
                parsed = json.loads(item)
                if isinstance(parsed, dict):
                    break
            except Exception as exc:
                parse_error = exc
            try:
                parsed = ast.literal_eval(item)
                if isinstance(parsed, dict):
                    break
            except Exception as exc:
                parse_error = exc

        if not isinstance(parsed, dict):
            return _json_error("Failed to parse AI response", 500, detail=str(parse_error), raw_response=response_text[:800])

        reasoning = parsed.get("reasoning", [])
        if isinstance(reasoning, str):
            reasoning = [reasoning]
        elif not isinstance(reasoning, list):
            reasoning = [str(reasoning)]

        return jsonify(
            {
                "recommended_id": parsed.get("recommended_id"),
                "recommended_name": parsed.get("recommended_name"),
                "reasoning": reasoning,
                "analysis": parsed.get("analysis", ""),
            }
        )
    except Exception as exc:
        return _json_error(f"ZhipuAI API error: {str(exc)}", 500)


@api_bp.get("/sync-status/")
def sync_status():
    service = get_sync_service()
    return jsonify(service.get_sync_status(request.args.get("sync_type")))


@api_bp.get("/sync-history/")
def sync_history():
    service = get_sync_service()
    try:
        limit = int(request.args.get("limit", 20))
    except ValueError:
        limit = 20
    data = service.get_sync_history(limit=limit, sync_type=request.args.get("sync_type"))
    return jsonify({"history": data, "total": len(data)})


@api_bp.post("/trigger-sync/")
def trigger_sync():
    service = get_sync_service()
    payload = request.get_json(silent=True) or {}
    sync_type = payload.get("sync_type", "full")
    force = bool(payload.get("force", False))
    try:
        if sync_type == "full":
            results = service.sync_all(triggered_by="manual", force=force)
        elif sync_type == "global_org":
            results = service.sync_global_orgs(triggered_by="manual", force=force)
        elif sync_type == "org_mapping":
            results = service.sync_org_mappings(triggered_by="manual", force=force)
        else:
            return _json_error("Invalid sync_type. Must be 'full', 'global_org', or 'org_mapping'", 400)

        errors = {}
        if isinstance(results, dict):
            for key in ["global_org", "org_mapping"]:
                part = results.get(key)
                if isinstance(part, dict) and part.get("error"):
                    errors[key] = part["error"]
        if errors:
            return jsonify({"success": False, "message": "Sync completed with errors", "errors": errors, "results": results})
        return jsonify({"success": True, "message": results.get("message", "Sync completed"), "results": results})
    except Exception as exc:
        return jsonify({"success": False, "error": str(exc), "message": "Sync failed. Please check server logs."}), 500


@api_bp.get("/check-for-updates/")
def check_for_updates():
    service = get_sync_service()
    sync_type = request.args.get("sync_type", "org_mapping")
    should_sync, reason, last_sync = service.should_sync(sync_type, force=False)
    return jsonify(
        {
            "has_updates": should_sync,
            "reason": reason,
            "last_sync_time": last_sync.completed_at.isoformat() if last_sync and last_sync.completed_at else None,
            "last_sync_status": last_sync.status if last_sync else None,
            "message": "Updates available" if should_sync else "No updates needed",
        }
    )


@api_bp.post("/merge-decisions/create/")
def create_merge_decision():
    data = request.get_json(silent=True) or {}
    required = [
        "instance_org_id",
        "instance_org_name",
        "original_global_org_id",
        "original_global_org_name",
        "target_global_org_id",
        "target_global_org_name",
    ]
    missing = [x for x in required if x not in data]
    if missing:
        return _json_error(f"Missing required fields: {', '.join(missing)}", 400)

    existing_pending = MergeDecision.query.filter_by(instance_org_id=data["instance_org_id"], execution_status="pending").first()
    if existing_pending:
        if existing_pending.target_global_org_id == data["target_global_org_id"]:
            return jsonify(
                {
                    "error": "A pending decision already exists for this mapping change",
                    "existing_decision_id": existing_pending.decision_id,
                }
            ), 409
        return (
            jsonify(
                {
                    "error": "Conflict: this instance organization already has another pending decision to a different target global organization",
                    "existing_decision_id": existing_pending.decision_id,
                    "existing_target_global_org_id": existing_pending.target_global_org_id,
                    "existing_target_global_org_name": existing_pending.target_global_org_name,
                }
            ),
            409,
        )

    decision = MergeDecision(
        instance_org_id=data["instance_org_id"],
        instance_org_name=data["instance_org_name"],
        original_global_org_id=data["original_global_org_id"],
        original_global_org_name=data["original_global_org_name"],
        target_global_org_id=data["target_global_org_id"],
        target_global_org_name=data["target_global_org_name"],
        decision_type=data.get("decision_type", "remap"),
        confidence=data.get("confidence"),
        similarity_score=data.get("similarity_score"),
        notes=data.get("notes", ""),
        decided_by=data.get("decided_by", "admin"),
    )
    db.session.add(decision)
    db.session.commit()

    return (
        jsonify(
            {
                "success": True,
                "decision_id": decision.decision_id,
                "message": "Mapping change decision recorded successfully",
                "decision": {
                    "decision_id": decision.decision_id,
                    "instance_org_id": decision.instance_org_id,
                    "instance_org_name": decision.instance_org_name,
                    "original_global_org_id": decision.original_global_org_id,
                    "original_global_org_name": decision.original_global_org_name,
                    "target_global_org_id": decision.target_global_org_id,
                    "target_global_org_name": decision.target_global_org_name,
                    "decision_type": decision.decision_type,
                    "confidence": decision.confidence,
                    "similarity_score": str(decision.similarity_score) if decision.similarity_score is not None else None,
                    "notes": decision.notes,
                    "decided_by": decision.decided_by,
                    "decided_at": decision.decided_at.isoformat() if decision.decided_at else None,
                    "execution_status": decision.execution_status,
                },
            }
        ),
        201,
    )


@api_bp.get("/merge-decisions/")
def list_merge_decisions():
    query = MergeDecision.query
    if request.args.get("status"):
        query = query.filter_by(execution_status=request.args.get("status"))
    if request.args.get("instance_org_id"):
        query = query.filter_by(instance_org_id=request.args.get("instance_org_id"))
    if request.args.get("original_global_org_id"):
        query = query.filter_by(original_global_org_id=request.args.get("original_global_org_id"))
    if request.args.get("target_global_org_id"):
        query = query.filter_by(target_global_org_id=request.args.get("target_global_org_id"))

    decisions = query.order_by(MergeDecision.decided_at.desc()).all()
    data = [
        {
            "decision_id": d.decision_id,
            "instance_org_id": d.instance_org_id,
            "instance_org_name": d.instance_org_name,
            "original_global_org_id": d.original_global_org_id,
            "original_global_org_name": d.original_global_org_name,
            "target_global_org_id": d.target_global_org_id,
            "target_global_org_name": d.target_global_org_name,
            "decision_type": d.decision_type,
            "confidence": d.confidence,
            "similarity_score": str(d.similarity_score) if d.similarity_score is not None else None,
            "notes": d.notes,
            "decided_by": d.decided_by,
            "decided_at": d.decided_at.isoformat() if d.decided_at else None,
            "execution_status": d.execution_status,
            "executed_at": d.executed_at.isoformat() if d.executed_at else None,
            "executed_by": d.executed_by,
            "execution_notes": d.execution_notes,
        }
        for d in decisions
    ]
    return jsonify({"count": len(data), "decisions": data})


@api_bp.delete("/merge-decisions/<int:decision_id>/")
def delete_merge_decision(decision_id):
    decision = MergeDecision.query.filter_by(decision_id=decision_id).first()
    if not decision:
        return _json_error("Decision not found", 404)
    if decision.execution_status != "pending":
        return _json_error(f"Cannot delete decision with status: {decision.execution_status}", 400)

    info = {
        "decision_id": decision.decision_id,
        "instance_org_name": decision.instance_org_name,
        "target_global_org_name": decision.target_global_org_name,
    }
    db.session.delete(decision)
    db.session.commit()
    return jsonify({"success": True, "message": "Decision deleted successfully", "deleted_decision": info})


@api_bp.patch("/merge-decisions/<int:decision_id>/status/")
def update_merge_decision_status(decision_id):
    decision = MergeDecision.query.filter_by(decision_id=decision_id).first()
    if not decision:
        return _json_error("Decision not found", 404)
    data = request.get_json(silent=True) or {}
    new_status = data.get("execution_status")
    if not new_status:
        return _json_error("execution_status is required", 400)
    if new_status not in ["executed", "cancelled", "pending"]:
        return _json_error("Invalid execution_status", 400)

    decision.execution_status = new_status
    mapping_updated = False
    if new_status == "executed":
        decision.executed_at = datetime.utcnow()
        decision.executed_by = data.get("executed_by", "admin")
        decision.execution_notes = data.get("execution_notes", "")

        updated = (
            OrgMapping.query.filter(
                and_(
                    OrgMapping.instance_org_id == decision.instance_org_id,
                    OrgMapping.global_org_id == decision.original_global_org_id,
                )
            )
            .update({"global_org_id": decision.target_global_org_id, "updated_at": datetime.utcnow()})
        )
        mapping_updated = updated > 0
        if mapping_updated:
            cache.delete("mapping_dashboard_data")
    elif new_status == "cancelled":
        decision.execution_notes = data.get("execution_notes", "Cancelled by user")

    db.session.commit()
    return jsonify(
        {
            "success": True,
            "message": f"Decision status updated to {new_status}",
            "mapping_updated": mapping_updated,
            "decision": {
                "decision_id": decision.decision_id,
                "execution_status": decision.execution_status,
                "executed_at": decision.executed_at.isoformat() if decision.executed_at else None,
                "executed_by": decision.executed_by,
                "execution_notes": decision.execution_notes,
            },
        }
    )
