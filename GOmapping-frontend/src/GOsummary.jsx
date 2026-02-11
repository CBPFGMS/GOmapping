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

    // Sync status state
    const [syncing, setSyncing] = useState(false);
    const [syncStatus, setSyncStatus] = useState(null);
    const [lastSyncTime, setLastSyncTime] = useState(null);
    const [syncPhase, setSyncPhase] = useState('');
    const [syncProgress, setSyncProgress] = useState(0);
    const [syncElapsedSeconds, setSyncElapsedSeconds] = useState(0);
    const [syncStartedAt, setSyncStartedAt] = useState(null);

    // AI recommendation state
    const [aiRecommendations, setAiRecommendations] = useState({}); // {group_id: {recommendation, reasoning, loading}}
    const [aiLoadingGroups, setAiLoadingGroups] = useState(new Set());

    // Merge Decision state
    const [showDecisionModal, setShowDecisionModal] = useState(false);
    const [decisionData, setDecisionData] = useState(null);
    const [submittingDecision, setSubmittingDecision] = useState(false);

    // Pagination state - Duplicate Groups
    const [dupCurrentPage, setDupCurrentPage] = useState(1);
    const [dupItemsPerPage, setDupItemsPerPage] = useState(15);
    const [dupJumpToPage, setDupJumpToPage] = useState('');

    // Pagination state - Unique Orgs
    const [uniqueCurrentPage, setUniqueCurrentPage] = useState(1);
    const [uniqueItemsPerPage, setUniqueItemsPerPage] = useState(15);
    const [uniqueJumpToPage, setUniqueJumpToPage] = useState('');

    // View toggle state
    const [currentView, setCurrentView] = useState('duplicates'); // 'duplicates' or 'unique'
    const [groupTabs, setGroupTabs] = useState({}); // {group_id: 'system' | 'ai'}

    const fetchData = (forceRefresh = false) => {
        // Only show loading on first load when there's no cache
        const hasCachedData = sessionStorage.getItem('go_summary_data');
        if (!hasCachedData) {
            setLoading(true);
        }

        // If forceRefresh, clear sessionStorage cache to ensure fresh data
        if (forceRefresh) {
            sessionStorage.removeItem('go_summary_data');
            console.log('🗑️ Cleared sessionStorage cache (force refresh)');
        }

        const refreshParam = forceRefresh ? '&refresh=true' : '';
        const timestamp = new Date().getTime();
        fetch(`http://localhost:8000/api/go-summary/?_t=${timestamp}${refreshParam}`)
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

                // Save to sessionStorage for page refreshes
                const cacheData = {
                    duplicate_groups: jsonData.duplicate_groups || [],
                    unique_organizations: jsonData.unique_organizations || [],
                    summary: jsonData.summary || {},
                    timestamp: Date.now()
                };
                sessionStorage.setItem('go_summary_data', JSON.stringify(cacheData));
                console.log('💾 Data saved to sessionStorage cache');

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

    // Trigger data sync (backend) - ONLY when user clicks Refresh button
    const triggerSync = async () => {
        if (syncing) return;

        console.log('🔄 Starting manual sync...');
        setSyncing(true);
        setLoading(true);
        setSyncPhase('Step 1/3: Syncing source data');
        setSyncProgress(8);
        setSyncElapsedSeconds(0);
        setSyncStartedAt(Date.now());

        try {
            // Step 1: Trigger backend sync (external API -> database)
            console.log('📡 Calling backend sync API...');
            const syncResponse = await fetch('http://localhost:8000/api/trigger-sync/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    sync_type: 'full',  // Sync both APIs
                    force: true  // Force sync (ignore time limits)
                })
            });

            const syncResult = await syncResponse.json();

            if (!syncResult.success) {
                throw new Error(syncResult.error || 'Sync failed');
            }

            console.log('✅ Backend sync completed:', syncResult.message);
            setSyncPhase('Step 2/3: Recalculating similarity');
            setSyncProgress(prev => Math.max(prev, 55));

            // Step 2: Force recalculate duplicates (with refresh=true)
            console.log('🔄 Recalculating duplicates...');
            sessionStorage.removeItem('go_summary_data');

            const timestamp = new Date().getTime();
            const dataResponse = await fetch(`http://localhost:8000/api/go-summary/?_t=${timestamp}&refresh=true`);

            if (!dataResponse.ok) {
                throw new Error('Failed to fetch updated data');
            }

            const jsonData = await dataResponse.json();

            // Step 3: Update UI with new data
            setDuplicateGroups(jsonData.duplicate_groups || []);
            setUniqueOrgs(jsonData.unique_organizations || []);
            setSummary(jsonData.summary || {});

            // Save to cache
            const cacheData = {
                duplicate_groups: jsonData.duplicate_groups || [],
                unique_organizations: jsonData.unique_organizations || [],
                summary: jsonData.summary || {},
                timestamp: Date.now()
            };
            sessionStorage.setItem('go_summary_data', JSON.stringify(cacheData));
            setSyncPhase('Step 3/3: Finalizing and loading results');
            setSyncProgress(prev => Math.max(prev, 92));

            // Fetch updated sync time from database (poll briefly to avoid stale timestamp)
            await waitForLatestSyncTime(lastSyncTime);

            // Reset pagination
            setDupCurrentPage(1);
            setUniqueCurrentPage(1);

            console.log('✅ Data refresh completed!');
            setSyncProgress(100);
            alert('✅ Data synced successfully!\n\n' + syncResult.message);

        } catch (err) {
            console.error('❌ Sync failed:', err);
            alert('❌ Sync failed: ' + err.message);
        } finally {
            setSyncing(false);
            setLoading(false);
            setSyncPhase('');
            setSyncProgress(0);
            setSyncElapsedSeconds(0);
            setSyncStartedAt(null);
        }
    };

    // Fetch last sync time from database
    const fetchLastSyncTime = async () => {
        try {
            const response = await fetch('http://localhost:8000/api/sync-status/');
            if (response.ok) {
                const data = await response.json();
                const latestSyncTime = data.last_sync?.time || null;
                setLastSyncTime(latestSyncTime);
                return latestSyncTime;
            }
        } catch (err) {
            console.error('Failed to fetch sync status:', err);
        }
        return null;
    };

    // Poll sync status briefly until latest sync time is visible
    const waitForLatestSyncTime = async (previousTime, maxAttempts = 10, intervalMs = 1000) => {
        const prevTs = previousTime ? new Date(previousTime).getTime() : 0;

        for (let attempt = 0; attempt < maxAttempts; attempt++) {
            try {
                const response = await fetch('http://localhost:8000/api/sync-status/');
                if (response.ok) {
                    const data = await response.json();
                    const latestSyncTime = data.last_sync?.time || null;
                    const latestTs = latestSyncTime ? new Date(latestSyncTime).getTime() : 0;
                    const isSyncing = !!data.is_syncing;

                    if (latestSyncTime && latestTs > prevTs) {
                        setLastSyncTime(latestSyncTime);
                        return latestSyncTime;
                    }

                    // Fallback: if backend says not syncing, use whatever latest value is available
                    if (!isSyncing) {
                        setLastSyncTime(latestSyncTime);
                        return latestSyncTime;
                    }
                }
            } catch (err) {
                console.error('Failed to poll sync status:', err);
            }

            // Wait before next poll
            await new Promise(resolve => setTimeout(resolve, intervalMs));
        }

        return fetchLastSyncTime();
    };

    //this will be executed once this component rendered to DOM 
    useEffect(() => {
        // Fetch last sync time from database
        fetchLastSyncTime();

        // Try to load from sessionStorage first (for browser refresh)
        const cachedData = sessionStorage.getItem('go_summary_data');

        if (cachedData) {
            try {
                const parsed = JSON.parse(cachedData);
                console.log('✅ Using cached data from sessionStorage');
                setDuplicateGroups(parsed.duplicate_groups || []);
                setUniqueOrgs(parsed.unique_organizations || []);
                setSummary(parsed.summary || {});
                setLoading(false);
                return; // Always use cache on page load
            } catch (e) {
                console.error('❌ Failed to parse cached data:', e);
            }
        }

        // If no cache, fetch from server (first time only)
        console.log('📭 No cached data found, fetching from server');
        fetchData();
    }, []);

    // Update elapsed time and smooth progress while syncing
    useEffect(() => {
        if (!syncing || !syncStartedAt) return undefined;

        const timerId = setInterval(() => {
            const elapsed = Math.floor((Date.now() - syncStartedAt) / 1000);
            setSyncElapsedSeconds(elapsed);

            setSyncProgress(prev => {
                let cap = 96;
                if (syncPhase.startsWith('Step 1/3')) cap = 45;
                else if (syncPhase.startsWith('Step 2/3')) cap = 88;

                if (prev >= cap) return prev;
                return Math.min(cap, prev + 0.8);
            });
        }, 500);

        return () => clearInterval(timerId);
    }, [syncing, syncStartedAt, syncPhase]);

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

    // Ask AI for recommendation
    const askAI = async (group, forceRegenerate = false) => {
        const groupId = group.group_id;

        // If already loading, ignore
        if (aiLoadingGroups.has(groupId)) {
            return;
        }

        // If regenerating, clear old recommendation first
        if (forceRegenerate && aiRecommendations[groupId]) {
            setAiRecommendations(prev => {
                const newRecs = { ...prev };
                delete newRecs[groupId];
                return newRecs;
            });
        }

        // Auto-expand the group to show AI result
        setExpandedGroups(prev => new Set([...prev, groupId]));

        // Set loading state
        setAiLoadingGroups(prev => new Set([...prev, groupId]));

        try {
            const response = await fetch(`http://localhost:8000/api/ai-recommendation/`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    group_id: groupId,
                    group_name: group.group_name,
                    members: group.members.map(m => ({
                        global_org_id: m.global_org_id,
                        global_org_name: m.global_org_name,
                        usage_count: m.usage_count,
                        is_recommended: m.is_recommended,
                        kb_match: m.kb_match
                    }))
                })
            });

            if (!response.ok) {
                // Surface backend error message (often contains the real cause)
                const raw = await response.text();
                let message = raw || 'AI recommendation failed';
                try {
                    const parsed = JSON.parse(raw);
                    if (parsed?.error) message = parsed.error;
                } catch {
                    // ignore JSON parse errors
                }
                throw new Error(message);
            }

            const data = await response.json();

            // Save AI recommendation
            setAiRecommendations(prev => ({
                ...prev,
                [groupId]: {
                    recommended_id: data.recommended_id,
                    recommended_name: data.recommended_name,
                    reasoning: data.reasoning,
                    analysis: data.analysis
                }
            }));
        } catch (err) {
            console.error('AI recommendation error:', err);
            setAiRecommendations(prev => ({
                ...prev,
                [groupId]: {
                    error: err?.message || 'Failed to get AI recommendation. Please try again.'
                }
            }));
        } finally {
            // Remove loading state
            setAiLoadingGroups(prev => {
                const newSet = new Set(prev);
                newSet.delete(groupId);
                return newSet;
            });
        }
    };

    // ========== Merge Decision Functions ==========

    const openDecisionModal = (instanceOrg, currentGlobalOrg, targetGlobalOrg, group) => {
        setDecisionData({
            instance_org_id: instanceOrg.instance_org_id,
            instance_org_name: instanceOrg.instance_org_name,
            original_global_org_id: currentGlobalOrg.global_org_id,
            original_global_org_name: currentGlobalOrg.global_org_name,
            target_global_org_id: targetGlobalOrg.global_org_id,
            target_global_org_name: targetGlobalOrg.global_org_name,
            similarity_score: group.max_similarity,
            decision_type: 'remap',
            confidence: 'high',
            notes: ''
        });
        setShowDecisionModal(true);
    };

    const submitDecision = async () => {
        if (!decisionData) return;

        setSubmittingDecision(true);
        try {
            const response = await fetch('http://localhost:8000/api/merge-decisions/create/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(decisionData)
            });

            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.error || 'Failed to record decision');
            }

            const result = await response.json();
            alert(`✅ Decision recorded successfully! (ID: ${result.decision_id})`);
            setShowDecisionModal(false);
            setDecisionData(null);
        } catch (err) {
            console.error('Error submitting decision:', err);
            alert(`❌ Error: ${err.message}`);
        } finally {
            setSubmittingDecision(false);
        }
    };

    const recordAllDecisions = async (member, targetGlobalOrg, group) => {
        if (!member.instance_organizations || member.instance_organizations.length === 0) {
            alert('No instances to record');
            return;
        }

        const count = member.instance_organizations.length;
        if (!window.confirm(`Record remapping decisions for all ${count} instances?\n\nThis will create ${count} decision records.`)) {
            return;
        }

        let successCount = 0;
        let failCount = 0;
        const errors = [];

        for (const inst of member.instance_organizations) {
            try {
                const decisionPayload = {
                    instance_org_id: inst.instance_org_id,
                    instance_org_name: inst.instance_org_name,
                    original_global_org_id: member.global_org_id,
                    original_global_org_name: member.global_org_name,
                    target_global_org_id: targetGlobalOrg.global_org_id,
                    target_global_org_name: targetGlobalOrg.global_org_name,
                    decision_type: 'remap',
                    confidence: 'high',
                    similarity_score: group.max_similarity,
                    notes: `Batch recorded from duplicate group`,
                    decided_by: 'admin'
                };

                const response = await fetch('http://localhost:8000/api/merge-decisions/create/', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify(decisionPayload)
                });

                if (!response.ok) {
                    const errorData = await response.json();
                    throw new Error(errorData.error || 'Failed to record decision');
                }

                successCount++;
            } catch (err) {
                failCount++;
                errors.push(`Instance #${inst.instance_org_id}: ${err.message}`);
            }
        }

        // Show results
        let message = `✅ Successfully recorded: ${successCount} decisions`;
        if (failCount > 0) {
            message += `\n❌ Failed: ${failCount} decisions`;
            if (errors.length > 0) {
                message += `\n\nErrors:\n${errors.slice(0, 3).join('\n')}`;
                if (errors.length > 3) {
                    message += `\n... and ${errors.length - 3} more`;
                }
            }
        }
        alert(message);
    };

    const getGroupTab = (groupId) => groupTabs[groupId] || 'system';

    const setGroupTab = (groupId, tab) => {
        setGroupTabs(prev => ({ ...prev, [groupId]: tab }));
    };

    const renderRecommendationTree = (group, mode = 'system') => {
        const aiRec = aiRecommendations[group.group_id];
        const recommendedIdRaw = mode === 'ai' ? aiRec?.recommended_id : group.recommended_master.global_org_id;
        const recommendedId = Number.parseInt(recommendedIdRaw, 10);
        const effectiveRecommendedId = Number.isFinite(recommendedId) ? recommendedId : null;

        const targetGlobalOrg = mode === 'system'
            ? group.recommended_master
            : group.members.find(m => m.global_org_id === effectiveRecommendedId) || group.recommended_master;

        const showActions = mode === 'system';

        return (
            <div className='tree-structure'>
                {group.members.map((member) => {
                    const isRecommended = effectiveRecommendedId !== null
                        ? member.global_org_id === effectiveRecommendedId
                        : member.is_recommended;

                    return (
                        <div key={member.global_org_id} className='tree-node'>
                            <div className='tree-node-header'>
                                {isRecommended ? (
                                    <span className='status-badge master'>⭐ KEEP</span>
                                ) : (
                                    <span className='status-badge merge'>MERGE</span>
                                )}
                                <span className='tree-node-id'>#{member.global_org_id} </span>
                                <span
                                    className='tree-node-name link-text'
                                    onClick={() => handleGONameClick(member.global_org_id)}
                                >
                                    {member.global_org_name} (global organization)
                                </span>
                                <span
                                    className='usage-badge clickable'
                                    onClick={() => handleUsageCountClick(member.global_org_id)}
                                    title="View all mappings"
                                >
                                    {member.usage_count} instances
                                </span>
                                {showActions && !isRecommended && member.instance_organizations && member.instance_organizations.length > 0 && (
                                    <button
                                        className='record-all-btn'
                                        onClick={() => recordAllDecisions(member, targetGlobalOrg, group)}
                                        title={`Record all ${member.instance_organizations.length} instances`}
                                    >
                                        📝 Record All ({member.instance_organizations.length})
                                    </button>
                                )}
                            </div>
                            {member.instance_organizations && member.instance_organizations.length > 0 && (
                                <div className='tree-children'>
                                    {member.instance_organizations.map((inst, idx) => (
                                        <div key={inst.instance_org_id || idx} className='tree-child'>
                                            <span className='tree-branch'>└─</span>
                                            <span className='inst-org-id'>#{inst.instance_org_id}</span>
                                            <span className='inst-org-name'>{inst.instance_org_name} </span>
                                            {inst.instance_org_acronym && (
                                                <span className='inst-org-acronym'>({inst.instance_org_acronym}) (instance organization)</span>
                                            )}
                                            <span className={`match-badge ${getMatchClass(inst.match_percent)}`}>
                                                {inst.match_percent !== null && inst.match_percent !== undefined
                                                    ? `${Math.round(inst.match_percent)}%`
                                                    : '—'}
                                            </span>
                                            {showActions && !isRecommended && (
                                                <button
                                                    className='record-decision-btn'
                                                    onClick={() => openDecisionModal(inst, member, targetGlobalOrg, group)}
                                                    title='Record mapping change decision'
                                                >
                                                    📝 Record
                                                </button>
                                            )}
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
                    );
                })}
            </div>
        );
    };

    // Don't show full-screen loading, only show in-place loading indicator
    // if (loading) {
    //     return loading page...
    // }

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
                    <div style={{ display: 'flex', gap: '15px', justifyContent: 'center', alignItems: 'flex-start' }}>
                        <button
                            className='nav-button'
                            onClick={() => navigate('/mapping-dashboard')}
                        >
                            📊 Check Mapping Dashboard
                        </button>
                        <button
                            className='nav-button'
                            onClick={() => navigate('/merge-decisions')}
                            style={{ minWidth: '180px' }}
                        >
                            📝 View Decisions
                        </button>
                        <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '5px', minHeight: '60px' }}>
                            <button
                                className='nav-button'
                                onClick={triggerSync}
                                disabled={syncing}
                                style={{
                                    opacity: syncing ? 0.7 : 1,
                                    backgroundColor: syncing ? '#ff9800' : undefined,
                                    minWidth: '180px'
                                }}
                            >
                                {syncing ? '⏳ Syncing & Calculating...' : '🔄 Refresh Data'}
                            </button>
                            {lastSyncTime && !syncing && (
                                <span style={{
                                    fontSize: '11px',
                                    color: '#DDD',
                                    display: 'flex',
                                    alignItems: 'center',
                                    gap: '4px',
                                    whiteSpace: 'nowrap'
                                }}>
                                    <span style={{ color: '#52c41a' }}>●</span>
                                    Last synced: {new Date(lastSyncTime).toLocaleString('zh-CN', {
                                        year: 'numeric',
                                        month: '2-digit',
                                        day: '2-digit',
                                        hour: '2-digit',
                                        minute: '2-digit',
                                        second: '2-digit',
                                        hour12: false
                                    })}
                                </span>
                            )}
                            {syncing && (
                                <>
                                    <span style={{
                                        fontSize: '12px',
                                        color: '#ff9800',
                                        fontWeight: '500'
                                    }}>
                                        {syncPhase || 'Sync in progress...'}
                                    </span>
                                    <span style={{
                                        fontSize: '11px',
                                        color: '#DDD'
                                    }}>
                                        Elapsed: {syncElapsedSeconds}s
                                    </span>
                                </>
                            )}
                            {!syncing && (
                                <span style={{
                                    fontSize: '11px',
                                    color: '#DDD'
                                }}>
                                    Tip: Click "Refresh Data" to sync latest records.
                                </span>
                            )}
                        </div>
                    </div>
                </div>

                {syncing ? (
                    <div style={{
                        marginTop: '24px',
                        padding: '40px 20px',
                        textAlign: 'center',
                        color: '#fff',
                        background: 'rgba(255, 255, 255, 0.08)',
                        borderRadius: '14px',
                        border: '1px solid rgba(255, 255, 255, 0.2)'
                    }}>
                        <div style={{ fontSize: '28px', marginBottom: '10px' }}>⏳</div>
                        <div style={{ fontSize: '18px', fontWeight: 600 }}>
                            {syncPhase || 'Sync and similarity calculation in progress'}
                        </div>
                        <div style={{
                            marginTop: '14px',
                            width: 'min(520px, 90%)',
                            marginLeft: 'auto',
                            marginRight: 'auto',
                            background: 'rgba(255, 255, 255, 0.2)',
                            borderRadius: '999px',
                            height: '12px',
                            overflow: 'hidden'
                        }}>
                            <div style={{
                                width: `${Math.round(syncProgress)}%`,
                                height: '100%',
                                background: 'linear-gradient(90deg, #ffb74d 0%, #ff9800 100%)',
                                transition: 'width 0.4s ease'
                            }} />
                        </div>
                        <div style={{ marginTop: '8px', opacity: 0.9 }}>
                            Progress: {Math.round(syncProgress)}% · Elapsed: {syncElapsedSeconds}s
                        </div>
                    </div>
                ) : (loading && duplicateGroups.length === 0 && uniqueOrgs.length === 0 && !summary.total_organizations) ? (
                    <div style={{
                        marginTop: '24px',
                        padding: '26px 20px',
                        textAlign: 'center',
                        color: '#fff',
                        background: 'rgba(255, 255, 255, 0.08)',
                        borderRadius: '14px',
                        border: '1px solid rgba(255, 255, 255, 0.2)'
                    }}>
                        <div style={{ fontSize: '16px', fontWeight: 600 }}>
                            No data loaded yet.
                        </div>
                        <div style={{ marginTop: '8px', opacity: 0.9 }}>
                            Please click "Refresh Data" to run sync and generate the latest summary.
                        </div>
                    </div>
                ) : (
                    <>
                        {/* Summary Statistics */}
                        <div className='summary-stats'>
                            <div className='stat-box'>
                                <div className='stat-number'>{summary.total_organizations || 0}</div>
                                <div className='stat-label'>Total Global Organizations</div>
                            </div>
                            <div
                                className={`stat-box warning clickable ${currentView === 'duplicates' ? 'active' : ''}`}
                                onClick={() => setCurrentView('duplicates')}
                                title="Click to view duplicate groups"
                            >
                                <div className='stat-number'>{summary.duplicate_groups_count || 0}</div>
                                <div className='stat-label'>
                                    Duplicate Groups
                                    {currentView === 'duplicates' && <span className='view-indicator'> ✓</span>}
                                </div>
                            </div>
                            <div
                                className={`stat-box success clickable ${currentView === 'unique' ? 'active' : ''}`}
                                onClick={() => setCurrentView('unique')}
                                title="Click to view unique organizations"
                            >
                                <div className='stat-number'>{summary.unique_count || 0}</div>
                                <div className='stat-label'>
                                    Unique Global Organizations
                                    {currentView === 'unique' && <span className='view-indicator'> ✓</span>}
                                </div>
                            </div>
                        </div>

                        {/* Duplicate Groups */}
                        {currentView === 'duplicates' && duplicateGroups.length > 0 && (
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
                                            >
                                                <div
                                                    className='group-header-main'
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
                                                <span className='meta-item' style={{ marginLeft: '12px' }}>
                                                    {aiRecommendations[group.group_id] ? '🤖 AI ready' : '🤖 AI not generated'}
                                                </span>
                                            </div>

                                            {expandedGroups.has(group.group_id) && (
                                                <div className='group-details'>
                                                    <div style={{ display: 'flex', gap: '10px', marginBottom: '14px' }}>
                                                        <button
                                                            className='expand-all-btn'
                                                            style={{
                                                                padding: '8px 14px',
                                                                background: getGroupTab(group.group_id) === 'system' ? '#5f7bf7' : '#ffffff',
                                                                color: getGroupTab(group.group_id) === 'system' ? '#fff' : '#5f7bf7',
                                                                borderColor: '#5f7bf7'
                                                            }}
                                                            onClick={() => setGroupTab(group.group_id, 'system')}
                                                        >
                                                            🧮 System Algorithm
                                                        </button>
                                                        <button
                                                            className='expand-all-btn'
                                                            style={{
                                                                padding: '8px 14px',
                                                                background: getGroupTab(group.group_id) === 'ai' ? '#5f7bf7' : '#ffffff',
                                                                color: getGroupTab(group.group_id) === 'ai' ? '#fff' : '#5f7bf7',
                                                                borderColor: '#5f7bf7'
                                                            }}
                                                            onClick={() => setGroupTab(group.group_id, 'ai')}
                                                        >
                                                            🤖 AI Model Recommendation
                                                        </button>
                                                    </div>

                                                    {getGroupTab(group.group_id) === 'system' && (
                                                        <>
                                                            <div className='recommended-info' style={{ marginBottom: '12px' }}>
                                                                ⭐ System Recommendation: #{group.recommended_master.global_org_id} - {group.recommended_master.global_org_name}
                                                            </div>
                                                            {renderRecommendationTree(group, 'system')}
                                                        </>
                                                    )}

                                                    {getGroupTab(group.group_id) === 'ai' && (
                                                        <>
                                                            {!aiRecommendations[group.group_id] && !aiLoadingGroups.has(group.group_id) && (
                                                                <div style={{
                                                                    marginBottom: '14px',
                                                                    padding: '14px',
                                                                    border: '1px dashed #8ba1ff',
                                                                    borderRadius: '10px',
                                                                    background: 'rgba(95, 123, 247, 0.06)'
                                                                }}>
                                                                    <div style={{ marginBottom: '10px', color: '#5f7bf7', fontWeight: 600 }}>
                                                                        AI recommendation has not been generated for this group.
                                                                    </div>
                                                                    <button
                                                                        className='ai-btn'
                                                                        onClick={() => askAI(group, false)}
                                                                    >
                                                                        🤖 Ask AI
                                                                    </button>
                                                                </div>
                                                            )}

                                                            {aiLoadingGroups.has(group.group_id) && (
                                                                <div className='ai-recommendation-panel'>
                                                                    <div className='ai-header'>
                                                                        <span className='ai-icon'>⏳</span>
                                                                        <h3 className='ai-title'>AI is analyzing this group...</h3>
                                                                    </div>
                                                                </div>
                                                            )}

                                                            {aiRecommendations[group.group_id]?.error && (
                                                                <div className='ai-error-panel'>
                                                                    <span className='error-icon'>⚠️</span>
                                                                    <span>{aiRecommendations[group.group_id].error}</span>
                                                                </div>
                                                            )}

                                                            {aiRecommendations[group.group_id] && !aiRecommendations[group.group_id].error && (
                                                                <>
                                                                    <div className='recommended-info' style={{ marginBottom: '12px' }}>
                                                                        🤖 AI Recommendation: #{aiRecommendations[group.group_id].recommended_id} - {aiRecommendations[group.group_id].recommended_name}
                                                                    </div>

                                                                    {renderRecommendationTree(group, 'ai')}

                                                                    <div className='ai-recommendation-panel' style={{ marginTop: '14px' }}>
                                                                        <div className='ai-header'>
                                                                            <span className='ai-icon'>🤖</span>
                                                                            <h3 className='ai-title'>AI Analysis & Reasons</h3>
                                                                        </div>
                                                                        <div className='ai-content'>
                                                                            <div className='ai-reasoning'>
                                                                                <div className='ai-label'>📊 Key Factors:</div>
                                                                                <ul className='ai-reasons-list'>
                                                                                    {aiRecommendations[group.group_id].reasoning.map((reason, idx) => (
                                                                                        <li key={idx}>{reason}</li>
                                                                                    ))}
                                                                                </ul>
                                                                            </div>
                                                                            {aiRecommendations[group.group_id].analysis && (
                                                                                <div className='ai-analysis'>
                                                                                    <div className='ai-label'>🔍 Detailed Analysis:</div>
                                                                                    <p className='ai-analysis-text'>{aiRecommendations[group.group_id].analysis}</p>
                                                                                </div>
                                                                            )}
                                                                        </div>
                                                                    </div>
                                                                </>
                                                            )}
                                                        </>
                                                    )}
                                                </div>
                                            )}
                                        </div>
                                    ))}
                                </div>
                                {/* Bottom pagination for Duplicate Groups */}
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
                            </div>
                        )}

                        {/* Unique Organizations */}
                        {currentView === 'unique' && uniqueOrgs.length > 0 && (
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
                                                                <span className='inst-org-name'>{inst.instance_org_name} </span>
                                                                {inst.instance_org_acronym && (
                                                                    <span className='inst-org-acronym'>({inst.instance_org_acronym}) (instance orgnization)</span>
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
                                {/* Bottom pagination for Unique Organizations */}
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
                            </div>
                        )}
                    </>
                )}

                {/* Merge Decision Modal */}
                {showDecisionModal && decisionData && (
                    <div className='modal-overlay' onClick={() => setShowDecisionModal(false)}>
                        <div className='modal-content' onClick={(e) => e.stopPropagation()}>
                            <div className='modal-header'>
                                <h2>📝 Record Mapping Change Decision</h2>
                                <button className='modal-close' onClick={() => setShowDecisionModal(false)}>✕</button>
                            </div>

                            <div className='modal-body'>
                                <div className='decision-flow'>
                                    <div className='flow-item'>
                                        <div className='flow-label'>Instance Organization</div>
                                        <div className='flow-value'>
                                            <strong>#{decisionData.instance_org_id}</strong>
                                            <span>{decisionData.instance_org_name}</span>
                                        </div>
                                    </div>

                                    <div className='flow-arrow'>↓</div>

                                    <div className='flow-item original'>
                                        <div className='flow-label'>Current Mapping</div>
                                        <div className='flow-value'>
                                            <strong>#{decisionData.original_global_org_id}</strong>
                                            <span>{decisionData.original_global_org_name}</span>
                                        </div>
                                    </div>

                                    <div className='flow-arrow change'>→</div>

                                    <div className='flow-item target'>
                                        <div className='flow-label'>New Mapping ⭐</div>
                                        <div className='flow-value'>
                                            <strong>#{decisionData.target_global_org_id}</strong>
                                            <span>{decisionData.target_global_org_name}</span>
                                        </div>
                                    </div>
                                </div>

                                <div className='form-group'>
                                    <label>Decision Type:</label>
                                    <select
                                        value={decisionData.decision_type}
                                        onChange={(e) => setDecisionData({ ...decisionData, decision_type: e.target.value })}
                                    >
                                        <option value="remap">Remap (Change mapping)</option>
                                        <option value="merge">Merge</option>
                                        <option value="review_later">Review Later</option>
                                    </select>
                                </div>

                                <div className='form-group'>
                                    <label>Confidence Level:</label>
                                    <select
                                        value={decisionData.confidence}
                                        onChange={(e) => setDecisionData({ ...decisionData, confidence: e.target.value })}
                                    >
                                        <option value="high">High</option>
                                        <option value="medium">Medium</option>
                                        <option value="low">Low</option>
                                    </select>
                                </div>

                                <div className='form-group'>
                                    <label>Notes (optional):</label>
                                    <textarea
                                        value={decisionData.notes}
                                        onChange={(e) => setDecisionData({ ...decisionData, notes: e.target.value })}
                                        placeholder="Add any notes about this decision..."
                                        rows="3"
                                    />
                                </div>

                                {decisionData.similarity_score && (
                                    <div className='info-box'>
                                        ℹ️ Similarity Score: <strong>{decisionData.similarity_score.toFixed(1)}%</strong>
                                    </div>
                                )}
                            </div>

                            <div className='modal-footer'>
                                <button
                                    className='btn-secondary'
                                    onClick={() => setShowDecisionModal(false)}
                                    disabled={submittingDecision}
                                >
                                    Cancel
                                </button>
                                <button
                                    className='btn-primary'
                                    onClick={submitDecision}
                                    disabled={submittingDecision}
                                >
                                    {submittingDecision ? '⏳ Recording...' : '✅ Record Decision'}
                                </button>
                            </div>
                        </div>
                    </div>
                )}
            </div>
        </div>
    );
}
export default GOsummary;