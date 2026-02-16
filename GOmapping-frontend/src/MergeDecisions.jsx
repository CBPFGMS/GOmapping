import { useState, useEffect } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import './MergeDecisions.css';

function MergeDecisions() {
    const [decisions, setDecisions] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);
    const location = useLocation();
    const queryParams = new URLSearchParams(location.search);
    const initialFilter = queryParams.get('status');
    const initialInstanceOrgId = queryParams.get('instance_org_id');
    const [filter, setFilter] = useState(['all', 'pending', 'executed', 'cancelled'].includes(initialFilter) ? initialFilter : 'all'); // all, pending, executed, cancelled
    const [searchTerm, setSearchTerm] = useState(initialInstanceOrgId || '');
    const navigate = useNavigate();

    useEffect(() => {
        const params = new URLSearchParams(location.search);
        const status = params.get('status');
        const instanceOrgId = params.get('instance_org_id');

        if (status && ['all', 'pending', 'executed', 'cancelled'].includes(status)) {
            setFilter(status);
        }
        if (instanceOrgId) {
            setSearchTerm(instanceOrgId);
        }
    }, [location.search]);

    const fetchDecisions = async () => {
        setLoading(true);
        try {
            const response = await fetch('http://localhost:8000/api/merge-decisions/');
            if (!response.ok) {
                throw new Error('Failed to fetch decisions');
            }
            const data = await response.json();
            setDecisions(data.decisions || []);
            setError(null);
        } catch (err) {
            console.error('Error fetching decisions:', err);
            setError(err.message);
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        fetchDecisions();
    }, []);

    const updateStatus = async (decisionId, newStatus, notes = '') => {
        try {
            const response = await fetch(`http://localhost:8000/api/merge-decisions/${decisionId}/status/`, {
                method: 'PATCH',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    execution_status: newStatus,
                    executed_by: 'admin',
                    execution_notes: notes
                })
            });

            if (!response.ok) {
                throw new Error('Failed to update status');
            }

            alert(`✅ Status updated to ${newStatus}`);
            fetchDecisions();
        } catch (err) {
            console.error('Error updating status:', err);
            alert(`❌ Error: ${err.message}`);
        }
    };

    const deleteDecision = async (decisionId) => {
        if (!window.confirm('Are you sure you want to delete this decision?')) {
            return;
        }

        try {
            const response = await fetch(`http://localhost:8000/api/merge-decisions/${decisionId}/`, {
                method: 'DELETE',
            });

            if (!response.ok) {
                throw new Error('Failed to delete decision');
            }

            alert('✅ Decision deleted successfully');
            fetchDecisions();
        } catch (err) {
            console.error('Error deleting decision:', err);
            alert(`❌ Error: ${err.message}`);
        }
    };

    const matchesDecisionSearch = (decision, term) => {
        const query = (term || '').trim().toLowerCase();
        if (!query) return true;

        const instanceOrgId = String(decision.instance_org_id ?? '');
        const decisionId = String(decision.decision_id ?? '');
        const instanceOrgName = (decision.instance_org_name || '').toLowerCase();
        const originalGlobalName = (decision.original_global_org_name || '').toLowerCase();
        const targetGlobalName = (decision.target_global_org_name || '').toLowerCase();

        // Numeric search from deep-link should pinpoint exact record by ID
        if (/^\d+$/.test(query)) {
            return instanceOrgId === query || decisionId === query;
        }

        return (
            instanceOrgName.includes(query) ||
            originalGlobalName.includes(query) ||
            targetGlobalName.includes(query) ||
            instanceOrgId.includes(query) ||
            decisionId.includes(query)
        );
    };

    const exportToCSV = () => {
        const filteredDecisions = decisions.filter(d => {
            if (filter !== 'all' && d.execution_status !== filter) return false;
            return matchesDecisionSearch(d, searchTerm);
        });

        const headers = [
            'Decision ID',
            'Instance Org ID',
            'Instance Org Name',
            'Original Global Org ID',
            'Original Global Org Name',
            'Target Global Org ID',
            'Target Global Org Name',
            'Decision Type',
            'Confidence',
            'Similarity Score',
            'Status',
            'Decided By',
            'Decided At',
            'Executed At',
            'Notes',
            'Execution Notes'
        ];

        const rows = filteredDecisions.map(d => [
            d.decision_id,
            d.instance_org_id,
            d.instance_org_name,
            d.original_global_org_id,
            d.original_global_org_name,
            d.target_global_org_id,
            d.target_global_org_name,
            d.decision_type,
            d.confidence || '',
            d.similarity_score || '',
            d.execution_status,
            d.decided_by,
            d.decided_at,
            d.executed_at || '',
            d.notes || '',
            d.execution_notes || ''
        ]);

        const csvContent = [
            headers.join(','),
            ...rows.map(row => row.map(cell => `"${cell}"`).join(','))
        ].join('\n');

        const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
        const link = document.createElement('a');
        const url = URL.createObjectURL(blob);
        link.setAttribute('href', url);
        link.setAttribute('download', `merge_decisions_${new Date().toISOString().split('T')[0]}.csv`);
        link.style.visibility = 'hidden';
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
    };

    const getStatusBadge = (status) => {
        const badges = {
            pending: { icon: '⏳', class: 'badge-pending', text: 'Pending' },
            executed: { icon: '✅', class: 'badge-executed', text: 'Executed' },
            cancelled: { icon: '❌', class: 'badge-cancelled', text: 'Cancelled' }
        };
        const badge = badges[status] || badges.pending;
        return <span className={`status-badge ${badge.class}`}>{badge.icon} {badge.text}</span>;
    };

    // Stats always reflect the full database counts (unfiltered)
    const stats = {
        total: decisions.length,
        pending: decisions.filter(d => d.execution_status === 'pending').length,
        executed: decisions.filter(d => d.execution_status === 'executed').length,
        cancelled: decisions.filter(d => d.execution_status === 'cancelled').length
    };

    // Apply tab filter + search filter for display
    const filteredDecisions = decisions.filter(d => {
        if (filter !== 'all' && d.execution_status !== filter) return false;
        return matchesDecisionSearch(d, searchTerm);
    });

    if (loading) {
        return (
            <div className='merge-decisions-container'>
                <div className='loading'>⏳ Loading decisions...</div>
            </div>
        );
    }

    if (error) {
        return (
            <div className='merge-decisions-container'>
                <div className='error'>❌ Error: {error}</div>
            </div>
        );
    }

    return (
        <div className='merge-decisions-container'>
            <div className='page-header'>
                <div className='header-left'>
                    <button className='back-btn' onClick={() => navigate('/go-summary')}>
                        ← Back to GO Summary
                    </button>
                    <h1>📝 Merge Decisions</h1>
                </div>
                <button className='export-btn' onClick={exportToCSV}>
                    📥 Export to CSV
                </button>
            </div>

            {/* Statistics */}
            <div className='stats-grid'>
                <div className='stat-card total'>
                    <div className='stat-number'>{stats.total}</div>
                    <div className='stat-label'>Total Decisions</div>
                </div>
                <div className='stat-card pending'>
                    <div className='stat-number'>{stats.pending}</div>
                    <div className='stat-label'>⏳ Pending</div>
                </div>
                <div className='stat-card executed'>
                    <div className='stat-number'>{stats.executed}</div>
                    <div className='stat-label'>✅ Executed</div>
                </div>
                <div className='stat-card cancelled'>
                    <div className='stat-number'>{stats.cancelled}</div>
                    <div className='stat-label'>❌ Cancelled</div>
                </div>
            </div>

            {/* Filters and Search */}
            <div className='controls'>
                <div className='filter-buttons'>
                    <button
                        className={`filter-btn ${filter === 'all' ? 'active' : ''}`}
                        onClick={() => setFilter('all')}
                    >
                        All
                    </button>
                    <button
                        className={`filter-btn ${filter === 'pending' ? 'active' : ''}`}
                        onClick={() => setFilter('pending')}
                    >
                        ⏳ Pending
                    </button>
                    <button
                        className={`filter-btn ${filter === 'executed' ? 'active' : ''}`}
                        onClick={() => setFilter('executed')}
                    >
                        ✅ Executed
                    </button>
                    <button
                        className={`filter-btn ${filter === 'cancelled' ? 'active' : ''}`}
                        onClick={() => setFilter('cancelled')}
                    >
                        ❌ Cancelled
                    </button>
                </div>
                <input
                    type='text'
                    className='search-input'
                    placeholder='🔍 Search organizations...'
                    value={searchTerm}
                    onChange={(e) => setSearchTerm(e.target.value)}
                />
            </div>

            {/* Decisions List */}
            <div className='decisions-list'>
                {filteredDecisions.length === 0 ? (
                    <div className='empty-state'>
                        <div className='empty-icon'>📋</div>
                        <div className='empty-text'>No decisions found</div>
                        <div className='empty-subtext'>
                            {searchTerm ? 'Try a different search term' : 'Record your first decision in GO Summary page'}
                        </div>
                    </div>
                ) : (
                    filteredDecisions.map(decision => (
                        <div key={decision.decision_id} className='decision-card'>
                            <div className='decision-header'>
                                <div className='decision-id'>
                                    Decision #{decision.decision_id}
                                </div>
                                {getStatusBadge(decision.execution_status)}
                            </div>

                            <div className='decision-flow'>
                                <div className='flow-step'>
                                    <div className='flow-label'>Instance Org</div>
                                    <div className='flow-value'>
                                        <strong>#{decision.instance_org_id}</strong> {decision.instance_org_name}
                                    </div>
                                </div>

                                <div className='flow-arrow'>↓</div>

                                <div className='flow-step original'>
                                    <div className='flow-label'>From (Original Global Org)</div>
                                    <div className='flow-value'>
                                        <strong>#{decision.original_global_org_id}</strong> {decision.original_global_org_name}
                                    </div>
                                </div>

                                <div className='flow-arrow change'>→</div>

                                <div className='flow-step target'>
                                    <div className='flow-label'>To (Target Global Org)</div>
                                    <div className='flow-value'>
                                        <strong>#{decision.target_global_org_id}</strong> {decision.target_global_org_name}
                                    </div>
                                </div>
                            </div>

                            <div className='decision-meta'>
                                <div className='meta-item'>
                                    <span className='meta-label'>Type:</span>
                                    <span className='meta-value'>{decision.decision_type}</span>
                                </div>
                                {decision.confidence && (
                                    <div className='meta-item'>
                                        <span className='meta-label'>Confidence:</span>
                                        <span className='meta-value'>{decision.confidence}</span>
                                    </div>
                                )}
                                {decision.similarity_score && (
                                    <div className='meta-item'>
                                        <span className='meta-label'>Similarity:</span>
                                        <span className='meta-value'>{decision.similarity_score}%</span>
                                    </div>
                                )}
                                <div className='meta-item'>
                                    <span className='meta-label'>Decided by:</span>
                                    <span className='meta-value'>{decision.decided_by}</span>
                                </div>
                                <div className='meta-item'>
                                    <span className='meta-label'>Decided at:</span>
                                    <span className='meta-value'>
                                        {new Date(decision.decided_at).toLocaleString('zh-CN', {
                                            year: 'numeric', month: '2-digit', day: '2-digit',
                                            hour: '2-digit', minute: '2-digit', hour12: false
                                        })}
                                    </span>
                                </div>
                            </div>

                            {decision.notes && (
                                <div className='decision-notes'>
                                    <div className='notes-label'>📝 Notes:</div>
                                    <div className='notes-content'>{decision.notes}</div>
                                </div>
                            )}

                            {decision.execution_notes && (
                                <div className='execution-notes'>
                                    <div className='notes-label'>📋 Execution Notes:</div>
                                    <div className='notes-content'>{decision.execution_notes}</div>
                                </div>
                            )}

                            <div className='decision-actions'>
                                {decision.execution_status === 'pending' && (
                                    <>
                                        <button
                                            className='action-btn execute'
                                            onClick={() => {
                                                const notes = prompt('Enter execution notes (optional):');
                                                if (notes !== null) {
                                                    updateStatus(decision.decision_id, 'executed', notes);
                                                }
                                            }}
                                        >
                                            ✅ Mark as Executed
                                        </button>
                                        <button
                                            className='action-btn cancel'
                                            onClick={() => {
                                                const notes = prompt('Enter cancellation reason:');
                                                if (notes !== null) {
                                                    updateStatus(decision.decision_id, 'cancelled', notes);
                                                }
                                            }}
                                        >
                                            ❌ Cancel
                                        </button>
                                        <button
                                            className='action-btn delete'
                                            onClick={() => deleteDecision(decision.decision_id)}
                                        >
                                            🗑️ Delete
                                        </button>
                                    </>
                                )}
                                {decision.execution_status === 'executed' && decision.executed_at && (
                                    <div className='execution-info'>
                                        ✅ Executed on {new Date(decision.executed_at).toLocaleString('zh-CN')}
                                        {decision.executed_by && ` by ${decision.executed_by}`}
                                    </div>
                                )}
                            </div>
                        </div>
                    ))
                )}
            </div>
        </div>
    );
}

export default MergeDecisions;
