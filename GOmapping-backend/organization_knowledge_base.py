"""
Global Organization Knowledge Base
Maintains standard names and country presence for known international organizations
"""

# Standard Global Organizations with their known presence
KNOWN_ORGANIZATIONS = {
    "save the children": {
        "standard_name": "Save the Children International",
        "acronym": "SC",
        "countries": ["UK", "USA", "Jordan", "Syria", "Ethiopia", "Somalia", "Afghanistan"],
        "priority": 10  # Higher priority = more authoritative
    },
    "international rescue committee": {
        "standard_name": "International Rescue Committee",
        "acronym": "IRC",
        "countries": ["Yemen", "Jordan", "Syria", "Somalia", "Afghanistan"],
        "priority": 9
    },
    "oxfam": {
        "standard_name": "Oxfam International",
        "acronym": "OXFAM",
        "countries": ["GB", "America", "International"],
        "priority": 9
    },
    "care": {
        "standard_name": "CARE International",
        "acronym": "CARE",
        "countries": ["International", "USA", "UK"],
        "priority": 9
    },
    "médecins sans frontières": {
        "standard_name": "Médecins Sans Frontières",
        "acronym": "MSF",
        "aliases": ["Doctors Without Borders", "MSF International"],
        "countries": ["France", "International"],
        "priority": 10
    },
    "doctors without borders": {
        "standard_name": "Médecins Sans Frontières",
        "acronym": "MSF",
        "is_alias": True,
        "canonical": "médecins sans frontières",
        "priority": 10
    },
    "world vision": {
        "standard_name": "World Vision International",
        "acronym": "WVI",
        "countries": ["International", "USA"],
        "priority": 9
    },
    "unicef": {
        "standard_name": "United Nations Children's Fund",
        "acronym": "UNICEF",
        "countries": ["Global"],
        "priority": 10
    },
    "unhcr": {
        "standard_name": "United Nations High Commissioner for Refugees",
        "acronym": "UNHCR",
        "countries": ["Global"],
        "priority": 10
    },
    "wfp": {
        "standard_name": "World Food Programme",
        "acronym": "WFP",
        "countries": ["Global"],
        "priority": 10
    },
    "zoa": {
        "standard_name": "ZOA International",
        "acronym": "ZOA",
        "aliases": ["ZOA Refugee Care"],
        "countries": ["Netherlands", "International", "Sudan", "Afghanistan", "Ethiopia"],
        "priority": 8
    },
    "islamic relief": {
        "standard_name": "Islamic Relief Worldwide",
        "acronym": "IRW",
        "aliases": ["IR Worldwide", "Islamic Relief"],
        "countries": ["UK", "Worldwide"],
        "priority": 8
    },
    "muslim hands": {
        "standard_name": "Muslim Hands",
        "acronym": "MH",
        "countries": ["UK", "International"],
        "priority": 7
    },
    "muslim aid": {
        "standard_name": "Muslim Aid UK",
        "acronym": "MA",
        "countries": ["UK", "Somalia", "Pakistan", "Iraq"],
        "priority": 7
    },
    "norwegian refugee council": {
        "standard_name": "Norwegian Refugee Council",
        "acronym": "NRC",
        "countries": ["Norway", "International"],
        "priority": 8
    },
    "danish refugee council": {
        "standard_name": "Danish Refugee Council",
        "acronym": "DRC",
        "countries": ["Denmark", "International"],
        "priority": 8
    },
    "mercy corps": {
        "standard_name": "Mercy Corps",
        "acronym": "MC",
        "countries": ["USA", "International"],
        "priority": 8
    },
    "action against hunger": {
        "standard_name": "Action Against Hunger",
        "acronym": "AAH",
        "countries": ["International"],
        "priority": 8
    },
    "plan international": {
        "standard_name": "Plan International",
        "acronym": "PI",
        "countries": ["International"],
        "priority": 8
    }
}


def normalize_for_kb(name):
    """Normalize organization name for knowledge base lookup"""
    import re
    if not name:
        return ""
    
    name = name.lower()
    # Remove special characters
    name = re.sub(r'[^\w\s]', ' ', name)
    # Remove common words
    stop_words = {'the', 'of', 'for', 'and', 'in', 'to', 'a', 'an'}
    words = [w for w in name.split() if w not in stop_words]
    name = ' '.join(words)
    
    # Remove country/location suffixes
    for suffix in ['international', 'uk', 'usa', 'jordan', 'yemen', 'somalia', 'ethiopia', 'syria', 'lebanon', 'iraq', 'afghanistan', 'sudan', 'pakistan', 'myanmar', 'colombia', 'south sudan', 'nigeria']:
        if name.endswith(' ' + suffix):
            name = name[:-len(' ' + suffix)]
            break
    
    return name.strip()


def find_standard_name(org_name):
    """
    Find the standard name for an organization
    Returns: (standard_name, priority, is_match) or (None, 0, False)
    """
    if not org_name:
        return None, 0, False
    
    normalized = normalize_for_kb(org_name)
    
    # Exact match
    if normalized in KNOWN_ORGANIZATIONS:
        org_info = KNOWN_ORGANIZATIONS[normalized]
        if org_info.get('is_alias'):
            # Redirect to canonical
            canonical = org_info['canonical']
            if canonical in KNOWN_ORGANIZATIONS:
                org_info = KNOWN_ORGANIZATIONS[canonical]
        return org_info['standard_name'], org_info.get('priority', 5), True
    
    # Partial match (check if normalized name contains or is contained in known org)
    for known_key, org_info in KNOWN_ORGANIZATIONS.items():
        if org_info.get('is_alias'):
            continue
        
        # Check if the known org name is in the input
        if known_key in normalized or normalized in known_key:
            return org_info['standard_name'], org_info.get('priority', 5), True
        
        # Check aliases
        if 'aliases' in org_info:
            for alias in org_info['aliases']:
                alias_norm = normalize_for_kb(alias)
                if alias_norm in normalized or normalized in alias_norm:
                    return org_info['standard_name'], org_info.get('priority', 5), True
    
    return None, 0, False


def get_recommendation_score(org_name, usage_count):
    """
    Calculate recommendation score for an organization
    Higher score = better candidate for master version
    
    Factors:
    - Knowledge base match (40%)
    - Usage count (40%)
    - Name completeness (20%)
    """
    standard_name, kb_priority, is_kb_match = find_standard_name(org_name)
    
    # KB score (0-40 points)
    kb_score = kb_priority * 4 if is_kb_match else 0
    
    # Usage score (0-40 points) - normalize to 0-40
    usage_score = min(usage_count * 4, 40)
    
    # Name completeness score (0-20 points)
    name_len = len(org_name) if org_name else 0
    completeness_score = min(name_len / 2, 20)
    
    total_score = kb_score + usage_score + completeness_score
    
    return {
        'score': total_score,
        'kb_match': is_kb_match,
        'standard_name': standard_name,
        'kb_priority': kb_priority,
        'usage_count': usage_count,
        'name_length': name_len
    }

