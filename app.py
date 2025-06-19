import streamlit as st
import json
import time
from datetime import datetime
from container_manager import ContainerManager
from redmine_integration import RedmineIntegration
from config_storage import ConfigStorage

# Configure page
st.set_page_config(
    page_title="DevOps AI Zealot",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Initialize session state
if 'container_manager' not in st.session_state:
    st.session_state.container_manager = ContainerManager()
if 'config_storage' not in st.session_state:
    st.session_state.config_storage = ConfigStorage()
if 'active_jobs' not in st.session_state:
    st.session_state.active_jobs = {}
if 'refresh_counter' not in st.session_state:
    st.session_state.refresh_counter = 0
if 'redmine_connection' not in st.session_state:
    st.session_state.redmine_connection = None
if 'redmine_projects' not in st.session_state:
    st.session_state.redmine_projects = []
if 'selected_issues' not in st.session_state:
    st.session_state.selected_issues = {}

# Load configurations
if 'job_defaults' not in st.session_state:
    st.session_state.job_defaults = st.session_state.config_storage.load_job_defaults()
if 'app_settings' not in st.session_state:
    st.session_state.app_settings = st.session_state.config_storage.load_app_settings()

# Auto-connect to Redmine if credentials are available
if 'auto_connected' not in st.session_state:
    st.session_state.auto_connected = False

if not st.session_state.auto_connected and not st.session_state.redmine_connection:
    config = st.session_state.config_storage.get_redmine_config()
    if config["api_key"] or (config["username"] and config["password"]):
        try:
            url = config["url"] if config["url"] else "https://redstone.redminecloud.net"
            redmine = RedmineIntegration(
                url=url,
                api_key=config["api_key"],
                username=config["username"],
                password=config["password"]
            )
            connection_test = redmine.test_connection()
            if connection_test["success"]:
                st.session_state.redmine_connection = redmine
                st.session_state.redmine_projects = redmine.get_projects()
        except Exception:
            pass  # Silent fail for auto-connection
    st.session_state.auto_connected = True

def main():
    st.title("⚡ DevOps AI Zealot")
    st.markdown("Relentless code optimization driven by project requirements")
    
    # Connection status indicator
    if st.session_state.redmine_connection:
        st.success("Connected to Redmine - Ready to select issues")
    else:
        st.warning("Redmine not connected - Set up connection in first tab")
    
    # Tab navigation
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "🔗 Redmine Setup", 
        "⚙️ Configure Job", 
        "🚀 Active Jobs", 
        "📋 Job History", 
        "📄 Container Logs"
    ])
    
    with tab1:
        redmine_setup_page()
    with tab2:
        job_configuration_page()
    with tab3:
        active_jobs_page()
    with tab4:
        job_history_page()
    with tab5:
        container_logs_page()

