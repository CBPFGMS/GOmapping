import { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import './OrgMappings.css';

function OrgMappings() {
    const { goId } = useParams();
    const navigate = useNavigate();
    const [goInfo, setGoInfo] = useState(null);
    const [organizations, setOrganizations] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);

    useEffect(() => {
        // 调用后端 API 获取 instance organizations
        fetch(`http://localhost:8000/api/org-mappings/${goId}/`)
            .then(response => {
                if (!response.ok) {
                    throw new Error('无法获取数据');
                }
                return response.json();
            })
            .then(data => {
                setGoInfo(data.go_info);
                setOrganizations(data.organizations);
                setLoading(false);
            })
            .catch(err => {
                setError(err.message);
                setLoading(false);
            });
    }, [goId]);

    // 相似度样式类
    const getSimilarityClass = (percent) => {
        if (percent === null) return 'similarity-none';
        if (percent >= 85) return 'similarity-high';
        if (percent >= 70) return 'similarity-medium';
        return 'similarity-low';
    };

    if (loading) {
        return (
            <div className='org-mappings-container'>
                <div className='org-mappings-content'>
                    <div className='loading'>正在加载数据...</div>
                </div>
            </div>
        );
    }
    
    if (error) {
        return (
            <div className='org-mappings-container'>
                <div className='org-mappings-content'>
                    <div className='error'>错误: {error}</div>
                </div>
            </div>
        );
    }

    return (
        <div className='org-mappings-container'>
            <div className='org-mappings-content'>
                <div className='mappings-header'>
                    <h1>Scenario 1 — GO Mapping</h1>
                    <h2>GO Mappings: {goInfo?.name}</h2>
                </div>
                
                <div className='table-wrapper'>
                    <table className='mappings-table'>
                        <thead>
                            <tr>
                                <th>Org ID</th>
                                <th>Organization Name</th>
                                <th>Org_Acronym</th>
                                <th>PoolFund</th>
                                <th>Similarity to GO (%)</th>
                            </tr>
                        </thead>
                        <tbody>
                            {organizations.map((org) => (
                                <tr key={org.org_id}>
                                    <td>{org.org_id}</td>
                                    <td className='org-name'>{org.org_name}</td>
                                    <td>{org.acronym}</td>
                                    <td>{org.poolfund}</td>
                                    <td className={getSimilarityClass(org.similarity)}>
                                        {org.similarity}%
                                    </td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                </div>

                <div className='back-btn' onClick={() => navigate(-1)}>
                    ← Back to GO Detail
                </div>
            </div>
        </div>
    );
}

export default OrgMappings;

