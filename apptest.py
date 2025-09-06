import streamlit as st
import pandas as pd
from datetime import datetime
import hashlib
import random
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import time
from contextlib import contextmanager
import json 

# Page configuration
st.set_page_config(
    page_title="AUSEC Club Management Tool",
    page_icon="🏢",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Google Sheets setup
SHEET_ID = "1VpWC8_P8_z_YW000xx5iWYlXFK5XXBGgtaFpV1kMqVc"

# Add caching for Google Sheets client
@st.cache_resource
def get_cached_gsheet_client():
    """Cache the Google Sheets client to avoid repeated authentication"""
    scope = [
        "https://spreadsheets.google.com/feeds",
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive.file",
        "https://www.googleapis.com/auth/drive"
    ]
    # If running on Streamlit Cloud, write credentials from st.secrets
    if "gcp_service_account" in st.secrets:
        with open("credentials.json", "w") as f:
            json.dump(dict(st.secrets["gcp_service_account"]), f)
    creds = ServiceAccountCredentials.from_json_keyfile_name("credentials.json", scope)
    return gspread.authorize(creds)

def get_worksheet(sheet_name):
    """Get worksheet using cached client"""
    client = get_cached_gsheet_client()
    return client.open_by_key(SHEET_ID).worksheet(sheet_name)

@contextmanager
def show_loading(message="Loading..."):
    """Context manager for showing loading spinner"""
    placeholder = st.empty()
    with placeholder.container():
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            with st.spinner(message):
                yield
    placeholder.empty()

# --- Helper Functions ---
def hash_password(password):
    """Hash password using SHA256"""
    return hashlib.sha256(password.encode()).hexdigest()

def verify_password(password, hashed):
    """Verify password against hash"""
    return hash_password(password) == hashed

def update_tasks_sheet_optimized(df):
    """Optimized version that updates tasks sheet"""
    try:
        with show_loading("Updating tasks..."):
            ws = get_worksheet("Tasks")
            ws.clear()
            if not df.empty:
                data_to_update = [df.columns.values.tolist()] + df.astype(str).values.tolist()
                ws.update(f'A1:Z{len(data_to_update)}', data_to_update)
        return True
    except Exception as e:
        if "Response [200]" not in str(e):
            st.error(f"Error updating tasks: {str(e)}")
        return False

def update_members_sheet_optimized(df):
    """Optimized version for members sheet"""
    try:
        with show_loading("Updating members..."):
            ws = get_worksheet("Members")
            ws.clear()
            if not df.empty:
                data_to_update = [df.columns.values.tolist()] + df.astype(str).values.tolist()
                ws.update(f'A1:Z{len(data_to_update)}', data_to_update)
        return True
    except Exception as e:
        if "Response [200]" not in str(e):
            st.error(f"Error updating members: {str(e)}")
        return False

# Cached data loading with refresh option
@st.cache_data(ttl=30)  # Cache for 30 seconds
def load_data_cached():
    """Cached version of load_data for better performance"""
    try:
        tasks_ws = get_worksheet("Tasks")
        tasks_data = tasks_ws.get_all_records()
        tasks_df = pd.DataFrame(tasks_data) if tasks_data else pd.DataFrame(columns=["TaskID", "TaskName", "AssignedTo", "Role", "Status", "Deadline", "Priority", "Description"])
    except Exception as e:
        tasks_df = pd.DataFrame(columns=["TaskID", "TaskName", "AssignedTo", "Role", "Status", "Deadline", "Priority", "Description"])
    
    try:
        members_ws = get_worksheet("Members")
        members_data = members_ws.get_all_records()
        # Updated columns to include Status and ApprovedBy
        expected_columns = ["Name", "Role", "Password", "Status", "ApprovedBy", "CreatedAt"]
        members_df = pd.DataFrame(members_data) if members_data else pd.DataFrame(columns=expected_columns)
        
        # Add missing columns if they don't exist
        for col in expected_columns:
            if col not in members_df.columns:
                if col == "Status":
                    members_df[col] = "Active"  # Default status
                elif col == "ApprovedBy":
                    members_df[col] = "System"  # Default approver
                elif col == "CreatedAt":
                    members_df[col] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                else:
                    members_df[col] = ""
    except Exception as e:
        expected_columns = ["Name", "Role", "Password", "Status", "ApprovedBy", "CreatedAt"]
        members_df = pd.DataFrame(columns=expected_columns)
    
    # Process columns safely
    if not tasks_df.empty and len(tasks_df.columns) > 0:
        tasks_df.columns = tasks_df.columns.astype(str).str.strip()
    
    if not members_df.empty and len(members_df.columns) > 0:
        members_df.columns = members_df.columns.astype(str).str.strip()
    
    return tasks_df, members_df

# Add refresh button functionality
def show_refresh_button():
    """Show a refresh button to clear cache and reload data"""
    if st.button("🔄 Refresh Data", help="Click to reload data from Google Sheets"):
        load_data_cached.clear()
        st.success("Data refreshed!")
        st.rerun()

# Add connection test function
def test_gsheets_connection():
    """Test Google Sheets connection"""
    try:
        with show_loading("Testing Google Sheets connection..."):
            client = get_cached_gsheet_client()
            sheet = client.open_by_key(SHEET_ID)
            st.success(f"✅ Connected to Google Sheet: {sheet.title}")
            return True
    except Exception as e:
        st.error(f"❌ Connection failed: {str(e)}")
        return False

def get_subordinates(member_name, members_df):
    """Get list of subordinates for a given member based on hierarchy and domain."""
    if members_df.empty:
        return []

    try:
        member_row = members_df[members_df["Name"] == member_name]
        if member_row.empty:
            return []
        member_role = member_row["Role"].iloc[0]

        # Dev: can see all members
        if member_role == "Dev":
            return members_df[members_df["Status"] == "Active"]["Name"].tolist()

        # Core Head: assign to Domain Heads and other Core Heads
        elif member_role == "Core Head":
            allowed_roles = ["Domain Head", "Core Head"]
            return members_df[
                (members_df["Role"].isin(allowed_roles)) & 
                (members_df["Status"] == "Active")
            ]["Name"].tolist()

        # Domain Head: assign to Associate Heads in their domain
        elif member_role == "Domain Head":
            # Find domain (assume domain is in another column, e.g., "Domain")
            if "Domain" in members_df.columns:
                domain = member_row["Domain"].iloc[0]
                return members_df[
                    (members_df["Role"] == "Associate Head") & 
                    (members_df["Domain"] == domain) & 
                    (members_df["Status"] == "Active")
                ]["Name"].tolist()
            else:
                return members_df[
                    (members_df["Role"] == "Associate Head") & 
                    (members_df["Status"] == "Active")
                ]["Name"].tolist()

        # Associate Head: assign to Junior Heads under them
        elif member_role == "Associate Head":
            # If you have a "ReportsTo" or "Parent" column, use it for strict mapping
            if "ReportsTo" in members_df.columns:
                return members_df[
                    (members_df["Role"] == "Junior Head") & 
                    (members_df["ReportsTo"] == member_name) & 
                    (members_df["Status"] == "Active")
                ]["Name"].tolist()
            else:
                return members_df[
                    (members_df["Role"] == "Junior Head") & 
                    (members_df["Status"] == "Active")
                ]["Name"].tolist()

        # Junior Head: no subordinates
        else:
            return []
    except Exception as e:
        return []

def authenticate_user(username, password, members_df):
    """Authenticate user credentials robustly"""
    if members_df.empty:
        return False, None, None, "No users found"

    user_row = members_df[members_df["Name"] == username]
    if user_row.empty:
        return False, None, None, "User not found"

    # Check if user is active (unless they're dev)
    user_status = user_row["Status"].iloc[0] if "Status" in members_df.columns else "Active"
    user_role = user_row["Role"].iloc[0] if "Role" in members_df.columns else ""
    
    if user_role != "Dev" and user_status != "Active":
        if user_status == "Pending":
            return False, None, None, "Account pending approval"
        elif user_status == "Suspended":
            return False, None, None, "Account suspended"
        else:
            return False, None, None, "Account inactive"

    if "Password" in members_df.columns:
        stored_password = str(user_row["Password"].iloc[0])
        # If the stored password looks like a hash (64 hex chars), compare hashes
        if len(stored_password) == 64 and all(c in "0123456789abcdef" for c in stored_password.lower()):
            if hash_password(password) == stored_password:
                return True, username, user_role, "Success"
        else:
            # Otherwise, compare as plain text
            if password == stored_password:
                return True, username, user_role, "Success"
    else:
        # No password column: default password is "password123"
        if password == "password123":
            return True, username, user_role, "Success"

    return False, None, None, "Invalid credentials"

def register_user(name, password, role, members_df, approver=None):
    """Register a new user and add to Members sheet"""
    hashed_pw = hash_password(password)

    # --- NEW LOGIC: Only allow Dev registration if database is empty ---
    if role == "Dev":
        if members_df.empty:
            # First Dev: immediate access, no approval needed
            initial_status = "Active"
            approved_by = "System"
        else:
            # Any further Devs: must be approved by the first Dev
            initial_status = "Pending"
            approved_by = ""
    else:
        initial_status = "Pending"
        approved_by = ""

    new_user = {
        "Name": name,
        "Role": role,
        "Password": hashed_pw,
        "Status": initial_status,
        "ApprovedBy": approved_by,
        "CreatedAt": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }

    if members_df.empty:
        members_df = pd.DataFrame([new_user])
    else:
        if name in members_df["Name"].values:
            return False, "User already exists."
        members_df = pd.concat([members_df, pd.DataFrame([new_user])], ignore_index=True)

    # Save Members sheet
    if update_members_sheet_optimized(members_df):
        if role == "Dev":
            if members_df.empty:
                return True, "Dev registration successful! You can now log in."
            else:
                return True, "Dev registration submitted! Awaiting approval by the parent Dev."
        else:
            return True, "Registration successful! Your account is pending approval by a Dev."
    else:
        return False, "Error saving user."

def approve_user(user_name, members_df, approver_name):
    """Approve a pending user. Only parent Dev can approve new Devs."""
    try:
        user_idx = members_df[members_df["Name"] == user_name].index[0]
        user_role = members_df.at[user_idx, "Role"]

        # Only parent Dev can approve new Devs
        if user_role == "Dev":
            # Find the parent Dev (the first Dev in the database)
            parent_dev_row = members_df[(members_df["Role"] == "Dev") & (members_df["ApprovedBy"] == "System")]
            if not parent_dev_row.empty and approver_name == parent_dev_row.iloc[0]["Name"]:
                members_df.at[user_idx, "Status"] = "Active"
                members_df.at[user_idx, "ApprovedBy"] = approver_name
            else:
                return False, "Only the parent Dev can approve new Devs."
        else:
            members_df.at[user_idx, "Status"] = "Active"
            members_df.at[user_idx, "ApprovedBy"] = approver_name

        if update_members_sheet_optimized(members_df):
            return True, f"User {user_name} approved successfully!"
        else:
            return False, "Error updating user status."
    except Exception as e:
        return False, f"Error approving user: {str(e)}"

def suspend_user(user_name, members_df):
    """Suspend a user account"""
    try:
        user_idx = members_df[members_df["Name"] == user_name].index[0]
        members_df.at[user_idx, "Status"] = "Suspended"
        
        if update_members_sheet_optimized(members_df):
            return True, f"User {user_name} suspended successfully!"
        else:
            return False, "Error suspending user."
    except Exception as e:
        return False, f"Error suspending user: {str(e)}"

def reactivate_user(user_name, members_df):
    """Reactivate a suspended user account"""
    try:
        user_idx = members_df[members_df["Name"] == user_name].index[0]
        members_df.at[user_idx, "Status"] = "Active"
        
        if update_members_sheet_optimized(members_df):
            return True, f"User {user_name} reactivated successfully!"
        else:
            return False, "Error reactivating user."
    except Exception as e:
        return False, f"Error reactivating user: {str(e)}"

def delete_user(user_name, members_df):
    """Delete a user from the database"""
    try:
        members_df = members_df[members_df["Name"] != user_name]
        
        if update_members_sheet_optimized(members_df):
            return True, f"User {user_name} deleted successfully!", members_df
        else:
            return False, "Error deleting user.", members_df
    except Exception as e:
        return False, f"Error deleting user: {str(e)}", members_df

def update_user_role(user_name, new_role, members_df):
    """Update a user's role"""
    try:
        user_idx = members_df[members_df["Name"] == user_name].index[0]
        members_df.at[user_idx, "Role"] = new_role
        
        if update_members_sheet_optimized(members_df):
            return True, f"User {user_name}'s role updated to {new_role}!"
        else:
            return False, "Error updating user role."
    except Exception as e:
        return False, f"Error updating user role: {str(e)}"

def generate_unique_taskid(tasks_df):
    """Generate a unique random TaskID not already in use."""
    if tasks_df.empty or "TaskID" not in tasks_df.columns:
        return random.randint(100000, 999999)
    existing_ids = set(pd.to_numeric(tasks_df["TaskID"], errors="coerce").dropna().astype(int))
    while True:
        new_id = random.randint(100000, 999999)
        if new_id not in existing_ids:
            return new_id

# --- Session State Initialization ---
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False
if "user_name" not in st.session_state:
    st.session_state.user_name = None
if "user_role" not in st.session_state:
    st.session_state.user_role = None
if "page" not in st.session_state:
    st.session_state.page = "login"

# --- Authentication Page ---
def show_login_page():
    st.title("🔐 Club Task Management - Login")
    st.markdown("---")
    
    # Add connection test button
    col1, col2 = st.columns([3, 1])
    with col2:
        if st.button("🔗 Test Connection"):
            test_gsheets_connection()
    
    # Load members data with caching
    _, members_df = load_data_cached()
    
    if members_df.empty:
        st.warning("No users found. Please register the first user.")
        if st.button("Register as First User"):
            st.session_state.page = "register"
            st.rerun()
        return
    
    # Login form
    with st.form("login_form"):
        st.subheader("Sign In")
        active_users = members_df[members_df["Status"] == "Active"]["Name"].tolist() if "Status" in members_df.columns else members_df["Name"].tolist()
        # Always allow Dev users to be visible for login
        dev_users = members_df[members_df["Role"] == "Dev"]["Name"].tolist() if "Role" in members_df.columns else []
        all_available_users = list(set(active_users + dev_users))
        
        username = st.selectbox("Select Your Name", [""] + sorted(all_available_users))
        password = st.text_input("Password", type="password", help="Default password: password123")
        submit_button = st.form_submit_button("Sign In")
        
        if submit_button:
            if username and password:
                with show_loading("Authenticating..."):
                    success, user, role, message = authenticate_user(username, password, members_df)
                    time.sleep(0.3)  # Brief delay for UX
                
                if success:
                    st.session_state.authenticated = True
                    st.session_state.user_name = user
                    st.session_state.user_role = role
                    st.session_state.page = "dashboard"
                    st.success(f"Welcome {user}!")
                    time.sleep(0.5)
                    st.rerun()
                else:
                    st.error(f"Login failed: {message}")
            else:
                st.warning("Please enter both username and password.")
    
    # Refresh button
    show_refresh_button()
    
    st.markdown("Don't have an account? [Register here](#)", unsafe_allow_html=True)
    if st.button("Register as New User"):
        st.session_state.page = "register"
        st.rerun()

    # Help section
    with st.expander("ℹ️ Help & Information"):
        st.info("""
        **Default Login Information:**
        - Password for all users: `password123`
        - Select your name from the dropdown
        
        **Role Hierarchy:**
        - **Dev**: Full database access, can approve/manage all members
        - **Core Head**: Can see all tasks, assign to Domain Heads and other Core Heads
        - **Domain Head**: Can assign to Associates and Junior Heads
        - **Associate Head**: Can assign to Junior Heads
        - **Junior Head**: Can only update their own task status
        
        **Account Status:**
        - **Active**: Full access to the system
        - **Pending**: Waiting for Dev approval
        - **Suspended**: Temporarily blocked access
        
        **Performance Tips:**
        - Data is cached for 30 seconds for faster loading
        - Use "Refresh Data" if you don't see recent changes
        - "Test Connection" verifies Google Sheets access
        """)

# --- Registration Page ---
def show_register_page():
    st.title("📝 Register New User")
    st.markdown("---")
    
    _, members_df = load_data_cached()
    
    # Check if this is the first user (should be Dev)
    if members_df.empty or (members_df[members_df["Role"] == "Dev"].empty):
        st.info("Registering the first user. It's recommended to choose 'Dev' for full administrative access.")
        role_options = ["Dev", "Core Head", "Domain Head", "Associate Head", "Junior Head"]
    else:
        role_options = ["Junior Head", "Associate Head", "Domain Head", "Core Head", "Dev"]
    
    with st.form("register_form"):
        name = st.text_input("Your Name")
        password = st.text_input("Password", type="password")
        confirm_password = st.text_input("Confirm Password", type="password")
        role = st.selectbox("Role", role_options)
        
        if role == "Dev":
            st.warning("⚠️ Dev role has full administrative access including member management.")
        elif role != "Dev" and not members_df.empty and not members_df[members_df["Role"] == "Dev"].empty:
            st.info("ℹ️ Your account will require approval from a Dev before you can access the system.")
        
        submit = st.form_submit_button("Register")

        if submit:
            if not name or not password or not confirm_password:
                st.warning("Please fill all fields.")
            elif password != confirm_password:
                st.warning("Passwords do not match.")
            else:
                with show_loading("Creating user account..."):
                    success, msg = register_user(name, password, role, members_df)
                    time.sleep(0.5)
                
                if success:
                    st.success(msg)
                    # Clear cache to reflect new user
                    load_data_cached.clear()
                    time.sleep(1)
                    st.session_state.page = "login"
                    st.rerun()
                else:
                    st.error(msg)

    # Add Back to Login button
    if st.button("⬅️ Back to Login"):
        st.session_state.page = "login"
        st.rerun()

# --- Dev Management Page ---
def show_dev_management():
    st.title("👨‍💻 Developer Dashboard")
    st.markdown("---")
    
    tasks_df, members_df = load_data_cached()
    
    # Dev statistics
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        total_members = len(members_df)
        st.metric("👥 Total Members", total_members)
    with col2:
        pending_count = len(members_df[members_df["Status"] == "Pending"]) if "Status" in members_df.columns else 0
        st.metric("⏳ Pending Approval", pending_count)
    with col3:
        active_count = len(members_df[members_df["Status"] == "Active"]) if "Status" in members_df.columns else total_members
        st.metric("✅ Active Members", active_count)
    with col4:
        suspended_count = len(members_df[members_df["Status"] == "Suspended"]) if "Status" in members_df.columns else 0
        st.metric("🚫 Suspended", suspended_count)
    
    # Tabs for different dev functions
    tab1, tab2, tab3, tab4 = st.tabs(["👥 Member Management", "✅ Approve Members", "📊 Database View", "⚙️ System Admin"])
    
    with tab1:
        st.subheader("👥 Member Management")
        
        if not members_df.empty:
            # Filter options
            col1, col2 = st.columns(2)
            with col1:
                status_filter = st.selectbox("Filter by Status", ["All", "Active", "Pending", "Suspended"])
            with col2:
                role_filter = st.selectbox("Filter by Role", ["All"] + members_df["Role"].unique().tolist())
            
            # Apply filters
            filtered_df = members_df.copy()
            if status_filter != "All":
                filtered_df = filtered_df[filtered_df["Status"] == status_filter]
            if role_filter != "All":
                filtered_df = filtered_df[filtered_df["Role"] == role_filter]
            
            # Display filtered members
            st.dataframe(filtered_df[["Name", "Role", "Status", "ApprovedBy", "CreatedAt"]], use_container_width=True)
            
            # Member actions
            st.subheader("🔧 Member Actions")
            selected_member = st.selectbox("Select Member", filtered_df["Name"].tolist())
            
            if selected_member:
                member_info = filtered_df[filtered_df["Name"] == selected_member].iloc[0]
                
                col1, col2, col3, col4 = st.columns(4)
                
                with col1:
                    if member_info["Status"] == "Suspended":
                        if st.button(f"🔄 Reactivate {selected_member}"):
                            success, msg = reactivate_user(selected_member, members_df)
                            if success:
                                st.success(msg)
                                load_data_cached.clear()
                                st.rerun()
                            else:
                                st.error(msg)
                    else:
                        if st.button(f"🚫 Suspend {selected_member}"):
                            success, msg = suspend_user(selected_member, members_df)
                            if success:
                                st.warning(msg)
                                load_data_cached.clear()
                                st.rerun()
                            else:
                                st.error(msg)
                
                with col2:
                    if st.button(f"🗑️ Delete {selected_member}"):
                        if selected_member != st.session_state.user_name:  # Prevent self-deletion
                            success, msg, updated_df = delete_user(selected_member, members_df)
                            if success:
                                st.success(msg)
                                load_data_cached.clear()
                                st.rerun()
                            else:
                                st.error(msg)
                        else:
                            st.error("Cannot delete your own account!")
                
                with col3:
                    # Role update
                    new_role = st.selectbox("Change Role", ["Dev", "Core Head", "Domain Head", "Associate Head", "Junior Head"], 
                                          index=["Dev", "Core Head", "Domain Head", "Associate Head", "Junior Head"].index(member_info["Role"]))
                    if st.button("💼 Update Role") and new_role != member_info["Role"]:
                        success, msg = update_user_role(selected_member, new_role, members_df)
                        if success:
                            st.success(msg)
                            load_data_cached.clear()
                            st.rerun()
                        else:
                            st.error(msg)
                
                with col4:
                    if member_info["Status"] == "Pending":
                        if st.button(f"✅ Approve {selected_member}"):
                            success, msg = approve_user(selected_member, members_df, st.session_state.user_name)
                            if success:
                                st.success(msg)
                                load_data_cached.clear()
                                st.rerun()
                            else:
                                st.error(msg)
        else:
            st.info("No members found in the database.")
    
    with tab2:
        st.subheader("✅ Pending Approvals")
        
        pending_members = members_df[members_df["Status"] == "Pending"] if "Status" in members_df.columns else pd.DataFrame()
        
        if not pending_members.empty:
            st.info(f"📋 {len(pending_members)} member(s) awaiting approval")
            
            for idx, member in pending_members.iterrows():
                with st.expander(f"👤 {member['Name']} - {member['Role']} (Registered: {member['CreatedAt']})"):
                    col1, col2, col3 = st.columns([2, 1, 1])
                    
                    with col1:
                        st.write(f"**Name:** {member['Name']}")
                        st.write(f"**Requested Role:** {member['Role']}")
                        st.write(f"**Registration Date:** {member['CreatedAt']}")
                    
                    with col2:
                        if st.button(f"✅ Approve", key=f"approve_{member['Name']}"):
                            success, msg = approve_user(member['Name'], members_df, st.session_state.user_name)
                            if success:
                                st.success(msg)
                                load_data_cached.clear()
                                st.rerun()
                            else:
                                st.error(msg)
                    
                    with col3:
                        if st.button(f"❌ Reject", key=f"reject_{member['Name']}"):
                            success, msg, updated_df = delete_user(member['Name'], members_df)
                            if success:
                                st.warning(f"Rejected and deleted {member['Name']}")
                                load_data_cached.clear()
                                st.rerun()
                            else:
                                st.error(msg)
        else:
            st.success("🎉 No pending approvals!")
    
    with tab3:
        st.subheader("📊 Complete Database View")
        
        # Show all data
        col1, col2 = st.columns(2)
        
        with col1:
            st.write("**👥 Members Database**")
            if not members_df.empty:
                st.dataframe(members_df, use_container_width=True, height=300)
            else:
                st.info("No members data")
        
        with col2:
            st.write("**📋 Tasks Database**")
            if not tasks_df.empty:
                st.dataframe(tasks_df, use_container_width=True, height=300)
            else:
                st.info("No tasks data")
        
        # Download options
        st.subheader("💾 Data Export")
        col1, col2 = st.columns(2)
        
        with col1:
            if not members_df.empty:
                csv_members = members_df.to_csv(index=False)
                st.download_button(
                    label="📥 Download Members CSV",
                    data=csv_members,
                    file_name=f"members_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                    mime="text/csv"
                )
        
        with col2:
            if not tasks_df.empty:
                csv_tasks = tasks_df.to_csv(index=False)
                st.download_button(
                    label="📥 Download Tasks CSV",
                    data=csv_tasks,
                    file_name=f"tasks_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                    mime="text/csv"
                )
    
    with tab4:
        st.subheader("⚙️ System Administration")
        
        # System stats
        st.write("**📈 System Statistics**")
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("🔄 Cache TTL", "30 seconds")
        with col2:
            st.metric("📊 Sheet ID", SHEET_ID[:8] + "...")
        with col3:
            connection_status = "🟢 Connected" if test_gsheets_connection() else "🔴 Disconnected"
            st.metric("🔗 Connection", connection_status)
        
        # Manual data refresh
        st.write("**🔄 Data Management**")
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button("🗑️ Clear Cache"):
                load_data_cached.clear()
                get_cached_gsheet_client.clear()
                st.success("Cache cleared!")
                st.rerun()
        
        with col2:
            if st.button("🔄 Force Refresh"):
                load_data_cached.clear()
                st.success("Data refreshed from Google Sheets!")
                st.rerun()
        
        # System settings
        st.write("**⚙️ System Configuration**")
        st.code(f"""
Sheet ID: {SHEET_ID}
Cache TTL: 30 seconds
Authentication: Service Account
Worksheets: Tasks, Members
        """)
        
        # Danger zone
        st.write("**⚠️ Danger Zone**")
        with st.expander("💀 Advanced Operations", expanded=False):
            st.warning("⚠️ These operations can cause data loss!")
            
            col1, col2 = st.columns(2)
            with col1:
                if st.button("🗑️ Clear All Tasks", help="This will delete ALL tasks"):
                    if st.checkbox("I understand this will delete all tasks"):
                        empty_df = pd.DataFrame(columns=["TaskID", "TaskName", "AssignedTo", "Role", "Status", "Deadline", "Priority", "Description"])
                        if update_tasks_sheet_optimized(empty_df):
                            st.success("All tasks cleared!")
                            load_data_cached.clear()
                        else:
                            st.error("Failed to clear tasks")
            
            with col2:
                if st.button("👥 Reset Member Status", help="Reset all members to Active"):
                    if st.checkbox("I understand this affects all member accounts"):
                        members_copy = members_df.copy()
                        members_copy["Status"] = "Active"
                        if update_members_sheet_optimized(members_copy):
                            st.success("All member statuses reset to Active!")
                            load_data_cached.clear()
                        else:
                            st.error("Failed to reset member statuses")

# --- Main Dashboard ---
def show_dashboard():
    tasks_df, members_df = load_data_cached()
    
    # Header with user info and logout
    col1, col2, col3 = st.columns([2, 1, 1])
    with col1:
        st.title(f"🏢 Club Management Dashboard")
        st.write(f"Welcome back, **{st.session_state.user_name}** ({st.session_state.user_role})")
    
    with col2:
        show_refresh_button()
    
    with col3:
        if st.button("🚪 Logout"):
            st.session_state.authenticated = False
            st.session_state.user_name = None
            st.session_state.user_role = None
            st.session_state.page = "login"
            st.rerun()
    
    st.markdown("---")
    
    # Role-specific dashboard
    if st.session_state.user_role == "Dev":
        show_dev_management()
    else:
        show_regular_dashboard(tasks_df, members_df)

def show_regular_dashboard(tasks_df, members_df):
    """Dashboard for non-Dev users"""
    user_name = st.session_state.user_name
    user_role = st.session_state.user_role
    
    # User's tasks overview
    user_tasks = tasks_df[tasks_df["AssignedTo"] == user_name] if not tasks_df.empty and "AssignedTo" in tasks_df.columns else pd.DataFrame()
    
    # Dashboard metrics
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        total_tasks = len(user_tasks)
        st.metric("📋 My Tasks", total_tasks)
    
    with col2:
        completed_tasks = len(user_tasks[user_tasks["Status"] == "Completed"]) if not user_tasks.empty else 0
        st.metric("✅ Completed", completed_tasks)
    
    with col3:
        in_progress_tasks = len(user_tasks[user_tasks["Status"] == "In Progress"]) if not user_tasks.empty else 0
        st.metric("🔄 In Progress", in_progress_tasks)
    
    with col4:
        pending_tasks = len(user_tasks[user_tasks["Status"] == "Pending"]) if not user_tasks.empty else 0
        st.metric("⏳ Pending", pending_tasks)
    
    # Tabs for different functions
    if user_role in ["Core Head", "Domain Head", "Associate Head"]:
        tab1, tab2, tab3 = st.tabs(["📋 My Tasks", "➕ Assign Tasks", "👥 Team View"])
    else:
        tab1, tab2 = st.tabs(["📋 My Tasks", "👥 Team View"])
        tab3 = None
    
    with tab1:
        st.subheader("📋 My Tasks")
        
        if not user_tasks.empty:
            # Filter options
            col1, col2 = st.columns(2)
            with col1:
                status_filter = st.selectbox("Filter by Status", ["All", "Pending", "In Progress", "Completed"])
            with col2:
                priority_filter = st.selectbox("Filter by Priority", ["All", "High", "Medium", "Low"])
            
            # Apply filters
            filtered_tasks = user_tasks.copy()
            if status_filter != "All":
                filtered_tasks = filtered_tasks[filtered_tasks["Status"] == status_filter]
            if priority_filter != "All":
                filtered_tasks = filtered_tasks[filtered_tasks["Priority"] == priority_filter]
            
            # Display tasks
            for idx, task in filtered_tasks.iterrows():
                with st.expander(f"📋 {task['TaskName']} - {task['Status']} ({task['Priority']} Priority)"):
                    col1, col2 = st.columns([2, 1])
                    
                    with col1:
                        st.write(f"**Task ID:** {task['TaskID']}")
                        st.write(f"**Description:** {task['Description']}")
                        st.write(f"**Deadline:** {task['Deadline']}")
                        st.write(f"**Priority:** {task['Priority']}")
                    
                    with col2:
                        current_status = task['Status']
                        new_status = st.selectbox(
                            "Update Status",
                            ["Pending", "In Progress", "Completed"],
                            index=["Pending", "In Progress", "Completed"].index(current_status),
                            key=f"status_{task['TaskID']}"
                        )
                        
                        if st.button("💾 Update", key=f"update_{task['TaskID']}") and new_status != current_status:
                            task_idx = tasks_df[tasks_df["TaskID"] == task["TaskID"]].index[0]
                            tasks_df.at[task_idx, "Status"] = new_status
                            
                            if update_tasks_sheet_optimized(tasks_df):
                                st.success(f"Task status updated to {new_status}!")
                                load_data_cached.clear()
                                st.rerun()
                            else:
                                st.error("Failed to update task status")
        else:
            st.info("📭 No tasks assigned to you yet!")
    
    if tab3:  # Only show for users who can assign tasks
        with tab3:
            st.subheader("➕ Assign New Task")
            
            subordinates = get_subordinates(user_name, members_df)
            
            if subordinates:
                with st.form("assign_task_form"):
                    task_name = st.text_input("Task Name")
                    assigned_to = st.selectbox("Assign To", subordinates)
                    deadline = st.date_input("Deadline")
                    priority = st.selectbox("Priority", ["Low", "Medium", "High"])
                    description = st.text_area("Task Description")
                    
                    if st.form_submit_button("📤 Assign Task"):
                        if task_name and assigned_to and description:
                            task_id = generate_unique_taskid(tasks_df)
                            
                            new_task = {
                                "TaskID": task_id,
                                "TaskName": task_name,
                                "AssignedTo": assigned_to,
                                "Role": user_role,
                                "Status": "Pending",
                                "Deadline": deadline.strftime("%Y-%m-%d"),
                                "Priority": priority,
                                "Description": description
                            }
                            
                            if tasks_df.empty:
                                tasks_df = pd.DataFrame([new_task])
                            else:
                                tasks_df = pd.concat([tasks_df, pd.DataFrame([new_task])], ignore_index=True)
                            
                            if update_tasks_sheet_optimized(tasks_df):
                                st.success(f"✅ Task '{task_name}' assigned to {assigned_to}!")
                                load_data_cached.clear()
                                st.rerun()
                            else:
                                st.error("❌ Failed to assign task")
                        else:
                            st.warning("⚠️ Please fill all required fields")
            else:
                st.info("ℹ️ No subordinates found. You cannot assign tasks to anyone.")
    
    with tab2:
        st.subheader("👥 Team Overview")
        
        # Show tasks assigned by this user
        assigned_tasks = tasks_df[tasks_df["Role"] == user_role] if not tasks_df.empty else pd.DataFrame()
        
        if not assigned_tasks.empty:
            st.write("**📤 Tasks I've Assigned**")
            
            # Group by assignee
            for assignee in assigned_tasks["AssignedTo"].unique():
                assignee_tasks = assigned_tasks[assigned_tasks["AssignedTo"] == assignee]
                
                with st.expander(f"👤 {assignee} ({len(assignee_tasks)} tasks)"):
                    for idx, task in assignee_tasks.iterrows():
                        status_color = {"Pending": "🟡", "In Progress": "🔵", "Completed": "🟢"}
                        st.write(f"{status_color.get(task['Status'], '⚪')} **{task['TaskName']}** - {task['Status']} ({task['Priority']} Priority)")
                        st.write(f"   📅 Deadline: {task['Deadline']}")
        else:
            st.info("📭 You haven't assigned any tasks yet.")

# --- Main App Logic ---
def main():
    # Handle page routing
    if not st.session_state.authenticated:
        if st.session_state.page == "register":
            show_register_page()
        else:
            show_login_page()
    else:
        show_dashboard()

if __name__ == "__main__":
    main()
