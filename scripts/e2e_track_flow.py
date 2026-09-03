import requests
import sys
import time

BASE_URL = "http://localhost:8000"

def e2e_track_flow():
    print("1. Submitting a new Citizen Report...")
    payload = {
        "category": "Lighting",
        "issue_type": "Multiple lights out",
        "description": "Multiple street lights are not functioning near the main road.",
        "zone": "Central",
        "citizen_severity": "High",
        "latitude": 11.0188,
        "longitude": 76.9582
    }
    
    resp = requests.post(f"{BASE_URL}/api/reports", json=payload)
    resp.raise_for_status()
    result = resp.json()
    
    report_id = result["report"]["report_id"]
    incident_id = result["report"]["incident_id"]
    
    print(f"✅ Report submitted successfully!")
    print(f"Report ID: {report_id}")
    print(f"Assigned Incident ID: {incident_id}")
    
    time.sleep(1) # wait for db
    
    print(f"\n2. Tracking the Report directly via /api/reports/{report_id} ...")
    resp = requests.get(f"{BASE_URL}/api/reports/{report_id}")
    resp.raise_for_status()
    track_result = resp.json()
    
    # Verify extended properties are returned
    required_keys = ['priority_score', 'priority_level', 'confidence_score', 'confidence_level', 'verification_status', 'human_status', 'incident_updated_at']
    for k in required_keys:
        if k not in track_result:
            print(f"❌ ERROR: Key {k} missing from report detail!")
            sys.exit(1)
            
    print(f"✅ All tracking keys found in the response!")
    print(f"Current Human Status: {track_result['human_status']}")
    print(f"Current Priority: {track_result['priority_level']}")
    
    print("\n3. Simulating Officer Review (VERIFY)...")
    decision_payload = {
        "decision": "VERIFY",
        "rationale": "Verified by field officer via CCTV.",
        "responder_name": "Officer Smith"
    }
    resp = requests.post(f"{BASE_URL}/api/incidents/{incident_id}/verification", json=decision_payload)
    resp.raise_for_status()
    print("✅ Officer review submitted.")
    
    time.sleep(1)
    
    print(f"\n4. Tracking the Report again to verify status change...")
    resp = requests.get(f"{BASE_URL}/api/reports/{report_id}")
    resp.raise_for_status()
    updated_track_result = resp.json()
    
    if updated_track_result['human_status'] != 'Verified':
        print(f"❌ ERROR: Expected human_status 'Verified', got {updated_track_result['human_status']}")
        sys.exit(1)
        
    print(f"✅ Human Status updated to: {updated_track_result['human_status']} (VERIFIED on frontend)")
    print("\n🚀 E2E Track Report Flow Completed Successfully!")

if __name__ == "__main__":
    e2e_track_flow()
