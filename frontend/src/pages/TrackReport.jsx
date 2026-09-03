import { useState, useEffect } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import { fetchReport } from '../services/api';

// Utility for readable timestamps
const formatRelativeTime = (timestamp) => {
  if (!timestamp) return 'Unknown time';
  const date = new Date(timestamp.endsWith('Z') ? timestamp : timestamp + 'Z');
  const now = new Date();
  const diffMs = now - date;
  const diffMins = Math.floor(diffMs / 60000);
  const diffHours = Math.floor(diffMins / 60);
  
  if (diffMins < 2) return 'Just now';
  if (diffMins < 60) return `${diffMins} min ago`;
  if (diffHours < 24) return `${diffHours} hour${diffHours > 1 ? 's' : ''} ago`;
  
  // Check if yesterday
  const yesterday = new Date(now);
  yesterday.setDate(yesterday.getDate() - 1);
  if (date.getDate() === yesterday.getDate() && date.getMonth() === yesterday.getMonth() && date.getFullYear() === yesterday.getFullYear()) {
    return `Yesterday, ${date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}`;
  }
  
  return date.toLocaleString('en-GB', {
    day: '2-digit', month: 'short', year: 'numeric',
    hour: '2-digit', minute: '2-digit', hour12: true
  });
};

const mapStatusToCitizen = (report) => {
  if (!report.incident_id) return 'SUBMITTED';
  
  if (report.verification_status === 'Resolved') return 'RESOLVED';
  
  switch (report.human_status) {
    case 'Verified': return 'VERIFIED';
    case 'Rejected': return 'REJECTED';
    case 'Needs More Evidence': return 'ESCALATED';
    default: return 'UNDER REVIEW';
  }
};

