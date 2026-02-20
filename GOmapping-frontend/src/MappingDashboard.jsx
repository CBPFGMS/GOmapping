import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import './MappingDashboard.css';

function MappingDashboard() {
    const navigate = useNavigate();
    const [data, setData] = useState([]);
    const [filteredData, setFilteredData] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);

    // Filter state
    const [goFilter, setGoFilter] = useState('');
    const [poolFundFilter, setPoolFundFilter] = useState('');
    const [riskFilter, setRiskFilter] = useState('');
    const [instanceOrgTypeFilter, setInstanceOrgTypeFilter] = useState('');
    // Unique values for dropdown options
    const [goOptions, setGoOptions] = useState([]);
    const [poolFundOptions, setPoolFundOptions] = useState([]);
    const [instanceOrgTypeOptions, setInstanceOrgTypeOptions] = useState([]);

    // Pagination state
    const [currentPage, setCurrentPage] = useState(1);
    const [itemsPerPage, setItemsPerPage] = useState(15);
    const [jumpToPage, setJumpToPage] = useState('');

    // Fetch data
    useEffect(() => {
        fetch('http://localhost:8000/mapping-dashboard/')
            .then(response => {
                if (!response.ok) {
                    throw new Error('fail to connect server');
                }
                return response.json();
            })
            .then(jsonData => {
                setData(jsonData);
                setFilteredData(jsonData);
                extractFilterOptions(jsonData);
                setLoading(false);
            })
            .catch(err => {
                setError(err.message);
                setLoading(false);
            });
    }, []);

    // Extract filter options
    const extractFilterOptions = (data) => {
        const goSet = new Set();
        const pfSet = new Set();
        const orgTypeSet = new Set();

        data.forEach(item => {
            goSet.add(item.global_org_name);
            item.mappings.forEach(mapping => {
                if (mapping.fund_name) {
                    pfSet.add(mapping.fund_name);
                }
                if (mapping.instance_org_type) {
                    orgTypeSet.add(mapping.instance_org_type);
                }
            });
        });

        setGoOptions([...goSet].sort());
        setPoolFundOptions([...pfSet].sort());
        setInstanceOrgTypeOptions([...orgTypeSet].sort());
    };

    const getRiskFromPercent = (percent) => {
        if (percent === null || percent === undefined) return null;
        if (percent >= 85) return 'LOW';
        if (percent >= 60) return 'MEDIUM';
        return 'HIGH';
    };

    const getRiskClass = (percent) => {
        if (percent === null) return 'risk-none';
        if (percent >= 85) return 'risk-low';
        if (percent >= 60) return 'risk-medium';
        return 'risk-high';
    };

    const getRiskLevel = (percent) => {
        return getRiskFromPercent(percent) || '—';
    };

    // Apply filters
    useEffect(() => {
        if (!data.length) return;

        const filtered = data.map(goItem => {
            // Filter Global Org
            if (goFilter && goItem.global_org_name !== goFilter) {
                return null;
            }

            // Filter mappings under this GO
            const filteredMappings = goItem.mappings.filter(mapping => {
                // Filter PoolFund
                if (poolFundFilter && mapping.fund_name !== poolFundFilter) {
                    return false;
                }

                // Filter Risk (derive from match_percent to handle null risk_level)
                if (riskFilter) {
                    const computedRisk = getRiskFromPercent(mapping.match_percent);
                    if (computedRisk !== riskFilter) {
                        return false;
                    }
                }

                // Filter Instance Org Type
                if (instanceOrgTypeFilter && mapping.instance_org_type !== instanceOrgTypeFilter) {
                    return false;
                }

                return true;
            });

            // Return null if no mappings match the criteria AND filters are applied
            // If no filters are applied, show all GOs even without mappings
            if (filteredMappings.length === 0 && (poolFundFilter || riskFilter || instanceOrgTypeFilter)) {
                return null;
            }

            return {
                ...goItem,
                mappings: filteredMappings
            };
        }).filter(item => item !== null);

        setFilteredData(filtered);
        setCurrentPage(1); // Reset to first page when filter changes
    }, [goFilter, poolFundFilter, riskFilter, instanceOrgTypeFilter, data]);

    // Calculate real mapping records (excluding empty GOs)
    const realMappingRecords = filteredData.reduce((total, goItem) => {
        return total + goItem.mappings.length;
    }, 0);

    // Flatten data to mapping record array (for pagination)
    // Include GOs without mappings as well (for display purposes)
    const flattenedData = filteredData.flatMap(goItem => {
        if (goItem.mappings.length === 0) {
            // GO without mappings - show as single row with empty mapping
            return [{
                goItem,
                mapping: null
            }];
        }
        return goItem.mappings.map(mapping => ({
            goItem,
            mapping
        }));
    });

    // Calculate pagination (based on display rows, including empty GOs)
    const totalRecords = flattenedData.length;
    const totalPages = Math.ceil(totalRecords / itemsPerPage);
    const startIndex = (currentPage - 1) * itemsPerPage;
    const endIndex = startIndex + itemsPerPage;
    const currentPageData = flattenedData.slice(startIndex, endIndex);

    // Reorganize current page data to grouped format
    const groupedPageData = currentPageData.reduce((acc, { goItem, mapping }) => {
        const lastGroup = acc[acc.length - 1];
        if (lastGroup && lastGroup.global_org_id === goItem.global_org_id) {
            lastGroup.mappings.push(mapping);
        } else {
            acc.push({
                global_org_id: goItem.global_org_id,
                global_org_name: goItem.global_org_name,
                global_acronym: goItem.global_acronym,
                mappings: [mapping]  // mapping can be null for GOs without mappings
            });
        }
        return acc;
    }, []);

    // Pagination control functions
    const handlePageChange = (page) => {
        if (page >= 1 && page <= totalPages) {
            setCurrentPage(page);
            window.scrollTo({ top: 0, behavior: 'smooth' });
        }
    };

    const handleItemsPerPageChange = (e) => {
        const newItemsPerPage = parseInt(e.target.value);
        setItemsPerPage(newItemsPerPage);
        setCurrentPage(1); // Reset to first page
    };

    const handleJumpToPage = () => {
        const page = parseInt(jumpToPage);
        if (page >= 1 && page <= totalPages) {
            setCurrentPage(page);
            setJumpToPage('');
            window.scrollTo({ top: 0, behavior: 'smooth' });
        } else {
            alert(`Please enter a page number between 1 and ${totalPages}`);
        }
    };

    // Export filtered data to CSV
    const exportToCSV = () => {
        const headers = [
            'Global_OrgName',
            'Global_Acronym',
            'Global_OrgId',
            'Instance_Org_Name',
            'Instance_Org_Acronym',
            'Instance_Org_Type',
            'InstanceOrgId',
            'ParentOrgId',
            'Match%',
            'Risk',
            'PoolFundID',
            'PoolFundName',
            'Status'
        ];

        const escapeCSV = (value) => {
            if (value === null || value === undefined) return '';
            const str = String(value);
            if (str.includes(',') || str.includes('"') || str.includes('\n')) {
                return `"${str.replace(/"/g, '""')}"`;
            }
            return str;
        };

        const rows = [];
        filteredData.forEach(goItem => {
            if (goItem.mappings.length === 0) {
                rows.push([
                    escapeCSV(goItem.global_org_name),
                    escapeCSV(goItem.global_acronym),
                    escapeCSV(goItem.global_org_id),
                    '', '', '', '', '', '', '', '', '', ''
                ].join(','));
            } else {
                goItem.mappings.forEach(mapping => {
                    rows.push([
                        escapeCSV(goItem.global_org_name),
                        escapeCSV(goItem.global_acronym),
                        escapeCSV(goItem.global_org_id),
                        escapeCSV(mapping.instance_org_name),
                        escapeCSV(mapping.instance_org_acronym),
                        escapeCSV(mapping.instance_org_type),
                        escapeCSV(mapping.instance_org_id),
                        escapeCSV(mapping.parent_instance_org_id),
                        mapping.match_percent !== null && mapping.match_percent !== undefined
                            ? `${mapping.match_percent.toFixed(0)}%` : '',
                        escapeCSV(getRiskFromPercent(mapping.match_percent)),
                        escapeCSV(mapping.fund_id),
                        escapeCSV(mapping.fund_name),
                        escapeCSV(mapping.status)
                    ].join(','));
                });
            }
        });

        const csvContent = '\uFEFF' + headers.join(',') + '\n' + rows.join('\n');
        const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
        const url = URL.createObjectURL(blob);
        const link = document.createElement('a');
        link.href = url;

        const now = new Date();
        const timestamp = now.toISOString().slice(0, 19).replace(/[T:]/g, '-');
        const filterInfo = [
            goFilter && `GO-${goFilter}`,
            poolFundFilter && `Fund-${poolFundFilter}`,
            riskFilter && `Risk-${riskFilter}`,
            instanceOrgTypeFilter && `Type-${instanceOrgTypeFilter}`
        ].filter(Boolean).join('_');

        link.download = `GO_Mapping_Dashboard_${timestamp}${filterInfo ? '_' + filterInfo : ''}.csv`;
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        URL.revokeObjectURL(url);
    };

    if (loading) {
        return (
            <div className='mapping-dashboard-container'>
                <div className='mapping-dashboard-content'>
                    <div className='loading'>loading...</div>
                </div>
            </div>
        );
    }

    if (error) {
        return (
            <div className='mapping-dashboard-container'>
                <div className='mapping-dashboard-content'>
                    <div className='error'>error: {error}</div>
                </div>
            </div>
        );
    }

    return (
        <div className='mapping-dashboard-container'>
            <div className='mapping-dashboard-content'>
                <div className='dashboard-header'>
                    <div className='header-top-row'>
                        <button
                            className='back-button'
                            onClick={() => navigate('/')}
                        >
                            ← return Summary
                        </button>
                        <button
                            className='export-csv-button'
                            onClick={exportToCSV}
                            disabled={filteredData.length === 0}
                            title='Export current filtered data to CSV file'
                        >
                            📥 Export to CSV
                        </button>
                    </div>
                    <h1>🗺️ GO Mapping Matrix Dashboard</h1>
                    <p>mapping dashboard</p>
                </div>

                {/* Filter section */}
                <div className='filter-section'>
                    <div className='filter-item'>
                        <label>filter Global Org:</label>
                        <select
                            value={goFilter}
                            onChange={(e) => setGoFilter(e.target.value)}
                            className='filter-select'
                        >
                            <option value="">all</option>
                            {goOptions.map(opt => (
                                <option key={opt} value={opt}>{opt}</option>
                            ))}
                        </select>
                    </div>

                    <div className='filter-item'>
                        <label>filter PoolFund (Country):</label>
                        <select
                            value={poolFundFilter}
                            onChange={(e) => setPoolFundFilter(e.target.value)}
                            className='filter-select'
                        >
                            <option value="">all</option>
                            {poolFundOptions.map(opt => (
                                <option key={opt} value={opt}>{opt}</option>
                            ))}
                        </select>
                    </div>

                    <div className='filter-item'>
                        <label>filter Risk:</label>
                        <select
                            value={riskFilter}
                            onChange={(e) => setRiskFilter(e.target.value)}
                            className='filter-select'
                        >
                            <option value="">all</option>
                            <option value="LOW">LOW</option>
                            <option value="MEDIUM">MEDIUM</option>
                            <option value="HIGH">HIGH</option>
                        </select>
                    </div>
                    <div className='filter-item'>
                        <label>Filter Instance Organization Type:</label>
                        <select
                            value={instanceOrgTypeFilter}
                            onChange={(e) => setInstanceOrgTypeFilter(e.target.value)}
                            className='filter-select'
                        >
                            <option value="">All</option>
                            {instanceOrgTypeOptions.map(opt => (
                                <option key={opt} value={opt}>{opt}</option>
                            ))}
                        </select>
                    </div>
                </div>

                {/* Data table */}
                <div className='table-wrapper'>
                    <table className="dashboard-table">
                        <thead>
                            <tr>
                                <th>Global_OrgName</th>
                                <th>Global_Acronym</th>
                                <th>Global_OrgId</th>
                                <th>Instance_Org_Name</th>
                                <th>Instance_Org_Acronym</th>
                                <th>Instance_Org_Type</th>
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
                            {groupedPageData.length === 0 ? (
                                <tr>
                                    <td colSpan="13" className="no-data">no data</td>
                                </tr>
                            ) : (
                                groupedPageData.map((goItem) => (
                                    goItem.mappings.map((mapping, idx) => {
                                        const isFirstRow = idx === 0;
                                        const isLastRow = idx === goItem.mappings.length - 1;
                                        const rowClass = `${isFirstRow ? 'group-first-row' : ''} ${isLastRow ? 'group-last-row' : ''} group-member-row`.trim();

                                        return (
                                            <tr
                                                key={`${goItem.global_org_id}-${idx}-${mapping ? `${mapping.instance_org_id}-${mapping.fund_id}` : 'empty'}`}
                                                className={rowClass}
                                            >
                                                {idx === 0 && (
                                                    <>
                                                        <td
                                                            rowSpan={goItem.mappings.length}
                                                            className='group-head'
                                                        >
                                                            {goItem.global_org_name}
                                                        </td>
                                                        <td
                                                            rowSpan={goItem.mappings.length}
                                                            className='group-head'
                                                        >
                                                            {goItem.global_acronym || '—'}
                                                        </td>
                                                        <td
                                                            rowSpan={goItem.mappings.length}
                                                            className='group-head'
                                                        >
                                                            {goItem.global_org_id}
                                                        </td>
                                                    </>
                                                )}
                                                {mapping ? (
                                                    <>
                                                        <td>{mapping.instance_org_name}</td>
                                                        <td>{mapping.instance_org_acronym || '—'}</td>
                                                        <td>{mapping.instance_org_type || '—'}</td>
                                                        <td>{mapping.instance_org_id || '—'}</td>
                                                        <td>{mapping.parent_instance_org_id || 'NULL'}</td>
                                                        <td className={getRiskClass(mapping.match_percent)}>
                                                            {mapping.match_percent !== null
                                                                ? `${mapping.match_percent.toFixed(0)}%`
                                                                : '—'}
                                                        </td>
                                                        <td className={getRiskClass(mapping.match_percent)}>
                                                            {getRiskLevel(mapping.match_percent)}
                                                        </td>
                                                        <td>{mapping.fund_id || '—'}</td>
                                                        <td>{mapping.fund_name || '—'}</td>
                                                        <td>
                                                            <span className={`status-badge status-${(mapping.status || '').toLowerCase().replace(/\s+/g, '-')}`}>
                                                                {mapping.status || '—'}
                                                            </span>
                                                        </td>
                                                    </>
                                                ) : (
                                                    <>
                                                        <td colSpan="10" className="no-data" style={{ textAlign: 'center', fontStyle: 'italic', color: '#999' }}>
                                                            No mappings available for this Global Organization
                                                        </td>
                                                    </>
                                                )}
                                            </tr>
                                        );
                                    })
                                ))
                            )}
                        </tbody>
                    </table>
                </div>

                {/* Pagination controls */}
                {totalRecords > 0 && (
                    <div className='pagination-container'>
                        <div className='pagination-info'>
                            <span>
                                Showing {startIndex + 1} to {Math.min(endIndex, totalRecords)} of {totalRecords} rows
                                <span style={{ color: '#999', marginLeft: '8px' }}>
                                    ({realMappingRecords} real mappings)
                                </span>
                            </span>
                        </div>

                        <div className='pagination-controls'>
                            {/* Items per page selection */}
                            <div className='items-per-page'>
                                <label>Items per page:</label>
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

                            {/* Page navigation buttons */}
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

                            {/* Jump to specific page */}
                            <div className='jump-to-page'>
                                <label>Go to page:</label>
                                <input
                                    type='number'
                                    min='1'
                                    max={totalPages}
                                    value={jumpToPage}
                                    onChange={(e) => setJumpToPage(e.target.value)}
                                    onKeyPress={(e) => e.key === 'Enter' && handleJumpToPage()}
                                    className='page-input'
                                    placeholder='#'
                                />
                                <button
                                    onClick={handleJumpToPage}
                                    className='page-btn jump-btn'
                                >
                                    Go
                                </button>
                            </div>
                        </div>
                    </div>
                )}

                <div className='summary-footer'>
                    <p>Total: <strong>{filteredData.length}</strong> global organizations，
                        <strong>{realMappingRecords}</strong> real mapping records
                        {totalRecords !== realMappingRecords && (
                            <span style={{ color: '#999', fontSize: '0.9rem', marginLeft: '10px' }}>
                                ({totalRecords - realMappingRecords} GOs without mappings)
                            </span>
                        )}
                    </p>
                </div>
            </div>
        </div>
    );
}

export default MappingDashboard;

