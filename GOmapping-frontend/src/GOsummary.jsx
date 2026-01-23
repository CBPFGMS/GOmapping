import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import './GOSummary.css';
import './GOSummary_grouped.css';

function GOsummary() {
    const [duplicateGroups, setDuplicateGroups] = useState([]);
    const [uniqueOrgs, setUniqueOrgs] = useState([]);
    const [summary, setSummary] = useState({});
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);
    const [expandedGroups, setExpandedGroups] = useState(new Set());
    const [expandedUniqueOrgs, setExpandedUniqueOrgs] = useState(new Set());
    const navigate = useNavigate();

    // Pagination state
    const [currentPage, setCurrentPage] = useState(1);
    const [itemsPerPage, setItemsPerPage] = useState(15);
    const [jumpToPage, setJumpToPage] = useState('');

    const fetchData = (forceRefresh = false) => {
        setLoading(true);
        const refreshParam = forceRefresh ? '&refresh=true' : '';
        const timestamp = new Date().getTime();
        fetch(`http://localhost:8000/go-summary/?_t=${timestamp}${refreshParam}`)
            .then(response => {
                if (!response.ok) {
                    throw new Error('fail to connect server');
                }
                return response.json();
            })
            .then(jsonData => {
                setDuplicateGroups(jsonData.duplicate_groups || []);
                setUniqueOrgs(jsonData.unique_organizations || []);
                setSummary(jsonData.summary || {});
                setLoading(false);
            })
            .catch(err => {
                setError(err.message);
                setLoading(false);
            });
    };

    useEffect(() => {
        fetchData();
    }, []);

    // Toggle group expansion
    const toggleGroup = (groupId) => {
        const newExpanded = new Set(expandedGroups);
        if (newExpanded.has(groupId)) {
            newExpanded.delete(groupId);
        } else {
            newExpanded.add(groupId);
        }
        setExpandedGroups(newExpanded);
    };

    // Expand/Collapse all duplicate groups
    const toggleAllGroups = () => {
        if (expandedGroups.size === duplicateGroups.length) {
            // All expanded - collapse all
            setExpandedGroups(new Set());
        } else {
            // Some or none expanded - expand all
            const allGroupIds = duplicateGroups.map(g => g.group_id);
            setExpandedGroups(new Set(allGroupIds));
        }
    };

    // Toggle unique org expansion
    const toggleUniqueOrg = (orgId) => {
        const newExpanded = new Set(expandedUniqueOrgs);
        if (newExpanded.has(orgId)) {
            newExpanded.delete(orgId);
        } else {
            newExpanded.add(orgId);
        }
        setExpandedUniqueOrgs(newExpanded);
    };

    // Expand/Collapse all unique organizations
    const toggleAllUniqueOrgs = () => {
        if (expandedUniqueOrgs.size === uniqueOrgs.length) {
            // All expanded - collapse all
            setExpandedUniqueOrgs(new Set());
        } else {
            // Some or none expanded - expand all
            const allOrgIds = uniqueOrgs.map(org => org.global_org_id);
            setExpandedUniqueOrgs(new Set(allOrgIds));
        }
    };

    // Similarity style class
    const getSimilarityClass = (percent) => {
        if (percent === null) return 'similarity-none';
        if (percent >= 85) return 'similarity-very-high';
        if (percent >= 70) return 'similarity-high';
        return 'similarity-medium';
    };

    // Match percentage style class
    const getMatchClass = (percent) => {
        if (percent === null || percent === undefined) return 'match-none';
        if (percent >= 85) return 'match-high';
        if (percent >= 60) return 'match-medium';
        return 'match-low';
    };

    //  GO Detail page
    const handleGONameClick = (goId) => {
        navigate(`/go-detail/${goId}`);
    };

    // Org Mappings page
    const handleUsageCountClick = (goId) => {
        navigate(`/org-mappings/${goId}`);
    };



    if (loading) {
        return (
            <div className='go-summary-container'>
                <div className='loading'>loding...</div>
            </div>
        );
    }

    if (error) {
        return (
            <div className='go-summary-container'>
                <div className='error'>error: {error}</div>
            </div>
        );
    }

    return (
        <div className='go-summary-container'>
            <div className='go-summary-content'>
                <div className='summary-header'>
                    <h1>🌍 Global Organization Mapping Summary</h1>
                    <div style={{ display: 'flex', gap: '15px', justifyContent: 'center' }}>
                        <button
                            className='nav-button'
                            onClick={() => navigate('/mapping-dashboard')}
                        >
                            📊 Check Mapping Dashboard
                        </button>
                        <button
                            className='nav-button'
                            onClick={() => fetchData(true)}
                            disabled={loading}
                            style={{ opacity: loading ? 0.6 : 1 }}
                        >
                            {loading ? '⏳ Loading...' : '🔄 Refresh Data'}
                        </button>
                    </div>
                </div>

                {/* Summary Statistics */}
                <div className='summary-stats'>
                    <div className='stat-box'>
                        <div className='stat-number'>{summary.total_organizations || 0}</div>
                        <div className='stat-label'>Total Global Organizations</div>
                    </div>
                    <div className='stat-box warning'>
                        <div className='stat-number'>{summary.duplicate_groups_count || 0}</div>
                        <div className='stat-label'>Duplicate Groups</div>
                    </div>
                    <div className='stat-box success'>
                        <div className='stat-number'>{summary.unique_count || 0}</div>
                        <div className='stat-label'>Unique Global Organizations</div>
                    </div>
                </div>

                {/* Duplicate Groups */}
                {duplicateGroups.length > 0 && (
                    <div className='section'>
                        <div className='section-header'>
                            <h2 className='section-title'>
                                🔄 Duplicate Groups ({duplicateGroups.length})
                            </h2>
                            <button
                                className='expand-all-btn'
                                onClick={toggleAllGroups}
                            >
                                {expandedGroups.size === duplicateGroups.length ? '📕 Collapse All' : '📖 Expand All'}
                            </button>
                        </div>
                        <div className='groups-list'>
                            {duplicateGroups.map((group) => (
                                <div key={group.group_id} className='group-card'>
                                    <div
                                        className='group-header'
                                        onClick={() => toggleGroup(group.group_id)}
                                    >
                                        <div className='group-title'>
                                            <span className='group-icon'>
                                                {expandedGroups.has(group.group_id) ? '▼' : '▶'}
                                            </span>
                                            <span className='group-name'>{group.group_name}</span>
                                            <span className={`similarity-badge ${getSimilarityClass(group.max_similarity)}`}>
                                                {group.max_similarity.toFixed(1)}% similar
                                            </span>
                                        </div>
                                        <div className='group-meta'>
                                            <span className='meta-item'>
                                                {group.total_members} members
                                            </span>
                                            <span className='meta-item'>
                                                {group.total_instances} instances
                                            </span>
                                        </div>
                                        <div className='recommended-info'>
                                            ⭐ Recommended: {group.recommended_master.global_org_name}
                                        </div>
                                    </div>

                                    {expandedGroups.has(group.group_id) && (
                                        <div className='group-details'>
                                            <div className='tree-structure'>
                                                {group.members.map((member) => (
                                                    <div key={member.global_org_id} className='tree-node'>
                                                        <div className='tree-node-header'>
                                                            {member.is_recommended ? (
                                                                <span className='status-badge master'>⭐ KEEP</span>
                                                            ) : (
                                                                <span className='status-badge merge'>MERGE</span>
                                                            )}
                                                            <span className='tree-node-id'>#{member.global_org_id}</span>
                                                            <span
                                                                className='tree-node-name link-text'
                                                                onClick={() => handleGONameClick(member.global_org_id)}
                                                            >
                                                                {member.global_org_name}
                                                            </span>
                                                            <span
                                                                className='usage-badge clickable'
                                                                onClick={() => handleUsageCountClick(member.global_org_id)}
                                                                title="View all mappings"
                                                            >
                                                                {member.usage_count} instances
                                                            </span>
                                                        </div>
                                                        {member.instance_organizations && member.instance_organizations.length > 0 && (
                                                            <div className='tree-children'>
                                                                {member.instance_organizations.map((inst, idx) => (
                                                                    <div key={inst.instance_org_id || idx} className='tree-child'>
                                                                        <span className='tree-branch'>└─</span>
                                                                        <span className='inst-org-id'>#{inst.instance_org_id}</span>
                                                                        <span className='inst-org-name'>{inst.instance_org_name}</span>
                                                                        {inst.instance_org_acronym && (
                                                                            <span className='inst-org-acronym'>({inst.instance_org_acronym})</span>
                                                                        )}
                                                                        <span className={`match-badge ${getMatchClass(inst.match_percent)}`}>
                                                                            {inst.match_percent !== null && inst.match_percent !== undefined
                                                                                ? `${Math.round(inst.match_percent)}%`
                                                                                : '—'}
                                                                        </span>
                                                                    </div>
                                                                ))}
                                                                {member.usage_count > member.instance_organizations.length && (
                                                                    <div className='tree-child more-items'>
                                                                        <span className='tree-branch'>└─</span>
                                                                        <span
                                                                            className='link-text'
                                                                            onClick={() => handleUsageCountClick(member.global_org_id)}
                                                                        >
                                                                            ... and {member.usage_count - member.instance_organizations.length} more
                                                                        </span>
                                                                    </div>
                                                                )}
                                                            </div>
                                                        )}
                                                    </div>
                                                ))}
                                            </div>
                                        </div>
                                    )}
                                </div>
                            ))}
                        </div>
                    </div>
                )}

                {/* Unique Organizations */}
                {uniqueOrgs.length > 0 && (
                    <div className='section'>
                        <div className='section-header'>
                            <h2 className='section-title'>
                                ✅ Unique Global Organizations ({uniqueOrgs.length})
                            </h2>
                            <button
                                className='expand-all-btn'
                                onClick={toggleAllUniqueOrgs}
                            >
                                {expandedUniqueOrgs.size === uniqueOrgs.length ? '📕 Collapse All' : '📖 Expand All'}
                            </button>
                        </div>
                        <div className='unique-list'>
                            {uniqueOrgs.map((org) => (
                                <div key={org.global_org_id} className='unique-org-card'>
                                    <div
                                        className='unique-org-header'
                                        onClick={() => toggleUniqueOrg(org.global_org_id)}
                                    >
                                        <span className='unique-org-icon'>
                                            {expandedUniqueOrgs.has(org.global_org_id) ? '▼' : '▶'}
                                        </span>
                                        <span className='unique-id'>#{org.global_org_id}</span>
                                        <span
                                            className='link-text'
                                            onClick={(e) => {
                                                e.stopPropagation();
                                                handleGONameClick(org.global_org_id);
                                            }}
                                        >
                                            {org.global_org_name}
                                        </span>
                                        <span
                                            className='usage-badge clickable'
                                            onClick={(e) => {
                                                e.stopPropagation();
                                                handleUsageCountClick(org.global_org_id);
                                            }}
                                            title="View all mappings"
                                        >
                                            {org.usage_count} instances
                                        </span>
                                    </div>
                                    {expandedUniqueOrgs.has(org.global_org_id) && org.instance_organizations && org.instance_organizations.length > 0 && (
                                        <div className='unique-org-details'>
                                            <div className='tree-children'>
                                                {org.instance_organizations.map((inst, idx) => (
                                                    <div key={inst.instance_org_id || idx} className='tree-child'>
                                                        <span className='tree-branch'>└─</span>
                                                        <span className='inst-org-id'>#{inst.instance_org_id}</span>
                                                        <span className='inst-org-name'>{inst.instance_org_name}</span>
                                                        {inst.instance_org_acronym && (
                                                            <span className='inst-org-acronym'>({inst.instance_org_acronym})</span>
                                                        )}
                                                        <span className={`match-badge ${getMatchClass(inst.match_percent)}`}>
                                                            {inst.match_percent !== null && inst.match_percent !== undefined
                                                                ? `${Math.round(inst.match_percent)}%`
                                                                : '—'}
                                                        </span>
                                                    </div>
                                                ))}
                                                {org.usage_count > org.instance_organizations.length && (
                                                    <div className='tree-child more-items'>
                                                        <span className='tree-branch'>└─</span>
                                                        <span
                                                            className='link-text'
                                                            onClick={() => handleUsageCountClick(org.global_org_id)}
                                                        >
                                                            ... and {org.usage_count - org.instance_organizations.length} more
                                                        </span>
                                                    </div>
                                                )}
                                            </div>
                                        </div>
                                    )}
                                </div>
                            ))}
                        </div>
                    </div>
                )}
            </div>
        </div>
    );
}
export default GOsummary;