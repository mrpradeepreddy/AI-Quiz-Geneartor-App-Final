import streamlit as st
import requests
import time
from student_page import handle_assessment_invite

API_BASE_URL = "http://localhost:8000/api/v1"

def authenticate_user(email, username, password):
    """Authenticate user and get JWT token."""
    try:
        response = requests.post(
            f"{API_BASE_URL}/auth/login",
            json={"email": email, "username": username, "password": password}
        )
        if response.status_code == 200:
            response_data = response.json()
            user_info = {
                "email": response_data.get("email"),
                "username": response_data.get("username"),
                "role": response_data.get("role")
            }
            # Store in session state for persistence (not in query params)
            st.session_state.token = response_data["access_token"]
            st.session_state.user = user_info
            return {"access_token": response_data["access_token"], "user": user_info}
        st.error(f"Login failed: {response.json().get('detail', 'Invalid credentials')}")
        return None
    except requests.exceptions.ConnectionError as e:
        st.error(f"Connection error: Could not connect to the server. Please ensure it's running. Details: {e}")
        return None


def show_login_page():
    """Displays the login and registration forms."""
    st.markdown("<h1 class='main-header'>🎯 Quiz Application</h1>", unsafe_allow_html=True)

    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        with st.form("login_form"):
            st.markdown("### Login")
            email = st.text_input("Email", placeholder="Enter your email")
            username = st.text_input("Username", placeholder="Enter your username")
            password = st.text_input("Password", type="password", placeholder="Enter your password")
            submitted = st.form_submit_button("Login", use_container_width=True)

            if submitted:
                if not username or not password:
                    st.warning("Please enter your username and password.")
                else:
                    auth_data = authenticate_user(email, username, password)
                    if auth_data:
                        st.session_state.page = 'dashboard'
                        st.success("Login successful!")
                        # Persist JWT in URL for refresh recovery
                        try:
                            st.query_params.update({
                                'jwt': st.session_state.token
                            })
                        except Exception:
                            pass
                        # Do NOT clear jwt here; let app.py use it to restore after refresh
                        # --- After login, check for invite token in session state ---
                        invite_token = st.session_state.get('invite')
                        if invite_token:
                            headers = {"Authorization": f"Bearer {st.session_state.token}"}
                            api_url = f"{API_BASE_URL}/invites/accept/{invite_token}"
                            try:
                                response = requests.post(api_url, headers=headers)
                                if response.status_code == 200:
                                    st.success("Invite accepted. Assessment assigned!")
                                    st.session_state.page = 'dashboard'
                                    # Clear invite after successful linking
                                    del st.session_state['invite']
                                    st.rerun()
                                else:
                                    st.warning("Could not accept invite: " + response.text)
                            except Exception as e:
                                st.warning(f"Error accepting invite: {e}")
                        st.rerun()

        st.markdown("---")
        st.markdown("Don't have an account?")
        if st.button("Create Account", use_container_width=True):
            st.session_state.page = 'register'
            st.rerun()