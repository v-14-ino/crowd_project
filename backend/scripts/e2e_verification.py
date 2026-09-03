import requests
import sys

BASE_URL = "http://localhost:8000"

def e2e_verification_flow():
    # 1. Fetch incidents
    resp = requests.get(f"{BASE_URL}/api/incidents")
    resp.raise_for_status()
    incidents = resp.json()
    if not incidents:
        print("No incidents found to test.")
        return
    
    incident = incidents[0]
    incident_id = incident["incident_id"]
    print(f"Testing against incident: {incident_id}")

    # 2. VERIFY decision
    print("Submitting VERIFY decision...")
    resp = requests.post(
        f"{BASE_URL}/api/incidents/{incident_id}/verification",
        json={
            "decision": "VERIFY",
            "rationale": "Verified via E2E test",
            "responder_name": "E2E Bot"
        }
    )
    resp.raise_for_status()
    print("VERIFY decision recorded.")

    # 3. REJECT decision
    print("Submitting REJECT decision...")
    resp = requests.post(
        f"{BASE_URL}/api/incidents/{incident_id}/verification",
        json={
            "decision": "REJECT",
            "rationale": "Rejecting via E2E test",
            "responder_name": "E2E Bot"
        }
    )
    resp.raise_for_status()
    print("REJECT decision recorded.")

    # 4. Fetch incident details and confirm history
    print("Fetching updated incident details...")
    resp = requests.get(f"{BASE_URL}/api/incidents/{incident_id}")
    resp.raise_for_status()
    updated_incident = resp.json()
    
    print(f"Current Human Status: {updated_incident['human_status']}")
    print(f"Number of verifications: {len(updated_incident.get('responder_verifications', []))}")
    if updated_incident['human_status'] != 'Rejected':
        print("ERROR: Status did not update correctly.")
        sys.exit(1)
        
    print("E2E Verification Flow Complete!")

if __name__ == "__main__":
    e2e_verification_flow()