def redmine_setup_page():
    st.header("Redmine Integration Setup")
    
    # Check for environment secrets first
    config = st.session_state.config_storage.get_redmine_config()
    
    if config["api_key"] or (config["username"] and config["password"]):
        st.success("🔐 Redmine credentials found in environment secrets")
        
        col1, col2 = st.columns([3, 1])
        with col1:
            st.info(f"Server: {config['url']}")
            if config["api_key"]:
                st.info("Authentication: API Key (from secrets)")
            else:
                st.info("Authentication: Username/Password (from secrets)")
        
        with col2:
            if st.button("Connect Now", type="primary"):
                try:
                    with st.spinner("Connecting to Redmine..."):
                        redmine = RedmineIntegration(
                            url=config["url"],
                            api_key=config["api_key"],
                            username=config["username"],
                            password=config["password"]
                        )
                        
                        connection_test = redmine.test_connection()
                        
                        if connection_test["success"]:
                            st.session_state.redmine_connection = redmine
                            st.session_state.redmine_projects = redmine.get_projects()
                            st.success("Connected successfully!")
                            st.rerun()
                        else:
                            st.error(f"Connection failed: {connection_test['error']}")
                except Exception as e:
                    st.error(f"Connection error: {str(e)}")
    else:
        st.warning("🔑 No Redmine credentials found in environment secrets")
        
        with st.expander("📋 How to set up Redmine secrets", expanded=True):
            st.markdown("""
            **Set these environment secrets in your Replit project:**
            
            1. **REDMINE_URL** - Your Redmine server URL
            2. **REDMINE_API_KEY** - Your API key (recommended)
            
            OR
            
            2. **REDMINE_USERNAME** - Your username  
            3. **REDMINE_PASSWORD** - Your password
            
            **To add secrets:**
            1. Go to your Replit project settings
            2. Click on "Secrets" tab
            3. Add the required environment variables
            4. Restart this application
            """)
        
        st.subheader("Manual Connection (Temporary)")
        st.caption("For testing only - credentials won't be saved")
        
        with st.form("manual_redmine_form"):
            redmine_url = st.text_input(
                "Redmine Server URL",
                value=config["url"],
                help="Your Redmine server URL"
            )
            
            auth_method = st.radio(
                "Authentication Method",
                ["API Key", "Username/Password"]
            )
            
            if auth_method == "API Key":
                api_key = st.text_input(
                    "API Key",
                    type="password",
                    help="Your Redmine API key (found in your account settings)"
                )
                username = None
                password = None
            else:
                username = st.text_input("Username")
                password = st.text_input("Password", type="password")
                api_key = None
        
        if st.form_submit_button("Connect to Redmine", type="primary"):
            if not redmine_url:
                st.error("Please enter the Redmine server URL")
                return
            
            if auth_method == "API Key" and not api_key:
                st.error("Please enter your API key")
                return
            
            if auth_method == "Username/Password" and (not username or not password):
                st.error("Please enter both username and password")
                return
            
            try:
                with st.spinner("Connecting to Redmine..."):
                    redmine = RedmineIntegration(
                        url=redmine_url,
                        api_key=api_key,
                        username=username,
                        password=password
                    )
                    
                    # Test connection
                    connection_test = redmine.test_connection()
                    
                    if connection_test["success"]:
                        st.session_state.redmine_connection = redmine
                        user_info = connection_test["user"]
                        
                        st.success(f"Connected successfully as {user_info['firstname']} {user_info['lastname']} ({user_info['login']})")
                        
                        # Load projects
                        with st.spinner("Loading projects..."):
                            projects = redmine.get_projects()
                            st.session_state.redmine_projects = projects
                            st.success(f"Loaded {len(projects)} projects")
                    else:
                        st.error(f"Connection failed: {connection_test['error']}")
                        
            except Exception as e:
                st.error(f"Failed to connect to Redmine: {str(e)}")
    
    # Show connection status
    if st.session_state.redmine_connection:
        st.success("✅ Connected to Redmine")
        
        # Project browser
        st.subheader("Available Projects")
        
        if st.session_state.redmine_projects:
            for project in st.session_state.redmine_projects:
                with st.expander(f"📁 {project['name']} ({project['identifier']})"):
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        st.text(f"ID: {project['id']}")
                        st.text(f"Status: {project['status']}")
                        st.text(f"Created: {project['created_on'][:10]}")
                    
                    with col2:
                        st.text(f"Updated: {project['updated_on'][:10]}")
                        if project['description']:
                            st.text("Description:")
                            st.caption(project['description'][:200] + "..." if len(project['description']) > 200 else project['description'])
                    
                    # Load issues for this project
                    if st.button(f"View Issues", key=f"issues_{project['id']}"):
                        try:
                            with st.spinner("Loading issues..."):
                                issues = st.session_state.redmine_connection.get_project_issues(project['identifier'])
                                st.session_state.selected_issues[project['id']] = issues
                                
                            st.subheader(f"Issues in {project['name']}")
                            for issue in issues[:10]:  # Show first 10 issues
                                st.text(f"#{issue['id']} - {issue['subject']} ({issue['status']['name']})")
                                
                            if len(issues) > 10:
                                st.info(f"Showing 10 of {len(issues)} issues. Use Job Configuration to select specific issues.")
                                
                        except Exception as e:
                            st.error(f"Failed to load issues: {str(e)}")
    else:
        st.info("Please connect to Redmine to view projects and issues")

