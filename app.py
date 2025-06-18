import streamlit as st
import os
import tempfile
import shutil
from pathlib import Path
import difflib
from git_operations import GitManager
from ai_agent import AICodeAgent
from utils import format_diff, get_file_extension_icon

# Configure page
st.set_page_config(
    page_title="AI Git Code Modifier",
    page_icon="🔧",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Initialize session state
if 'git_manager' not in st.session_state:
    st.session_state.git_manager = None
if 'ai_agent' not in st.session_state:
    st.session_state.ai_agent = AICodeAgent()
if 'current_repo_path' not in st.session_state:
    st.session_state.current_repo_path = None
if 'selected_files' not in st.session_state:
    st.session_state.selected_files = []
if 'modifications' not in st.session_state:
    st.session_state.modifications = {}

def main():
    st.title("🔧 AI-Powered Git Repository Code Modifier")
    st.markdown("Analyze and modify code in Git repositories using AI assistance")
    
    # Sidebar navigation
    with st.sidebar:
        st.header("Navigation")
        page = st.selectbox(
            "Select Page",
            ["Repository Setup", "File Browser", "AI Modifications", "Commit & Push"]
        )
    
    if page == "Repository Setup":
        repository_setup_page()
    elif page == "File Browser":
        file_browser_page()
    elif page == "AI Modifications":
        ai_modifications_page()
    elif page == "Commit & Push":
        commit_push_page()

def repository_setup_page():
    st.header("Repository Setup")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("Repository Information")
        repo_url = st.text_input(
            "Repository URL",
            placeholder="https://github.com/user/repo.git",
            help="Enter the Git repository URL to clone"
        )
        
        branch_name = st.text_input(
            "Working Branch Name",
            value="ai-modifications",
            help="Name for the new branch where modifications will be made"
        )
        
        base_branch = st.text_input(
            "Base Branch",
            value="main",
            help="Base branch to create the working branch from"
        )
    
    with col2:
        st.subheader("Authentication (Optional)")
        username = st.text_input("Git Username", help="For private repositories")
        password = st.text_input("Git Password/Token", type="password", help="Personal access token or password")
    
    if st.button("Clone Repository", type="primary"):
        if not repo_url:
            st.error("Please enter a repository URL")
            return
        
        with st.spinner("Cloning repository..."):
            try:
                # Create temporary directory for the repo
                temp_dir = tempfile.mkdtemp(prefix="git_repo_")
                st.session_state.current_repo_path = temp_dir
                
                # Initialize Git manager
                git_manager = GitManager(temp_dir)
                
                # Clone repository
                auth = (username, password) if username and password else None
                git_manager.clone_repository(repo_url, auth)
                
                # Create working branch
                git_manager.create_branch(branch_name, base_branch)
                
                st.session_state.git_manager = git_manager
                st.success(f"✅ Repository cloned successfully to branch '{branch_name}'")
                st.info(f"Repository path: {temp_dir}")
                
                # Show repository info
                repo_info = git_manager.get_repository_info()
                st.json(repo_info)
                
            except Exception as e:
                st.error(f"Failed to clone repository: {str(e)}")
                if 'current_repo_path' in st.session_state and st.session_state.current_repo_path:
                    shutil.rmtree(st.session_state.current_repo_path, ignore_errors=True)
                    st.session_state.current_repo_path = None

def file_browser_page():
    st.header("File Browser")
    
    if not st.session_state.git_manager:
        st.warning("Please clone a repository first in the Repository Setup page.")
        return
    
    try:
        files = st.session_state.git_manager.list_files()
        
        if not files:
            st.info("No files found in the repository.")
            return
        
        st.subheader("Repository Files")
        
        # File selection
        col1, col2 = st.columns([2, 3])
        
        with col1:
            st.markdown("**Select files for modification:**")
            selected_files = []
            
            # Group files by directory
            file_tree = {}
            for file_path in files:
                parts = Path(file_path).parts
                current = file_tree
                for part in parts[:-1]:
                    if part not in current:
                        current[part] = {}
                    current = current[part]
                current[parts[-1]] = file_path
            
            def render_file_tree(tree, path="", level=0):
                for name, content in sorted(tree.items()):
                    indent = "  " * level
                    if isinstance(content, dict):
                        st.markdown(f"{indent}📁 **{name}/**")
                        render_file_tree(content, f"{path}/{name}" if path else name, level + 1)
                    else:
                        icon = get_file_extension_icon(name)
                        if st.checkbox(f"{indent}{icon} {name}", key=content):
                            selected_files.append(content)
            
            render_file_tree(file_tree)
            st.session_state.selected_files = selected_files
        
        with col2:
            if selected_files:
                st.markdown("**File Preview:**")
                selected_file = st.selectbox("Choose file to preview", selected_files)
                
                if selected_file:
                    try:
                        content = st.session_state.git_manager.read_file(selected_file)
                        st.code(content, language=Path(selected_file).suffix[1:] if Path(selected_file).suffix else None)
                    except Exception as e:
                        st.error(f"Could not read file: {str(e)}")
            else:
                st.info("Select files from the left panel to preview them here.")
    
    except Exception as e:
        st.error(f"Error browsing files: {str(e)}")

def ai_modifications_page():
    st.header("AI Code Modifications")
    
    if not st.session_state.git_manager:
        st.warning("Please clone a repository first in the Repository Setup page.")
        return
    
    if not st.session_state.selected_files:
        st.warning("Please select files to modify in the File Browser page.")
        return
    
    st.subheader("Selected Files")
    for file_path in st.session_state.selected_files:
        st.text(f"📄 {file_path}")
    
    # AI prompt input
    st.subheader("Modification Instructions")
    context = st.text_area(
        "Context/Background",
        placeholder="Provide any relevant context about the codebase or the changes needed...",
        height=100
    )
    
    prompt = st.text_area(
        "Modification Prompt",
        placeholder="Describe what changes you want to make to the code...",
        height=150
    )
    
    if st.button("Analyze and Generate Modifications", type="primary"):
        if not prompt.strip():
            st.error("Please provide modification instructions.")
            return
        
        with st.spinner("AI is analyzing and modifying the code..."):
            try:
                modifications = {}
                
                for file_path in st.session_state.selected_files:
                    # Read current file content
                    current_content = st.session_state.git_manager.read_file(file_path)
                    
                    # Get AI modifications
                    modified_content = st.session_state.ai_agent.modify_code(
                        file_path, current_content, prompt, context
                    )
                    
                    if modified_content and modified_content != current_content:
                        modifications[file_path] = {
                            'original': current_content,
                            'modified': modified_content
                        }
                
                st.session_state.modifications = modifications
                
                if modifications:
                    st.success(f"✅ Generated modifications for {len(modifications)} file(s)")
                else:
                    st.info("No modifications were suggested by the AI.")
                
            except Exception as e:
                st.error(f"Error generating modifications: {str(e)}")
    
    # Display modifications
    if st.session_state.modifications:
        st.subheader("Proposed Changes")
        
        for file_path, changes in st.session_state.modifications.items():
            with st.expander(f"📄 {file_path}", expanded=True):
                
                # Show diff
                diff_html = format_diff(
                    changes['original'].splitlines(keepends=True),
                    changes['modified'].splitlines(keepends=True),
                    file_path
                )
                st.markdown(diff_html, unsafe_allow_html=True)
                
                col1, col2 = st.columns(2)
                with col1:
                    if st.button(f"Apply Changes to {Path(file_path).name}", key=f"apply_{file_path}"):
                        try:
                            st.session_state.git_manager.write_file(file_path, changes['modified'])
                            st.success(f"✅ Applied changes to {file_path}")
                        except Exception as e:
                            st.error(f"Failed to apply changes: {str(e)}")
                
                with col2:
                    if st.button(f"Reject Changes to {Path(file_path).name}", key=f"reject_{file_path}"):
                        del st.session_state.modifications[file_path]
                        st.rerun()

def commit_push_page():
    st.header("Commit & Push Changes")
    
    if not st.session_state.git_manager:
        st.warning("Please clone a repository first in the Repository Setup page.")
        return
    
    try:
        # Check for changes
        status = st.session_state.git_manager.get_status()
        
        if not any([status['modified'], status['added'], status['deleted']]):
            st.info("No changes to commit.")
            return
        
        st.subheader("Repository Status")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            if status['modified']:
                st.markdown("**Modified Files:**")
                for file in status['modified']:
                    st.text(f"🔄 {file}")
        
        with col2:
            if status['added']:
                st.markdown("**Added Files:**")
                for file in status['added']:
                    st.text(f"➕ {file}")
        
        with col3:
            if status['deleted']:
                st.markdown("**Deleted Files:**")
                for file in status['deleted']:
                    st.text(f"➖ {file}")
        
        # Commit form
        st.subheader("Commit Changes")
        
        commit_message = st.text_area(
            "Commit Message",
            value="AI-powered code modifications",
            help="Describe the changes made to the code"
        )
        
        author_name = st.text_input(
            "Author Name",
            value=os.getenv("GIT_AUTHOR_NAME", "AI Code Modifier"),
            help="Name to use for the commit author"
        )
        
        author_email = st.text_input(
            "Author Email",
            value=os.getenv("GIT_AUTHOR_EMAIL", "ai@codemodifier.com"),
            help="Email to use for the commit author"
        )
        
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button("Commit Changes", type="primary"):
                if not commit_message.strip():
                    st.error("Please provide a commit message.")
                    return
                
                try:
                    commit_hash = st.session_state.git_manager.commit_changes(
                        commit_message, author_name, author_email
                    )
                    st.success(f"✅ Changes committed successfully!")
                    st.info(f"Commit hash: {commit_hash}")
                except Exception as e:
                    st.error(f"Failed to commit changes: {str(e)}")
        
        with col2:
            if st.button("Push to Remote"):
                try:
                    st.session_state.git_manager.push_changes()
                    st.success("✅ Changes pushed to remote repository!")
                except Exception as e:
                    st.error(f"Failed to push changes: {str(e)}")
                    st.info("Make sure you have proper authentication and push permissions.")
    
    except Exception as e:
        st.error(f"Error checking repository status: {str(e)}")

if __name__ == "__main__":
    main()
