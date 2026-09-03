import json
from datetime import datetime, timedelta
from pprint import pprint

from fastapi.testclient import TestClient

from main import app
from database.connection import SessionLocal
from models.models import Report, Incident, IncidentReport
from sqlalchemy import select, func

client = TestClient(app)

BASE_LAT = 11.0168
BASE_LON = 76.9558

def post_report(payload):
    r = client.post('/api/reports', json=payload)
    try:
        body = r.json()
    except Exception:
        body = r.text
    return r.status_code, body


def insert_report_and_incident(session, lat, lon, category, issue_type, minutes_offset=0):
    now = datetime.utcnow()
    reported_time = now - timedelta(minutes=minutes_offset)
    report = Report(
        report_id=f'RPT-VAL-{int(datetime.utcnow().timestamp()*1000)}',
        category=category,
        issue_type=issue_type,
        description='validation insert',
        zone='Test',
        latitude=lat,
        longitude=lon,
        reported_time=reported_time,
        citizen_severity='Low',
        location_status='Available',
        freshness_status='Pending',
    )
    session.add(report)
    session.flush()
    incident = Incident(
        incident_id=f'INC-VAL-{int(datetime.utcnow().timestamp()*1000)}',
        category=category,
        issue_type=issue_type,
        zone='Test',
        status='Pending',
    )
    session.add(incident)
    session.flush()
    link = IncidentReport(incident_id=incident.id, report_id=report.id)
    session.add(link)
    session.commit()
    return incident.incident_id


