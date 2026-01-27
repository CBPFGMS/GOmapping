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

    // Pagination state - Duplicate Groups
    const [dupCurrentPage, setDupCurrentPage] = useState(1);
    const [dupItemsPerPage, setDupItemsPerPage] = useState(15);
    const [dupJumpToPage, setDupJumpToPage] = useState('');

    // Pagination state - Unique Orgs
    const [uniqueCurrentPage, setUniqueCurrentPage] = useState(1);
    const [uniqueItemsPerPage, setUniqueItemsPerPage] = useState(15);
    const [uniqueJumpToPage, setUniqueJumpToPage] = useState('');

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
                // Reset pagination when new data is loaded
                setDupCurrentPage(1);
                setUniqueCurrentPage(1);
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

    // ---------- Pagination helpers ----------
    const clampPage = (page, totalPages) => {
        if (totalPages <= 0) return 1;
        if (page < 1) return 1;
        if (page > totalPages) return totalPages;
        return page;
    };

    const PaginationControls = ({
        totalItems,
        currentPage,
        itemsPerPage,
        setCurrentPage,
        jumpToPage,
        setJumpToPage,
        setItemsPerPage,
        labelPrefix = 'Items per page'
    }) => {
        const totalPages = Math.ceil(totalItems / itemsPerPage) || 1;
        const startIndex = (currentPage - 1) * itemsPerPage;
        const endIndex = Math.min(startIndex + itemsPerPage, totalItems);

        const handlePageChange = (page) => {
            const next = clampPage(page, totalPages);
            setCurrentPage(next);
        };

        const handleItemsPerPageChange = (e) => {
            const next = parseInt(e.target.value, 10);
            setItemsPerPage(next);
            setCurrentPage(1);
        };

        const handleJump = () => {
            const page = parseInt(jumpToPage, 10);
            if (!Number.isFinite(page)) return;
            setCurrentPage(clampPage(page, totalPages));
            setJumpToPage('');
        };

        if (totalItems <= 0) return null;

        return (
            <div className='pagination-container' style={{ marginTop: '15px' }}>
                <div className='pagination-info'>
                    <span>
                        Showing {totalItems === 0 ? 0 : startIndex + 1} to {endIndex} of {totalItems}
                    </span>
                </div>

                <div className='pagination-controls'>
                    <div className='items-per-page'>
                        <label>{labelPrefix}:</label>
                        <select
                            value={itemsPerPage}
                            onChange={handleItemsPerPageChange}
                            className='page-select'
                        >
                            <option value={10}>10</option>
                            <option value={15}>15</option>
                            <option value={20}>20</option>
                            <option value={30}>30</option>
                            <option value={50}>50</option>
                            <option value={100}>100</option>
                        </select>
                    </div>

                    <div className='page-buttons'>
                        <button
                            onClick={() => handlePageChange(1)}
                            disabled={currentPage === 1}
                            className='page-btn'
                        >
                            ««
                        </button>
                        <button
                            onClick={() => handlePageChange(currentPage - 1)}
                            disabled={currentPage === 1}
                            className='page-btn'
                        >
                            ‹
                        </button>

                        <span className='page-info'>
                            Page {currentPage} of {totalPages}
                        </span>

                        <button
                            onClick={() => handlePageChange(currentPage + 1)}
                            disabled={currentPage === totalPages}
                            className='page-btn'
                        >
                            ›
                        </button>
                        <button
                            onClick={() => handlePageChange(totalPages)}
                            disabled={currentPage === totalPages}
                            className='page-btn'
                        >
                            »»
                        </button>
                    </div>

                    <div className='jump-to-page'>
                        <label>Go to page:</label>
                        <input
                            type='number'
                            min='1'
                            max={totalPages}
                            value={jumpToPage}
                            onChange={(e) => setJumpToPage(e.target.value)}
                            onKeyDown={(e) => e.key === 'Enter' && handleJump()}
                            className='page-input'
                            placeholder='#'
                        />
                        <button onClick={handleJump} className='page-btn jump-btn'>
                            Go
                        </button>
                    </div>
                </div>
            </div>
        );
    };

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
            <div className='go-summary-container loading-fullscreen'>
                <div className='loading-card'>
                    <div className='loading-spinner'></div>
                    <h2 className='loading-title'>⏳ Processing Data...</h2>
                    <p className='loading-subtitle'>We're calculating usage counts and analyzing similarities</p>
                    <div className='loading-steps'>
                        <div className='loading-step'>
                            <span className='step-icon'>✓</span>
                            <span>Fetching global organizations</span>
                        </div>
                        <div className='loading-step active'>
                            <span className='step-icon'>⟳</span>
                            <span>Calculating usage statistics</span>
                        </div>
                        <div className='loading-step'>
                            <span className='step-icon'>○</span>
                            <span>Identifying duplicates</span>
                        </div>
                        <div className='loading-step'>
                            <span className='step-icon'>○</span>
                            <span>Organizing results</span>
                        </div>
                    </div>
                    <p className='loading-note'>This may take a few moments for large datasets...</p>
                </div>
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

    // ---------- Apply pagination ----------
    const dupTotalPages = Math.ceil(duplicateGroups.length / dupItemsPerPage) || 1;
    const safeDupPage = clampPage(dupCurrentPage, dupTotalPages);
    const dupStart = (safeDupPage - 1) * dupItemsPerPage;
    const paginatedDuplicateGroups = duplicateGroups.slice(dupStart, dupStart + dupItemsPerPage);

    const uniqueTotalPages = Math.ceil(uniqueOrgs.length / uniqueItemsPerPage) || 1;
    const safeUniquePage = clampPage(uniqueCurrentPage, uniqueTotalPages);
    const uniqueStart = (safeUniquePage - 1) * uniqueItemsPerPage;
    const paginatedUniqueOrgs = uniqueOrgs.slice(uniqueStart, uniqueStart + uniqueItemsPerPage);

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
                        <PaginationControls
                            totalItems={duplicateGroups.length}
                            currentPage={safeDupPage}
                            itemsPerPage={dupItemsPerPage}
                            setCurrentPage={setDupCurrentPage}
                            jumpToPage={dupJumpToPage}
                            setJumpToPage={setDupJumpToPage}
                            setItemsPerPage={setDupItemsPerPage}
                            labelPrefix='Groups per page'
                        />
                        <div className='groups-list'>
                            {paginatedDuplicateGroups.map((group) => (
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
                                            ⭐ Recommended: #{group.recommended_master.global_org_id} - {group.recommended_master.global_org_name}
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
                        <PaginationControls
                            totalItems={uniqueOrgs.length}
                            currentPage={safeUniquePage}
                            itemsPerPage={uniqueItemsPerPage}
                            setCurrentPage={setUniqueCurrentPage}
                            jumpToPage={uniqueJumpToPage}
                            setJumpToPage={setUniqueJumpToPage}
                            setItemsPerPage={setUniqueItemsPerPage}
                            labelPrefix='Orgs per page'
                        />
                        <div className='unique-list'>
                            {paginatedUniqueOrgs.map((org) => (
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