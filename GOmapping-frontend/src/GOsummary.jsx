import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import './GOSummary.css';

function GOsummary() {
    const [data, setData] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);
    const navigate = useNavigate();

    useEffect(() => {
        fetch('http://localhost:8000/go-summary/')
            .then(response => {
                if (!response.ok) {
                    throw new Error('fail to connect server');
                }
                return response.json();
            })
            .then(jsonData => {
                setData(jsonData);
                setLoading(false);
            })
            .catch(err => {
                setError(err.message);
                setLoading(false);
            });
    }, []);

    // 相似度样式类
    const getSimilarityClass = (percent) => {
        if (percent === null) return 'similarity-none';
        if (percent >= 85) return 'similarity-high';
        if (percent >= 70) return 'similarity-medium';
        return 'similarity-low';
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
            <div className='summary-header'>
                <h1>🌍 Global Organization Mapping Summary</h1>
            </div>

            <div className='table-wrapper'>
                <table className="gotable">
                    <thead>
                        <tr>
                            <th>Global_OrgId</th>
                            <th>Global_OrgName</th>
                            <th>Usage Count</th>
                            <th>Most Similar GO</th>
                            <th>Similarity (%)</th>
                        </tr>
                    </thead>
                    <tbody>
                        {data.map((row) => (
                            <tr key={row.global_org_id}>
                                <td>{row.global_org_id}</td>
                                <td>
                                    <span
                                        className='link-text'
                                        onClick={() => handleGONameClick(row.global_org_id)}
                                    >
                                        {row.global_org_name}
                                    </span>
                                </td>
                                <td>
                                    <span
                                        className='usage-badge clickable'
                                        onClick={() => handleUsageCountClick(row.global_org_id)}
                                    >
                                        {row.usage_count}
                                    </span>
                                </td>
                                <td>{row.most_similar_go || '—'}</td>
                                <td className={getSimilarityClass(row.similarity_percent)}>
                                    {row.similarity_percent !== null
                                        ? `${row.similarity_percent}%`
                                        : '—'}
                                </td>
                            </tr>
                        ))}
                    </tbody>
                </table>
            </div>
        </div>
    );
}
export default GOsummary;