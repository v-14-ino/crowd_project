import { useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import { postReport, uploadEvidence } from './services/api';
import RecentReports from './components/RecentReports';

const CATEGORY_OPTIONS = ['Roads', 'Lighting', 'Waste'];
const ISSUE_TYPES = {
  Roads: [
    'Pothole',
    'Road flooding',
    'Fallen tree',
    'Road obstruction',
    'Damaged road surface',
  ],
  Lighting: [
    'Streetlight outage',
    'Damaged light pole',
    'Exposed wiring',
    'Multiple lights out',
  ],
  Waste: [
    'Overflowing bin',
    'Illegal dumping',
    'Uncollected waste',
    'Blocked drainage',
    'Hazardous waste',
  ],
};
const SEVERITY_OPTIONS = ['Low', 'Medium', 'High', 'Critical'];

function ReportIssue() {
  const [form, setForm] = useState({
    category: 'Roads',
    issue_type: ISSUE_TYPES.Roads[0],
    description: '',
    zone: '',
    citizen_severity: 'Low',
    latitude: '',
    longitude: '',
  });
  const [errors, setErrors] = useState([]);
  const [apiMessage, setApiMessage] = useState(null);
  const [submitting, setSubmitting] = useState(false);
  const [locating, setLocating] = useState(false);
  const [pincode, setPincode] = useState('');
  const [pincodeError, setPincodeError] = useState('');
  const [resolvedLocationName, setResolvedLocationName] = useState('');
  const [resolvingPincode, setResolvingPincode] = useState(false);
  const [evidenceFile, setEvidenceFile] = useState(null);
  const [evidencePreview, setEvidencePreview] = useState(null);

  const issueTypeOptions = useMemo(
    () => ISSUE_TYPES[form.category] || [],
    [form.category]
  );

  const handleChange = (field) => (event) => {
    const value = event.target.value;
    setForm((current) => ({
      ...current,
      [field]: value,
    }));
  };

  const handleSeverityClick = (severity) => {
    setForm((current) => ({
      ...current,
      citizen_severity: severity,
    }));
  };

  const handleFileChange = (e) => {
    const file = e.target.files[0];
    if (file) {
      if (file.size > 10 * 1024 * 1024) { // 10MB
        setErrors(['Evidence file is too large (max 10MB)']);
        window.scrollTo({ top: 0, behavior: 'smooth' });
        return;
      }
      setEvidenceFile(file);
      setEvidencePreview(URL.createObjectURL(file));
      setErrors([]);
    }
  };

  const removeEvidence = () => {
    setEvidenceFile(null);
    setEvidencePreview(null);
  };

  const handleUseLocation = () => {
    setErrors([]); // Clear any previous location errors
    if (!navigator.geolocation) {
      setErrors(['Geolocation is not supported by your browser. Please enter your location manually.']);
      window.scrollTo({ top: 0, behavior: 'smooth' });
      return;
    }
    setLocating(true);
    navigator.geolocation.getCurrentPosition(
      (position) => {
        setForm((current) => ({
          ...current,
          latitude: position.coords.latitude.toFixed(6),
          longitude: position.coords.longitude.toFixed(6),
        }));
        setLocating(false);
      },
      (error) => {
        let msg = "Unable to retrieve your location. Please enter it manually.";
        if (error.code === 1) {
          msg = "Location permission denied. Please enter your location manually.";
        } else if (error.code === 2) {
          msg = "Location information is unavailable. Please enter it manually.";
        } else if (error.code === 3) {
          msg = "Location request timed out. Please try again or enter it manually.";
        }
        setErrors([msg]);
        window.scrollTo({ top: 0, behavior: 'smooth' });
        setLocating(false);
      },
      { enableHighAccuracy: false, timeout: 15000, maximumAge: Infinity }
    );
  };

  const handleFindLocation = async () => {
    setPincodeError('');
    setResolvedLocationName('');
    
    const pin = pincode.trim();
    if (!/^\d{6}$/.test(pin)) {
      setPincodeError('Please enter a valid 6-digit Indian pincode.');
      return;
    }

    setResolvingPincode(true);
    try {
      const response = await fetch(`https://nominatim.openstreetmap.org/search?postalcode=${pin}&countrycodes=in&format=json`);
      if (!response.ok) throw new Error('Network response was not ok');
      const data = await response.json();

      if (data && data.length > 0) {
        const location = data[0];
        let locName = location.display_name;
        
        try {
           const postRes = await fetch(`https://api.postalpincode.in/pincode/${pin}`);
           if (postRes.ok) {
               const postData = await postRes.json();
               if (postData && postData[0] && postData[0].Status === 'Success' && postData[0].PostOffice && postData[0].PostOffice.length > 0) {
                   const po = postData[0].PostOffice[0];
                   locName = `${po.Name}, ${po.State}`;
               }
           }
        } catch (e) {
           // Fallback to nominatim name
        }

        setForm((current) => ({
          ...current,
          latitude: Number(location.lat).toFixed(6),
          longitude: Number(location.lon).toFixed(6),
        }));
        setResolvedLocationName(locName);
      } else {
        setPincodeError('Pincode not found. Please check and try again.');
      }
    } catch (error) {
      setPincodeError('Failed to resolve location. Please try again later.');
    } finally {
      setResolvingPincode(false);
    }
  };

  const validate = () => {
    const nextErrors = [];

    if (!form.category) {
      nextErrors.push('Category is required.');
    }
    if (!form.issue_type) {
      nextErrors.push('Issue Type is required.');
    }
    if (!form.description.trim()) {
      nextErrors.push('Description is required.');
    } else if (form.description.trim().length < 10) {
      nextErrors.push('Description must be at least 10 characters.');
    }
    if (!form.citizen_severity) {
      nextErrors.push('Severity is required.');
    }

    const hasLat = form.latitude.toString().trim() !== '';
    const hasLng = form.longitude.toString().trim() !== '';
    if (hasLat !== hasLng) {
      nextErrors.push('Both latitude and longitude must be provided together.');
    }
    if (hasLat && hasLng) {
      const latitude = Number(form.latitude);
      const longitude = Number(form.longitude);
      if (Number.isNaN(latitude) || latitude < -90 || latitude > 90) {
        nextErrors.push('Latitude must be a valid number between -90 and 90.');
      }
      if (Number.isNaN(longitude) || longitude < -180 || longitude > 180) {
        nextErrors.push('Longitude must be a valid number between -180 and 180.');
      }
    }

    return nextErrors;
  };

  const handleSubmit = async (event) => {
    event.preventDefault();
    if (submitting) return;

    setApiMessage(null);
    const nextErrors = validate();
    if (nextErrors.length > 0) {
      setErrors(nextErrors);
      window.scrollTo({ top: 0, behavior: 'smooth' });
      return;
    }

    setErrors([]);
    setSubmitting(true);

    try {
      const payload = {
        category: form.category,
        issue_type: form.issue_type,
        description: form.description.trim(),
        zone: form.zone.trim() || null,
        citizen_severity: form.citizen_severity,
        latitude: form.latitude.toString().trim() ? Number(form.latitude) : null,
        longitude: form.longitude.toString().trim() ? Number(form.longitude) : null,
      };

      const result = await postReport(payload);
      
      let evidenceMsg = '';
      if (evidenceFile && result.report.incident_id) {
        try {
          const formData = new FormData();
          formData.append('file', evidenceFile);
          formData.append('source_type', 'Citizen');
          formData.append('source_status', 'Standard');
          formData.append('details', 'Attached during initial report submission');
          
          await uploadEvidence(result.report.incident_id, formData);
          evidenceMsg = ' Evidence attached successfully.';
        } catch (evErr) {
          console.error("Evidence upload failed:", evErr);
          evidenceMsg = ' However, evidence upload failed. Please try attaching it later or contact support.';
        }
      }

      setApiMessage({
        type: 'success',
        data: result,
        extraMessage: evidenceMsg
      });
      window.scrollTo({ top: 0, behavior: 'smooth' });
    } catch (error) {
      if (error?.detail) {
        const detail = Array.isArray(error.detail)
          ? error.detail.map((item) => item.msg || item).join(' ')
          : error.detail;
        setApiMessage({ type: 'error', text: String(detail) });
      } else {
        setApiMessage({ type: 'error', text: 'Failed to submit report. Please try again or check your connection.' });
      }
      window.scrollTo({ top: 0, behavior: 'smooth' });
    } finally {
      setSubmitting(false);
    }
  };

  const resetForm = () => {
    setApiMessage(null);
    setForm({
      category: 'Roads',
      issue_type: ISSUE_TYPES['Roads'][0],
      description: '',
      zone: '',
      citizen_severity: 'Low',
      latitude: '',
      longitude: '',
    });
    setEvidenceFile(null);
    setEvidencePreview(null);
    setPincode('');
    setPincodeError('');
    setResolvedLocationName('');
  };

  return (
    <div className="dashboard-layout">
      {/* HEADER */}
      <header className="dashboard-header">
        <div className="municipality-brand">
          <div className="crest-icon">🏛️</div>
          <div>
            <div className="header-title">Citizen Service Portal</div>
            <div className="header-subtitle">Municipality Crowd Verification</div>
          </div>
        </div>
        <nav className="header-nav">
          <Link className="nav-btn" to="/">Home</Link>
          <Link className="nav-btn active" to="/report">Report an Issue</Link>
          <Link className="nav-btn" to="/track">Track Report</Link>
          <Link className="nav-btn" to="/dashboard">Officer Dashboard</Link>
        </nav>
      </header>

      <main className="dashboard-content">
        
        <div className="citizen-portal-layout">
          {apiMessage?.type === 'success' && apiMessage.data ? (
            /* SUCCESS STATE */
            <div className="success-confirmation-card">
              <span className="success-icon-large">✅</span>
              <h2 className="success-title">Report Submitted Successfully</h2>
              <p className="success-message">
                Thank you. Your municipal issue has been registered and routed to the appropriate department.
                {apiMessage?.extraMessage && (
                  <span style={{ display: 'block', marginTop: '8px', fontWeight: 'bold' }}>
                    {apiMessage.extraMessage}
                  </span>
                )}
              </p>
              
              <div className="success-id-box">
                <span className="success-id-label">Your Report Reference</span>
                <span className="success-id-value">{apiMessage.data.report.report_id}</span>
                
                {apiMessage.data.report.incident_id && (
                  <>
                    <span className="success-id-label" style={{ marginTop: '16px' }}>Assigned Incident ID</span>
                    <span className="success-id-value">{apiMessage.data.report.incident_id}</span>
                  </>
                )}
              </div>

              <div className="success-actions-grid">
                <button type="button" onClick={resetForm} className="btn-outline">
                  Submit Another Issue
                </button>
                <button 
                  type="button" 
                  onClick={() => navigator.clipboard.writeText(apiMessage.data.report.report_id)}
                  className="btn-outline"
                >
                  Copy Report ID
                </button>
                <Link to={`/track?id=${apiMessage.data.report.report_id}`} className="btn-outline" style={{ background: '#2563eb', color: '#fff', borderColor: '#2563eb', gridColumn: 'span 2' }}>
                  Track This Report
                </Link>
              </div>
            </div>
          ) : (
            /* FORM STATE */
            <div className="citizen-portal-card">
            
            <div className="hero-heading-row" style={{ marginBottom: '24px' }}>
              <div>
                <h1 className="hero-main-title">Report a Municipal Issue</h1>
                <p className="hero-sub-text">
                  Help us identify and resolve issues in your area. Submit accurate details and location information.
                </p>
              </div>
            </div>

            {errors.length > 0 && (
              <div className="message-box error-box" style={{ marginBottom: '24px', borderRadius: '12px' }}>
                <strong>Please fix the following:</strong>
                <ul>
                  {errors.map((error) => (
                    <li key={error}>{error}</li>
                  ))}
                </ul>
              </div>
            )}

            {apiMessage?.type === 'error' && (
              <div className="message-box error-box" style={{ marginBottom: '24px', borderRadius: '12px' }}>
                <p>{apiMessage.text}</p>
              </div>
            )}

            <form onSubmit={handleSubmit} noValidate>
              
              {/* SECTION A: ISSUE DETAILS */}
              <div className="report-section-container">
                <h3 className="report-section-title">Section A: Issue Details</h3>
                
                <div className="location-grid">
                  <div className="form-group">
                    <label>Category</label>
                    <select 
                      value={form.category} 
                      onChange={(event) => {
                        const category = event.target.value;
                        setForm((current) => ({
                          ...current,
                          category,
                          issue_type: ISSUE_TYPES[category][0],
                        }));
                      }}
                    >
                      {CATEGORY_OPTIONS.map((category) => (
                        <option key={category} value={category}>{category}</option>
                      ))}
                    </select>
                  </div>

                  <div className="form-group">
                    <label>Specific Issue Type</label>
                    <select value={form.issue_type} onChange={handleChange('issue_type')}>
                      {issueTypeOptions.map((issueType) => (
                        <option key={issueType} value={issueType}>{issueType}</option>
                      ))}
                    </select>
                  </div>
                </div>

                <div className="form-group" style={{ marginBottom: 0 }}>
                  <label>Description</label>
                  <textarea
                    value={form.description}
                    onChange={handleChange('description')}
                    rows={4}
                    placeholder="Provide details about the issue..."
                  />
                  <span className={`char-counter ${form.description.length > 0 && form.description.length < 10 ? 'error' : ''}`}>
                    {form.description.length} chars (Min 10)
                  </span>
                </div>
              </div>

              {/* SECTION B: LOCATION */}
              <div className="report-section-container">
                <h3 className="report-section-title">Section B: Location</h3>
                
                <div className="location-action-row" style={{ display: 'flex', flexDirection: 'column', gap: '16px', alignItems: 'flex-start' }}>
                  <p className="location-description" style={{ marginBottom: 0 }}>
                    Pinpoint the exact location for faster resolution.
                  </p>
                  <button 
                    type="button" 
                    className="btn-use-location"
                    onClick={handleUseLocation}
                    disabled={locating}
                  >
                    📍 {locating ? 'Locating...' : 'Use My Location'}
                  </button>
                  
                  <div style={{ display: 'flex', alignItems: 'center', width: '100%', gap: '16px' }}>
                    <div style={{ flex: 1, height: '1px', background: '#e2e8f0' }}></div>
                    <span style={{ fontSize: '14px', color: '#64748b', fontWeight: 'bold' }}>OR ENTER PINCODE</span>
                    <div style={{ flex: 1, height: '1px', background: '#e2e8f0' }}></div>
                  </div>

                  <div style={{ display: 'flex', gap: '12px', width: '100%', alignItems: 'flex-start', flexWrap: 'wrap' }}>
                    <div style={{ flex: '1 1 200px' }}>
                      <input
                        type="text"
                        value={pincode}
                        onChange={(e) => setPincode(e.target.value.replace(/\D/g, '').slice(0, 6))}
                        placeholder="e.g. 624202"
                        maxLength="6"
                        style={{ width: '100%' }}
                      />
                      {pincodeError && <div style={{ color: '#ef4444', fontSize: '13px', marginTop: '4px' }}>{pincodeError}</div>}
                    </div>
                    <button 
                      type="button" 
                      onClick={handleFindLocation}
                      disabled={resolvingPincode}
                      className="btn-outline"
                      style={{ padding: '10px 16px', whiteSpace: 'nowrap', height: '42px', margin: 0 }}
                    >
                      {resolvingPincode ? 'Finding location...' : 'Find Location'}
                    </button>
                  </div>
                  {resolvedLocationName && (
                    <div style={{ color: '#10b981', fontSize: '14px', fontWeight: 'bold', marginTop: '-8px' }}>
                      ✓ {resolvedLocationName}
                    </div>
                  )}
                </div>

                <div className="form-group" style={{ marginTop: '24px' }}>
                  <label>Zone / Neighborhood (Optional)</label>
                  <input
                    type="text"
                    value={form.zone}
                    onChange={handleChange('zone')}
                    placeholder="e.g. North District, Downtown..."
                  />
                </div>

                <div className="location-grid">
                  <div className="form-group" style={{ marginBottom: 0 }}>
                    <label>Latitude (Optional)</label>
                    <input
                      type="number"
                      step="any"
                      value={form.latitude}
                      onChange={handleChange('latitude')}
                      placeholder="e.g. 34.0522"
                    />
                  </div>
                  <div className="form-group" style={{ marginBottom: 0 }}>
                    <label>Longitude (Optional)</label>
                    <input
                      type="number"
                      step="any"
                      value={form.longitude}
                      onChange={handleChange('longitude')}
                      placeholder="e.g. -118.2437"
                    />
                  </div>
                </div>
              </div>

              {/* SECTION C: SEVERITY */}
              <div className="report-section-container">
                <h3 className="report-section-title">Section C: Severity</h3>
                <p className="severity-description">
                  How severe is this issue? This helps municipal officers prioritize their response.
                </p>
                <div className="severity-cards-grid">
                  {SEVERITY_OPTIONS.map((sev) => {
                    const isSelected = form.citizen_severity === sev;
                    return (
                      <div 
                        key={sev}
                        className={`severity-card ${isSelected ? 'selected' : ''} ${sev.toLowerCase()}`}
                        onClick={() => handleSeverityClick(sev)}
                      >
                        <div className="severity-card-title">{sev}</div>
                      </div>
                    );
                  })}
                </div>
              </div>

              {/* SECTION D: EVIDENCE */}
              <div className="report-section-container">
                <h3 className="report-section-title">Section D: Evidence (Optional)</h3>
                <p className="severity-description">
                  Attach an image to help officers understand the issue better.
                </p>
                
                <div className="form-group" style={{ marginBottom: 0 }}>
                  {!evidencePreview ? (
                    <div style={{ border: '2px dashed #cbd5e1', padding: '24px', textAlign: 'center', borderRadius: '8px', background: '#f8fafc' }}>
                      <input 
                        type="file" 
                        accept="image/jpeg, image/png, image/jpg" 
                        onChange={handleFileChange}
                        style={{ display: 'none' }}
                        id="evidence-upload"
                      />
                      <label htmlFor="evidence-upload" style={{ cursor: 'pointer', color: '#3b82f6', fontWeight: 'bold' }}>
                        📸 Click to Select Image
                      </label>
                      <p style={{ marginTop: '8px', fontSize: '13px', color: '#64748b' }}>JPG, JPEG, PNG (Max 10MB)</p>
                    </div>
                  ) : (
                    <div style={{ border: '1px solid #e2e8f0', padding: '16px', borderRadius: '8px', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
                        <img src={evidencePreview} alt="Evidence Preview" style={{ width: '80px', height: '80px', objectFit: 'cover', borderRadius: '8px' }} />
                        <div>
                          <div style={{ fontWeight: 'bold', fontSize: '14px' }}>{evidenceFile.name}</div>
                          <div style={{ fontSize: '12px', color: '#64748b' }}>{(evidenceFile.size / (1024 * 1024)).toFixed(2)} MB</div>
                        </div>
                      </div>
                      <button type="button" onClick={removeEvidence} style={{ background: '#ef4444', color: 'white', padding: '6px 12px', border: 'none', borderRadius: '6px', cursor: 'pointer' }}>
                        Remove
                      </button>
                    </div>
                  )}
                </div>
              </div>

              <div className="form-actions">
                <button type="submit" className="btn-submit-report" disabled={submitting}>
                  {submitting ? 'Submitting Report...' : 'Submit Report'}
                </button>
              </div>
            </form>
          </div>
        )}
        
        {/* Right side: Recent Reports Feed */}
        <RecentReports />
        </div>
      </main>
    </div>
  );
}

export default ReportIssue;
