import React, { useState } from 'react';
import { Link } from 'react-router-dom';

import { formatRelativeTime } from '../utils/dateFormatter';

function getVerificationBadge(status) {
  switch (status) {
    case 'Verified':
      return <span className="status-pill verified">✅ Verified</span>;
    case 'Corroborated':
      return <span className="status-pill corroborated">👥 Corroborated</span>;
    case 'Conflicted':
      return <span className="status-pill conflicted">⚡ Conflicted</span>;
    case 'Rejected':
      return <span className="status-pill rejected">❌ Rejected</span>;
    case 'Unknown':
      return <span className="status-pill unknown">❓ Unknown</span>;
    default:
      return <span className="status-pill pending">⏳ Pending</span>;
  }
}

function getPriorityBadge(score, level) {
  if (score === null || score === undefined) return <span className="priority-tag-empty">Unscored</span>;
  const lvlClass = (level || 'low').toLowerCase();
  return (
    <span className={`priority-tag ${lvlClass}`}>
      {level || 'Priority'} ({score})
    </span>
  );
}

function getFreshnessBadge(freshness) {
  switch (freshness) {
    case 'Fresh':
      return <span className="freshness-badge fresh">🟢 Fresh</span>;
    case 'Aging':
      return <span className="freshness-badge aging">🟡 Aging</span>;
    case 'Stale':
      return <span className="freshness-badge stale">🔴 Stale</span>;
    default:
      return <span className="freshness-badge unknown">⚪ Unknown</span>;
  }
}