def job_configuration_page():
    st.header("Configure New Container Job")
    
    # Redmine Issue Selection (outside form)
    st.subheader("Redmine Issue Integration")
    selected_issue = None
    
    if st.session_state.redmine_connection:
        st.success("Connected to Redmine")
        
        # Auto-load projects if not already loaded
        if not st.session_state.redmine_projects:
            try:
                with st.spinner("Loading projects..."):
                    st.session_state.redmine_projects = st.session_state.redmine_connection.get_projects()
            except Exception as e:
                st.error(f"Failed to load projects: {str(e)}")
        
        # Project selection
        if st.session_state.redmine_projects:
            project_options = {f"{p['name']} ({p['identifier']})": p for p in st.session_state.redmine_projects}
            selected_project_name = st.selectbox(
                "Select Project",
                ["None"] + list(project_options.keys()),
                help="Choose a Redmine project to link this job to"
            )
            
            if selected_project_name != "None":
                selected_project = project_options[selected_project_name]
                project_key = f"issues_{selected_project['identifier']}"
                
                # Auto-load issues if not already loaded
                if project_key not in st.session_state:
                    try:
                        with st.spinner("Loading issues..."):
                            issues = st.session_state.redmine_connection.get_project_issues(selected_project['identifier'], status_filter="all")
                            st.session_state[project_key] = issues
                        st.success(f"Loaded {len(issues)} issues")
                    except Exception as e:
                        st.error(f"Failed to auto-load issues: {str(e)}")
                        st.session_state[project_key] = []
                
                # Button to refresh issues
                col_a, col_b = st.columns([2, 1])
                with col_a:
                    st.write(f"Project: {selected_project['name']}")
                with col_b:
                    if st.button("Refresh Issues", key=f"refresh_{selected_project['identifier']}"):
                        try:
                            with st.spinner("Refreshing issues..."):
                                issues = st.session_state.redmine_connection.get_project_issues(selected_project['identifier'], status_filter="all")
                                st.session_state[project_key] = issues
                            st.success(f"Refreshed {len(issues)} issues (all statuses)")
                            if len(issues) == 0:
                                st.warning("No issues found in this project")
                            else:
                                issue_ids = [f"#{issue['id']}" for issue in issues[:10]]
                                st.info(f"Found issues: {', '.join(issue_ids)}{'...' if len(issues) > 10 else ''}")
                        except Exception as e:
                            st.error(f"Failed to load issues: {str(e)}")
                
                # Show issues if loaded
                if project_key in st.session_state and st.session_state[project_key]:
                    issues = st.session_state[project_key]
                    
                    # Create issue options with full details
                    issue_options = {}
                    for issue in issues:
                        key = f"#{issue['id']} - {issue['subject']}"
                        issue_options[key] = issue
                    
                    selected_issue_name = st.selectbox(
                        "Select Issue",
                        ["None"] + list(issue_options.keys()),
                        help="Choose a specific issue this job addresses"
                    )
                    
                    if selected_issue_name != "None":
                        selected_issue = issue_options[selected_issue_name]
                        
                        # Show issue details in a compact format
                        col1, col2 = st.columns([1, 1])
                        with col1:
                            st.text(f"Status: {selected_issue['status']['name']}")
                            st.text(f"Priority: {selected_issue['priority']['name']}")
                        with col2:
                            st.text(f"Tracker: {selected_issue['tracker']['name']}")
                            if 'assigned_to' in selected_issue and selected_issue['assigned_to']:
                                st.text(f"Assigned: {selected_issue['assigned_to']['name']}")
                        
                        # Show description if available
                        if selected_issue.get('description'):
                            with st.expander("Issue Description", expanded=False):
                                st.text_area("", value=selected_issue['description'], height=100, disabled=True)
                
                elif project_key not in st.session_state:
                    st.info("Issues will load automatically when you select a project")
                else:
                    st.warning("No issues found in this project")
    else:
        st.warning("Redmine not connected")
        st.info("Go to the 'Redmine Setup' tab to connect and access your issues")
    
    st.divider()
    
    # Main job configuration form
    with st.form("job_config_form"):
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("Repository Settings")
            repo_url = st.text_input(
                "Repository URL *",
                placeholder="https://github.com/user/repo.git",
                help="Git repository URL to clone and modify"
            )
            
            branch_name = st.text_input(
                "Working Branch Name *",
                value=f"ai-modifications-{datetime.now().strftime('%Y%m%d-%H%M%S')}",
                help="New branch name for modifications"
            )
            
            base_branch = st.text_input(
                "Base Branch",
                value="main",
                help="Branch to create working branch from"
            )
        
        with col2:
            st.subheader("Authentication (Optional)")
            auth_username = st.text_input(
                "Git Username",
                help="Username for private repositories"
            )
            
            auth_token = st.text_input(
                "Git Token/Password",
                type="password",
                help="Personal access token or password"
            )
        
        st.subheader("AI Instructions")
        
        # Pre-fill context and prompt if issue is selected
        default_context = ""
        default_prompt = ""
        
        if selected_issue:
            default_context = f"Working on Redmine issue #{selected_issue['id']}: {selected_issue['subject']}\n\n"
            if selected_issue['description']:
                default_context += f"Issue Description:\n{selected_issue['description']}\n\n"
            default_context += f"Priority: {selected_issue['priority']['name']}\nTracker: {selected_issue['tracker']['name']}"
            
            default_prompt = f"Address the requirements described in issue #{selected_issue['id']}: {selected_issue['subject']}"
        
        context = st.text_area(
            "Context/Background",
            value=default_context,
            placeholder="Provide context about the codebase, project goals, or any relevant background information...",
            height=100,
            help="Background information to help the AI understand the codebase"
        )
        
        prompt = st.text_area(
            "Modification Instructions *",
            value=default_prompt,
            placeholder="Describe the changes you want the AI to make to the code...",
            height=150,
            help="Detailed instructions for code modifications"
        )
        
        st.subheader("File Selection")
        file_patterns = st.multiselect(
            "File Patterns to Include",
            ["*.py", "*.js", "*.ts", "*.java", "*.go", "*.cpp", "*.c", "*.rb", "*.php", "*.rs"],
            default=["*.py"],
            help="File patterns to include in the analysis"
        )
        
        custom_pattern = st.text_input(
            "Custom Pattern",
            placeholder="*.custom",
            help="Add custom file pattern if needed"
        )
        
        if custom_pattern:
            file_patterns.append(custom_pattern)
        
        submitted = st.form_submit_button("🚀 Launch Container Job", type="primary")
        
        if submitted:
            if not repo_url or not branch_name or not prompt:
                st.error("Please fill in all required fields (marked with *)")
                return
            
            try:
                # Create job configuration
                config = st.session_state.container_manager.create_container_config(
                    repo_url=repo_url,
                    branch_name=branch_name,
                    base_branch=base_branch,
                    prompt=prompt,
                    context=context,
                    file_patterns=file_patterns,
                    auth_username=auth_username if auth_username else None,
                    auth_token=auth_token if auth_token else None,
                    redmine_issue_id=selected_issue['id'] if selected_issue else None
                )
                
                st.success(f"✅ Job configured with ID: {config['job_id']}")
                
                # Display configuration
                with st.expander("Job Configuration", expanded=True):
                    job_display = {
                        "job_id": config["job_id"],
                        "repo_url": config["repo_url"],
                        "branch_name": config["branch_name"],
                        "base_branch": config["base_branch"],
                        "file_patterns": config["file_patterns"],
                        "has_auth": config["auth"] is not None,
                        "redmine_issue": f"#{selected_issue['id']} - {selected_issue['subject']}" if selected_issue else "None"
                    }
                    st.json(job_display)
                
                # Create Redmine link if issue selected
                if selected_issue and st.session_state.redmine_connection:
                    try:
                        st.session_state.redmine_connection.create_issue_link_comment(
                            selected_issue['id'],
                            config['job_id'],
                            repo_url,
                            branch_name
                        )
                        st.success(f"Linked job to Redmine issue #{selected_issue['id']}")
                    except Exception as e:
                        st.warning(f"Job created but failed to link to Redmine: {str(e)}")
                
                # Launch container
                with st.spinner("Launching container..."):
                    success = st.session_state.container_manager.launch_container(config['job_id'])
                    
                    if success:
                        st.success("Container launched successfully!")
                        st.info("Check the 'Active Jobs' page to monitor progress.")
                        st.session_state.active_jobs[config['job_id']] = config
                    else:
                        st.error("Failed to launch container. Check container logs for details.")
                        
            except Exception as e:
                st.error(f"Error creating job: {str(e)}")

