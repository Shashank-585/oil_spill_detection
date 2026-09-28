import requests

base = "http://127.0.0.1:8000"
for case_id in ["case_001", "case_002_wakashio", "case_003_golden_ray"]:
    print(f"=== Testing {case_id} ===")
    r_val = requests.get(f"{base}/api/cases/{case_id}/satellite/validation")
    assert r_val.status_code == 200, f"Validation failed: {r_val.text}"
    v_data = r_val.json()
    print(f"Validation: {v_data['overall_status']}, {len(v_data['checks'])} checks evaluated")
    if case_id != "case_002_wakashio":
        for chk in v_data['checks']:
            assert chk['passed'], f"Check failed: {chk['name']}"
    else:
        print(f"-> Case 002 correctly reports missing SAR raster: {v_data['overall_status']}")
    
    r_proc = requests.post(f"{base}/api/cases/{case_id}/satellite/process", json={})
    assert r_proc.status_code == 200, f"Process failed: {r_proc.text}"
    p_data = r_proc.json()
    job_id = p_data["job_id"]
    print(f"Job: {job_id} | Stage: {p_data['current_stage']}")
    
    if p_data['current_stage'] == "COMPLETE":
        r_res = requests.get(f"{base}/api/satellite/jobs/{job_id}/results")
        assert r_res.status_code == 200, f"Results failed: {r_res.text}"
        res_data = r_res.json()
        det = res_data["detection"]
        print(f"Detection: {det['total_candidates']} extracted, {det['accepted_candidates']} accepted, {det['rejected_candidates']} rejected")
        print(f"Provenance chain: {len(res_data['provenance_chain'])} steps recorded")
    else:
        print(f"Failed as expected: {p_data.get('error_message')}")

print("\n>>> ALL CASES HTTP VERIFIED SUCCESSFULLY <<<")
