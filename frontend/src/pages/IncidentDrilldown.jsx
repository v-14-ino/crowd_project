import React, { useEffect, useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import DashboardNavbar from '../components/DashboardNavbar';
import EvidenceSection from '../components/EvidenceSection';
import ResponderVerificationSection from '../components/ResponderVerificationSection';
import { fetchHealthStatus, fetchIncident } from '../services/api';


function getFreshnessIcon(freshness) {
  switch (freshness) {
    case 'Fresh':
      return { icon: '🟢', label: 'Fresh (≤24h)', cls: 'fresh' };
    case 'Aging':
      return { icon: '🟡', label: 'Aging (24h-72h)', cls: 'aging' };
    case 'Stale':
      return { icon: '🔴', label: 'Stale (>72h)', cls: 'stale' };
    default:
      return { icon: '⚪', label: 'Unknown Freshness', cls: 'unknown' };
  }
}

function getStatusBadge(status) {
  switch (status) {
    case 'Verified':
      return { icon: '✅', label: 'Verified', cls: 'verified' };
    case 'Corroborated':
      return { icon: '👥', label: 'Corroborated', cls: 'corroborated' };
    case 'Conflicted':
      return { icon: '⚡', label: 'Conflicted', cls: 'conflicted' };
    case 'Rejected':
      return { icon: '❌', label: 'Rejected', cls: 'rejected' };
    case 'Unknown':
      return { icon: '❓', label: 'Unknown', cls: 'unknown' };
    default:
      return { icon: '⏳', label: 'Pending', cls: 'pending' };
  }
}

function getRecommendationStyle(status, priorityLevel) {
  if (status === 'Verified' || (status === 'Corroborated' && (priorityLevel === 'Critical' || priorityLevel === 'High'))) {
    return 'rec-critical';
  }
  if (status === 'Conflicted') {
    return 'rec-warning';
  }
  if (status === 'Corroborated') {
    return 'rec-info';
  }
  return 'rec-neutral';
}

function cleanExplanationText(text) {
  if (!text) return '';
  // Transform technical prefixes if any into clean officer badges
  if (text.startsWith('Base score:')) {
    return { type: 'base', text: text.replace('Base score:', 'Initial Citizen Report:') };
  }
  if (text.startsWith('Corroboration:')) {
    return { type: 'corroboration', text };
  }
  if (text.startsWith('Deduplication:')) {
    return { type: 'dedup', text };
  }
  if (text.startsWith('External Evidence:') || text.startsWith('Evidence Quality:')) {
    return { type: 'evidence', text };
  }
  if (text.startsWith('Location Penalty:') || text.startsWith('Conflict Penalty:') || text.startsWith('Freshness Penalty:')) {
    return { type: 'penalty', text };
  }
  if (text.startsWith('Official Responder Verification:')) {
    return { type: 'responder', text };
  }
  return { type: 'general', text };
}

export default function IncidentDrilldown() {
  const { incidentId } = useParams();
  const [incident, setIncident] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [backendStatus, setBackendStatus] = useState('Checking...');

  const loadIncidentData = async () => {
    if (!incidentId) return;
    setLoading(true);
    setError(null);

    try {
      try {
        await fetchHealthStatus();
        setBackendStatus('Connected');
      } catch {
        setBackendStatus('Disconnected');
      }

      const data = await fetchIncident(incidentId);
      setIncident(data);
    } catch (err) {
      setError(err?.detail || err.message || `Failed to load details for incident ${incidentId}`);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadIncidentData();
  }, [incidentId]);

  if (loading) {
    return (
      <div className="dashboard-layout">
        <DashboardNavbar backendStatus={backendStatus} />
        <main className="dashboard-content">
          <div className="drilldown-card loading-box">
            <div className="spinner"></div>
            <p>Loading incident audit and verification details...</p>
          </div>
        </main>
      </div>
    );
  }

  if (error || !incident) {
    return (
      <div className="dashboard-layout">
        <DashboardNavbar backendStatus={backendStatus} />
        <main className="dashboard-content">
          <div className="drilldown-card error-card">
            <div className="error-icon-big">⚠️</div>
            <h2>Incident Not Found or Unavailable</h2>
            <p>{error || `Incident with ID ${incidentId} could not be retrieved.`}</p>
            <div className="drilldown-actions">
              <Link to="/dashboard" className="btn-primary-link">
                ← Return to Officer Dashboard
              </Link>
              <button className="btn-secondary" onClick={loadIncidentData}>
                Retry
              </button>
            </div>
          </div>
        </main>
      </div>
    );
  }

  const statusInfo = getStatusBadge(incident.status);
  const freshnessInfo = getFreshnessIcon(incident.freshness);
  const recStyle = getRecommendationStyle(incident.status, incident.priority_level);
  const hasCoordinates = incident.latitude !== null && incident.longitude !== null;

  return (
    <div className="dashboard-layout">
      <DashboardNavbar backendStatus={backendStatus} onRefresh={loadIncidentData} />

      <main className="dashboard-content">
        {/* Navigation Breadcrumb */}
        <div className="drilldown-top-bar">
          <Link to="/dashboard" className="back-link">
            ← Back to Incidents Queue
          </Link>
          <div className="top-right-meta">
            <span className="meta-item">Incident ID: <strong>{incident.incident_id}</strong></span>
            <span className="meta-item">Created: {new Date(incident.created_at).toLocaleString()}</span>
          </div>
        </div>

        {/* Header Title Card */}
        <div className="drilldown-header-card">
          <div className="header-badge-row">
            <span className="category-pill-lg">{incident.category}</span>
            <span className={`status-pill-lg ${statusInfo.cls}`}>
              {statusInfo.icon} {statusInfo.label}
            </span>
            <span className={`freshness-pill-lg ${freshnessInfo.cls}`}>
              {freshnessInfo.icon} {freshnessInfo.label}
            </span>
          </div>

          <h1 className="drilldown-title">{incident.issue_type}</h1>
          <p className="drilldown-zone">
            📍 <strong>{incident.zone || 'Unspecified Zone'}</strong>
            {hasCoordinates ? ` (${incident.latitude?.toFixed(5)}, ${incident.longitude?.toFixed(5)})` : ' (Coordinates Missing)'}
          </p>
        </div>

        {/* Section 1: Recommended Action Card */}
        <div className={`recommendation-box ${recStyle}`}>
          <div className="rec-header">
            <span className="rec-icon">🎯</span>
            <div>
              <div className="rec-badge">Recommended Decision Support Action</div>
              <div className="rec-action-text">{incident.recommended_action || 'Review incident reports and verify details.'}</div>
            </div>
          </div>
          <div className="rec-rationale">
            <strong>System Rationale:</strong> Based on <strong>{incident.status}</strong> verification status, <strong>{incident.priority_level}</strong> priority (Score: {incident.priority_score}/100), and <strong>{incident.confidence_level}</strong> confidence ({incident.confidence_score}%).
          </div>
        </div>

        {/* Section 2: Executive Metrics Grid */}
        <div className="drilldown-metrics-grid">
          {/* Priority Card */}
          <div className="metric-box priority-box">
            <div className="metric-header">
              <span className="metric-icon">🚨</span>
              <span className="metric-title">Priority Assessment</span>
            </div>
            <div className="metric-main-value">
              <span className="big-num">{incident.priority_score}</span>
              <span className="max-num">/100</span>
              <span className={`lvl-tag ${incident.priority_level.toLowerCase()}`}>{incident.priority_level}</span>
            </div>
            <p className="metric-desc">Urgency of municipal response and resource dispatch.</p>
          </div>

          {/* Confidence Card */}
          <div className="metric-box confidence-box">
            <div className="metric-header">
              <span className="metric-icon">🛡️</span>
              <span className="metric-title">Confidence Rating</span>
            </div>
            <div className="metric-main-value">
              <span className="big-num">{incident.confidence_score}%</span>
              <span className={`lvl-tag ${incident.confidence_level.toLowerCase()}`}>{incident.confidence_level}</span>
            </div>
            <div className="conf-progress-track">
              <div className="conf-progress-fill" style={{ width: `${Math.min(100, Math.max(0, incident.confidence_score))}%` }}></div>
            </div>
            <p className="metric-desc">Trustworthiness and multi-source validation score.</p>
          </div>

          {/* Crowd Corroboration Card */}
          <div className="metric-box crowd-box">
            <div className="metric-header">
              <span className="metric-icon">👥</span>
              <span className="metric-title">Crowd Corroboration</span>
            </div>
            <div className="crowd-stats-row">
              <div className="stat-col">
                <span className="stat-num">{incident.total_reports_count}</span>
                <span className="stat-lbl">Total Reports</span>
              </div>
              <div className="stat-col">
                <span className="stat-num highlight">{incident.independent_reports_count}</span>
                <span className="stat-lbl">Independent</span>
              </div>
              <div className="stat-col">
                <span className="stat-num muted">{incident.duplicate_reports_count}</span>
                <span className="stat-lbl">Duplicates</span>
              </div>
            </div>
            <p className="metric-desc">Filtered duplicates prevent artificial score inflation.</p>
          </div>

          {/* Location & Time Card */}
          <div className="metric-box location-box">
            <div className="metric-header">
              <span className="metric-icon">📍</span>
              <span className="metric-title">Spatial & Freshness</span>
            </div>
            <div className="loc-detail-rows">
              <div className="loc-row">
                <span className="label">Zone:</span>
                <span className="val">{incident.zone || 'Unassigned'}</span>
              </div>
              <div className="loc-row">
                <span className="label">Coords:</span>
                <span className="val">
                  {hasCoordinates ? `${incident.latitude?.toFixed(4)}, ${incident.longitude?.toFixed(4)}` : '⚠️ Missing Coordinates'}
                </span>
              </div>
              <div className="loc-row">
                <span className="label">Last Report:</span>
                <span className="val">
                  {incident.last_reported_time ? new Date(incident.last_reported_time).toLocaleString() : 'N/A'}
                </span>
              </div>
            </div>
          </div>
        </div>

        {/* Section 3: Explainability Audit Breakdown */}
        <div className="section-card explainability-card">
          <div className="section-title-row">
            <h2>🔍 Verification Engine Audit & Explainability</h2>
            <span className="rule-engine-tag">Deterministic Heuristics v2.0</span>
          </div>
          <p className="section-desc">
            Complete transparent step-by-step reasoning behind the confidence and priority scores:
          </p>

          <div className="explanations-columns">
            {/* Confidence Explanations */}
            <div className="exp-col">
              <h3>Confidence Factor Breakdown</h3>
              <ul className="exp-list">
                {incident.confidence_explanations && incident.confidence_explanations.length > 0 ? (
                  incident.confidence_explanations.map((exp, idx) => {
                    const parsed = cleanExplanationText(exp);
                    const isPenalty = parsed.type === 'penalty';
                    const isPositive = exp.includes('+');
                    const isResponder = parsed.type === 'responder';

                    return (
                      <li key={idx} className={`exp-item ${isPenalty ? 'penalty' : isPositive ? 'positive' : isResponder ? 'responder' : 'neutral'}`}>
                        <span className="exp-icon">
                          {isPenalty ? '⚠️' : isPositive ? '✓' : isResponder ? '🏛️' : 'ℹ️'}
                        </span>
                        <span className="exp-text">{exp}</span>
                      </li>
                    );
                  })
                ) : (
                  <li className="exp-item neutral">
                    <span className="exp-icon">ℹ️</span>
                    <span className="exp-text">No confidence adjustments recorded.</span>
                  </li>
                )}
              </ul>
            </div>

            {/* Priority Explanations */}
            <div className="exp-col">
              <h3>Priority Factor Breakdown</h3>
              <ul className="exp-list">
                {incident.priority_explanations && incident.priority_explanations.length > 0 ? (
                  incident.priority_explanations.map((exp, idx) => {
                    const isPenalty = exp.toLowerCase().includes('penalty');
                    const isPositive = exp.includes('+');

                    return (
                      <li key={idx} className={`exp-item ${isPenalty ? 'penalty' : isPositive ? 'positive' : 'neutral'}`}>
                        <span className="exp-icon">
                          {isPenalty ? '⚠️' : isPositive ? '✓' : 'ℹ️'}
                        </span>
                        <span className="exp-text">{exp}</span>
                      </li>
                    );
                  })
                ) : (
                  <li className="exp-item neutral">
                    <span className="exp-icon">ℹ️</span>
                    <span className="exp-text">Standard baseline priority applied.</span>
                  </li>
                )}
              </ul>
            </div>
          </div>
        </div>

        {/* Section 4: Citizen Reports List */}
        <div className="section-card">
          <div className="section-title-row">
            <h2>📢 Citizen Reports ({incident.reports?.length || 0})</h2>
            <span className="counter-pill">{incident.independent_reports_count} Independent Sources</span>
          </div>

          {incident.reports && incident.reports.length > 0 ? (
            <div className="reports-table-wrapper">
              <table className="reports-table">
                <thead>
                  <tr>
                    <th>Report ID</th>
                    <th>Reported Time</th>
                    <th>Severity</th>
                    <th>Location Status</th>
                    <th>Freshness</th>
                    <th>Citizen Description</th>
                    <th>Conflict Flag</th>
                  </tr>
                </thead>
                <tbody>
                  {incident.reports.map((report) => {
                    const hasReportCoords = report.latitude !== null && report.longitude !== null;
                    const isConflicted = report.conflicting_evidence && ['yes', 'true', 'conflicted', '1'].includes(String(report.conflicting_evidence).toLowerCase());

                    return (
                      <tr key={report.report_id} className={isConflicted ? 'conflicted-row' : ''}>
                        <td className="font-mono">{report.report_id}</td>
                        <td>
                          {report.reported_time ? new Date(report.reported_time).toLocaleString() : 'N/A'}
                        </td>
                        <td>
                          <span className={`badge-severity ${report.citizen_severity?.toLowerCase() || 'low'}`}>
                            {report.citizen_severity || 'Low'}
                          </span>
                        </td>
                        <td>
                          <span className={`location-status-badge ${report.location_status === 'Available' ? 'available' : 'missing'}`}>
                            {hasReportCoords ? `📍 (${report.latitude?.toFixed(4)}, ${report.longitude?.toFixed(4)})` : '⚠️ Missing Location'}
                          </span>
                        </td>
                        <td>
                          <span className="badge-freshness-sm">
                            {report.freshness_status || 'Fresh'}
                          </span>
                        </td>
                        <td className="desc-cell">
                          <div className="citizen-quote">"{report.description || 'No description provided.'}"</div>
                        </td>
                        <td>
                          {isConflicted ? (
                            <span className="conflict-badge">⚡ Yes (Conflicted)</span>
                          ) : (
                            <span className="no-conflict">None</span>
                          )}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          ) : (
            <div className="empty-sub-box">No individual citizen reports found for this incident.</div>
          )}
        </div>

        {/* Section 5: External Evidence & Telemetry Management */}
        <EvidenceSection incident={incident} onEvidenceUpdated={loadIncidentData} />


        {/* Section 6: Responder Verification Section */}
        <ResponderVerificationSection 
          incident={incident} 
          onDecisionSubmitted={loadIncidentData} 
        />
      </main>
    </div>
  );
}