def run():
    session = SessionLocal()
    results = {'posted': [], 'created_incidents': []}
    try:
        print('1) Submit 5 close pothole reports and verify they attach to ONE incident')
        pothole_ids = []
        payloads = []
        deltas = [0.0, 0.0005, -0.0006, 0.0007, -0.0004]
        for d in deltas:
            payload = {
                'category': 'Roads',
                'issue_type': 'Pothole',
                'description': 'Pothole near main',
                'zone': 'North',
                'latitude': BASE_LAT + d,
                'longitude': BASE_LON,
                'citizen_severity': 'Medium',
            }
            status, body = post_report(payload)
            print('posted status', status, 'body', body)
            payloads.append((status, body))
            incident_id = body.get('report', {}).get('incident_id') if isinstance(body, dict) else None
            pothole_ids.append(incident_id)
        print('Collected incident ids for 5 reports:', pothole_ids)
        same = len(set([i for i in pothole_ids if i is not None])) == 1
        print('All 5 attached to same incident?', same)
        results['posted'].append(('5_close_potholes', payloads, pothole_ids, same))

        print('\n2) Submit another pothole 5km away and verify a NEW incident is created')
        payload_far = {
            'category': 'Roads',
            'issue_type': 'Pothole',
            'description': 'Pothole far away',
            'zone': 'North',
            'latitude': BASE_LAT + 0.045,  # ~5km north
            'longitude': BASE_LON,
            'citizen_severity': 'Medium',
        }
        status_far, body_far = post_report(payload_far)
        print('posted far status', status_far, 'body', body_far)
        far_incident = body_far.get('report', {}).get('incident_id') if isinstance(body_far, dict) else None
        print('Far incident id:', far_incident)
        results['posted'].append(('pothole_far', (status_far, body_far), far_incident))

        print('\n3) Submit lighting issue at same location and verify NEW incident')
        payload_light = {
            'category': 'Lighting',
            'issue_type': 'Streetlight outage',
            'description': 'Light outage near main',
            'zone': 'North',
            'latitude': BASE_LAT,
            'longitude': BASE_LON,
            'citizen_severity': 'Low',
        }
        status_light, body_light = post_report(payload_light)
        print('posted lighting status', status_light, 'body', body_light)
        light_incident = body_light.get('report', {}).get('incident_id') if isinstance(body_light, dict) else None
        print('Lighting incident id:', light_incident)
        results['posted'].append(('lighting_same_loc', (status_light, body_light), light_incident))

        print('\n4) Submit waste issue at same location and verify NEW incident')
        payload_waste = {
            'category': 'Waste',
            'issue_type': 'Overflowing bin',
            'description': 'Overflowing bin near main',
            'zone': 'North',
            'latitude': BASE_LAT,
            'longitude': BASE_LON,
            'citizen_severity': 'Low',
        }
        status_waste, body_waste = post_report(payload_waste)
        print('posted waste status', status_waste, 'body', body_waste)
        waste_incident = body_waste.get('report', {}).get('incident_id') if isinstance(body_waste, dict) else None
        print('Waste incident id:', waste_incident)
        results['posted'].append(('waste_same_loc', (status_waste, body_waste), waste_incident))

        print('\n5) Test correlation boundaries: distance 200m / 201m and time 60min / 61min')
        # Distance boundary: insert existing report at ~200m and ~201m, then post new report at base and check matching
        # 200m ~ 0.001802 degrees latitude
        lat_200 = BASE_LAT + 0.001802
        lat_201 = BASE_LAT + 0.00182
        inc200 = insert_report_and_incident(session, lat_200, BASE_LON, 'Roads', 'Pothole', minutes_offset=0)
        inc201 = insert_report_and_incident(session, lat_201, BASE_LON, 'Roads', 'Pothole', minutes_offset=0)
        print('Inserted incidents for 200m and 201m test:', inc200, inc201)
        # Post new report at base, should match inc200 but not inc201; however since both incidents exist, first matching incident returned by logic may be inc200 depending on query ordering.
        status_d, body_d = post_report({'category':'Roads','issue_type':'Pothole','description':'Boundary test','zone':'Test','latitude':BASE_LAT,'longitude':BASE_LON,'citizen_severity':'Low'})
        new_inc = body_d.get('report',{}).get('incident_id') if isinstance(body_d, dict) else None
        print('New report matched incident id (distance test):', new_inc)
        results['posted'].append(('distance_boundary', (status_d, body_d), new_inc))

        # Time boundary: insert reports at now-60 and now-61 minutes
        inc_t60 = insert_report_and_incident(session, BASE_LAT+0.0001, BASE_LON, 'Roads', 'Pothole', minutes_offset=60)
        inc_t61 = insert_report_and_incident(session, BASE_LAT+0.0002, BASE_LON, 'Roads', 'Pothole', minutes_offset=61)
        print('Inserted incidents for time test:', inc_t60, inc_t61)
        status_t, body_t = post_report({'category':'Roads','issue_type':'Pothole','description':'Time boundary test','zone':'Test','latitude':BASE_LAT+0.00015,'longitude':BASE_LON,'citizen_severity':'Low'})
        matched_time_inc = body_t.get('report',{}).get('incident_id') if isinstance(body_t, dict) else None
        print('New report matched incident id (time test):', matched_time_inc)
        results['posted'].append(('time_boundary', (status_t, body_t), matched_time_inc))

        print('\n6) Query PostgreSQL for totals and reports per incident')
        total_incidents = session.execute(select(func.count(Incident.id))).scalar_one()
        print('Total incidents in DB:', total_incidents)
        incident_rows = session.execute(select(Incident).order_by(Incident.created_at.desc()).limit(20)).scalars().all()
        reports_per_incident = {}
        for inc in incident_rows:
            count = session.execute(select(func.count(IncidentReport.id)).where(IncidentReport.incident_id==inc.id)).scalar_one()
            reports_per_incident[inc.incident_id] = count
        pprint(reports_per_incident)
        results['created_incidents_snapshot'] = list(reports_per_incident.items())

        print('\n7) Test incident endpoints')
        r_list = client.get('/api/incidents')
        print('GET /api/incidents status', r_list.status_code)
        r_json = r_list.json() if r_list.status_code==200 else r_list.text
        print('List length or body:', len(r_json) if isinstance(r_json, list) else r_json)
        # pick one incident id from earlier pothole cluster
        example_inc = pothole_ids[0]
        r_detail = client.get(f'/api/incidents/{example_inc}')
        print(f'GET /api/incidents/{example_inc} status', r_detail.status_code)
        print('detail body:', r_detail.json() if r_detail.status_code==200 else r_detail.text)
        r_reports = client.get(f'/api/incidents/{example_inc}/reports')
        print(f'GET /api/incidents/{example_inc}/reports status', r_reports.status_code)
        print('reports body or message:', r_reports.text)

        print('\n8) Frontend check: cannot run browser here, but /api/incidents and /api/incidents/{id} were validated above')

        print('\nSummary results:')
        pprint(results)

    finally:
        session.close()


if __name__ == '__main__':
    run()
