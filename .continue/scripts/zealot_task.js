// Script to create a DevOpsZealot task from Continue
async function run({ input, context, ide }) {
  // Get current file info
  const currentFile = await ide.getCurrentFile();
  if (!currentFile) {
    return "No file is currently open";
  }

  // Extract repository info from git
  const gitInfo = await ide.runCommand("git remote get-url origin");
  const repository = gitInfo.trim();
  
  if (!repository) {
    return "Not in a git repository";
  }

  // Prompt for requirements
  const requirements = await ide.showInputBox({
    prompt: "Enter requirements (comma-separated):",
    placeHolder: "e.g., Enable encryption, Add monitoring, Improve security"
  });

  if (!requirements) {
    return "Task creation cancelled";
  }

  // Get selected text or entire file
  const selectedText = await ide.getSelectedText();
  const hasSelection = selectedText && selectedText.trim().length > 0;
  
  // Prompt for validation rules
  const validationRules = await ide.showQuickPick(
    ["terraform_validate", "security_scan", "cost_analysis", "best_practices"],
    {
      canPickMany: true,
      placeHolder: "Select validation rules to apply"
    }
  );

  // Create task payload
  const task = {
    repository: repository,
    branch: await ide.runCommand("git branch --show-current").then(b => b.trim()),
    files: [currentFile.path],
    requirements: requirements.split(',').map(r => r.trim()),
    validation_rules: validationRules || ["terraform_validate", "security_scan"],
    metadata: {
      created_by: "continue",
      has_selection: hasSelection,
      file_type: currentFile.path.split('.').pop()
    }
  };

  // If user selected specific text, add it to metadata
  if (hasSelection) {
    task.metadata.selected_content = selectedText;
    task.metadata.selection_context = "User selected specific code to modify";
  }

  try {
    // Call DevOpsZealot API
    const response = await fetch("http://localhost:8080/api/v1/tasks", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-API-Key": process.env.ZEALOT_API_KEY || ""
      },
      body: JSON.stringify(task)
    });

    if (!response.ok) {
      const error = await response.json();
      return `Failed to create task: ${error.detail || response.statusText}`;
    }

    const result = await response.json();
    
    // Show success message with task ID
    await ide.showNotification({
      message: `Task created successfully! ID: ${result.task_id}`,
      level: "info",
      actions: [
        {
          title: "View Status",
          command: "zealot.viewTaskStatus",
          arguments: [result.task_id]
        }
      ]
    });

    return `✅ Task created: ${result.task_id}
Status: ${result.status}
Provider: ${result.ai_provider || 'auto'}

You can check the status at: http://localhost:8080/api/v1/tasks/${result.task_id}`;

  } catch (error) {
    return `❌ Error creating task: ${error.message}`;
  }
}

module.exports = { run };
