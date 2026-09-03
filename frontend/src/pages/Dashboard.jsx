import React, { useEffect, useState, useCallback, useRef } from 'react';
import DashboardNavbar from '../components/DashboardNavbar';
import KpiCards from '../components/KpiCards';
import FilterBar from '../components/FilterBar';
import IncidentQueue from '../components/IncidentQueue';
import IncidentMap from '../components/IncidentMap';
import RecentReportsSection from '../components/RecentReportsSection';
import {
  fetchHealthStatus,
  fetchIncidentStats,
  fetchIncidents,
  fetchRecentReports,
  fetchReport,
  fetchIncident,
} from '../services/api';

const DEFAULT_FILTERS = {
  search: '',
  category: 'All',
  priorityLevel: 'All',
  confidenceLevel: 'All',
  status: 'All',
  freshness: 'All',
  zone: 'All',
};

export default function Dashboard() {
  const [stats, setStats] = useState(null);
  const [incidents, setIncidents] = useState([]);
  const [recentReports, setRecentReports] = useState([]);
  const [filters, setFilters] = useState(DEFAULT_FILTERS);
  const [searchStatus, setSearchStatus] = useState(null);
  const [backendStatus, setBackendStatus] = useState('Checking...');
  const [loading, setLoading] = useState(true);
  const [recentLoading, setRecentLoading] = useState(false);
  const [error, setError] = useState(null);
  const [lastRefreshed, setLastRefreshed] = useState(new Date());
  const [previousPollTime, setPreviousPollTime] = useState(null);
  const [viewMode, setViewMode] = useState('split'); // 'split', 'map', 'queue'

  const lastSyncRef = useRef(new Date());

  const loadData = useCallback(async (currentFilters, isPolling = false) => {
    if (!isPolling) setLoading(true);
    setError(null);

    try {
      // Check health
      try {
        await fetchHealthStatus();
        setBackendStatus('Connected');
      } catch {
        setBackendStatus('Disconnected');
      }

      // Fetch stats, incidents, and recent citizen reports in parallel
      const [statsData, incidentsDataRaw, recentReportsData] = await Promise.all([
        fetchIncidentStats(),
        fetchIncidents(currentFilters),
        fetchRecentReports(10).catch(() => []),
      ]);
      
      let incidentsData = incidentsDataRaw || [];

      // Ensure that incidents for the most recent reports are always displayed on the map/queue,
      // even if they don't make the top 100 prioritized list.
      if (recentReportsData && recentReportsData.length > 0) {
        const existingIncidentIds = new Set(incidentsData.map(inc => inc.incident_id));
        const missingRecentIncidentIds = [
          ...new Set(
            recentReportsData
              .map(rep => rep.incident_id)
              .filter(id => id && !existingIncidentIds.has(id))
          )
        ];

        if (missingRecentIncidentIds.length > 0) {
          const missingIncidents = await Promise.all(
            missingRecentIncidentIds.map(id => fetchIncident(id).catch(() => null))
          );
          incidentsData = [...incidentsData, ...missingIncidents.filter(Boolean)];
        }
      }

      let searchStatusInfo = null;
      const searchTerm = (currentFilters.search || '').trim();

      if ((!incidentsData || incidentsData.length === 0) && searchTerm.toUpperCase().startsWith('RPT-')) {
        try {
          const report = await fetchReport(searchTerm);
          if (report && !report.incident_id) {
            searchStatusInfo = {
              type: 'unassigned_report',
              reportId: searchTerm,
              message: 'Report found, but no incident has been assigned yet.',
            };
          }
        } catch {
          searchStatusInfo = {
            type: 'not_found',
            reportId: searchTerm,
            message: `No report or incident found for ${searchTerm}.`,
          };
        }
      }

      setPreviousPollTime(lastSyncRef.current);
      lastSyncRef.current = new Date();
      setLastRefreshed(new Date());

      setStats(statsData);
      setIncidents(incidentsData);
      setRecentReports(recentReportsData || []);
      setSearchStatus(searchStatusInfo);
    } catch (err) {
      setError(err?.detail || err.message || 'Unable to connect to backend server. Please verify backend is running on port 8000.');
      setBackendStatus('Disconnected');
    } finally {
      if (!isPolling) setLoading(false);
    }
  }, []);

  // Initial load and on filters change
  useEffect(() => {
    loadData(filters, false);
  }, [filters, loadData]);

  // Automatic live polling (every 12 seconds)
  useEffect(() => {
    const pollTimer = setInterval(() => {
      loadData(filters, true);
    }, 12000);

    return () => clearInterval(pollTimer);
  }, [filters, loadData]);

  const handleFilterChange = (field, value) => {
    setFilters((prev) => ({
      ...prev,
      [field]: value,
    }));
  };

  const handleKpiCardClick = (filterType, filterVal) => {
    if (filterType === 'all') {
      setFilters(DEFAULT_FILTERS);
    } else {
      setFilters((prev) => ({
        ...DEFAULT_FILTERS,
        [filterType]: filterVal,
      }));
    }
  };

  const handleResetFilters = () => {
    setFilters(DEFAULT_FILTERS);
  };

  const handleManualRefresh = () => {
    loadData(filters, false);
  };

  return (
    <div className="dashboard-layout">
      <DashboardNavbar
        backendStatus={backendStatus}
        onRefresh={handleManualRefresh}
      />

      <main className="dashboard-content">
        {/* Section A: Operations Center Hero & KPI Summary */}
        <section className="dashboard-hero-section">
          <div className="hero-heading-row">
            <div>
              <h1 className="hero-main-title">Officer Operations &amp; Verification Center</h1>
              <p className="hero-sub-text">
                Real-time decision support for municipal operations. Prioritized by severity, crowd corroboration, and spatial telemetry.
              </p>
            </div>
            <div className="last-sync-tag">
              <span className="live-pulse-dot"></span>
              LIVE: Synced {lastRefreshed.toLocaleTimeString()}
            </div>
          </div>

          <KpiCards
            stats={stats}
            activeFilter={filters}
            onCardClick={handleKpiCardClick}
          />
        </section>

        {/* Section B: Recent Citizen Reports (Live Activity Feed) */}
        <section className="dashboard-recent-section">
          <RecentReportsSection
            recentReports={recentReports}
            loading={loading}
            lastPollTime={lastRefreshed}
            previousPollTime={previousPollTime}
            onRefresh={handleManualRefresh}
          />
        </section>

        {/* Section C: Queue Controls & Search */}
        <section className="dashboard-queue-section">
          <div className="section-header-block">
            <h2 className="section-title">📋 Prioritized Incident Queue &amp; Spatial Map</h2>
            <p className="section-subtitle">
              Interactive operations console with SQL-indexed filtering, geospatial Leaflet markers, and incident drill-down.
            </p>
          </div>

          <FilterBar
            filters={filters}
            onFilterChange={handleFilterChange}
            onReset={handleResetFilters}
            totalCount={stats?.total_incidents || incidents.length}
            filteredCount={incidents.length}
          />

          {/* View Mode Switcher */}
          <div className="view-mode-bar">
            <div className="view-mode-title">
              {viewMode === 'map' && '🗺️ Spatial Map Overview'}
              {viewMode === 'queue' && '📋 Priority Incident Queue'}
              {viewMode === 'split' && '🗺️ Spatial Map & 📋 Priority Queue'}
            </div>

            <div className="view-mode-toggle">
              <button
                className={`toggle-btn ${viewMode === 'split' ? 'active' : ''}`}
                onClick={() => setViewMode('split')}
                title="Show both map and queue"
              >
                🔀 Split View
              </button>
              <button
                className={`toggle-btn ${viewMode === 'map' ? 'active' : ''}`}
                onClick={() => setViewMode('map')}
                title="Show spatial incident map only"
              >
                🗺️ Map Only
              </button>
              <button
                className={`toggle-btn ${viewMode === 'queue' ? 'active' : ''}`}
                onClick={() => setViewMode('queue')}
                title="Show priority queue table only"
              >
                📋 Table Only
              </button>
            </div>
          </div>

          {/* Map Component (shown in 'split' or 'map' mode) */}
          {(viewMode === 'split' || viewMode === 'map') && (
            <div className="dashboard-map-panel">
              <IncidentMap
                incidents={incidents}
                loading={loading}
                error={error}
              />
            </div>
          )}

          {/* Queue Component (shown in 'split' or 'queue' mode) */}
          {(viewMode === 'split' || viewMode === 'queue') && (
            <div className="dashboard-table-panel">
              <IncidentQueue
                incidents={incidents}
                loading={loading}
                error={error}
                searchStatus={searchStatus}
                searchTerm={filters.search}
              />
            </div>
          )}
        </section>
      </main>
    </div>
  );
}