def active_jobs_page():
    st.header("Active Container Jobs")
    
    # Auto-refresh toggle
    col1, col2 = st.columns([3, 1])
    with col1:
        st.markdown("Monitor running container jobs and their progress")
    with col2:
        auto_refresh = st.checkbox("Auto-refresh (5s)", value=True)
    
    if auto_refresh:
        time.sleep(5)
        st.session_state.refresh_counter += 1
        st.rerun()
    
    # Get all jobs
    all_jobs = st.session_state.container_manager.list_jobs()
    active_jobs = {job_id: job for job_id, job in all_jobs.items() 
                   if job["status"] in ["configured", "running"]}
    
    if not active_jobs:
        st.info("No active jobs. Configure a new job to get started.")
        return
    
    # Display active jobs
    for job_id, job_summary in active_jobs.items():
        with st.expander(f"🔄 Job {job_id} - {job_summary['status'].upper()}", expanded=True):
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.metric("Status", job_summary["status"])
                st.text(f"Started: {job_summary['timestamp'][:19]}")
            
            with col2:
                st.text(f"Repository: {job_summary['repo_url']}")
                st.text(f"Branch: {job_summary['branch_name']}")
            
            with col3:
                if st.button(f"Refresh Status", key=f"refresh_{job_id}"):
                    status_info = st.session_state.container_manager.check_container_status(job_id)
                    st.json(status_info)
                
                if st.button(f"View Logs", key=f"logs_{job_id}"):
                    st.session_state.selected_job_for_logs = job_id
                    st.rerun()
            
            # Show detailed status
            status_info = st.session_state.container_manager.check_container_status(job_id)
            
            if status_info.get("status") == "completed":
                st.success("✅ Job completed successfully!")
                if "results" in status_info and status_info["results"]:
                    st.subheader("Results")
                    st.json(status_info["results"])
            elif status_info.get("status") == "failed":
                st.error("❌ Job failed")
            elif status_info.get("status") == "running":
                st.info("🔄 Job is running...")
            
            # Show recent logs
            if "logs" in status_info and status_info["logs"]:
                recent_logs = status_info["logs"][-5:]  # Show last 5 log entries
                st.subheader("Recent Logs")
                for log in recent_logs:
                    st.code(log)

