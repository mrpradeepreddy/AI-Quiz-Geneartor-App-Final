import streamlit as st
import requests

from student_page import handle_assessment_invite
from student_stats_utils import fetch_student_scores
import plotly.express as px

API_BASE_URL = "http://localhost:8000/api/v1"

# -------------------------------------------------------------------
#  API HELPER
# -------------------------------------------------------------------

def get_student_dashboard_data_api():
    """Fetches personalized assessment data for the logged-in student."""
    if not st.session_state.token:
        return []
    try:
        headers = {"Authorization": f"Bearer {st.session_state.token}"}
        response = requests.get(f"{API_BASE_URL}/user_assessments/students/me/assessments", headers=headers)
        if response.status_code == 200:
            return response.json()
        return []
    except requests.exceptions.RequestException:
        return []

def get_recruiter_assessments_api():
    """Fetches assessments from the recruiter the student is linked to."""
    if not st.session_state.token:
        return []
    try:
        headers = {"Authorization": f"Bearer {st.session_state.token}"}
        response = requests.get(f"{API_BASE_URL}/recruiter-code/recruiter-assessments", headers=headers)
        if response.status_code == 200:
            return response.json().get('assessments', [])
        return []
    except requests.exceptions.RequestException:
        return []

def get_my_recruiter_info_api():
    """Gets information about the recruiter the student is linked to."""
    if not st.session_state.token:
        return None
    try:
        headers = {"Authorization": f"Bearer {st.session_state.token}"}
        response = requests.get(f"{API_BASE_URL}/recruiter-code/my-recruiter", headers=headers)
        if response.status_code == 200:
            return response.json()
        return None
    except requests.exceptions.RequestException:
        return None

def validate_recruiter_code_api(recruiter_code: str):
    """Validates a recruiter code via the backend API."""
    try:
        response = requests.post(
            f"{API_BASE_URL}/recruiter-code/validate",
            json={"recruiter_code": recruiter_code}
        )
        if response.status_code == 200:
            return response.json()
        return None
    except requests.exceptions.RequestException:
        return None

def link_to_recruiter_api(recruiter_code: str):
    """Links the student to a recruiter via the backend API."""
    if not st.session_state.token:
        return None
    try:
        headers = {"Authorization": f"Bearer {st.session_state.token}"}
        response = requests.post(
            f"{API_BASE_URL}/recruiter-code/link",
            json={"recruiter_code": recruiter_code},
            headers=headers
        )
        if response.status_code == 200:
            return response.json()
        return None
    except requests.exceptions.RequestException:
        return None

# -------------------------------------------------------------------
#  RECRUITER CODE MODAL
# -------------------------------------------------------------------

def show_recruiter_code_modal():
    """Shows a modal for entering recruiter code."""
    with st.container(border=True):
        st.subheader("🔗 Enter Recruiter Code")
        st.write("Enter the recruiter code provided to you to access their assessments.")
        
        recruiter_code = st.text_input(
            "Recruiter Code",
            placeholder="Enter recruiter code (UUID or code)",
            key="recruiter_code_input"
        )
        
        col1, col2 = st.columns([1, 1])
        
        with col1:
            if st.button("🔍 Validate Code", key="validate_code_btn"):
                if recruiter_code and len(recruiter_code) >= 6:
                    validation_result = validate_recruiter_code_api(recruiter_code)
                    if validation_result and validation_result.get('is_valid'):
                        st.success(f"✅ Valid code for {validation_result['recruiter_name']}")
                        st.session_state.validated_recruiter_code = recruiter_code
                        st.session_state.validated_recruiter_name = validation_result['recruiter_name']
                    else:
                        st.error("❌ Invalid recruiter code. Please check and try again.")
                else:
                    st.warning("Please enter a valid recruiter code.")
        
        with col2:
            if st.button("🔗 Link to Recruiter", key="link_recruiter_btn", disabled=not st.session_state.get('validated_recruiter_code')):
                if st.session_state.get('validated_recruiter_code'):
                    link_result = link_to_recruiter_api(st.session_state.validated_recruiter_code)
                    if link_result:
                        st.success(f"✅ Successfully linked to {link_result['recruiter_name']}!")
                        st.info(f"📚 {len(link_result['linked_assessments'])} assessments are now available to you.")
                        
                        # Clear session state
                        if 'validated_recruiter_code' in st.session_state:
                            del st.session_state.validated_recruiter_code
                        if 'validated_recruiter_name' in st.session_state:
                            del st.session_state.validated_recruiter_name
                        
                        # Refresh the page to show new assessments
                        st.rerun()
                    else:
                        st.error("❌ Failed to link to recruiter. Please try again.")

# -------------------------------------------------------------------
#  MAIN STUDENT DASHBOARD ROUTER
# -------------------------------------------------------------------