function TrackReport() {
  const [searchParams, setSearchParams] = useSearchParams();
  const initialId = searchParams.get('id') || '';
  
  const [reportIdInput, setReportIdInput] = useState(initialId);
  const [reportData, setReportData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const loadReport = async (idToLoad) => {
    if (!idToLoad || !idToLoad.trim()) return;
    
    setLoading(true);
    setError(null);
    setReportData(null);
    
    try {
      // Basic normalization
      let formattedId = idToLoad.trim().toUpperCase();
      if (!formattedId.startsWith('RPT-')) {
        // Just in case user types the raw ID part
        if (formattedId.length > 5 && !formattedId.includes('-')) {
          formattedId = `RPT-${formattedId}`;
        }
      }
      
      const data = await fetchReport(formattedId);
      setReportData(data);
      // Update URL silently
      setSearchParams({ id: formattedId }, { replace: true });
    } catch (err) {
      if (err.status === 404 || err.detail === 'Report not found') {
        setError(`No report found for ${idToLoad}`);
      } else {
        setError('Failed to fetch report details. Please try again.');
      }
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (initialId) {
      loadReport(initialId);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const handleSearch = (e) => {
    e.preventDefault();
    if (reportIdInput.trim()) {
      loadReport(reportIdInput);
    }
  };

  const renderTimeline = () => {
    if (!reportData) return null;
    
    const currentStatus = mapStatusToCitizen(reportData);
    
    // Define steps
    const stepSubmitted = {
      label: 'Report Submitted',
      description: 'Report received successfully',
      date: reportData.created_at,
      completed: true,
      active: currentStatus === 'SUBMITTED'
    };
    
    const stepReview = {
      label: 'Under Review',
      description: reportData.incident_id ? 'Municipal team is reviewing the report' : 'Awaiting team assignment',
      date: reportData.incident_id ? reportData.created_at : null,
      completed: !!reportData.incident_id,
      active: currentStatus === 'UNDER REVIEW'
    };
    
    let decisionCompleted = false;
    let decisionLabel = 'Officer Decision';
    let decisionDesc = 'Pending responder verification';
    
    if (['VERIFIED', 'REJECTED', 'ESCALATED'].includes(currentStatus)) {
      decisionCompleted = true;
      if (currentStatus === 'VERIFIED') {
        decisionLabel = 'Verified';
        decisionDesc = 'Report verified by field officer';
      } else if (currentStatus === 'REJECTED') {
        decisionLabel = 'Rejected';
        decisionDesc = 'Report rejected by field officer';
      } else {
        decisionLabel = 'Escalated';
        decisionDesc = 'Report escalated for further attention';
      }
    }
    
    const stepDecision = {
      label: decisionLabel,
      description: decisionDesc,
      date: decisionCompleted ? reportData.incident_updated_at : null,
      completed: decisionCompleted,
      active: ['VERIFIED', 'REJECTED', 'ESCALATED'].includes(currentStatus)
    };
    
    const stepResolved = {
      label: 'Resolved',
      description: currentStatus === 'RESOLVED' ? 'Issue has been resolved' : 'Pending',
      date: currentStatus === 'RESOLVED' ? reportData.incident_updated_at : null,
      completed: currentStatus === 'RESOLVED',
      active: currentStatus === 'RESOLVED'
    };

    const steps = [stepSubmitted, stepReview, stepDecision, stepResolved];

    return (
      <div className="status-timeline">
        {steps.map((step, index) => (
          <div key={index} className={`timeline-item ${step.completed ? 'completed' : ''} ${step.active ? 'active' : ''}`}>
            <div className="timeline-marker">
              <div className="timeline-dot">{step.completed ? '✓' : ''}</div>
              {index < steps.length - 1 && <div className="timeline-line"></div>}
            </div>
            <div className="timeline-content">
              <div className="timeline-label">{step.label}</div>
              <div className="timeline-desc">{step.description}</div>
              {step.date && <div className="timeline-date">{formatRelativeTime(step.date)}</div>}
            </div>
          </div>
        ))}
      </div>
    );
  };

  return (
    <div className="dashboard-layout citizen-track-page">
      {/* HEADER */}
      <header className="dashboard-header">
        <div className="municipality-brand">
          <div className="crest-icon">🏛️</div>
          <div>
            <div className="header-title">Citizen Service Portal</div>
            <div className="header-subtitle">Municipality Crowd Verification</div>
          </div>
        </div>
        <nav className="header-nav">
          <Link className="nav-btn" to="/">Home</Link>
          <Link className="nav-btn" to="/report">Report an Issue</Link>
          <Link className="nav-btn active" to="/track">Track Report</Link>
          <Link className="nav-btn" to="/dashboard">Officer Dashboard</Link>
        </nav>
      </header>

      <main className="dashboard-content">
        <div className="citizen-portal-card track-card-container">
          
          <div className="hero-heading-row" style={{ marginBottom: '24px' }}>
            <div>
              <h1 className="hero-main-title">Track Your Report</h1>
              <p className="hero-sub-text">
                Enter your Report ID to view the latest status of your municipal issue.
              </p>
            </div>
          </div>

          <form onSubmit={handleSearch} className="track-search-form">
            <div className="search-input-group">
              <input
                type="text"
                placeholder="e.g. RPT-432B1077F015"
                value={reportIdInput}
                onChange={(e) => setReportIdInput(e.target.value)}
                className="track-search-input"
              />
              <button type="submit" className="btn-track-search" disabled={loading || !reportIdInput.trim()}>
                {loading ? 'Searching...' : 'Track Report'}
              </button>
            </div>
          </form>

          {error && (
            <div className="message-box error-box" style={{ marginTop: '24px', borderRadius: '12px', textAlign: 'center' }}>
              <p style={{ margin: 0, fontWeight: 'bold' }}>{error}</p>
              <p style={{ margin: '8px 0 0', fontSize: '0.9rem' }}>Please check your Report ID and try again.</p>
            </div>
          )}

          {loading && !error && (
            <div className="loading-state" style={{ padding: '40px', textAlign: 'center', color: '#64748b' }}>
              <div className="spinner" style={{ margin: '0 auto 16px', width: '30px', height: '30px', border: '3px solid #e2e8f0', borderTopColor: '#2563eb', borderRadius: '50%', animation: 'spin 1s linear infinite' }}></div>
              Searching for your report...
            </div>
          )}

          {reportData && !loading && !error && (
            <div className="tracking-result-container">
              <div className="tracking-header">
                <h2>Report {reportData.report_id}</h2>
                <span className={`status-badge ${mapStatusToCitizen(reportData).replace(' ', '-').toLowerCase()}`}>
                  {mapStatusToCitizen(reportData)}
                </span>
              </div>
              
              <div className="tracking-layout-grid">
                {/* TIMELINE SIDE */}
                <div className="tracking-timeline-section">
                  <h3 className="section-title">Status Timeline</h3>
                  {renderTimeline()}
                </div>

                {/* DETAILS SIDE */}
                <div className="tracking-details-section">
                  <h3 className="section-title">Report Details</h3>
                  
                  <div className="detail-grid">
                    <div className="detail-item">
                      <div className="detail-label">Issue Type</div>
                      <div className="detail-value">{reportData.issue_type || '-'}</div>
                    </div>
                    <div className="detail-item">
                      <div className="detail-label">Category</div>
                      <div className="detail-value">{reportData.category || '-'}</div>
                    </div>
                    <div className="detail-item">
                      <div className="detail-label">Location / Zone</div>
                      <div className="detail-value">{reportData.zone || 'Unknown'}</div>
                    </div>
                    <div className="detail-item">
                      <div className="detail-label">Reported</div>
                      <div className="detail-value">{formatRelativeTime(reportData.created_at)}</div>
                    </div>
                    <div className="detail-item">
                      <div className="detail-label">Severity</div>
                      <div className="detail-value">{reportData.citizen_severity || '-'}</div>
                    </div>
                    
                    {reportData.incident_id && (
                      <>
                        <div className="detail-item">
                          <div className="detail-label">Priority</div>
                          <div className="detail-value">
                            <span className={`prio-badge prio-${reportData.priority_level?.toLowerCase()}`}>
                              {reportData.priority_level}
                            </span>
                          </div>
                        </div>
                        <div className="detail-item">
                          <div className="detail-label">Verification</div>
                          <div className="detail-value">
                            {reportData.verification_status === 'Pending' ? 'Pending Evidence' : reportData.verification_status}
                          </div>
                        </div>
                      </>
                    )}
                  </div>
                  
                  <div className="detail-item full-width" style={{ marginTop: '16px' }}>
                    <div className="detail-label">Description</div>
                    <div className="detail-value desc-text">{reportData.description || 'No description provided.'}</div>
                  </div>
                </div>
              </div>
            </div>
          )}
          
        </div>
      </main>
    </div>
  );
}

export default TrackReport;
