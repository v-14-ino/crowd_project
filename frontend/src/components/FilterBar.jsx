import React from 'react';

const CATEGORIES = ['All', 'Roads', 'Lighting', 'Waste'];
const PRIORITIES = ['All', 'Critical', 'High', 'Medium', 'Low'];
const CONFIDENCES = ['All', 'High', 'Medium', 'Low'];
const STATUSES = ['All', 'Pending', 'Corroborated', 'Verified', 'Conflicted', 'Rejected', 'Unknown'];
const FRESHNESSES = ['All', 'Fresh', 'Aging', 'Stale', 'Unknown'];
const ZONES = ['All', 'North', 'South', 'East', 'West', 'Central', 'Test'];

export default function FilterBar({ filters, onFilterChange, onReset, totalCount, filteredCount }) {
  return (
    <div className="filter-panel">
      <div className="search-row">
        <div className="search-input-wrapper">
          <span className="search-icon">🔍</span>
          <input
            type="text"
            className="search-input"
            placeholder="Search by Incident ID, Report ID, Category, Issue Type, Zone..."
            value={filters.search || ''}
            onChange={(e) => onFilterChange('search', e.target.value)}
          />

          {filters.search && (
            <button
              className="clear-search-btn"
              onClick={() => onFilterChange('search', '')}
              title="Clear search"
            >
              ×
            </button>
          )}
        </div>

        <div className="results-count">
          Showing <strong>{filteredCount}</strong> of <strong>{totalCount}</strong> incidents
        </div>

        <button className="btn-reset" onClick={onReset}>
          Reset Filters
        </button>
      </div>

      <div className="filter-dropdowns-grid">
        <div className="filter-field">
          <label>Category</label>
          <select
            value={filters.category || 'All'}
            onChange={(e) => onFilterChange('category', e.target.value)}
          >
            {CATEGORIES.map((c) => (
              <option key={c} value={c}>
                {c === 'All' ? 'All Categories' : c}
              </option>
            ))}
          </select>
        </div>

        <div className="filter-field">
          <label>Priority</label>
          <select
            value={filters.priorityLevel || 'All'}
            onChange={(e) => onFilterChange('priorityLevel', e.target.value)}
          >
            {PRIORITIES.map((p) => (
              <option key={p} value={p}>
                {p === 'All' ? 'All Priorities' : p}
              </option>
            ))}
          </select>
        </div>

        <div className="filter-field">
          <label>Confidence</label>
          <select
            value={filters.confidenceLevel || 'All'}
            onChange={(e) => onFilterChange('confidenceLevel', e.target.value)}
          >
            {CONFIDENCES.map((c) => (
              <option key={c} value={c}>
                {c === 'All' ? 'All Confidence' : `${c} Confidence`}
              </option>
            ))}
          </select>
        </div>

        <div className="filter-field">
          <label>Verification Status</label>
          <select
            value={filters.status || 'All'}
            onChange={(e) => onFilterChange('status', e.target.value)}
          >
            {STATUSES.map((s) => (
              <option key={s} value={s}>
                {s === 'All' ? 'All Verification States' : s}
              </option>
            ))}
          </select>
        </div>

        <div className="filter-field">
          <label>Freshness</label>
          <select
            value={filters.freshness || 'All'}
            onChange={(e) => onFilterChange('freshness', e.target.value)}
          >
            {FRESHNESSES.map((f) => (
              <option key={f} value={f}>
                {f === 'All'
                  ? 'All Freshness'
                  : f === 'Fresh'
                  ? '🟢 Fresh (≤24h)'
                  : f === 'Aging'
                  ? '🟡 Aging (24h-72h)'
                  : f === 'Stale'
                  ? '🔴 Stale (>72h)'
                  : '⚪ Unknown'}
              </option>
            ))}
          </select>
        </div>

        <div className="filter-field">
          <label>Zone</label>
          <select
            value={filters.zone || 'All'}
            onChange={(e) => onFilterChange('zone', e.target.value)}
          >
            {ZONES.map((z) => (
              <option key={z} value={z}>
                {z === 'All' ? 'All Zones' : `Zone: ${z}`}
              </option>
            ))}
          </select>
        </div>
      </div>
    </div>
  );
}
