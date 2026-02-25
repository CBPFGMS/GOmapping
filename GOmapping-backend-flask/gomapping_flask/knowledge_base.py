import re


KNOWN_ORGANIZATIONS = {
    "save the children": {
        "standard_name": "Save the Children International",
        "acronym": "SC",
        "countries": ["UK", "USA", "Jordan", "Syria", "Ethiopia", "Somalia", "Afghanistan"],
        "priority": 10,
    },
    "international rescue committee": {
        "standard_name": "International Rescue Committee",
        "acronym": "IRC",
        "countries": ["Yemen", "Jordan", "Syria", "Somalia", "Afghanistan"],
        "priority": 9,
    },
    "oxfam": {
        "standard_name": "Oxfam International",
        "acronym": "OXFAM",
        "countries": ["GB", "America", "International"],
        "priority": 9,
    },
    "care": {
        "standard_name": "CARE International",
        "acronym": "CARE",
        "countries": ["International", "USA", "UK"],
        "priority": 9,
    },
    "world vision": {
        "standard_name": "World Vision International",
        "acronym": "WVI",
        "countries": ["International", "USA"],
        "priority": 9,
    },
    "unicef": {
        "standard_name": "United Nations Children's Fund",
        "acronym": "UNICEF",
        "countries": ["Global"],
        "priority": 10,
    },
    "unhcr": {
        "standard_name": "United Nations High Commissioner for Refugees",
        "acronym": "UNHCR",
        "countries": ["Global"],
        "priority": 10,
    },
    "wfp": {
        "standard_name": "World Food Programme",
        "acronym": "WFP",
        "countries": ["Global"],
        "priority": 10,
    },
}


def normalize_for_kb(name: str) -> str:
    if not name:
        return ""
    text = name.lower()
    text = re.sub(r"[^\w\s]", " ", text)
    stop_words = {"the", "of", "for", "and", "in", "to", "a", "an"}
    words = [w for w in text.split() if w not in stop_words]
    text = " ".join(words)
    suffixes = [
        "international",
        "uk",
        "usa",
        "jordan",
        "yemen",
        "somalia",
        "ethiopia",
        "syria",
        "lebanon",
        "iraq",
        "afghanistan",
        "sudan",
        "pakistan",
    ]
    for suffix in suffixes:
        if text.endswith(" " + suffix):
            text = text[: -len(" " + suffix)]
            break
    return text.strip()


def find_standard_name(org_name: str):
    if not org_name:
        return None, 0, False
    normalized = normalize_for_kb(org_name)
    if normalized in KNOWN_ORGANIZATIONS:
        item = KNOWN_ORGANIZATIONS[normalized]
        return item["standard_name"], item.get("priority", 0), True

    for key, item in KNOWN_ORGANIZATIONS.items():
        if key in normalized or normalized in key:
            return item["standard_name"], item.get("priority", 0), True

    return None, 0, False


def get_recommendation_score(org_name: str, usage_count: int):
    standard_name, kb_priority, kb_match = find_standard_name(org_name)
    kb_score = kb_priority * 4 if kb_match else 0
    usage_score = min((usage_count or 0) * 4, 40)
    name_len = len(org_name or "")
    completeness_score = min(name_len / 2, 20)
    total = kb_score + usage_score + completeness_score
    return {
        "score": total,
        "kb_match": kb_match,
        "standard_name": standard_name,
        "kb_priority": kb_priority,
        "usage_count": usage_count or 0,
        "name_length": name_len,
    }
