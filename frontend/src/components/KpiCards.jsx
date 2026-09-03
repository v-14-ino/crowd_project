import React from 'react';

export default function KpiCards({ stats, activeFilter, onCardClick }) {
  if (!stats) {
    return (
      <div className="kpi-grid loading">
        {Array.from({ length: 8 }).map((_, i) => (
          <div key={i} className="kpi-card skeleton">
            <div className="kpi-skeleton-label"></div>
            <div className="kpi-skeleton-val"></div>
          </div>
        ))}
      </div>
    );
  }

  const cards = [
    {
      id: 'total',
      label: 'Total Incidents',
      count: stats.total_incidents,
      icon: '📋',
      theme: 'neutral',
      filterType: 'all',
      filterVal: 'All',
    },
    {
      id: 'critical',
      label: 'Critical Incidents',
      count: stats.critical_incidents,
      icon: '🚨',
      theme: 'critical',
      filterType: 'priorityLevel',
      filterVal: 'Critical',
    },
    {
      id: 'high',
      label: 'High Priority',
      count: stats.high_priority_incidents,
      icon: '⚠️',
      theme: 'high',
      filterType: 'priorityLevel',
      filterVal: 'High',
    },
    {
      id: 'corroborated',
      label: 'Corroborated',
      count: stats.corroborated_incidents,
      icon: '👥',
      theme: 'corroborated',
      filterType: 'status',
      filterVal: 'Corroborated',
    },
    {
      id: 'verified',
      label: 'Official Verified',
      count: stats.verified_incidents,
      icon: '✅',
      theme: 'verified',
      filterType: 'status',
      filterVal: 'Verified',
    },
    {
      id: 'pending',
      label: 'Pending Review',
      count: stats.pending_incidents,
      icon: '⏳',
      theme: 'pending',
      filterType: 'status',
      filterVal: 'Pending',
    },
    {
      id: 'conflicted',
      label: 'Conflicted',
      count: stats.conflicted_incidents,
      icon: '⚡',
      theme: 'conflicted',
      filterType: 'status',
      filterVal: 'Conflicted',
    },
    {
      id: 'stale',
      label: 'Stale Incidents',
      count: stats.stale_incidents,
      icon: '🕰️',
      theme: 'stale',
      filterType: 'freshness',
      filterVal: 'Stale',
    },
  ];

  return (
    <div className="kpi-grid">
      {cards.map((card) => {
        const isSelected =
          (card.filterType === 'all' && activeFilter?.priorityLevel === 'All' && activeFilter?.status === 'All' && activeFilter?.freshness === 'All') ||
          (card.filterType === 'priorityLevel' && activeFilter?.priorityLevel === card.filterVal) ||
          (card.filterType === 'status' && activeFilter?.status === card.filterVal) ||
          (card.filterType === 'freshness' && activeFilter?.freshness === card.filterVal);

        return (
          <div
            key={card.id}
            className={`kpi-card ${card.theme} ${isSelected ? 'selected' : ''}`}
            onClick={() => onCardClick && onCardClick(card.filterType, card.filterVal)}
            role="button"
            tabIndex={0}
            title={`Filter by ${card.label}`}
          >
            <div className="kpi-top">
              <span className="kpi-icon">{card.icon}</span>
              <span className="kpi-count">{card.count ?? 0}</span>
            </div>
            <div className="kpi-label">{card.label}</div>
          </div>
        );
      })}
    </div>
  );
}
