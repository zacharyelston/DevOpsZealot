"""
MCP Bridge for Continue.dev integration
Enables DevOpsZealot to be accessed through Continue's MCP protocol
"""
import json
import asyncio
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, asdict
import structlog
from datetime import datetime

logger = structlog.get_logger()

@dataclass
class MCPResource:
    """MCP Resource definition"""
    uri: str
    name: str
    description: str
    mimeType: str = "application/json"
    
@dataclass
class MCPTool:
    """MCP Tool definition"""
    name: str
    description: str
    parameters: Dict[str, Any]
    
@dataclass
class MCPPrompt:
    """MCP Prompt template"""
    name: str
    description: str
    template: str
    parameters: List[str]

class MCPBridge:
    """
    Bridge between DevOpsZealot and Continue.dev via MCP
    
    This allows Continue to:
    - Access DevOpsZealot resources (tasks, logs, etc.)
    - Trigger DevOpsZealot actions (create tasks, validate code)
    - Use pre-configured prompts for infrastructure patterns
    """
    
    def __init__(self, zealot_engine):
        self.zealot_engine = zealot_engine
        self.resources = self._init_resources()
        self.tools = self._init_tools()
        self.prompts = self._init_prompts()
        
        logger.info("MCPBridge initialized",
                   resources=len(self.resources),
                   tools=len(self.tools),
                   prompts=len(self.prompts))
    
    def _init_resources(self) -> List[MCPResource]:
        """Initialize available MCP resources"""
        return [
            MCPResource(
                uri="zealot://tasks/active",
                name="Active Tasks",
                description="List of currently active DevOpsZealot tasks"
            ),
            MCPResource(
                uri="zealot://tasks/history",
                name="Task History", 
                description="Historical task execution data"
            ),
            MCPResource(
                uri="zealot://templates/infrastructure",
                name="Infrastructure Templates",
                description="Pre-configured infrastructure patterns"
            ),
            MCPResource(
                uri="zealot://validation/rules",
                name="Validation Rules",
                description="Available validation rules and their configurations"
            ),
            MCPResource(
                uri="zealot://metrics/performance",
                name="Performance Metrics",
                description="System performance and AI model metrics"
            )
        ]
    
    def _init_tools(self) -> List[MCPTool]:
        """Initialize available MCP tools"""
        return [
            MCPTool(
                name="create_infrastructure_task",
                description="Create a new infrastructure editing task",
                parameters={
                    "type": "object",
                    "properties": {
                        "repository": {
                            "type": "string",
                            "description": "Git repository URL"
                        },
                        "branch": {
                            "type": "string", 
                            "description": "Target branch",
                            "default": "main"
                        },
                        "files": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Files to edit"
                        },
                        "requirements": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Requirements for the changes"
                        },
                        "validation_rules": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Validation rules to apply",
                            "default": ["terraform_validate", "security_scan"]
                        }
                    },
                    "required": ["repository", "files", "requirements"]
                }
            ),
            MCPTool(
                name="validate_infrastructure_code",
                description="Validate infrastructure code without creating a task",
                parameters={
                    "type": "object",
                    "properties": {
                        "content": {
                            "type": "string",
                            "description": "Code content to validate"
                        },
                        "file_type": {
                            "type": "string",
                            "description": "Type of file (terraform, yaml, etc.)"
                        },
                        "rules": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Validation rules to apply"
                        }
                    },
                    "required": ["content", "file_type"]
                }
            ),
            MCPTool(
                name="get_task_status",
                description="Get the status of a DevOpsZealot task",
                parameters={
                    "type": "object",
                    "properties": {
                        "task_id": {
                            "type": "string",
                            "description": "Task ID to check"
                        }
                    },
                    "required": ["task_id"]
                }
            ),
            MCPTool(
                name="analyze_infrastructure_drift",
                description="Analyze drift between code and deployed infrastructure",
                parameters={
                    "type": "object",
                    "properties": {
                        "repository": {
                            "type": "string",
                            "description": "Repository to analyze"
                        },
                        "environment": {
                            "type": "string",
                            "description": "Target environment",
                            "enum": ["dev", "staging", "prod"]
                        }
                    },
                    "required": ["repository", "environment"]
                }
            )
        ]
    
    def _init_prompts(self) -> List[MCPPrompt]:
        """Initialize pre-configured prompts"""
        return [
            MCPPrompt(
                name="terraform_security_hardening",
                description="Harden Terraform configurations for security",
                template="""Review and update the Terraform configuration to implement security best practices:

Requirements:
- Enable encryption at rest for all data stores
- Implement least privilege IAM policies
- Add necessary security groups with minimal permissions
- Enable logging and monitoring for all resources
- Add tags for compliance tracking
- Ensure all secrets are managed through secure services

Current configuration:
{code}

Environment: {environment}
Compliance requirements: {compliance_standards}""",
                parameters=["code", "environment", "compliance_standards"]
            ),
            MCPPrompt(
                name="kubernetes_resource_optimization", 
                description="Optimize Kubernetes resource allocations",
                template="""Analyze and optimize Kubernetes resource allocations:

Current manifest:
{manifest}

Optimization goals:
- Right-size resource requests and limits
- Implement horizontal pod autoscaling where appropriate
- Add resource quotas for namespace
- Optimize for cost while maintaining performance
- Consider spot/preemptible instances where suitable

Cluster info:
- Cloud provider: {cloud_provider}
- Node types: {node_types}
- Current utilization: {utilization_metrics}""",
                parameters=["manifest", "cloud_provider", "node_types", "utilization_metrics"]
            ),
            MCPPrompt(
                name="infrastructure_documentation",
                description="Generate comprehensive infrastructure documentation",
                template="""Generate detailed documentation for this infrastructure code:

Code:
{code}

Documentation should include:
- Overview and architecture
- Resource descriptions and relationships
- Configuration parameters
- Dependencies and requirements
- Deployment instructions
- Maintenance procedures
- Troubleshooting guide
- Cost estimates

Format: {format}
Audience: {audience}""",
                parameters=["code", "format", "audience"]
            )
        ]
    
    async def handle_resource_request(self, uri: str) -> Dict[str, Any]:
        """Handle MCP resource request"""
        logger.info(f"Handling resource request: {uri}")
        
        if uri == "zealot://tasks/active":
            # Get active tasks from engine
            tasks = await self._get_active_tasks()
            return {
                "content": json.dumps(tasks, default=str),
                "mimeType": "application/json"
            }
        
        elif uri == "zealot://tasks/history":
            # Get task history
            history = await self._get_task_history()
            return {
                "content": json.dumps(history, default=str),
                "mimeType": "application/json"
            }
        
        elif uri == "zealot://templates/infrastructure":
            # Return available templates
            templates = self._get_infrastructure_templates()
            return {
                "content": json.dumps(templates),
                "mimeType": "application/json"
            }
        
        elif uri == "zealot://validation/rules":
            # Return validation rules
            rules = self._get_validation_rules()
            return {
                "content": json.dumps(rules),
                "mimeType": "application/json"
            }
        
        elif uri == "zealot://metrics/performance":
            # Return performance metrics
            metrics = await self._get_performance_metrics()
            return {
                "content": json.dumps(metrics),
                "mimeType": "application/json"
            }
        
        else:
            raise ValueError(f"Unknown resource URI: {uri}")
    
    async def handle_tool_request(self, tool_name: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Handle MCP tool execution request"""
        logger.info(f"Handling tool request: {tool_name}", parameters=parameters)
        
        if tool_name == "create_infrastructure_task":
            return await self._create_task(parameters)
        
        elif tool_name == "validate_infrastructure_code":
            return await self._validate_code(parameters)
        
        elif tool_name == "get_task_status":
            return await self._get_task_status(parameters["task_id"])
        
        elif tool_name == "analyze_infrastructure_drift":
            return await self._analyze_drift(parameters)
        
        else:
            raise ValueError(f"Unknown tool: {tool_name}")
    
    async def _create_task(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new DevOpsZealot task"""
        from ...zealot.engine import Task
        
        task = Task(
            repository=params["repository"],
            branch=params.get("branch", "main"),
            files=params["files"],
            requirements=params["requirements"],
            validation_rules=params.get("validation_rules", ["terraform_validate", "security_scan"]),
            metadata=params.get("metadata", {})
        )
        
        task_id = await self.zealot_engine.submit_task(task)
        
        return {
            "success": True,
            "task_id": task_id,
            "status": "queued",
            "message": f"Task {task_id} created successfully"
        }
    
    async def _validate_code(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Validate infrastructure code"""
        validation_results = await self.zealot_engine.validation_pipeline.validate(
            file_type=params["file_type"],
            content=params["content"],
            original="",  # No original for standalone validation
            container=None,  # Run without container for quick validation
            rules=params.get("rules", ["syntax", "security", "best_practices"])
        )
        
        return {
            "valid": validation_results["passed"],
            "results": validation_results,
            "summary": f"Validation {'passed' if validation_results['passed'] else 'failed'}"
        }
    
    async def _get_task_status(self, task_id: str) -> Dict[str, Any]:
        """Get status of a specific task"""
        result = await self.zealot_engine.get_task_status(task_id)
        
        if result:
            return asdict(result)
        else:
            return {
                "error": f"Task {task_id} not found",
                "success": False
            }
    
    async def _analyze_drift(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze infrastructure drift"""
        # This would integrate with terraform state, k8s API, etc.
        # For now, return a mock response
        return {
            "repository": params["repository"],
            "environment": params["environment"],
            "drift_detected": True,
            "resources_drifted": [
                {
                    "resource": "aws_instance.web",
                    "drift_type": "configuration",
                    "details": "Instance type changed from t3.micro to t3.small"
                },
                {
                    "resource": "aws_security_group.web",
                    "drift_type": "missing",
                    "details": "Security group exists in state but not in code"
                }
            ],
            "recommendation": "Run terraform plan to see detailed changes"
        }
    
    async def _get_active_tasks(self) -> List[Dict[str, Any]]:
        """Get list of active tasks"""
        # In real implementation, query task queue
        return [
            {
                "task_id": "task-123",
                "repository": "https://github.com/example/infra",
                "status": "processing",
                "created_at": datetime.utcnow().isoformat(),
                "requirements": ["Enable encryption", "Add monitoring"]
            }
        ]
    
    async def _get_task_history(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get task execution history"""
        # In real implementation, query database
        return [
            {
                "task_id": "task-122",
                "repository": "https://github.com/example/infra",
                "status": "completed",
                "success": True,
                "duration_seconds": 45.2,
                "pr_url": "https://github.com/example/infra/pull/42",
                "completed_at": datetime.utcnow().isoformat()
            }
        ]
    
    def _get_infrastructure_templates(self) -> Dict[str, Any]:
        """Get available infrastructure templates"""
        return {
            "templates": [
                {
                    "name": "aws_web_app",
                    "description": "Standard AWS web application infrastructure",
                    "components": ["ALB", "ECS", "RDS", "ElastiCache"],
                    "estimated_cost": "$150-200/month"
                },
                {
                    "name": "kubernetes_microservice",
                    "description": "Kubernetes microservice deployment",
                    "components": ["Deployment", "Service", "Ingress", "HPA"],
                    "requirements": ["Kubernetes 1.24+"]
                }
            ]
        }
    
    def _get_validation_rules(self) -> Dict[str, Any]:
        """Get available validation rules"""
        return {
            "rules": [
                {
                    "name": "terraform_validate",
                    "description": "Terraform syntax and semantic validation",
                    "severity": "error"
                },
                {
                    "name": "security_scan",
                    "description": "Security best practices scan",
                    "severity": "warning",
                    "checks": ["encryption", "public_access", "iam_permissions"]
                },
                {
                    "name": "cost_analysis",
                    "description": "Analyze potential infrastructure costs",
                    "severity": "info"
                }
            ]
        }
    
    async def _get_performance_metrics(self) -> Dict[str, Any]:
        """Get system performance metrics"""
        # Get metrics from hybrid client if available
        ai_metrics = {}
        if hasattr(self.zealot_engine, 'ai_client') and hasattr(self.zealot_engine.ai_client, 'get_performance_report'):
            ai_metrics = self.zealot_engine.ai_client.get_performance_report()
        
        return {
            "system": {
                "tasks_processed_today": 42,
                "average_task_duration": 38.5,
                "success_rate": 0.95
            },
            "ai_providers": ai_metrics,
            "validation": {
                "rules_executed": 256,
                "issues_found": 23,
                "false_positive_rate": 0.05
            }
        }
    
    def export_mcp_config(self) -> Dict[str, Any]:
        """Export MCP configuration for Continue.dev"""
        return {
            "resources": [asdict(r) for r in self.resources],
            "tools": [asdict(t) for t in self.tools],
            "prompts": [asdict(p) for p in self.prompts]
        }
