import difflib
from pathlib import Path
from typing import List

def format_diff(original_lines: List[str], modified_lines: List[str], filename: str) -> str:
    """
    Generate HTML formatted diff between original and modified content.
    
    Args:
        original_lines: List of lines from original content
        modified_lines: List of lines from modified content
        filename: Name of the file being compared
        
    Returns:
        HTML string with formatted diff
    """
    differ = difflib.unified_diff(
        original_lines,
        modified_lines,
        fromfile=f"original/{filename}",
        tofile=f"modified/{filename}",
        lineterm=""
    )
    
    diff_lines = list(differ)
    
    if not diff_lines:
        return "<p style='color: green;'>✅ No changes needed</p>"
    
    html_lines = []
    html_lines.append("<div style='font-family: monospace; font-size: 14px; border: 1px solid #ddd; border-radius: 4px; overflow: auto;'>")
    
    for line in diff_lines:
        if line.startswith('+++') or line.startswith('---'):
            html_lines.append(f"<div style='background-color: #f8f9fa; padding: 4px; font-weight: bold;'>{escape_html(line)}</div>")
        elif line.startswith('@@'):
            html_lines.append(f"<div style='background-color: #e1f5fe; padding: 4px; color: #01579b;'>{escape_html(line)}</div>")
        elif line.startswith('+'):
            html_lines.append(f"<div style='background-color: #e8f5e8; padding: 4px; color: #2e7d32;'>{escape_html(line)}</div>")
        elif line.startswith('-'):
            html_lines.append(f"<div style='background-color: #ffebee; padding: 4px; color: #c62828;'>{escape_html(line)}</div>")
        else:
            html_lines.append(f"<div style='padding: 4px;'>{escape_html(line)}</div>")
    
    html_lines.append("</div>")
    return "".join(html_lines)

def escape_html(text: str) -> str:
    """Escape HTML special characters."""
    return (text
            .replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace('"', "&quot;")
            .replace("'", "&#x27;"))

def get_file_extension_icon(filename: str) -> str:
    """
    Get an appropriate icon for a file based on its extension.
    
    Args:
        filename: Name of the file
        
    Returns:
        Unicode icon string
    """
    extension = Path(filename).suffix.lower()
    
    icon_map = {
        # Programming languages
        '.py': '🐍',
        '.js': '📜',
        '.ts': '📘',
        '.java': '☕',
        '.cpp': '⚙️',
        '.c': '⚙️',
        '.cs': '💎',
        '.php': '🐘',
        '.rb': '💎',
        '.go': '🐹',
        '.rs': '🦀',
        '.swift': '🦉',
        '.kt': '🎯',
        '.scala': '⚡',
        
        # Web technologies
        '.html': '🌐',
        '.css': '🎨',
        '.scss': '🎨',
        '.sass': '🎨',
        '.jsx': '⚛️',
        '.tsx': '⚛️',
        '.vue': '💚',
        
        # Data formats
        '.json': '📋',
        '.xml': '📋',
        '.yaml': '📋',
        '.yml': '📋',
        '.csv': '📊',
        '.sql': '🗄️',
        
        # Documentation
        '.md': '📝',
        '.txt': '📄',
        '.pdf': '📕',
        '.doc': '📘',
        '.docx': '📘',
        
        # Images
        '.png': '🖼️',
        '.jpg': '🖼️',
        '.jpeg': '🖼️',
        '.gif': '🖼️',
        '.svg': '🎨',
        
        # Scripts
        '.sh': '📜',
        '.bat': '📜',
        '.ps1': '📜',
        
        # Config files
        '.config': '⚙️',
        '.conf': '⚙️',
        '.ini': '⚙️',
        '.toml': '⚙️',
        
        # Docker and deployment
        '.dockerfile': '🐳',
        '.dockerignore': '🐳',
        '.gitignore': '🚫',
        '.env': '🔐',
        
        # Package files
        '.package.json': '📦',
        '.requirements.txt': '📦',
        '.gemfile': '💎',
        '.cargo.toml': '📦',
    }
    
    # Special cases for specific filenames
    filename_lower = filename.lower()
    if filename_lower == 'dockerfile':
        return '🐳'
    elif filename_lower == 'makefile':
        return '🔨'
    elif filename_lower == 'readme.md':
        return '📖'
    elif filename_lower.startswith('.git'):
        return '🔧'
    
    return icon_map.get(extension, '📄')

def get_file_language(filename: str) -> str:
    """
    Determine the programming language for syntax highlighting based on file extension.
    
    Args:
        filename: Name of the file
        
    Returns:
        Language identifier for syntax highlighting
    """
    extension = Path(filename).suffix.lower()
    
    language_map = {
        '.py': 'python',
        '.js': 'javascript',
        '.ts': 'typescript',
        '.jsx': 'javascript',
        '.tsx': 'typescript',
        '.java': 'java',
        '.cpp': 'cpp',
        '.c': 'c',
        '.cs': 'csharp',
        '.php': 'php',
        '.rb': 'ruby',
        '.go': 'go',
        '.rs': 'rust',
        '.swift': 'swift',
        '.kt': 'kotlin',
        '.scala': 'scala',
        '.html': 'html',
        '.css': 'css',
        '.scss': 'scss',
        '.sass': 'sass',
        '.json': 'json',
        '.xml': 'xml',
        '.yaml': 'yaml',
        '.yml': 'yaml',
        '.sql': 'sql',
        '.sh': 'bash',
        '.bat': 'batch',
        '.ps1': 'powershell',
        '.md': 'markdown',
        '.dockerfile': 'dockerfile',
        '.tf': 'terraform',
        '.vue': 'vue',
        '.r': 'r',
        '.m': 'matlab',
        '.pl': 'perl',
        '.lua': 'lua',
        '.dart': 'dart',
    }
    
    return language_map.get(extension, 'text')

def truncate_text(text: str, max_length: int = 100) -> str:
    """
    Truncate text to a maximum length with ellipsis.
    
    Args:
        text: Text to truncate
        max_length: Maximum length before truncation
        
    Returns:
        Truncated text with ellipsis if needed
    """
    if len(text) <= max_length:
        return text
    
    return text[:max_length - 3] + "..."

def format_file_size(size_bytes: int) -> str:
    """
    Format file size in human-readable format.
    
    Args:
        size_bytes: Size in bytes
        
    Returns:
        Formatted size string
    """
    if size_bytes == 0:
        return "0 B"
    
    size_names = ["B", "KB", "MB", "GB", "TB"]
    i = 0
    size = float(size_bytes)
    
    while size >= 1024.0 and i < len(size_names) - 1:
        size /= 1024.0
        i += 1
    
    return f"{size:.1f} {size_names[i]}"