export default function RecentReportsSection({
  recentReports,
  loading,
  lastPollTime,
  onRefresh,
  previousPollTime,
}) {
  const [selectedReport, setSelectedReport] = useState(null);

  return (
    <div className="recent-reports-panel">
      <div className="recent-reports-header">
        <div className="recent-header-left">
          <div className="section-title-row">
            <span className="live-dot" title="Live automatic polling active"></span>
            <h2 className="section-title">📡 Recent Citizen Reports (Live Feed)</h2>
            <span className="polling-tag">Auto-refresh: 12s</span>
          </div>
          <p className="section-subtitle">
            Chronological stream of new citizen reports. Monitored for clustering and automated correlation.
          </p>
        </div>

        <div className="recent-header-right">
          <button
            className="btn-refresh-feed"
            onClick={onRefresh}
            title="Refresh recent citizen reports now"
          >
            🔄 Refresh Feed
          </button>
        </div>
      </div>

      {loading && (!recentReports || recentReports.length === 0) ? (
        <div className="recent-reports-grid skeleton-grid">
          {Array.from({ length: 4 }).map((_, i) => (
            <div key={i} className="recent-report-card skeleton">
              <div className="sk-line title"></div>
              <div className="sk-line text"></div>
              <div className="sk-line badge"></div>
            </div>
          ))}
        </div>
      ) : !recentReports || recentReports.length === 0 ? (
        <div className="recent-reports-empty">
          <span className="empty-icon">📭</span>
          <h4>No recent reports found</h4>
          <p>No citizen reports have been recorded in the database yet.</p>
        </div>
      ) : (
        <div className="recent-reports-grid">
          {recentReports.map((item) => {
            const isNew = previousPollTime && item.created_at && new Date(item.created_at) > new Date(previousPollTime);
            const isAttached = item.relationship_type?.startsWith('Attached');
            const isNewInc = item.relationship_type?.startsWith('New Incident');
            const hasCoords = item.latitude !== null && item.longitude !== null;

            return (
              <div
                key={item.report_id}
                className={`recent-report-card ${isNew ? 'new-arrival' : ''}`}
                onClick={() => setSelectedReport(item)}
                role="button"
                tabIndex={0}
              >
                <div className="card-top-row">
                  <div className="report-id-badge">
                    <span className="id-icon">📄</span>
                    <strong>{item.report_id}</strong>
                  </div>
                  <div className="card-top-badges">
                    {isNew && <span className="badge-new-arrival">✨ New</span>}
                    <span className="card-rel-time">{formatRelativeTime(item.created_at || item.reported_time)}</span>
                  </div>
                </div>

                <div className="card-main-info">
                  <div className="card-issue-line">
                    <span className="cat-pill">{item.category || 'General'}</span>
                    <span className="issue-text">{item.issue_type || 'Unspecified issue'}</span>
                  </div>

                  {item.description && (
                    <p className="card-desc-snippet">{item.description}</p>
                  )}
                </div>

                {/* Relationship Tag */}
                <div className="card-relationship-box">
                  {isAttached ? (
                    <span className="rel-tag attached" title={item.relationship_type}>
                      🔗 {item.relationship_type}
                    </span>
                  ) : isNewInc ? (
                    <span className="rel-tag new-inc" title={item.relationship_type}>
                      ✨ {item.relationship_type}
                    </span>
                  ) : (
                    <span className="rel-tag unassigned">
                      ⏳ Awaiting Incident Assignment
                    </span>
                  )}
                </div>

                {/* Metadata & Status Footer */}
                <div className="card-footer-row">
                  <div className="footer-location">
                    <span>📍 {item.zone || 'Unassigned'}</span>
                    <span className="coord-mini">
                      {hasCoords ? `${item.latitude.toFixed(2)}, ${item.longitude.toFixed(2)}` : 'No GPS'}
                    </span>
                  </div>

                  <div className="footer-status">
                    {item.verification_status && getVerificationBadge(item.verification_status)}
                    {item.priority_level && getPriorityBadge(item.priority_score, item.priority_level)}
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* Report Detail Modal */}
      {selectedReport && (
        <div className="modal-backdrop" onClick={() => setSelectedReport(null)}>
          <div className="modal-card report-detail-modal" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <div className="modal-title-row">
                <span className="modal-icon">📄</span>
                <h3>Citizen Report Detail: {selectedReport.report_id}</h3>
              </div>
              <button className="btn-close-modal" onClick={() => setSelectedReport(null)}>
                ×
              </button>
            </div>

            <div className="modal-body">
              {/* Correlation Banner */}
              <div className="modal-relationship-banner">
                <div className="banner-label">Incident Correlation Status:</div>
                <div className="banner-value">
                  {selectedReport.incident_id ? (
                    <span>
                      <strong>{selectedReport.relationship_type}</strong> (Total linked reports: {selectedReport.total_incident_reports || 1})
                    </span>
                  ) : (
                    <span className="unassigned-text">⏳ Awaiting Incident Assignment</span>
                  )}
                </div>
              </div>

              <div className="modal-grid-two-col">
                <div className="modal-info-col">
                  <h4>Report Information</h4>
                  <div className="info-row">
                    <span className="lbl">Report ID:</span>
                    <span className="val font-mono">{selectedReport.report_id}</span>
                  </div>
                  <div className="info-row">
                    <span className="lbl">Category:</span>
                    <span className="val">{selectedReport.category || 'Unknown'}</span>
                  </div>
                  <div className="info-row">
                    <span className="lbl">Issue Type:</span>
                    <span className="val">{selectedReport.issue_type || 'Unknown'}</span>
                  </div>
                  <div className="info-row">
                    <span className="lbl">Citizen Severity:</span>
                    <span className="val">
                      <span className={`severity-tag ${(selectedReport.citizen_severity || 'medium').toLowerCase()}`}>
                        {selectedReport.citizen_severity || 'Unknown'} (Citizen input)
                      </span>
                    </span>
                  </div>
                  <div className="info-row">
                    <span className="lbl">Received Time:</span>
                    <span className="val">
                      {selectedReport.created_at
                        ? new Date(selectedReport.created_at).toLocaleString()
                        : selectedReport.reported_time
                        ? new Date(selectedReport.reported_time).toLocaleString()
                        : 'Unknown'}
                    </span>
                  </div>
                  <div className="info-row">
                    <span className="lbl">Location &amp; Zone:</span>
                    <span className="val">📍 {selectedReport.zone || 'Unknown Zone'}</span>
                  </div>
                  <div className="info-row">
                    <span className="lbl">Coordinates:</span>
                    <span className="val">
                      {selectedReport.latitude !== null && selectedReport.longitude !== null
                        ? `${selectedReport.latitude.toFixed(5)}, ${selectedReport.longitude.toFixed(5)}`
                        : 'Evidence location: Unknown'}
                    </span>
                  </div>
                </div>

                <div className="modal-info-col">
                  <h4>Associated Incident Evaluation</h4>
                  {selectedReport.incident_id ? (
                    <>
                      <div className="info-row">
                        <span className="lbl">Associated Incident:</span>
                        <span className="val font-mono font-bold text-accent">
                          {selectedReport.incident_id}
                        </span>
                      </div>
                      <div className="info-row">
                        <span className="lbl">Canonical Priority:</span>
                        <span className="val">
                          {getPriorityBadge(selectedReport.priority_score, selectedReport.priority_level)}
                        </span>
                      </div>
                      <div className="info-row">
                        <span className="lbl">Confidence Score:</span>
                        <span className="val">
                          {selectedReport.confidence_score !== null
                            ? `${selectedReport.confidence_score}% (${selectedReport.confidence_level || 'Evaluated'})`
                            : 'Unknown'}
                        </span>
                      </div>
                      <div className="info-row">
                        <span className="lbl">Verification Status:</span>
                        <span className="val">
                          {getVerificationBadge(selectedReport.verification_status || 'Pending')}
                        </span>
                      </div>
                      <div className="info-row">
                        <span className="lbl">Freshness Status:</span>
                        <span className="val">
                          {getFreshnessBadge(selectedReport.freshness_status || 'Fresh')}
                        </span>
                      </div>
                    </>
                  ) : (
                    <div className="no-incident-box">
                      <p>This report has not yet been linked to an active incident cluster.</p>
                    </div>
                  )}
                </div>
              </div>

              {/* Full Description */}
              <div className="modal-desc-section">
                <h4>Citizen Description</h4>
                <div className="desc-text-box">
                  {selectedReport.description || 'No detailed description was provided by the citizen.'}
                </div>
              </div>
            </div>

            <div className="modal-footer">
              {selectedReport.incident_id ? (
                <Link
                  to={`/dashboard/${selectedReport.incident_id}`}
                  className="btn-modal-action primary"
                >
                  Inspect Incident {selectedReport.incident_id} →
                </Link>
              ) : (
                <span className="unassigned-note">Awaiting automated spatial correlation</span>
              )}
              <button
                className="btn-modal-action secondary"
                onClick={() => setSelectedReport(null)}
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
