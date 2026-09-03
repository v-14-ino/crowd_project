import React from 'react';
import { Link } from 'react-router-dom';

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
  const lvlClass = (level || 'low').toLowerCase();
  return (
    <div className={`priority-indicator ${lvlClass}`}>
      <span className="score-num">{score}</span>
      <span className="score-lbl">{level}</span>
    </div>
  );
}

function getConfidenceBadge(score, level) {
  const lvlClass = (level || 'low').toLowerCase();
  return (
    <div className={`confidence-indicator ${lvlClass}`}>
      <div className="conf-bar-wrapper">
        <div className="conf-bar-fill" style={{ width: `${Math.min(100, Math.max(0, score))}%` }}></div>
      </div>
      <div className="conf-text">
        <span className="conf-num">{score}%</span>
        <span className="conf-lvl">({level})</span>
      </div>
    </div>
  );
}

import { formatRelativeTime, formatExactTime } from '../utils/dateFormatter';

export default function IncidentQueue({ incidents, loading, error, searchStatus, searchTerm }) {
  if (loading) {
    return (
      <div className="queue-container">
        <div className="queue-loading">
          <div className="spinner"></div>
          <p>Loading prioritized incidents queue...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="queue-container">
        <div className="queue-error">
          <span className="error-icon">⚠️</span>
          <div>
            <h3>Unable to load incidents</h3>
            <p>{error}</p>
          </div>
        </div>
      </div>
    );
  }

  if (!incidents || incidents.length === 0) {
    if (searchStatus?.type === 'unassigned_report') {
      return (
        <div className="queue-container">
          <div className="queue-empty unassigned-report">
            <span className="empty-icon">📄</span>
            <h3>Report found, but no incident has been assigned yet.</h3>
            <p>
              Report <strong>{searchStatus.reportId}</strong> was recorded in the database, but has not yet been linked to an active incident cluster.
            </p>
          </div>
        </div>
      );
    }

    if (searchStatus?.type === 'not_found') {
      return (
        <div className="queue-container">
          <div className="queue-empty not-found">
            <span className="empty-icon">🔍</span>
            <h3>No report or incident found for {searchStatus.reportId}.</h3>
            <p>Please check the Report ID and verify the format or try searching with different criteria.</p>
          </div>
        </div>
      );
    }

    return (
      <div className="queue-container">
        <div className="queue-empty">
          <span className="empty-icon">📭</span>
          <h3>No incidents found</h3>
          <p>
            {searchTerm
              ? `There are no incidents matching "${searchTerm}".`
              : 'There are no incidents matching your active search and filter criteria.'}
          </p>
        </div>
      </div>
    );
  }


  return (
    <div className="queue-container">
      <div className="table-responsive">
        <table className="incident-table">
          <thead>
            <tr>
              <th>Priority</th>
              <th>Incident Details</th>
              <th>Location & Zone</th>
              <th>Confidence</th>
              <th>Automated Status</th>
              <th>Human Decision</th>
              <th>Freshness</th>
              <th>Reports</th>
              <th>Last Activity</th>
              <th>Action</th>
            </tr>
          </thead>
          <tbody>
            {incidents.map((incident) => {
              const hasCoords = incident.latitude !== null && incident.longitude !== null;
              return (
                <tr key={incident.incident_id} className="incident-row">
                  <td className="col-priority">
                    {getPriorityBadge(incident.priority_score, incident.priority_level)}
                  </td>

                  <td className="col-details">
                    <Link to={`/dashboard/${incident.incident_id}`} className="incident-id-link">
                      {incident.incident_id}
                    </Link>
                    <div className="incident-category-line">
                      <span className="badge-cat">{incident.category}</span>
                      <span className="issue-type-text">{incident.issue_type}</span>
                    </div>
                  </td>

                  <td className="col-location">
                    <div className="zone-text">📍 {incident.zone || 'Unassigned Zone'}</div>
                    <div className="coord-text">
                      {hasCoords
                        ? `${incident.latitude?.toFixed(4)}, ${incident.longitude?.toFixed(4)}`
                        : <span className="missing-coord">Coords Missing</span>}
                    </div>
                  </td>

                  <td className="col-confidence">
                    {getConfidenceBadge(incident.confidence_score, incident.confidence_level)}
                  </td>

                  <td className="col-status">
                    {getVerificationBadge(incident.status)}
                  </td>

                  <td className="col-human-decision">
                    <span className={`human-status-badge ${incident.human_status.toLowerCase().replace(/ /g, '-')}`}>
                      {incident.human_status}
                    </span>
                  </td>

                  <td className="col-freshness">
                    {getFreshnessBadge(incident.freshness)}
                  </td>

                  <td className="col-reports">
                    <div className="report-count-box" title={`${incident.total_reports_count} total, ${incident.independent_reports_count} independent, ${incident.duplicate_reports_count} duplicates`}>
                      <span className="indep-count">{incident.independent_reports_count || 1}</span>
                      <span className="indep-label">indep.</span>
                      {incident.duplicate_reports_count > 0 && (
                        <span className="dup-pill">+{incident.duplicate_reports_count} dup</span>
                      )}
                    </div>
                  </td>

                  <td className="col-time">
                    <div className="rel-time">{formatRelativeTime(incident.updated_at || incident.created_at)}</div>
                    <div className="exact-time">
                      {formatExactTime(incident.updated_at || incident.created_at)}
                    </div>
                  </td>

                  <td className="col-action">
                    <Link to={`/dashboard/${incident.incident_id}`} className="btn-drilldown">
                      Inspect →
                    </Link>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}
