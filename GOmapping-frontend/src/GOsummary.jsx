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
    const navigate = useNavigate();

    // Pagination state
    const [currentPage, setCurrentPage] = useState(1);
    const [itemsPerPage, setItemsPerPage] = useState(15);
    const [jumpToPage, setJumpToPage] = useState('');

    useEffect(() => {
        const timestamp = new Date().getTime();
        fetch(`http://localhost:8000/go-summary/?_t=${timestamp}`)
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

    // Similarity style class
    const getSimilarityClass = (percent) => {
        if (percent === null) return 'similarity-none';
        if (percent >= 85) return 'similarity-very-high';
        if (percent >= 70) return 'similarity-high';
        return 'similarity-medium';
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
                    <button
                        className='nav-button'
                        onClick={() => navigate('/mapping-dashboard')}
                    >
                        📊 Check Mapping Dashboard
                    </button>
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
                        <h2 className='section-title'>
                            🔄 Duplicate Groups ({duplicateGroups.length})
                        </h2>
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
                                            <table className='members-table'>
                                                <thead>
                                                    <tr>
                                                        <th>Status</th>
                                                        <th>GO ID</th>
                                                        <th>Organization Name</th>
                                                        <th>Usage Count</th>
                                                        <th>Actions</th>
                                                    </tr>
                                                </thead>
                                                <tbody>
                                                    {group.members.map((member) => (
                                                        <tr
                                                            key={member.global_org_id}
                                                            className={member.is_recommended ? 'recommended' : ''}
                                                        >
                                                            <td>
                                                                {member.is_recommended ? (
                                                                    <span className='status-badge master'>⭐ KEEP</span>
                                                                ) : (
                                                                    <span className='status-badge merge'>MERGE</span>
                                                                )}
                                                            </td>
                                                            <td>{member.global_org_id}</td>
                                                            <td>
                                                                <span
                                                                    className='link-text'
                                                                    onClick={() => handleGONameClick(member.global_org_id)}
                                                                >
                                                                    {member.global_org_name}
                                                                </span>
                                                            </td>
                                                            <td>
                                                                <span
                                                                    className='usage-badge clickable'
                                                                    onClick={() => handleUsageCountClick(member.global_org_id)}
                                                                >
                                                                    {member.usage_count}
                                                                </span>
                                                            </td>
                                                            <td>
                                                                <button
                                                                    className='action-btn'
                                                                    onClick={() => handleUsageCountClick(member.global_org_id)}
                                                                    title="View all instance organizations mapped to this GO"
                                                                >
                                                                    View Mappings
                                                                </button>
                                                            </td>
                                                        </tr>
                                                    ))}
                                                </tbody>
                                            </table>
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
                        <h2 className='section-title'>
                            ✅ Unique Global Organizations ({uniqueOrgs.length})
                        </h2>
                        <div className='unique-list'>
                            {uniqueOrgs.map((org) => (
                                <div key={org.global_org_id} className='unique-item'>
                                    <span className='unique-id'>{org.global_org_id}</span>
                                    <span
                                        className='link-text'
                                        onClick={() => handleGONameClick(org.global_org_id)}
                                    >
                                        {org.global_org_name}
                                    </span>
                                    <span
                                        className='usage-badge clickable'
                                        onClick={() => handleUsageCountClick(org.global_org_id)}
                                    >
                                        {org.usage_count}
                                    </span>
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