def show_student_dashboard():
    """Displays the main dashboard and sidebar navigation for a student."""
    user_name = st.session_state.user.get('name', 'Student')
    st.sidebar.title(f"Welcome, {user_name}! 👋")

    # Check if student is linked to a recruiter
    recruiter_info = get_my_recruiter_info_api()
    
    # Show recruiter info if linked
    if recruiter_info and recruiter_info.get('recruiter'):
        recruiter = recruiter_info['recruiter']
        st.sidebar.success(f"🔗 Linked to: {recruiter['name']}")
        st.sidebar.info(f"📧 {recruiter['email']}")
    
    # Add recruiter code button
    if st.sidebar.button("🔗 Enter Recruiter Code", key="enter_recruiter_code_btn"):
        st.session_state.show_recruiter_code_modal = True

    # --- Sidebar Navigation ---
    student_choice = st.sidebar.radio(
        "Navigation",
        ["Assessments", "My Progress", "Statistics",""],
        label_visibility="collapsed"
    )

    # Show recruiter code modal if requested
    if st.session_state.get('show_recruiter_code_modal', False):
        show_recruiter_code_modal()
        if st.button("❌ Close", key="close_modal_btn"):
            st.session_state.show_recruiter_code_modal = False
            st.rerun()

    # --- Page Routing based on sidebar selection ---
    if student_choice == "Assessments":
        display_student_assessments_view()
    elif student_choice == "My Progress":
        display_student_progress_view()
    elif student_choice == "Statistics":
        display_student_stats_view()

# -------------------------------------------------------------------
#  DASHBOARD VIEWS (PAGES)
# -------------------------------------------------------------------

def display_student_assessments_view():
    """The default view showing available and completed assessments."""
    st.title("My Assessments")
    st.markdown("Here are your assigned assessments. Good luck!")
    st.markdown("---")

    # Get both regular student assessments and recruiter assessments
    student_assessments = get_student_dashboard_data_api()
    recruiter_assessments = get_recruiter_assessments_api()
    
    # Combine and deduplicate assessments
    all_assessments = []
    seen_assessment_ids = set()
    
    # Add student assessments
    for sa in student_assessments:
        if sa['assessment_id'] not in seen_assessment_ids:
            all_assessments.append(sa)
            seen_assessment_ids.add(sa['assessment_id'])
    
    # Add recruiter assessments
    for ra in recruiter_assessments:
        if ra['id'] not in seen_assessment_ids:
            # Convert recruiter assessment format to match student assessment format
            converted_assessment = {
                'assessment_id': ra['id'],
                'assessment_name': ra['name'],
                'status': ra['status'],
                'score': ra['score'],
                'start_time': ra['start_time'],
                'end_time': ra['end_time']
            }
            all_assessments.append(converted_assessment)
            seen_assessment_ids.add(ra['id'])
    
    if not all_assessments:
        st.info("You have no assigned assessments at the moment.")
        return

    available = [sa for sa in all_assessments if sa['status'] != 'Completed']
    completed = [sa for sa in all_assessments if sa['status'] == 'Completed']

    tab1, tab2 = st.tabs(["▶️ Available to Take", "✅ Completed"])

    with tab1:
        if not available:
            st.write("You have no new assessments to take. Great job!")
        else:
            for sa in available:
                with st.container(border=True):
                    st.subheader(sa['assessment_name'])
                    if st.button("Start Assessment", key=f"start_{sa['assessment_id']}"):
                        handle_assessment_invite(str(sa['assessment_id']), st.session_state.token)
    with tab2:
        if not completed:
            st.write("You have not completed any assessments yet.")
        else:
            for sa in completed:
                with st.container(border=True):
                    st.subheader(sa['assessment_name'])
                    st.metric(label="Your Score", value=f"{sa['score']:.2f}%")

def display_student_progress_view():
    st.title("📊 My Progress")
    st.markdown("<h4 style='color:#4F8BF9;'>Track your assessment journey and see your improvement over time!</h4>", unsafe_allow_html=True)
    if not st.session_state.token:
        st.warning("Please log in to view your progress.")
        return
    df = fetch_student_scores(st.session_state.token)
    if df.empty or 'score' not in df:
        st.info("No progress data available yet.")
        return
    df = df[df['score'].notnull()]
    if df.empty:
        st.info("No completed assessments yet.")
        return
    fig = px.line(df, x='assessment_name', y='score', markers=True, title='Score Progression', labels={'score': 'Score (%)', 'assessment_name': 'Assessment'})
    fig.update_traces(line_color='#4F8BF9', marker_color='#F97C4F')
    st.plotly_chart(fig, use_container_width=True)
    st.markdown("<div style='margin-top:20px; color:#888;'>Keep up the good work! 🚀</div>", unsafe_allow_html=True)

def display_student_stats_view():
    st.title("📈 My Statistics")
    st.markdown("<h4 style='color:#F97C4F;'>Your performance at a glance</h4>", unsafe_allow_html=True)
    if not st.session_state.token:
        st.warning("Please log in to view your statistics.")
        return
    df = fetch_student_scores(st.session_state.token)
    if df.empty or 'score' not in df:
        st.info("No statistics available yet.")
        return
    df = df[df['score'].notnull()]
    if df.empty:
        st.info("No completed assessments yet.")
        return
    avg_score = df['score'].mean()
    max_score = df['score'].max()
    min_score = df['score'].min()
    st.metric("Average Score", f"{avg_score:.2f}%")
    st.metric("Best Score", f"{max_score:.2f}%")
    st.metric("Lowest Score", f"{min_score:.2f}%")
    fig = px.bar(df, x='assessment_name', y='score', color='score', color_continuous_scale='Blues', title='Scores by Assessment', labels={'score': 'Score (%)', 'assessment_name': 'Assessment'})
    fig.update_layout(showlegend=False)
    st.plotly_chart(fig, use_container_width=True)
    st.markdown("<div style='margin-top:20px; color:#888;'>Review your results and aim higher! 🌟</div>", unsafe_allow_html=True)