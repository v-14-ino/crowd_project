import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { formatRelativeTime } from '../utils/dateFormatter';

export default function RecentReports() {
  const [reports, setReports] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    fetchRecentReports();
    // Poll every 30s
    const interval = setInterval(fetchRecentReports, 30000);
    return () => clearInterval(interval);
  }, []);

  const fetchRecentReports = async () => {
    try {
      const res = await fetch('http://localhost:8000/api/reports/recent?limit=5');
      if (!res.ok) throw new Error('Failed to fetch recent reports');
      const data = await res.json();
      setReports(data);
      setError(null);
    } catch (err) {
      console.error(err);
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const getStatusBadge = (report) => {
    // Phase 4C: map to existing workflow statuses
    const status = report.human_status || report.verification_status || 'Pending';
    
    // Convert to citizen view
    let citizenStatus = 'UNDER REVIEW';
    if (status === 'Verified') citizenStatus = 'VERIFIED';
    else if (status === 'Rejected') citizenStatus = 'REJECTED';
    else if (status === 'Needs More Evidence') citizenStatus = 'ESCALATED';
    else if (status === 'Resolved') citizenStatus = 'RESOLVED';

    const statusClass = citizenStatus.toLowerCase().replace(' ', '-');
    return <span className={`status-pill ${statusClass}`}>{citizenStatus}</span>;
  };

  if (loading && reports.length === 0) {
    return (
      <div className="recent-reports-citizen">
        <h3>Recent Reports</h3>
        <p>Loading newest reports...</p>
      </div>
    );
  }

  if (error && reports.length === 0) {
    return (
      <div className="recent-reports-citizen">
        <h3>Recent Reports</h3>
        <p>Could not load reports.</p>
      </div>
    );
  }

  return (
    <div className="recent-reports-citizen">
      <h3>Recent Reports</h3>
      <div className="recent-reports-list">
        {reports.map((report) => (
          <div key={report.report_id} className="citizen-report-card">
            <div className="citizen-report-header">
              <span className="citizen-report-id">{report.report_id}</span>
              {getStatusBadge(report)}
            </div>
            
            <div className="citizen-report-details">
              <strong>{report.category}</strong> - {report.issue_type}
            </div>
            
            <div className="citizen-report-location">
              📍 {report.zone || 'Unassigned Zone'}
            </div>
            
            <div className="citizen-report-meta">
              <span>Submitted {formatRelativeTime(report.created_at || report.reported_time)}</span>
              {report.priority_level && (
                <span className={`priority-tag ${report.priority_level.toLowerCase()}`}>
                  {report.priority_level} Priority
                </span>
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