def job_history_page():
    st.header("Job History")
    
    all_jobs = st.session_state.container_manager.list_jobs()
    
    if not all_jobs:
        st.info("No jobs found.")
        return
    
    # Filter options
    col1, col2 = st.columns(2)
    with col1:
        status_filter = st.selectbox(
            "Filter by Status",
            ["All", "completed", "failed", "running", "configured"]
        )
    
    with col2:
        sort_order = st.selectbox("Sort by", ["Newest First", "Oldest First"])
    
    # Filter and sort jobs
    filtered_jobs = all_jobs
    if status_filter != "All":
        filtered_jobs = {job_id: job for job_id, job in all_jobs.items() 
                        if job["status"] == status_filter}
    
    # Sort by timestamp
    sorted_jobs = sorted(filtered_jobs.items(), 
                        key=lambda x: x[1]["timestamp"], 
                        reverse=(sort_order == "Newest First"))
    
    # Display jobs
    for job_id, job_summary in sorted_jobs:
        status_emoji = {
            "completed": "✅",
            "failed": "❌", 
            "running": "🔄",
            "configured": "⚙️"
        }.get(job_summary["status"], "❓")
        
        with st.expander(f"{status_emoji} {job_id} - {job_summary['status']} ({job_summary['timestamp'][:19]})"):
            col1, col2 = st.columns(2)
            
            with col1:
                st.text(f"Repository: {job_summary['repo_url']}")
                st.text(f"Branch: {job_summary['branch_name']}")
                st.text(f"Status: {job_summary['status']}")
            
            with col2:
                st.text(f"Timestamp: {job_summary['timestamp']}")
                if st.button(f"View Full Details", key=f"details_{job_id}"):
                    full_config = st.session_state.container_manager.containers.get(job_id, {})
                    st.json(full_config)
                
                if st.button(f"Cleanup", key=f"cleanup_{job_id}"):
                    success = st.session_state.container_manager.cleanup_container(job_id)
                    if success:
                        st.success("Container cleaned up")
                    else:
                        st.error("Cleanup failed")
            
            # Show prompt preview
            st.text("Prompt:")
            st.code(job_summary["prompt"])

def container_logs_page():
    st.header("Container Logs")
    
    # Job selection
    all_jobs = st.session_state.container_manager.list_jobs()
    if not all_jobs:
        st.info("No jobs available.")
        return
    
    job_options = {f"{job_id} - {job['status']}": job_id 
                   for job_id, job in all_jobs.items()}
    
    selected_display = st.selectbox("Select Job", list(job_options.keys()))
    selected_job_id = job_options[selected_display] if selected_display else None
    
    if not selected_job_id:
        return
    
    col1, col2 = st.columns([3, 1])
    with col1:
        st.subheader(f"Logs for Job {selected_job_id}")
    with col2:
        if st.button("🔄 Refresh Logs"):
            st.rerun()
    
    # Get and display logs
    try:
        logs = st.session_state.container_manager.get_container_logs(selected_job_id)
        
        if logs:
            # Display logs in a scrollable container
            log_text = "\n".join(logs)
            st.text_area("Container Logs", value=log_text, height=400)
            
            # Download logs button
            st.download_button(
                "📥 Download Logs",
                data=log_text,
                file_name=f"container_logs_{selected_job_id}.txt",
                mime="text/plain"
            )
        else:
            st.info("No logs available yet.")
            
    except Exception as e:
        st.error(f"Error retrieving logs: {str(e)}")

if __name__ == "__main__":
    main()