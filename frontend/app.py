import streamlit as st
import requests
import time
from register import show_register_page
from login_page import show_login_page
from dashboard import show_dashboard
from assessment_page import show_create_assessment_page
from get_assess import show_assessment, show_results_page
from student_page import handle_assessment_invite
from take_assessment import show_take_assessment_page
from view_assess_page import show_view_assessment_page

# --- Page Configuration ---
st.set_page_config(
    page_title="Quiz Application",
    page_icon="🎯",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- API Configuration ---
API_BASE_URL = "http://localhost:8000/api/v1"

# --- Query Param Helper (works with new/old Streamlit) ---
def get_query_param(key: str):
    try:
        if hasattr(st, "query_params"):
            val = st.query_params.get(key)
        else:
            # Fallback for older Streamlit versions
            qp = st.experimental_get_query_params()
            val = qp.get(key)
        if isinstance(val, list):
            return val[0] if val else None
        return val
    except Exception:
        return None

# --- Initialize Session State ---
def initialize_session_state():
    """Initializes all necessary keys in the session state and persists login across refreshes."""
    import streamlit as st
    defaults = {
        'token': None,
        'user': None,
        'page': 'login',
        'current_assessment_id': None,
        'test_started': False, # For student page
        'user_answers': {},   # For student page
        'start_time': None    # For student page
    }
    
    # Only use query params for first-time deep-linking (invite links) and optional JWT restore
    invite_token = get_query_param('invite')
    jwt_token = get_query_param('jwt')
    recruiter_code = get_query_param('recruiter_code')  # New: handle recruiter code

    if invite_token:
        st.session_state['invite'] = invite_token

    if recruiter_code:
        st.session_state['recruiter_code'] = recruiter_code

    # If we don't have a session user but we have a jwt in URL, try to restore via /auth/me
    if (('user' not in st.session_state) or (st.session_state['user'] is None)) and jwt_token:
        try:
            headers = {"Authorization": f"Bearer {jwt_token}"}
            resp = requests.get(f"{API_BASE_URL}/auth/me", headers=headers, timeout=5)
            if resp.status_code == 200:
                st.session_state['token'] = jwt_token
                st.session_state['user'] = resp.json()
                # Clean URL after restoring
                st.query_params.clear()
        except Exception:
            pass
    
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value

# Call the initialization function once at the start
initialize_session_state()

# --- Custom CSS ---
st.markdown("""
    <style>
    .main-header {
        font-size: 3rem;
        color: #1f77b4;
        text-align: center;
        margin-bottom: 2rem;
    }
    .question-card {
        background-color: #f0f2f6;
        padding: 2rem;
        border-radius: 10px;
        margin: 1rem 0;
        border: 1px solid #e0e0e0;
    }
    .stButton>button {
        width: 100%;
        margin: 0.5rem 0;
    }
    .success-message {
        color: #28a745;
        font-weight: bold;
    }
    .error-message {
        color: #dc3545;
        font-weight: bold;
    }
    </style>
""", unsafe_allow_html=True)

# --- Main App Logic ---
def main():
    """Main function to control page navigation."""
    
    # Prevent infinite loops by checking if we've already processed the current request
    current_invite = get_query_param('invite')
    current_recruiter_code = get_query_param('recruiter_code')
    
    # Check if we've already processed these parameters in this session
    processed_invite = st.session_state.get('processed_invite')
    processed_recruiter_code = st.session_state.get('processed_recruiter_code')
    
    # Process invitation token if present and not already processed
    if (current_invite and 
        current_invite != processed_invite and 
        st.session_state.get('user') and 
        st.session_state.get('token')):
        
        st.session_state['processed_invite'] = current_invite
        
        try:
            headers = {"Authorization": f"Bearer {st.session_state.token}"}
            resp = requests.post(
                f"{API_BASE_URL}/invites/accept/{current_invite}", 
                headers=headers, 
                timeout=10
            )
            
            if resp.status_code == 200:
                st.success("✅ Invite accepted! Assessment assigned successfully.")
            elif resp.status_code == 400:
                st.error("❌ This invitation link is invalid or has expired.")
            elif resp.status_code == 404:
                st.error("❌ Assessment not found for this invitation.")
            else:
                st.warning("⚠️ Unable to process invitation. Please try again later.")
                
        except requests.exceptions.Timeout:
            st.error("⏰ Request timed out. Please check your connection and try again.")
        except requests.exceptions.ConnectionError:
            st.error("🔌 Connection error. Please check if the server is running.")
        except Exception as e:
            st.error(f"❌ Error processing invitation: {str(e)}")
        
        # Clean the URL after processing
        try:
            if hasattr(st, "query_params"):
                st.query_params.clear()
        except Exception:
            pass
        time.sleep(2)  # Show message briefly
        st.rerun()

    # Process recruiter code if present and not already processed
    elif (current_recruiter_code and 
          current_recruiter_code != processed_recruiter_code and 
          st.session_state.get('user') and 
          st.session_state.get('token')):
        
        st.session_state['processed_recruiter_code'] = current_recruiter_code
        
        try:
            headers = {"Authorization": f"Bearer {st.session_state.token}"}
            resp = requests.post(
                f"{API_BASE_URL}/recruiter-code/link",
                json={"recruiter_code": current_recruiter_code},
                headers=headers,
                timeout=10
            )
            
            if resp.status_code == 200:
                result = resp.json()
                st.success(f"✅ Successfully linked to {result['recruiter_name']}!")
                st.info(f"📚 {len(result['linked_assessments'])} assessments are now available to you.")
            elif resp.status_code == 400:
                st.error("❌ Invalid recruiter code or already linked.")
            elif resp.status_code == 403:
                st.error("❌ Only students can link to recruiters.")
            else:
                st.warning("⚠️ Unable to process recruiter code. Please try again later.")
                
        except requests.exceptions.Timeout:
            st.error("⏰ Request timed out. Please check your connection and try again.")
        except requests.exceptions.ConnectionError:
            st.error("🔌 Connection error. Please check if the server is running.")
        except Exception as e:
            st.error(f"❌ Error processing recruiter code: {str(e)}")
        
        # Clean the URL after processing
        try:
            if hasattr(st, "query_params"):
                st.query_params.clear()
        except Exception:
            pass
        time.sleep(2)  # Show message briefly
        st.rerun()

    # Handle unauthenticated users with invitation or recruiter code
    elif (current_invite or current_recruiter_code) and not st.session_state.get('user'):
        # Store the parameters for later processing after login
        if current_invite:
            st.session_state['pending_invite'] = current_invite
        if current_recruiter_code:
            st.session_state['pending_recruiter_code'] = current_recruiter_code
        
        # Clean URL and redirect to login
        try:
            if hasattr(st, "query_params"):
                st.query_params.clear()
        except Exception:
            pass
        st.session_state.page = "login"
        st.rerun()

    # Process pending invitations/recruiter codes after successful login
    elif st.session_state.get('user') and st.session_state.get('token'):
        pending_invite = st.session_state.get('pending_invite')
        pending_recruiter_code = st.session_state.get('pending_recruiter_code')
        
        if pending_invite:
            # Process pending invitation
            try:
                headers = {"Authorization": f"Bearer {st.session_state.token}"}
                resp = requests.post(
                    f"{API_BASE_URL}/invites/accept/{pending_invite}", 
                    headers=headers, 
                    timeout=10
                )
                
                if resp.status_code == 200:
                    st.success("✅ Pending invitation processed! Assessment assigned successfully.")
                else:
                    st.warning("⚠️ Unable to process pending invitation.")
                    
            except Exception as e:
                st.error(f"❌ Error processing pending invitation: {str(e)}")
            
            # Clear pending invitation
            del st.session_state['pending_invite']
            time.sleep(2)
            st.rerun()
            
        elif pending_recruiter_code:
            # Process pending recruiter code
            try:
                headers = {"Authorization": f"Bearer {st.session_state.token}"}
                resp = requests.post(
                    f"{API_BASE_URL}/recruiter-code/link",
                    json={"recruiter_code": pending_recruiter_code},
                    headers=headers,
                    timeout=10
                )
                
                if resp.status_code == 200:
                    result = resp.json()
                    st.success(f"✅ Pending recruiter code processed! Linked to {result['recruiter_name']}.")
                else:
                    st.warning("⚠️ Unable to process pending recruiter code.")
                    
            except Exception as e:
                st.error(f"❌ Error processing pending recruiter code: {str(e)}")
            
            # Clear pending recruiter code
            del st.session_state['pending_recruiter_code']
            time.sleep(2)
            st.rerun()
    
    # Get the current page
    page = st.session_state.get('page', 'login')

    if page == "take_assessment":
        # This route is accessible to anyone with the link, no login required.
        show_take_assessment_page()

    # --- Priority 2: The Main Authentication Gate ---
    elif not st.session_state.get('user'):
        # --- Unauthenticated User Routing (Login and Register) ---
        if page == 'register':
            show_register_page()
        else: # Default to login for any other page state
            show_login_page()
        
        return # Stop here for unauthenticated users

    else:
        if page == 'dashboard':
            show_dashboard()
        elif page == 'assessment':
            show_assessment()
        elif page == 'results':
            show_results_page()
        elif page == 'create_assessment':
            show_create_assessment_page()
        elif page == 'view_assessment':
            show_view_assessment_page()
        else:
            # If the page state is invalid for a logged-in user, reset to the dashboard.
            st.session_state.page = 'dashboard'
            st.rerun()

if __name__ == "__main__":
    main()