import requests
import sys
import time

BASE_URL = "http://localhost:8000"

def e2e_report_flow():
    print("1. Submitting a new Citizen Report...")
    payload = {
        "category": "Roads",
        "issue_type": "Pothole",
        "description": "Massive pothole on main street, very dangerous.",
        "zone": "Downtown",
        "citizen_severity": "High",
        "latitude": 34.0522,
        "longitude": -118.2437
    }
    
    resp = requests.post(f"{BASE_URL}/api/reports", json=payload)
    resp.raise_for_status()
    result = resp.json()
    
    report_id = result["report"]["report_id"]
    incident_id = result["report"]["incident_id"]
    
    print(f"✅ Report submitted successfully!")
    print(f"Report ID: {report_id}")
    print(f"Assigned Incident ID: {incident_id}")
    
    time.sleep(1) # wait a moment
    
    print("\n2. Searching for the Report in Officer Dashboard (Recent Reports)...")
    # In the dashboard, recent reports are fetched
    resp = requests.get(f"{BASE_URL}/api/reports/recent?limit=10")
    resp.raise_for_status()
    recent_reports = resp.json()
    
    found_report = next((r for r in recent_reports if r["report_id"] == report_id), None)
    if not found_report:
        print("❌ ERROR: Report not found in recent reports!")
        sys.exit(1)
        
    print(f"✅ Report found in Recent Reports queue!")
    
    print("\n3. Verifying corresponding Incident details...")
    resp = requests.get(f"{BASE_URL}/api/incidents/{incident_id}")
    resp.raise_for_status()
    found_incident = resp.json()
    
    print(f"✅ Incident {incident_id} fetched successfully!")
    print(f"Incident Freshness: {found_incident['freshness']}")
    
    if found_incident['freshness'] != 'Pending' and found_incident['freshness'] != 'Just now' and found_incident['freshness'] != 'Fresh':
        print(f"⚠️ Warning: Expected freshness to be Pending/Fresh/Just now, got {found_incident['freshness']}")
        
    print("\n4. Verifying Drilldown Data (Map/Location/etc)...")
    incident_detail = found_incident
    
    print(f"Latitude: {incident_detail['latitude']}")
    print(f"Longitude: {incident_detail['longitude']}")
    if incident_detail['latitude'] != 34.0522 or incident_detail['longitude'] != -118.2437:
        print("❌ ERROR: Location mismatch in drilldown!")
        sys.exit(1)
        
    print("✅ Drilldown data matches perfectly.")
    print("\n🚀 E2E Report Flow Completed Successfully!")

if __name__ == "__main__":
    e2e_report_flow()
