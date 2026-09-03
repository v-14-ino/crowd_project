import React, { useState } from 'react';
import { uploadEvidence, deleteEvidence } from '../services/api';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

const SOURCE_TYPES = [
  'Photo',
  'Video reference',
  'CCTV',
  'IoT/Sensor',
  'Citizen submission',
  'Citizen',
  'Municipal Officer',
  'Field Responder',
  'Simulated External Source',
];

const SOURCE_STATUSES = [
  'Standard',
  'High Quality',
  'Verified',
  'Unverified',
];

function getSourceIcon(sourceType) {
  switch (sourceType) {
    case 'Photo':
      return '📷';
    case 'Video reference':
      return '🎬';
    case 'CCTV':
      return '📹';
    case 'IoT/Sensor':
      return '📡';
    case 'Field Responder':
      return '👮';
    case 'Municipal Officer':
      return '🏛️';
    case 'Citizen submission':
    case 'Citizen':
      return '👥';
    case 'Simulated External Source':
      return '🧪';
    default:
      return '📎';
  }
}

function getFreshnessBadge(freshness) {
  switch (freshness) {
    case 'Fresh':
      return <span className="freshness-badge fresh">🟢 Fresh (≤24h)</span>;
    case 'Aging':
      return <span className="freshness-badge aging">🟡 Aging (24h-72h)</span>;
    case 'Stale':
      return <span className="freshness-badge stale">🔴 Stale (&gt;72h)</span>;
    default:
      return <span className="freshness-badge unknown">⚪ Timestamp: Unknown</span>;
  }
}

