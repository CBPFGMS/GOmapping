import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import './GOSummary.css';

function GOsummary() {
    const [data, setData] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);
    const navigate = useNavigate();

    // Pagination state
    const [currentPage, setCurrentPage] = useState(1);
    const [itemsPerPage, setItemsPerPage] = useState(15);
    const [jumpToPage, setJumpToPage] = useState('');

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

    // Similarity style class
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

    // Calculate pagination
    const totalRecords = data.length;
    const totalPages = Math.ceil(totalRecords / itemsPerPage);
    const startIndex = (currentPage - 1) * itemsPerPage;
    const endIndex = startIndex + itemsPerPage;
    const currentPageData = data.slice(startIndex, endIndex);

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
                            {currentPageData.map((row) => (
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

                {/* Pagination controls */}
                {totalRecords > 0 && (
                    <div className='pagination-container'>
                        <div className='pagination-info'>
                            <span>
                                Showing {startIndex + 1} to {Math.min(endIndex, totalRecords)} of {totalRecords} records
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
            </div>
        </div>
    );
}
export default GOsummary;