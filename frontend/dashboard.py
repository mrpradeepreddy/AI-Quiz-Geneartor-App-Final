import streamlit as st
import requests
import time
from assessment_page import show_create_assessment_page
from get_assess import get_assessments,get_assessment_questions
from ai_generator import show_ai_generator_page
from invite import show_invite_page
from student_dashboard import show_student_dashboard 
from streamlit_option_menu import option_menu
# from stats_page import show_stats_page

API_BASE_URL = "http://localhost:8000/api/v1"

# -------------------------------------------------------------------
#  THE MAIN DASHBOARD ROUTER
# -------------------------------------------------------------------

def show_dashboard():
    """
    Acts as a router to show the correct dashboard based on user role.
    This is the only function that should be imported into your main app.py.
    """
    if 'user' not in st.session_state or not st.session_state.user:
        st.error("You must be logged in to view the dashboard.")
        st.session_state.page = 'login'
        st.rerun()
        return

    # Check the user's role and call the appropriate dashboard function
    if st.session_state.user.get('role', '').lower() in ['recruiter','admin']:
        show_admin_dashboard()
    else:
        show_student_dashboard()

# -------------------------------------------------------------------
#  THE RECRUITER DASHBOARD
# -------------------------------------------------------------------

def show_admin_dashboard():
    """
    Displays the dashboard with all controls for a recruiter user.
    """
    st.markdown("""
        <style>
        .admin-header {
            font-size: 2.5rem;
            font-weight: bold;
            background: linear-gradient(90deg, #4F8BF9 0%, #F97C4F 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            margin-bottom: 0.5rem;
        }
        .admin-card {
            box-shadow: 0 4px 16px rgba(79,139,249,0.08), 0 1.5px 6px rgba(249,124,79,0.08);
            border-radius: 16px;
            transition: box-shadow 0.2s;
        }
        .admin-card:hover {
            box-shadow: 0 8px 32px rgba(79,139,249,0.18), 0 3px 12px rgba(249,124,79,0.18);
        }
        .admin-sidebar .st-emotion-cache-1avcm0n {
            background: #f0f2f6 !important;
        }
        </style>
    """, unsafe_allow_html=True)
    st.sidebar.title(":blue[Recruiter Dashboard]")
    st.sidebar.markdown(f"#### 👋 Welcome, <span style='color:#4F8BF9'>{st.session_state.user.get('name', 'Recruiter')}</span>!", unsafe_allow_html=True)
    with st.sidebar:
        admin_choice = option_menu(
            menu_title="",
            options=["View Assessments", "Create New Assessment", "Generate-Questions-AI", "Invite Students", "Students Connected", "Stats"],
            icons=["card-checklist", "plus-square-fill", "robot", "person-plus-fill", "people-fill", "bar-chart-line-fill"],
            menu_icon="cast",
            default_index=0,
            styles={
                "container": {"padding": "5px !important", "background-color": "#f0f2f6"},
                "icon": {"color": "#F97C4F", "font-size": "25px"},
                "nav-link": {"font-size": "17px", "text-align": "left", "margin":"0px", "--hover-color": "#e6f0ff"},
                "nav-link-selected": {"background-color": "#4F8BF9", "color": "#fff"},
            }
        )
    # Page routing based on the recruiter's choice
    if admin_choice == "View Assessments":
        display_all_assessments_for_admin()
    elif admin_choice == "Create New Assessment":
        show_create_assessment_page()
    elif admin_choice == "Generate-Questions-AI":
        show_ai_generator_page()
    elif admin_choice == "Invite Students":
        show_invite_page()
    elif admin_choice == "Students Connected":
        show_recruiter_students_connected()
    elif admin_choice == "Stats":
        show_recruiter_stats_page()

