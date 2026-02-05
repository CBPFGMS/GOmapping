import { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import './OrgMappings.css';

function OrgMappings() {
    const { goId } = useParams();
    const navigate = useNavigate();
    const [goInfo, setGoInfo] = useState(null);
    const [mappings, setMappings] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);

    useEffect(() => {
        // Call backend API to fetch mapping data
        fetch(`http://localhost:8000/api/org-mappings/${goId}/`)
            .then(response => {
                if (!response.ok) {
                    throw new Error('Failed to fetch data');
                }
                return response.json();
            })
            .then(data => {
                setGoInfo(data.go_info);
                setMappings(data.mappings);
                setLoading(false);
            })
            .catch(err => {
                setError(err.message);
                setLoading(false);
            });
    }, [goId]);

    // Get risk level style class (same as MappingDashboard)
    const getRiskClass = (percent) => {
        if (percent === null) return 'risk-none';
        if (percent >= 85) return 'risk-low';
        if (percent >= 60) return 'risk-medium';
        return 'risk-high';
    };

    // Get risk level text
    const getRiskLevel = (riskLevel) => {
        return riskLevel || '—';
    };

    if (loading) {
        return (
            <div className='org-mappings-container'>
                <div className='org-mappings-content'>
                    <div className='loading'>Loading data...</div>
                </div>
            </div>
        );
    }
    
    if (error) {
        return (
            <div className='org-mappings-container'>
                <div className='org-mappings-content'>
                    <div className='error'>Error: {error}</div>
                </div>
            </div>
        );
    }

    return (
        <div className='org-mappings-container'>
            <div className='org-mappings-content'>
                <div className='mappings-header'>
                    <button
                        className='back-button'
                        onClick={() => navigate(-1)}
                    >
                        ← Back to Summary
                    </button>
                    <h1>🗺️ GO Mapping Details</h1>
                    <h2>{goInfo?.global_org_name}</h2>
                    <p className='go-meta'>
                        <span>GO ID: {goInfo?.global_org_id}</span>
                        {goInfo?.global_acronym && <span> | Acronym: {goInfo.global_acronym}</span>}
                    </p>
                </div>
                
                <div className='table-wrapper'>
                    <table className='mappings-table'>
                        <thead>
                            <tr>
                                <th>Global_OrgName</th>
                                <th>Global_Acronym</th>
                                <th>Global_OrgId</th>
                                <th>Org_OrgName</th>
                                <th>Org_Acronym</th>
                                <th>InstanceOrgId</th>
                                <th>ParentOrgId</th>
                                <th>Match%</th>
                                <th>Risk</th>
                                <th>PoolFundID</th>
                                <th>PoolFundName</th>
                                <th>Status</th>
                            </tr>
                        </thead>
                        <tbody>
                            {mappings.length === 0 ? (
                                <tr>
                                    <td colSpan="12" className="no-data">No mappings found</td>
                                </tr>
                            ) : (
                                mappings.map((mapping, idx) => (
                                    <tr key={mapping.instance_org_id || idx}>
                                        {idx === 0 && (
                                            <>
                                                <td
                                                    rowSpan={mappings.length}
                                                    className='group-head'
                                                >
                                                    {goInfo?.global_org_name}
                                                </td>
                                                <td
                                                    rowSpan={mappings.length}
                                                    className='group-head'
                                                >
                                                    {goInfo?.global_acronym || '—'}
                                                </td>
                                                <td
                                                    rowSpan={mappings.length}
                                                    className='group-head'
                                                >
                                                    {goInfo?.global_org_id}
                                                </td>
                                            </>
                                        )}
                                        <td>{mapping.instance_org_name}</td>
                                        <td>{mapping.instance_org_acronym || '—'}</td>
                                        <td>{mapping.instance_org_id || '—'}</td>
                                        <td>{mapping.parent_instance_org_id || 'NULL'}</td>
                                        <td className={getRiskClass(mapping.match_percent)}>
                                            {mapping.match_percent !== null
                                                ? `${mapping.match_percent.toFixed(0)}%`
                                                : '—'}
                                        </td>
                                        <td className={getRiskClass(mapping.match_percent)}>
                                            {getRiskLevel(mapping.risk_level)}
                                        </td>
                                        <td>{mapping.fund_id || '—'}</td>
                                        <td>{mapping.fund_name || '—'}</td>
                                        <td>
                                            <span className={`status-badge status-${(mapping.status || '').toLowerCase().replace(/\s+/g, '-')}`}>
                                                {mapping.status || '—'}
                                            </span>
                                        </td>
                                    </tr>
                                ))
                            )}
                        </tbody>
                    </table>
                </div>

                <div className='summary-footer'>
                    <p>Total: <strong>{mappings.length}</strong> mapping records</p>
                </div>
            </div>
        </div>
    );
}

export default OrgMappings;

