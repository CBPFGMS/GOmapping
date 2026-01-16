import { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import './GODetail.css';

function GODetail() {
    const { goId } = useParams();
    const navigate = useNavigate();
    const [goInfo, setGoInfo] = useState(null);
    const [similarGOs, setSimilarGOs] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);

    useEffect(() => {
        // Call backend API to fetch similar GOs
        fetch(`http://localhost:8000/api/go-detail/${goId}/`)
            .then(response => {
                if (!response.ok) {
                    throw new Error('Failed to fetch data');
                }
                return response.json();
            })
            .then(data => {
                setGoInfo(data.go_info);
                setSimilarGOs(data.similar_gos);
                setLoading(false);
            })
            .catch(err => {
                setError(err.message);
                setLoading(false);
            });
    }, [goId]);

    if (loading) {
        return (
            <div className='go-detail-container'>
                <div className='go-detail-content'>
                    <div className='loading'>Loading data...</div>
                </div>
            </div>
        );
    }
    
    if (error) {
        return (
            <div className='go-detail-container'>
                <div className='go-detail-content'>
                    <div className='error'>Error: {error}</div>
                </div>
            </div>
        );
    }

    return (
        <div className='go-detail-container'>
            <div className='go-detail-content'>
                <div className='detail-header'>
                    <h1>Scenario 1 — GO Mapping</h1>
                    <h2>GO Detail — similar GOs with "{goInfo?.name}"</h2>
                </div>
                
                <div className='table-wrapper'>
                    <table className='detail-table'>
                        <thead>
                            <tr>
                                <th>GO Name</th>
                                <th>Similarity (%)</th>
                                <th>Mapping Count</th>
                            </tr>
                        </thead>
                        <tbody>
                            {similarGOs.map((row, index) => (
                                <tr key={index}>
                                    <td>{row.go_name}</td>
                                    <td className='similarity-cell'>{row.similarity}%</td>
                                    <td>
                                        <span 
                                            className='link-text'
                                            onClick={() => navigate(`/org-mappings/${row.go_id}`)}
                                        >
                                            {row.mapping_count}
                                        </span>
                                    </td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                </div>

                <div className='back-btn' onClick={() => navigate('/')}>
                    ← Back to Summary
                </div>
            </div>
        </div>
    );
}

export default GODetail;

