import streamlit as st
import json
import time
from datetime import datetime
from container_manager import ContainerManager

# Configure page
st.set_page_config(
    page_title="AI Git Container Orchestrator",
    page_icon="🚀",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Initialize session state
if 'container_manager' not in st.session_state:
    st.session_state.container_manager = ContainerManager()
if 'active_jobs' not in st.session_state:
    st.session_state.active_jobs = {}
if 'refresh_counter' not in st.session_state:
    st.session_state.refresh_counter = 0

def main():
    st.title("🚀 AI Git Container Orchestrator")
    st.markdown("Launch containerized AI agents to modify Git repositories")
    
    # Sidebar navigation
    with st.sidebar:
        st.header("Navigation")
        page = st.selectbox(
            "Select Page",
            ["Job Configuration", "Active Jobs", "Job History", "Container Logs"]
        )
    
    if page == "Job Configuration":
        job_configuration_page()
    elif page == "Active Jobs":
        active_jobs_page()
    elif page == "Job History":
        job_history_page()
    elif page == "Container Logs":
        container_logs_page()

def job_configuration_page():
    st.header("Configure New Container Job")
    
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
        context = st.text_area(
            "Context/Background",
            placeholder="Provide context about the codebase, project goals, or any relevant background information...",
            height=100,
            help="Background information to help the AI understand the codebase"
        )
        
        prompt = st.text_area(
            "Modification Instructions *",
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
                    auth_token=auth_token if auth_token else None
                )
                
                st.success(f"✅ Job configured with ID: {config['job_id']}")
                
                # Display configuration
                with st.expander("Job Configuration", expanded=True):
                    st.json({
                        "job_id": config["job_id"],
                        "repo_url": config["repo_url"],
                        "branch_name": config["branch_name"],
                        "base_branch": config["base_branch"],
                        "file_patterns": config["file_patterns"],
                        "has_auth": config["auth"] is not None
                    })
                
                # Launch container
                with st.spinner("Launching container..."):
                    success = st.session_state.container_manager.launch_container(config['job_id'])
                    
                    if success:
                        st.success("🚀 Container launched successfully!")
                        st.info("Check the 'Active Jobs' page to monitor progress.")
                        st.session_state.active_jobs[config['job_id']] = config
                    else:
                        st.error("❌ Failed to launch container. Check container logs for details.")
                        
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