import React, { useState } from 'react';
import { submitResponderVerification } from '../services/api';

export default function ResponderVerificationSection({ incident, onDecisionSubmitted }) {
  const [decision, setDecision] = useState('');
  const [rationale, setRationale] = useState('');
  const [responderName, setResponderName] = useState('Officer Default');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!decision || !rationale.trim()) {
      setError('Please select a decision and provide a rationale.');
      return;
    }
    
    setLoading(true);
    setError('');
    setSuccess('');
    
    try {
      await submitResponderVerification(incident.incident_id, {
        decision,
        rationale,
        responder_name: responderName
      });
      setSuccess('Responder decision recorded successfully.');
      setDecision('');
      setRationale('');
      if (onDecisionSubmitted) {
        onDecisionSubmitted();
      }
    } catch (err) {
      setError(err?.detail || err.message || 'Failed to submit decision.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="section-card">
      <div className="section-title-row">
        <h2>👮 Human Responder Verification</h2>
        <span className="counter-pill">{incident.responder_verifications?.length || 0} Record(s)</span>
      </div>

      <div className="responder-grid">
        <div className="responder-form-area">
          <h3>Record Decision</h3>
          {error && <div className="error-banner" style={{background: '#ffebee', color: '#c62828', padding: '10px', marginBottom: '15px'}}>{error}</div>}
          {success && <div className="success-banner" style={{background: '#e8f5e9', color: '#2e7d32', padding: '10px', marginBottom: '15px'}}>{success}</div>}
          
          <form onSubmit={handleSubmit} className="responder-form">
            <div className="form-group" style={{marginBottom: '15px'}}>
              <label style={{display:'block', marginBottom: '5px', fontWeight: 'bold'}}>Decision:</label>
              <div className="decision-buttons" style={{display: 'flex', gap: '10px'}}>
                <button 
                  type="button" 
                  style={{flex: 1, padding: '10px', border: '1px solid #ccc', background: decision === 'VERIFY' ? '#e8f5e9' : '#fff', cursor: 'pointer', borderRadius: '4px'}}
                  onClick={() => setDecision('VERIFY')}
                >
                  ✅ Verify
                </button>
                <button 
                  type="button" 
                  style={{flex: 1, padding: '10px', border: '1px solid #ccc', background: decision === 'REJECT' ? '#ffebee' : '#fff', cursor: 'pointer', borderRadius: '4px'}}
                  onClick={() => setDecision('REJECT')}
                >
                  ❌ Reject
                </button>
                <button 
                  type="button" 
                  style={{flex: 1, padding: '10px', border: '1px solid #ccc', background: decision === 'ESCALATE' ? '#fff3e0' : '#fff', cursor: 'pointer', borderRadius: '4px'}}
                  onClick={() => setDecision('ESCALATE')}
                >
                  ⏳ Needs More Evidence
                </button>
              </div>
            </div>

            <div className="form-group" style={{marginBottom: '15px'}}>
              <label style={{display:'block', marginBottom: '5px', fontWeight: 'bold'}}>Rationale:</label>
              <textarea 
                rows="4"
                style={{width: '100%', padding: '10px', borderRadius: '4px', border: '1px solid #ccc', fontFamily: 'inherit'}}
                placeholder="Provide a detailed rationale for this decision..."
                value={rationale}
                onChange={(e) => setRationale(e.target.value)}
              />
            </div>
            
            <div className="form-group" style={{marginBottom: '15px'}}>
              <label style={{display:'block', marginBottom: '5px', fontWeight: 'bold'}}>Responder Name:</label>
              <input 
                type="text" 
                style={{width: '100%', padding: '10px', borderRadius: '4px', border: '1px solid #ccc', fontFamily: 'inherit'}}
                value={responderName}
                onChange={(e) => setResponderName(e.target.value)}
              />
            </div>

            <button type="submit" className="btn-primary" disabled={loading || !decision || !rationale.trim()} style={{width: '100%', padding: '12px'}}>
              {loading ? 'Submitting...' : 'Submit Decision'}
            </button>
          </form>
        </div>

        <div className="responder-history-area" style={{marginTop: '30px', borderTop: '1px solid #eee', paddingTop: '20px'}}>
          <h3>Decision History</h3>
          <div className="current-human-status" style={{marginBottom: '15px'}}>
            <strong>Current Human Status: </strong> 
            <span className={`human-status-badge ${incident.human_status.toLowerCase().replace(/ /g, '-')}`}>
              {incident.human_status}
            </span>
          </div>

          {incident.responder_verifications && incident.responder_verifications.length > 0 ? (
            <div className="responder-records-list" style={{display: 'flex', flexDirection: 'column', gap: '15px'}}>
              {incident.responder_verifications.slice().reverse().map((item) => (
                <div key={item.id} className="responder-card" style={{padding: '15px', border: '1px solid #ddd', borderRadius: '6px', background: '#f9f9f9'}}>
                  <div className="responder-header" style={{display: 'flex', justifyContent: 'space-between', marginBottom: '10px', fontSize: '0.9em', color: '#555'}}>
                    <span className="responder-badge" style={{fontWeight: 'bold', color: item.verification_status === 'Verified' ? '#2e7d32' : item.verification_status === 'Rejected' ? '#c62828' : '#e65100'}}>
                      {item.verification_status === 'Verified' ? '✅ VERIFIED' : 
                       item.verification_status === 'Rejected' ? '❌ REJECTED' : 
                       '⏳ NEEDS MORE EVIDENCE'}
                    </span>
                    <span className="responder-id">By: {item.responder_name || `Officer #${item.responder_id || 'Unknown'}`}</span>
                    <span className="responder-time">
                      {item.verified_at ? new Date(item.verified_at).toLocaleString() : 'N/A'}
                    </span>
                  </div>
                  <div className="responder-notes" style={{fontSize: '0.95em'}}>
                    <strong>Rationale:</strong> "{item.notes || 'No rationale provided.'}"
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div className="empty-sub-box" style={{padding: '20px', textAlign: 'center', color: '#777', border: '1px dashed #ccc', borderRadius: '4px'}}>
              No human decisions have been made yet.
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