export default function EvidenceSection({ incident, onEvidenceUpdated }) {
  const [showForm, setShowForm] = useState(false);
  const [mode, setMode] = useState('upload'); // 'upload' or 'simulated'
  const [sourceType, setSourceType] = useState('Photo');
  const [sourceStatus, setSourceStatus] = useState('Standard');
  const [observedAt, setObservedAt] = useState(new Date().toISOString().slice(0, 16));
  const [latitude, setLatitude] = useState(incident?.latitude ? String(incident.latitude) : '');
  const [longitude, setLongitude] = useState(incident?.longitude ? String(incident.longitude) : '');
  const [details, setDetails] = useState('');
  const [selectedFile, setSelectedFile] = useState(null);
  const [previewUrl, setPreviewUrl] = useState(null);
  const [submitting, setSubmitting] = useState(false);
  const [errorMsg, setErrorMsg] = useState(null);
  const [successResult, setSuccessResult] = useState(null);
  const [previewModalImg, setPreviewModalImg] = useState(null);
  const [deletingId, setDeletingId] = useState(null);
  const [brokenImages, setBrokenImages] = useState({});

  const handleImageError = (id) => {
    setBrokenImages((prev) => ({ ...prev, [id]: true }));
  };

  const handleFileChange = (e) => {
    const file = e.target.files?.[0];
    setErrorMsg(null);
    if (!file) {
      setSelectedFile(null);
      setPreviewUrl(null);
      return;
    }

    const validExtensions = ['.jpg', '.jpeg', '.png', '.webp'];
    const ext = file.name.substring(file.name.lastIndexOf('.')).toLowerCase();
    if (!validExtensions.includes(ext)) {
      setErrorMsg(`Unsupported file type '${ext}'. Please select a JPG, PNG, or WEBP image.`);
      setSelectedFile(null);
      setPreviewUrl(null);
      return;
    }

    if (file.size > 10 * 1024 * 1024) {
      setErrorMsg(`File size exceeds 10MB limit (${(file.size / (1024 * 1024)).toFixed(2)} MB).`);
      setSelectedFile(null);
      setPreviewUrl(null);
      return;
    }

    setSelectedFile(file);
    const objectUrl = URL.createObjectURL(file);
    setPreviewUrl(objectUrl);
  };

  const handleResetForm = () => {
    setShowForm(false);
    setSelectedFile(null);
    if (previewUrl) URL.revokeObjectURL(previewUrl);
    setPreviewUrl(null);
    setDetails('');
    setErrorMsg(null);
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setErrorMsg(null);
    setSuccessResult(null);
    setSubmitting(true);

    try {
      let res;
      if (mode === 'upload' && selectedFile) {
        const formData = new FormData();
        formData.append('file', selectedFile);
        formData.append('source_type', sourceType);
        formData.append('source_status', sourceStatus);
        if (observedAt) formData.append('observed_at', observedAt);
        if (latitude && latitude.trim()) formData.append('latitude', latitude.trim());
        if (longitude && longitude.trim()) formData.append('longitude', longitude.trim());
        if (details) formData.append('details', details);

        res = await uploadEvidence(incident.incident_id, formData);
      } else {
        const payload = {
          source_type: sourceType,
          source_status: sourceStatus,
          observed_at: observedAt ? new Date(observedAt).toISOString() : null,
          latitude: latitude && latitude.trim() ? parseFloat(latitude.trim()) : null,
          longitude: longitude && longitude.trim() ? parseFloat(longitude.trim()) : null,
          details: details.trim() || 'Simulated telemetry evidence attachment.',
        };

        res = await uploadEvidence(incident.incident_id, payload);
      }

      setSuccessResult(res);
      handleResetForm();
      if (onEvidenceUpdated) {
        onEvidenceUpdated();
      }
    } catch (err) {
      setErrorMsg(err?.detail || err.message || 'Failed to attach evidence.');
    } finally {
      setSubmitting(false);
    }
  };

  const [confirmDeleteId, setConfirmDeleteId] = useState(null);

  const handleDelete = async (evidenceId) => {
    setDeletingId(evidenceId);
    setErrorMsg(null);
    try {
      await deleteEvidence(evidenceId);
      setConfirmDeleteId(null);
      setSuccessResult(null);
      if (onEvidenceUpdated) {
        onEvidenceUpdated();
      }
    } catch (err) {
      setErrorMsg(err?.detail || err.message || 'Failed to delete evidence.');
    } finally {
      setDeletingId(null);
    }
  };

  const evidenceList = incident?.evidence || [];

  return (
    <div className="section-card evidence-management-section">
      <div className="section-title-row">
        <div className="title-left">
          <h2>📷 External Evidence &amp; Telemetry</h2>
          <span className="counter-pill">{evidenceList.length} Attached Source(s)</span>
        </div>

        <button
          className="btn-attach-evidence"
          onClick={() => {
            setShowForm(!showForm);
            setSuccessResult(null);
            setErrorMsg(null);
          }}
        >
          {showForm ? '✕ Close Form' : '➕ Attach New Evidence'}
        </button>
      </div>

      {/* Verification Impact Delta Banner */}
      {successResult && (
        <div className="evidence-impact-banner">
          <div className="impact-header">
            <span className="impact-icon">✨</span>
            <div className="impact-title-group">
              <strong>Evidence added successfully.</strong>
              <span>VerificationEngine recalculation complete:</span>
            </div>
            <button className="btn-dismiss-impact" onClick={() => setSuccessResult(null)}>✕</button>
          </div>

          <div className="impact-metrics-row">
            <div className="impact-metric-pill">
              <span className="metric-tag">Confidence</span>
              <div className="metric-delta">
                <span className="val-prev">{successResult.previous_confidence_score ?? incident?.confidence_score}%</span>
                <span className="arrow">→</span>
                <span className="val-new">{successResult.updated_confidence_score}%</span>
                {successResult.updated_confidence_score > (successResult.previous_confidence_score ?? 0) && (
                  <span className="badge-gain">+{successResult.updated_confidence_score - (successResult.previous_confidence_score ?? 0)}%</span>
                )}
              </div>
            </div>

            <div className="impact-metric-pill">
              <span className="metric-tag">Priority</span>
              <div className="metric-delta">
                <span className="val-prev">{successResult.previous_priority_score ?? incident?.priority_score}/100</span>
                <span className="arrow">→</span>
                <span className="val-new">{successResult.updated_priority_score}/100</span>
                {successResult.updated_priority_score > (successResult.previous_priority_score ?? 0) && (
                  <span className="badge-gain">+{successResult.updated_priority_score - (successResult.previous_priority_score ?? 0)}</span>
                )}
              </div>
            </div>

            <div className="impact-metric-pill">
              <span className="metric-tag">Status</span>
              <div className="metric-delta">
                <span className="val-status">{successResult.status}</span>
              </div>
            </div>
          </div>

          {successResult.confidence_explanations && successResult.confidence_explanations.length > 0 && (
            <div className="impact-explanations">
              <span className="exp-title">Engine Audit Explanations:</span>
              <ul className="exp-bullets">
                {successResult.confidence_explanations.map((exp, idx) => (
                  <li key={idx}>✓ {exp}</li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}

      {errorMsg && (
        <div className="message-banner error">
          ⚠️ {errorMsg}
        </div>
      )}

      {/* Attach Evidence Form */}
      {showForm && (
        <form className="evidence-form-card" onSubmit={handleSubmit}>
          <div className="form-header">
            <h3>Attach Evidence to Incident #{incident.incident_id}</h3>
            <div className="mode-switch">
              <button
                type="button"
                className={`mode-btn ${mode === 'upload' ? 'active' : ''}`}
                onClick={() => setMode('upload')}
              >
                📸 Image File Upload
              </button>
              <button
                type="button"
                className={`mode-btn ${mode === 'simulated' ? 'active' : ''}`}
                onClick={() => setMode('simulated')}
              >
                📡 Simulated / Telemetry Data
              </button>
            </div>
          </div>

          <div className="form-grid-2">
            <div className="form-group">
              <label>Evidence Type / Source</label>
              <select
                value={sourceType}
                onChange={(e) => setSourceType(e.target.value)}
              >
                {SOURCE_TYPES.map((st) => (
                  <option key={st} value={st}>
                    {getSourceIcon(st)} {st}
                  </option>
                ))}
              </select>
            </div>

            <div className="form-group">
              <label>Quality &amp; Trust Level</label>
              <select
                value={sourceStatus}
                onChange={(e) => setSourceStatus(e.target.value)}
              >
                {SOURCE_STATUSES.map((ss) => (
                  <option key={ss} value={ss}>
                    {ss} {ss === 'High Quality' || ss === 'Verified' ? '(+15 Confidence Boost)' : ''}
                  </option>
                ))}
              </select>
            </div>
          </div>

          {mode === 'upload' && (
            <div className="form-group file-upload-area">
              <label>Select Photo / Image (JPG, PNG, WEBP — Max 10MB)</label>
              <input
                type="file"
                accept=".jpg,.jpeg,.png,.webp,image/jpeg,image/png,image/webp"
                onChange={handleFileChange}
              />
              {previewUrl && (
                <div className="upload-preview-box">
                  <img src={previewUrl} alt="Upload preview" className="thumb-preview" />
                  <span className="file-info">
                    {selectedFile?.name} ({(selectedFile?.size / 1024).toFixed(1)} KB)
                  </span>
                </div>
              )}
            </div>
          )}

          <div className="form-grid-3">
            <div className="form-group">
              <label>Observed Timestamp</label>
              <input
                type="datetime-local"
                value={observedAt}
                onChange={(e) => setObservedAt(e.target.value)}
              />
            </div>

            <div className="form-group">
              <label>Latitude (Optional)</label>
              <input
                type="number"
                step="any"
                placeholder="e.g. 11.0168"
                value={latitude}
                onChange={(e) => setLatitude(e.target.value)}
              />
            </div>

            <div className="form-group">
              <label>Longitude (Optional)</label>
              <input
                type="number"
                step="any"
                placeholder="e.g. 76.9558"
                value={longitude}
                onChange={(e) => setLongitude(e.target.value)}
              />
            </div>
          </div>

          <div className="form-group">
            <label>Evidence Description &amp; Technical Metadata</label>
            <textarea
              rows="2"
              placeholder="Enter sensor reading details, camera feed location, or photo observations..."
              value={details}
              onChange={(e) => setDetails(e.target.value)}
            />
          </div>

          <div className="form-actions-row">
            <button
              type="submit"
              className="btn-submit-evidence"
              disabled={submitting || (mode === 'upload' && !selectedFile)}
            >
              {submitting ? 'Submitting Evidence...' : '💾 Attach Evidence & Recalculate'}
            </button>
            <button
              type="button"
              className="btn-cancel"
              onClick={handleResetForm}
            >
              Cancel
            </button>
          </div>
        </form>
      )}

      {/* Evidence Cards Display */}
      {evidenceList.length > 0 ? (
        <div className="evidence-grid">
          {evidenceList.map((item) => {
            const hasLocation = item.latitude !== null && item.longitude !== null && !isNaN(Number(item.latitude)) && !isNaN(Number(item.longitude));
            const icon = getSourceIcon(item.source_type);
            const isHighQuality = item.source_status === 'High Quality' || item.source_status === 'Verified';
            const fullImgUrl = item.file_url ? (item.file_url.startsWith('http') ? item.file_url : `${API_BASE_URL}${item.file_url}`) : null;
            const isBroken = brokenImages[item.id];

            return (
              <div key={item.id} className={`evidence-card ${isHighQuality ? 'hq-border' : ''}`}>
                <div className="evidence-card-header">
                  <div className="source-info">
                    <span className="source-icon-badge">{icon}</span>
                    <div>
                      <div className="source-name">{item.source_type || 'Source: Unknown'}</div>
                      <span className="evidence-code font-mono">#{item.evidence_id || `EVD-${item.id}`}</span>
                    </div>
                  </div>

                  <span className={`evidence-status ${isHighQuality ? 'hq' : 'standard'}`}>
                    {item.source_status || 'Standard'}
                  </span>
                </div>

                {fullImgUrl && (
                  <div className="evidence-thumb-container">
                    {isBroken ? (
                      <div className="evidence-file-unavailable">
                        <span className="unavail-icon">⚠️</span>
                        <span>Evidence file unavailable</span>
                      </div>
                    ) : (
                      <div onClick={() => setPreviewModalImg(fullImgUrl)} style={{ cursor: 'pointer', width: '100%' }}>
                        <img
                          src={fullImgUrl}
                          alt="Evidence attachment"
                          className="evidence-thumb-img"
                          onError={() => handleImageError(item.id)}
                        />
                        <span className="thumb-zoom-hint">🔍 Click to zoom</span>
                      </div>
                    )}
                  </div>
                )}

                <div className="evidence-details-text">
                  "{item.details || 'No additional technical notes provided.'}"
                </div>

                <div className="evidence-meta-grid">
                  <div className="meta-row">
                    <span className="meta-lbl">Observed:</span>
                    <span className="meta-val">
                      {item.observed_at ? new Date(item.observed_at).toLocaleString() : 'Timestamp: Unknown'}
                    </span>
                  </div>

                  <div className="meta-row">
                    <span className="meta-lbl">Freshness:</span>
                    {getFreshnessBadge(item.freshness_status)}
                  </div>

                  <div className="meta-row">
                    <span className="meta-lbl">Location:</span>
                    <span className="meta-val">
                      {hasLocation
                        ? `📍 ${Number(item.latitude).toFixed(4)}, ${Number(item.longitude).toFixed(4)}`
                        : <span className="text-warning">Location: Unknown</span>}
                    </span>
                  </div>

                  <div className="meta-row">
                    <span className="meta-lbl">Associated:</span>
                    <span className="meta-val font-mono">
                      {item.report_id ? `Report #${item.report_id}` : 'General Incident'}
                    </span>
                  </div>

                  {item.file_size ? (
                    <div className="meta-row">
                      <span className="meta-lbl">File:</span>
                      <span className="meta-val font-mono">
                        {item.filename || 'Image'} ({(item.file_size / 1024).toFixed(1)} KB)
                      </span>
                    </div>
                  ) : null}
                </div>

                <div className="evidence-card-footer">
                  {confirmDeleteId === (item.evidence_id || item.id) ? (
                    <div className="delete-confirm-group">
                      <button
                        className="btn-confirm-delete"
                        disabled={deletingId === item.id}
                        onClick={() => handleDelete(item.evidence_id || item.id)}
                      >
                        {deletingId === item.id ? 'Deleting...' : '⚠️ Confirm Delete'}
                      </button>
                      <button
                        type="button"
                        className="btn-cancel-delete"
                        onClick={() => setConfirmDeleteId(null)}
                      >
                        Cancel
                      </button>
                    </div>
                  ) : (
                    <button
                      className="btn-delete-evidence"
                      onClick={() => setConfirmDeleteId(item.evidence_id || item.id)}
                      title="Remove evidence"
                    >
                      🗑️ Delete Evidence
                    </button>
                  )}
                </div>

              </div>
            );
          })}
        </div>
      ) : (
        <div className="missing-data-box">
          <span className="box-icon">ℹ️</span>
          <div>
            <strong>Evidence: Not available</strong>
            <p>No external IoT sensor telemetry, CCTV feeds, or photo attachments are linked to this incident.</p>
          </div>
        </div>
      )}

      {/* Lightbox Modal for Image Preview */}
      {previewModalImg && (
        <div className="image-lightbox-overlay" onClick={() => setPreviewModalImg(null)}>
          <div className="lightbox-content" onClick={(e) => e.stopPropagation()}>
            <button className="btn-close-lightbox" onClick={() => setPreviewModalImg(null)}>✕</button>
            <img src={previewModalImg} alt="Full resolution evidence" className="lightbox-img" />
          </div>
        </div>
      )}
    </div>
  );
}

