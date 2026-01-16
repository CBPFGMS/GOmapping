import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import './MappingDashboard.css';

function MappingDashboard() {
    const navigate = useNavigate();
    const [data, setData] = useState([]);
    const [filteredData, setFilteredData] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);

    // 筛选器状态
    const [goFilter, setGoFilter] = useState('');
    const [poolFundFilter, setPoolFundFilter] = useState('');
    const [riskFilter, setRiskFilter] = useState('');

    // 用于下拉选项的唯一值
    const [goOptions, setGoOptions] = useState([]);
    const [poolFundOptions, setPoolFundOptions] = useState([]);

    // 获取数据
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

    // 提取筛选器选项
    const extractFilterOptions = (data) => {
        const goSet = new Set();
        const pfSet = new Set();

        data.forEach(item => {
            goSet.add(item.global_org_name);
            item.mappings.forEach(mapping => {
                if (mapping.fund_name) {
                    pfSet.add(mapping.fund_name);
                }
            });
        });

        setGoOptions([...goSet].sort());
        setPoolFundOptions([...pfSet].sort());
    };

    // 应用筛选
    useEffect(() => {
        if (!data.length) return;

        const filtered = data.map(goItem => {
            // 筛选 Global Org
            if (goFilter && goItem.global_org_name !== goFilter) {
                return null;
            }

            // 筛选该 GO 下的 mappings
            const filteredMappings = goItem.mappings.filter(mapping => {
                // 筛选 PoolFund
                if (poolFundFilter && mapping.fund_name !== poolFundFilter) {
                    return false;
                }

                // 筛选 Risk
                if (riskFilter && mapping.risk_level !== riskFilter) {
                    return false;
                }

                return true;
            });

            // 如果该 GO 没有符合条件的 mapping，返回 null
            if (filteredMappings.length === 0) {
                return null;
            }

            return {
                ...goItem,
                mappings: filteredMappings
            };
        }).filter(item => item !== null);

        setFilteredData(filtered);
    }, [goFilter, poolFundFilter, riskFilter, data]);

    // 获取风险等级样式类
    const getRiskClass = (percent) => {
        if (percent === null) return 'risk-none';
        if (percent >= 85) return 'risk-low';
        if (percent >= 60) return 'risk-medium';
        return 'risk-high';
    };

    // 获取风险等级文本
    const getRiskLevel = (riskLevel) => {
        return riskLevel || '—';
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
                    <button
                        className='back-button'
                        onClick={() => navigate('/')}
                    >
                        ← return Summary
                    </button>
                    <h1>🗺️ GO Mapping Matrix Dashboard</h1>
                    <p>mapping dashboard</p>
                </div>

                {/* 筛选器区域 */}
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
                </div>

                {/* 数据表格 */}
                <div className='table-wrapper'>
                    <table className="dashboard-table">
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
                            {filteredData.length === 0 ? (
                                <tr>
                                    <td colSpan="12" className="no-data">no data</td>
                                </tr>
                            ) : (
                                filteredData.map((goItem) => (
                                    goItem.mappings.map((mapping, idx) => (
                                        <tr key={`${goItem.global_org_id}-${mapping.instance_org_id || idx}`}>
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
                                ))
                            )}
                        </tbody>
                    </table>
                </div>

                <div className='summary-footer'>
                    <p>shows <strong>{filteredData.length}</strong> global orgnizations，
                        <strong>
                            {filteredData.reduce((sum, item) => sum + item.mappings.length, 0)}
                        </strong> mapping records in total
                    </p>
                </div>
            </div>
        </div>
    );
}

export default MappingDashboard;

