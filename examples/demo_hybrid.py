#!/usr/bin/env python3
"""
Demo script showing DevOpsZealot + Continue.dev integration
"""
import asyncio
import json
from typing import Dict, Any
import httpx

# Configuration
ZEALOT_API_URL = "http://localhost:8080"
API_KEY = "your-api-key-here"  # Set this or use environment variable

async def create_infrastructure_task():
    """Create a task using the hybrid AI system"""
    
    # Example task: Harden security for a Terraform configuration
    task_payload = {
        "type": "infrastructure_edit",
        "repository": "https://github.com/example/infrastructure",
        "branch": "main",
        "files": ["terraform/aws/web-app/main.tf"],
        "requirements": [
            "Enable encryption at rest for all data stores",
            "Implement least privilege IAM policies",
            "Add CloudWatch logging for all resources",
            "Enable AWS GuardDuty for threat detection",
            "Add cost allocation tags"
        ],
        "validation_rules": ["terraform_validate", "security_scan", "cost_analysis"],
        "metadata": {
            "priority": "high",
            "compliance": "SOC2",
            "estimated_impact": "medium"
        },
        "ai_provider": "auto"  # Let the system choose the best provider
    }
    
    async with httpx.AsyncClient() as client:
        # Create task
        print("Creating infrastructure task...")
        response = await client.post(
            f"{ZEALOT_API_URL}/api/v1/tasks",
            json=task_payload,
            headers={"X-API-Key": API_KEY}
        )
        
        if response.status_code != 200:
            print(f"Error creating task: {response.text}")
            return None
        
        result = response.json()
        task_id = result["task_id"]
        print(f"✅ Task created: {task_id}")
        print(f"   AI Provider: {result.get('ai_provider', 'unknown')}")
        
        return task_id

async def monitor_task(task_id: str):
    """Monitor task progress"""
    async with httpx.AsyncClient() as client:
        print(f"\nMonitoring task {task_id}...")
        
        previous_status = None
        while True:
            response = await client.get(
                f"{ZEALOT_API_URL}/api/v1/tasks/{task_id}",
                headers={"X-API-Key": API_KEY}
            )
            
            if response.status_code != 200:
                print(f"Error getting task status: {response.text}")
                break
            
            data = response.json()
            status = data["status"]
            
            if status != previous_status:
                print(f"Status: {status}")
                previous_status = status
            
            if status in ["completed", "failed"]:
                if data.get("result"):
                    print(f"\nTask {status}!")
                    print(f"Duration: {data['result'].get('duration_seconds', 'N/A')} seconds")
                    
                    if status == "completed":
                        print(f"PR URL: {data['result'].get('pr_url', 'N/A')}")
                        print(f"Commit: {data['result'].get('commit_sha', 'N/A')}")
                        print(f"AI Provider Used: {data.get('ai_provider_used', 'unknown')}")
                        
                        # Show changes summary
                        changes = data['result'].get('changes', [])
                        if changes:
                            print(f"\nChanges made ({len(changes)} files):")
                            for change in changes:
                                print(f"  - {change.get('file', 'unknown')}: {change.get('summary', 'modified')}")
                    else:
                        print(f"Error: {data['result'].get('error', 'Unknown error')}")
                
                break
            
            await asyncio.sleep(2)

async def check_ai_stats():
    """Check AI provider performance statistics"""
    async with httpx.AsyncClient() as client:
        print("\nChecking AI provider statistics...")
        
        response = await client.get(
            f"{ZEALOT_API_URL}/api/v1/ai/stats",
            headers={"X-API-Key": API_KEY}
        )
        
        if response.status_code == 200:
            stats = response.json()
            
            print("\nAI Provider Performance:")
            for provider, data in stats["providers"].items():
                print(f"\n{provider.upper()}:")
                print(f"  Total calls: {data['total_calls']}")
                print(f"  Success rate: {data['success_rate']*100:.1f}%")
                print(f"  Avg response time: {data['average_time']:.2f}s")
                print(f"  Performance score: {data['performance_score']:.2f}")
                print(f"  Recommendation: {stats['recommendations'][provider]}")

async def test_mcp_integration():
    """Test MCP server integration"""
    async with httpx.AsyncClient() as client:
        print("\nTesting MCP integration...")
        
        # Get MCP configuration
        response = await client.get(
            f"{ZEALOT_API_URL}/mcp/config",
            headers={"X-API-Key": API_KEY}
        )
        
        if response.status_code == 200:
            config = response.json()
            print(f"✅ MCP server is running")
            print(f"   Resources: {len(config['resources'])}")
            print(f"   Tools: {len(config['tools'])}")
            print(f"   Prompts: {len(config['prompts'])}")
            
            # Test a resource
            resource_response = await client.get(
                f"{ZEALOT_API_URL}/mcp/resource",
                params={"uri": "zealot://validation/rules"},
                headers={"X-API-Key": API_KEY}
            )
            
            if resource_response.status_code == 200:
                rules = resource_response.json()
                print(f"\nAvailable validation rules:")
                for rule in rules.get("rules", []):
                    print(f"  - {rule['name']}: {rule['description']}")

async def analyze_codebase_demo():
    """Demo codebase analysis feature"""
    async with httpx.AsyncClient() as client:
        print("\nRunning codebase security analysis...")
        
        response = await client.post(
            f"{ZEALOT_API_URL}/api/v1/ai/analyze",
            params={
                "repository_path": "/path/to/your/infrastructure",
                "analysis_type": "security"
            },
            headers={"X-API-Key": API_KEY}
        )
        
        if response.status_code == 200:
            analysis = response.json()
            print(f"✅ Analysis complete")
            print(f"   Type: {analysis['analysis_type']}")
            print(f"   Provider: {analysis['provider']}")
            print("\nFindings:")
            print(analysis['findings'][:500] + "..." if len(analysis['findings']) > 500 else analysis['findings'])

async def main():
    """Run the demo"""
    print("DevOpsZealot + Continue.dev Integration Demo")
    print("=" * 50)
    
    # Check system health
    async with httpx.AsyncClient() as client:
        health_response = await client.get(f"{ZEALOT_API_URL}/health")
        
        if health_response.status_code != 200:
            print("❌ DevOpsZealot server is not running!")
            print("   Please start it with: python -m zealot.server")
            return
        
        health = health_response.json()
        print(f"✅ System health: {health['status']}")
        print(f"   Continue integration: {'enabled' if health['components'].get('continue_integration') else 'disabled'}")
        
        if health.get('ai_providers'):
            print("\nAI Providers available:")
            for provider in health['ai_providers']:
                print(f"   - {provider}")
    
    # Run demos
    try:
        # 1. Test MCP integration
        await test_mcp_integration()
        
        # 2. Check AI provider stats
        await check_ai_stats()
        
        # 3. Create and monitor a task
        task_id = await create_infrastructure_task()
        if task_id:
            await monitor_task(task_id)
        
        # 4. Demo codebase analysis (if available)
        # await analyze_codebase_demo()
        
    except Exception as e:
        print(f"\n❌ Error: {e}")

if __name__ == "__main__":
    asyncio.run(main())
