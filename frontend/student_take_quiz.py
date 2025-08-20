import streamlit as st
import requests
import time

API_BASE_URL = "http://localhost:8000/api/v1"

def validate_token(token):
    """Validate the invite token and fetch assessment info."""
    try:
        resp = requests.get(f"{API_BASE_URL}/invites/validate/{token}")
        if resp.status_code == 200:
            return resp.json()
        return None
    except requests.exceptions.RequestException:
        return None

def submit_answers(token, answers):
    """Submit student answers to the backend."""
    try:
        resp = requests.post(f"{API_BASE_URL}/assessments/submit", json={"token": token, "answers": answers})
        return resp.ok
    except requests.exceptions.RequestException:
        return False

def show_take_assessment_page():
    st.title("Take Your Quiz")
    # Get token from query params
    query_params = st.experimental_get_query_params()
    token = query_params.get("token", [None])[0]
    if not token:
        st.error("No invite token found in the URL.")
        return

    quiz = validate_token(token)
    if not quiz:
        st.error("Invalid or expired invite link.")
        return

    st.header(quiz.get("title", "Quiz"))
    answers = {}
    for q in quiz.get("questions", []):
        ans = st.text_input(q.get("text", "Question"), key=str(q.get("id")))
        answers[q.get("id")] = ans

    if st.button("Submit Answers"):
        if submit_answers(token, answers):
            st.success("Your answers have been submitted!")
        else:
            st.error("Submission failed. Please try again.")

if __name__ == "__main__":
    show_take_assessment_page()