# --- Recruiter Stats Page ---
def show_recruiter_stats_page():
    st.markdown("<div class='admin-header'>📊 Student Stats (Your Invited Students)</div>", unsafe_allow_html=True)
    API_BASE_URL = "http://localhost:8000/api/v1"
    headers = {"Authorization": f"Bearer {st.session_state.token}"}
    try:
        # Try to fetch summary stats for charts
        summary = None
        try:
            sresp = requests.get(f"{API_BASE_URL}/user_assessments/recruiter/stats", headers=headers)
            if sresp.status_code == 200:
                summary = sresp.json()
        except Exception:
            summary = None
        response = requests.get(f"{API_BASE_URL}/user_assessments/recruiter/students", headers=headers)
        if response.status_code == 200:
            students = response.json()
        else:
            st.error("Failed to fetch student stats.")
            return
    except Exception as e:
        st.error(f"Error fetching stats: {e}")
        return
    # Chart summary if available
    if summary:
        try:
            import plotly.express as px
            import pandas as pd
            pie_df = pd.DataFrame([
                {"label": "Passed", "value": summary.get("passed", 0)},
                {"label": "Failed", "value": summary.get("failed", 0)}
            ])
            pie = px.pie(pie_df, names="label", values="value", title="Pass vs Fail")
            st.plotly_chart(pie, use_container_width=True)
            bar_df = pd.DataFrame([
                {"label": "Attempted", "value": summary.get("attempted", 0)},
                {"label": "Not Attempted", "value": summary.get("not_attempted", 0)},
                {"label": "Completed", "value": summary.get("completed", 0)}
            ])
            bar = px.bar(bar_df, x="label", y="value", title="Assessment Attempts")
            st.plotly_chart(bar, use_container_width=True)
        except Exception:
            pass
    if not students:
        st.info("No students have accepted your invites yet.")
        return
    import pandas as pd
    # Flatten for table
    rows = []
    for s in students:
        for a in s["assessments"]:
            rows.append({
                "Student Name": s["student_name"],
                "Email": s["student_email"],
                "Assessment": a["assessment_name"],
                "Status": a["status"],
                "Score": a["score"] if a["score"] is not None else "-"
            })
    df = pd.DataFrame(rows)
    st.dataframe(df, use_container_width=True, hide_index=True)
    st.markdown("""
        <style>
        .stDataFrame th, .stDataFrame td {
            font-size: 1.1rem;
            padding: 0.5rem 0.7rem;
        }
        </style>
    """, unsafe_allow_html=True)

def show_recruiter_students_connected():
    st.markdown("<div class='admin-header'>👥 Students Connected</div>", unsafe_allow_html=True)
    headers = {"Authorization": f"Bearer {st.session_state.token}"}
    try:
        response = requests.get(f"{API_BASE_URL}/user_assessments/recruiter/students", headers=headers)
        if response.status_code != 200:
            st.error("Failed to fetch connected students.")
            return
        students = response.json()
    except Exception as e:
        st.error(f"Error: {e}")
        return

    if not students:
        st.info("No students linked yet.")
        return

    import pandas as pd
    simple_rows = []
    for s in students:
        simple_rows.append({
            "Student Name": s.get("student_name"),
            "Email": s.get("student_email"),
            "Total Assigned": s.get("total_assigned"),
            "Completed": s.get("total_completed"),
            "Average Score": round(s.get("average_score", 0.0), 2)
        })
    df = pd.DataFrame(simple_rows)
    st.dataframe(df, use_container_width=True, hide_index=True)

def display_all_assessments_for_admin():
    """The default view for the recruiter, showing a list of all assessments."""
    st.markdown("<div class='admin-header'>📚 All Assessments</div>", unsafe_allow_html=True)
    
    # This function call should be in your api_helpers.py or similar
    assessments = get_assessments()

    if not assessments:
        st.info("No assessments found. Create one from the sidebar.")
        return
    
    def go_to_view_page(assessment_id):
        """Sets the necessary session state to navigate to the view page."""
        st.session_state.current_assessment_id = assessment_id
        st.session_state.page = 'view_assessment'

    # Use 3 columns for a more compact and modern look
    cols = st.columns(3)
    for idx, assessment in enumerate(assessments):
        with cols[idx % 3]:
            with st.container():
                st.markdown("<div class='admin-card' style='padding: 1.5rem; margin-bottom: 1.5rem;'>", unsafe_allow_html=True)
                # --- Card Header ---
                st.subheader(assessment.get('name', 'Untitled Assessment'))
                # Use a colored badge for the status
                status = assessment.get('status', 'N/A').capitalize()
                if status == 'Draft':
                    st.markdown(f"<span style='color:gray; font-weight:bold;'>Status: {status}</span>", unsafe_allow_html=True)
                else:
                    st.markdown(f"<span style='color:green; font-weight:bold;'>Status: {status}</span>", unsafe_allow_html=True)
                st.markdown("<hr style='margin:0.5rem 0;'>", unsafe_allow_html=True)
                # --- Card Body with Metrics ---
                col1, col2 = st.columns(2)
                with col1:
                    st.metric(label="❓ Questions", value=assessment.get('total_questions', 0))
                with col2:
                    st.metric(label="⏱️ Duration", value=f"{assessment.get('duration', 0)} min")
                # --- Card Footer with Button ---
                st.button(
                    "⚙️ Manage",
                    key=f"manage_{assessment['id']}",
                    on_click=go_to_view_page,
                    args=(assessment['id'],),
                    use_container_width=True,
                )
                st.markdown("</div>", unsafe_allow_html=True)

