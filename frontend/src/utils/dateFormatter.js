export function formatRelativeTime(dateStr) {
  if (!dateStr) return 'N/A';
  try {
    // Append 'Z' if missing to ensure naive backend times are parsed as UTC
    const normalizedStr = dateStr.endsWith('Z') ? dateStr : `${dateStr}Z`;
    const d = new Date(normalizedStr);
    
    // Check if valid date
    if (isNaN(d.getTime())) return 'Invalid date';

    const now = new Date();
    const diffMs = now - d;
    
    // Fallback if future time somehow
    if (diffMs < 0) return 'Just now';

    const diffMins = Math.floor(diffMs / 60000);
    const diffHours = Math.floor(diffMins / 60);

    if (diffMins < 1) return 'Just now';
    if (diffMins < 60) return `${diffMins} min ago`;
    if (diffHours < 24) {
      if (diffHours === 1) return '1 hour ago';
      return `${diffHours} hours ago`;
    }

    // Check if it was yesterday
    const yesterday = new Date(now);
    yesterday.setDate(now.getDate() - 1);
    
    if (
      d.getDate() === yesterday.getDate() &&
      d.getMonth() === yesterday.getMonth() &&
      d.getFullYear() === yesterday.getFullYear()
    ) {
      return `Yesterday, ${d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}`;
    }

    // Older dates
    return d.toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  } catch {
    return String(dateStr);
  }
}

export function formatExactTime(dateStr) {
  if (!dateStr) return 'N/A';
  try {
    const normalizedStr = dateStr.endsWith('Z') ? dateStr : `${dateStr}Z`;
    const d = new Date(normalizedStr);
    if (isNaN(d.getTime())) return 'Invalid date';
    return d.toLocaleTimeString([], {
      hour: '2-digit',
      minute: '2-digit',
    });
  } catch {
    return String(dateStr);
  }
}
