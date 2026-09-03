import React, { useEffect, useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { MapContainer, TileLayer, Marker, Popup, useMap } from 'react-leaflet';
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';

// Fix Leaflet's default icon URLs if ever needed
delete L.Icon.Default.prototype._getIconUrl;
L.Icon.Default.mergeOptions({
  iconRetinaUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon-2x.png',
  iconUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon.png',
  shadowUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-shadow.png',
});

// Helper component to auto-fit map bounds to available incident coordinates
function MapAutoFit({ incidents }) {
  const map = useMap();

  useEffect(() => {
    if (!map || !incidents || incidents.length === 0) return;

    const validCoords = incidents
      .filter((inc) => inc.latitude !== null && inc.longitude !== null && !isNaN(inc.latitude) && !isNaN(inc.longitude))
      .map((inc) => [inc.latitude, inc.longitude]);

    if (validCoords.length === 0) return;

    if (validCoords.length === 1) {
      map.setView(validCoords[0], 14, { animate: true });
    } else {
      const bounds = L.latLngBounds(validCoords);
      map.fitBounds(bounds, {
        padding: [50, 50],
        maxZoom: 15,
        animate: true,
      });
    }
  }, [map, incidents]);

  return null;
}

// Generate distinct Leaflet DivIcons based on priority and status
function createIncidentIcon(incident) {
  const priorityLevel = (incident.priority_level || 'Low').toLowerCase();
  const priorityScore = incident.priority_score ?? 0;

  let markerIcon = '📍';
  if (priorityLevel === 'critical') markerIcon = '🚨';
  else if (priorityLevel === 'high') markerIcon = '⚠️';
  else if (priorityLevel === 'medium') markerIcon = '⚡';

  const isVerified = incident.status === 'Verified';
  const isConflicted = incident.status === 'Conflicted';

  const statusDotClass = isVerified ? 'verified-dot' : isConflicted ? 'conflicted-dot' : '';

  const html = `
    <div class="custom-incident-pin ${priorityLevel} ${isVerified ? 'is-verified' : ''} ${isConflicted ? 'is-conflicted' : ''}">
      <div class="pin-badge">
        <span class="pin-icon">${markerIcon}</span>
        <span class="pin-score">${priorityScore}</span>
      </div>
      <div class="pin-tip"></div>
      ${statusDotClass ? `<span class="pin-status-dot ${statusDotClass}"></span>` : ''}
    </div>
  `;

  return L.divIcon({
    className: 'custom-pin-container',
    html,
    iconSize: [38, 46],
    iconAnchor: [19, 46],
    popupAnchor: [0, -44],
  });
}

function getFreshnessPill(freshness) {
  switch (freshness) {
    case 'Fresh':
      return <span className="map-badge fresh">🟢 Fresh (≤24h)</span>;
    case 'Aging':
      return <span className="map-badge aging">🟡 Aging (24h-72h)</span>;
    case 'Stale':
      return <span className="map-badge stale">🔴 Stale (&gt;72h)</span>;
    default:
      return <span className="map-badge unknown">⚪ Unknown Freshness</span>;
  }
}

function getStatusPill(status) {
  switch (status) {
    case 'Verified':
      return <span className="map-badge status-verified">✅ Verified</span>;
    case 'Corroborated':
      return <span className="map-badge status-corroborated">👥 Corroborated</span>;
    case 'Conflicted':
      return <span className="map-badge status-conflicted">⚡ Conflicted</span>;
    case 'Rejected':
      return <span className="map-badge status-rejected">❌ Rejected</span>;
    case 'Unknown':
      return <span className="map-badge status-unknown">❓ Unknown</span>;
    default:
      return <span className="map-badge status-pending">⏳ Pending</span>;
  }
}

export default function IncidentMap({ incidents = [], loading = false, error = null }) {
  const navigate = useNavigate();
  const [selectedIncidentId, setSelectedIncidentId] = useState(null);
  const [showUnmappedList, setShowUnmappedList] = useState(false);

  // Filter valid mappable vs unmapped incidents
  const { mappableIncidents, unmappedIncidents } = useMemo(() => {
    const mappable = [];
    const unmapped = [];

    (incidents || []).forEach((inc) => {
      const lat = Number(inc.latitude);
      const lng = Number(inc.longitude);
      if (
        inc.latitude !== null &&
        inc.longitude !== null &&
        !isNaN(lat) &&
        !isNaN(lng) &&
        Math.abs(lat) <= 90 &&
        Math.abs(lng) <= 180 &&
        (lat !== 0 || lng !== 0)
      ) {
        mappable.push({ ...inc, latitude: lat, longitude: lng });
      } else {
        unmapped.push(inc);
      }
    });

    return { mappableIncidents: mappable, unmappedIncidents: unmapped };
  }, [incidents]);

  // Default fallback coordinates (e.g. Coimbatore municipal center or center of first incident)
  const defaultCenter = useMemo(() => {
    if (mappableIncidents.length > 0) {
      return [mappableIncidents[0].latitude, mappableIncidents[0].longitude];
    }
    return [11.0168, 76.9558];
  }, [mappableIncidents]);

  if (loading) {
    return (
      <div className="incident-map-container loading-state">
        <div className="spinner"></div>
        <p>Loading spatial incident coordinates &amp; layers...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="incident-map-container error-state">
        <span className="error-icon">⚠️</span>
        <h3>Map Unavailable</h3>
        <p>{error}</p>
      </div>
    );
  }

  return (
    <div className="incident-map-wrapper">
      {/* Top Map Control Bar */}
      <div className="map-control-bar">
        <div className="map-stats-summary">
          <span className="map-stat-item">
            📍 <strong>{mappableIncidents.length}</strong> Mapped Incidents
          </span>
          {unmappedIncidents.length > 0 && (
            <button
              className={`unmapped-toggle-btn ${showUnmappedList ? 'active' : ''}`}
              onClick={() => setShowUnmappedList(!showUnmappedList)}
              title="View incidents without GPS coordinates"
            >
              ⚠️ {unmappedIncidents.length} Missing Location
            </button>
          )}
        </div>

        <div className="map-quick-hint">
          Click any marker to inspect incident details and priority rationale.
        </div>
      </div>

      <div className="map-layout-row">
        {/* Main Leaflet Map View */}
        <div className="map-canvas-container">
          {mappableIncidents.length === 0 ? (
            <div className="map-empty-overlay">
              <div className="empty-content-box">
                <span className="empty-icon">🗺️</span>
                <h3>No mappable incidents available.</h3>
                <p>
                  {unmappedIncidents.length > 0
                    ? `${unmappedIncidents.length} incidents in the current filter lack GPS coordinates.`
                    : 'There are no active incidents matching the selected criteria.'}
                </p>
              </div>
            </div>
          ) : null}

          <MapContainer
            center={defaultCenter}
            zoom={12}
            scrollWheelZoom={true}
            className="leaflet-map-root"
          >
            <TileLayer
              attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
              url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
            />

            <MapAutoFit incidents={mappableIncidents} />

            {mappableIncidents.map((incident) => {
              const icon = createIncidentIcon(incident);
              return (
                <Marker
                  key={incident.incident_id}
                  position={[incident.latitude, incident.longitude]}
                  icon={icon}
                  eventHandlers={{
                    click: () => setSelectedIncidentId(incident.incident_id),
                  }}
                >
                  <Popup className="incident-leaflet-popup" minWidth={280} maxWidth={320}>
                    <div className="popup-card">
                      <div className="popup-header">
                        <span className="popup-category">{incident.category}</span>
                        {getStatusPill(incident.status)}
                      </div>

                      <h4 className="popup-title">{incident.issue_type}</h4>

                      <div className="popup-id-row">
                        <span className="popup-id font-mono">#{incident.incident_id}</span>
                        <span className="popup-zone">📍 {incident.zone || 'Unassigned Zone'}</span>
                      </div>

                      <div className="popup-metrics-grid">
                        <div className={`popup-metric-item prio-${(incident.priority_level || 'low').toLowerCase()}`}>
                          <span className="lbl">Priority</span>
                          <span className="val">
                            {incident.priority_score} <small>({incident.priority_level})</small>
                          </span>
                        </div>

                        <div className="popup-metric-item conf-item">
                          <span className="lbl">Confidence</span>
                          <span className="val">
                            {incident.confidence_score}% <small>({incident.confidence_level})</small>
                          </span>
                        </div>
                      </div>

                      <div className="popup-sub-info">
                        <div className="sub-row">
                          <span className="lbl">Freshness:</span>
                          {getFreshnessPill(incident.freshness)}
                        </div>
                        <div className="sub-row">
                          <span className="lbl">Reports:</span>
                          <span className="val">
                            <strong>{incident.total_reports_count || 1}</strong> total ({incident.independent_reports_count || 1} independent
                            {incident.duplicate_reports_count > 0 ? `, ${incident.duplicate_reports_count} dup` : ''})
                          </span>
                        </div>
                        <div className="sub-row">
                          <span className="lbl">Coordinates:</span>
                          <span className="val font-mono">
                            {incident.latitude.toFixed(4)}, {incident.longitude.toFixed(4)}
                          </span>
                        </div>
                      </div>

                      <button
                        className="popup-cta-btn"
                        onClick={() => navigate(`/dashboard/${incident.incident_id}`)}
                      >
                        View Drill-down Details →
                      </button>
                    </div>
                  </Popup>
                </Marker>
              );
            })}
          </MapContainer>

          {/* Interactive Map Legend Overlay */}
          <div className="map-legend-overlay">
            <div className="legend-title">Map Legend</div>
            <div className="legend-grid">
              <div className="legend-item">
                <span className="legend-badge critical">🚨 Critical</span>
                <span className="legend-desc">80-100 Prio</span>
              </div>
              <div className="legend-item">
                <span className="legend-badge high">⚠️ High</span>
                <span className="legend-desc">60-79 Prio</span>
              </div>
              <div className="legend-item">
                <span className="legend-badge medium">⚡ Medium</span>
                <span className="legend-desc">40-59 Prio</span>
              </div>
              <div className="legend-item">
                <span className="legend-badge low">📍 Low</span>
                <span className="legend-desc">0-39 Prio</span>
              </div>
            </div>
            <div className="legend-divider"></div>
            <div className="legend-footer">
              <span>Status: ✅ Verified | 👥 Corroborated | ⚡ Conflicted | ⏳ Pending</span>
            </div>
          </div>
        </div>

        {/* Unmapped Incidents Drawer (when toggled or visible) */}
        {showUnmappedList && unmappedIncidents.length > 0 && (
          <aside className="unmapped-drawer">
            <div className="drawer-header">
              <h3>⚠️ Location Unavailable ({unmappedIncidents.length})</h3>
              <button
                className="btn-close-drawer"
                onClick={() => setShowUnmappedList(false)}
                title="Close drawer"
              >
                ✕
              </button>
            </div>
            <p className="drawer-notice">
              These incidents were reported without valid GPS coordinates and cannot be mapped spatially.
            </p>
            <div className="unmapped-list">
              {unmappedIncidents.map((inc) => (
                <div key={inc.incident_id} className="unmapped-item-card">
                  <div className="unmapped-top">
                    <span className="unmapped-id font-mono">#{inc.incident_id}</span>
                    <span className={`badge-severity ${(inc.priority_level || 'low').toLowerCase()}`}>
                      {inc.priority_score} {inc.priority_level}
                    </span>
                  </div>
                  <div className="unmapped-issue">{inc.issue_type}</div>
                  <div className="unmapped-meta">
                    <span>Category: {inc.category}</span>
                    <span>Zone: {inc.zone || 'Unassigned'}</span>
                  </div>
                  <div className="unmapped-status-line">
                    {getStatusPill(inc.status)}
                    {getFreshnessPill(inc.freshness)}
                  </div>
                  <button
                    className="btn-inspect-sm"
                    onClick={() => navigate(`/dashboard/${inc.incident_id}`)}
                  >
                    Inspect Details →
                  </button>
                </div>
              ))}
            </div>
          </aside>
        )}
      </div>
    </div>
  );
}
