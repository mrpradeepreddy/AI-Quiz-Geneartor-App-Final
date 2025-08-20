import requests
import pandas as pd

API_BASE_URL = "http://localhost:8000/api/v1"

def fetch_student_scores(token):
    headers = {"Authorization": f"Bearer {token}"}
    resp = requests.get(f"{API_BASE_URL}/user_assessments/students/me/assessments", headers=headers)
    if resp.status_code == 200:
        data = resp.json()
        # Expecting: [{assessment_id, assessment_name, status, score}]
        return pd.DataFrame(data)
    return pd.DataFrame([])
