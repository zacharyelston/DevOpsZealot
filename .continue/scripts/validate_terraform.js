// Script to validate Terraform configuration
async function run({ input, context, ide }) {
  const currentFile = await ide.getCurrentFile();
  
  if (!currentFile || !currentFile.path.endsWith('.tf')) {
    return "Please open a Terraform file to validate";
  }

  const content = await ide.readFile(currentFile.path);
  
  try {
    // Call DevOpsZealot validation API
    const response = await fetch("http://localhost:8080/api/v1/validate", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-API-Key": process.env.ZEALOT_API_KEY || ""
      },
      body: JSON.stringify({
        content: content,
        file_type: "terraform",
        rules: ["syntax", "security", "best_practices"]
      })
    });

    const result = await response.json();
    
    if (result.passed) {
      await ide.showNotification({
        message: "✅ Terraform validation passed!",
        level: "info"
      });
      
      return "✅ Validation passed! No issues found.";
    } else {
      // Highlight issues in the editor
      const diagnostics = result.issues.map(issue => ({
        line: issue.line || 0,
        column: issue.column || 0,
        severity: issue.severity || "error",
        message: issue.message
      }));
      
      await ide.setDiagnostics(currentFile.path, diagnostics);
      
      return `❌ Validation failed:

${result.issues.map(issue => `- Line ${issue.line || '?'}: ${issue.message}`).join('\n')}

${result.suggestions ? '\nSuggestions:\n' + result.suggestions.join('\n') : ''}`;
    }
  } catch (error) {
    return `❌ Validation error: ${error.message}`;
  }
}

module.exports = { run };
