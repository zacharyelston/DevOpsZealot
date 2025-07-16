#!/usr/bin/env python3
"""
Test script for Zealot Development Cycles
Demonstrates build/review/test/report cycle with multiple AI providers
"""
import asyncio
import json
from datetime import datetime
from pathlib import Path

# Add parent directory to path
import sys
sys.path.append(str(Path(__file__).parent.parent))

from src.zealot_cycles import (
    CycleManager, 
    Feature,
    AIProvider,
    EngineeringManager,
    GradingSystem
)
from src.zealot.engine import ZealotEngine
from src.zealot.config import Config
from src.ai.continue_integration import HybridAIClient, HybridConfig, ContinueConfig
from src.ai.continue_integration.hybrid_client import ModelProvider

async def create_test_feature() -> Feature:
    """Create a test feature for comparison"""
    return Feature(
        name="Secure S3 Bucket with Lifecycle Management",
        description="Create an AWS S3 bucket with encryption, versioning, lifecycle policies, and access logging",
        requirements=[
            "Enable AES-256 encryption at rest",
            "Enable versioning with 30-day retention",
            "Configure lifecycle policy to move objects to Glacier after 90 days",
            "Enable access logging to a separate bucket",
            "Implement least-privilege bucket policy",
            "Add cost allocation tags",
            "Enable MFA delete protection"
        ],
        acceptance_criteria=[
            "All data encrypted at rest and in transit",
            "Versioning enabled with proper retention",
            "Lifecycle transitions working correctly",
            "Access logs being written to logging bucket",
            "Bucket policy follows principle of least privilege",
            "All resources properly tagged",
            "MFA delete protection active"
        ],
        technical_constraints=[
            "Use Terraform 1.5+",
            "Compatible with AWS provider 5.x",
            "Must pass tfsec security scanning",
            "Estimated monthly cost under $50"
        ],
        test_scenarios=[
            "Verify encryption is enabled",
            "Test versioning with multiple object versions",
            "Validate lifecycle policy transitions",
            "Confirm access logging is working",
            "Test bucket policy permissions",
            "Verify MFA delete protection"
        ]
    )

async def setup_zealot_engine() -> ZealotEngine:
    """Setup ZealotEngine with hybrid AI client"""
    # Load configuration
    config = Config.from_env()
    
    # Create hybrid AI configuration
    continue_config = ContinueConfig(
        continue_config_path=config.continue_config_path,
        api_url=config.continue_api_url,
        default_model=config.continue_default_model,
        use_local_models=config.use_local_models
    )
    
    hybrid_config = HybridConfig(
        continue_config=continue_config,
        openai_api_key=config.openai_api_key,
        openai_model=config.ai_model,
        default_provider=ModelProvider.AUTO,
        prefer_local=False,
        fallback_enabled=True
    )
    
    # Create engine
    engine = ZealotEngine(config)
    
    # Replace AI client with hybrid client
    engine.ai_client = HybridAIClient(hybrid_config)
    
    # Start engine (mock for testing)
    engine._running = True
    
    return engine

async def run_comparison_test():
    """Run the complete comparison test"""
    print("🚀 Starting Zealot Development Cycle Comparison Test")
    print("=" * 60)
    
    # Setup
    print("\n📋 Setting up test environment...")
    engine = await setup_zealot_engine()
    
    # Create managers
    cycle_manager = CycleManager(engine, {
        'grading_criteria': {}  # Use default criteria
    })
    
    engineering_manager = EngineeringManager({
        'decision_thresholds': {
            'minimum_grade': 0.75,
            'max_acceptable_cost': 5.00
        }
    })
    
    # Create test feature
    print("\n🎯 Creating test feature...")
    feature = await create_test_feature()
    print(f"Feature: {feature.name}")
    print(f"Requirements: {len(feature.requirements)}")
    print(f"Test scenarios: {len(feature.test_scenarios)}")
    
    # Select AI providers to test
    ai_providers = [
        AIProvider.OPENAI_GPT4,
        AIProvider.ANTHROPIC_CLAUDE,
        AIProvider.CONTINUE_MIXED
    ]
    
    print(f"\n🤖 Testing with {len(ai_providers)} AI providers:")
    for provider in ai_providers:
        print(f"  - {provider.value}")
    
    # Run comparison
    print("\n🔄 Running development cycles...")
    print("This will execute build/review/test/report for each provider")
    print("-" * 60)
    
    try:
        comparison_result = await cycle_manager.run_feature_comparison(
            feature=feature,
            ai_providers=ai_providers
        )
        
        # Display results
        print("\n📊 Cycle Results:")
        print("-" * 60)
        
        for provider, result in comparison_result['results'].items():
            print(f"\n{provider}:")
            print(f"  Success: {'✅' if result.success else '❌'}")
            if result.success:
                print(f"  Grade: {result.grade:.2%} ({_get_letter_grade(result.grade)})")
                print(f"  Time: {result.total_time:.1f}s")
                print(f"  Cost: ${result.total_cost:.2f}")
                
                if result.metrics:
                    print(f"  Quality Score: {result.metrics.code_quality_score:.2%}")
                    print(f"  Test Coverage: {result.metrics.test_coverage:.2%}")
                    print(f"  Security Score: {result.metrics.security_score:.2%}")
            else:
                print(f"  Error: {result.stages.get('error', 'Unknown error')}")
        
        # Display comparison
        print("\n📈 Comparison Analysis:")
        print("-" * 60)
        
        comparison = comparison_result['comparison']
        if 'rankings' in comparison:
            print("\nRankings:")
            print(f"  By Grade: {' > '.join(comparison['rankings'].get('by_grade', []))}")
            print(f"  By Cost: {' > '.join(comparison['rankings'].get('by_cost', []))}")
            print(f"  By Time: {' > '.join(comparison['rankings'].get('by_time', []))}")
        
        if 'recommendations' in comparison:
            print("\nRecommendations:")
            for rec in comparison['recommendations']:
                print(f"  • {rec}")
        
        # Engineering Manager Decision
        print("\n🎓 Engineering Manager Analysis:")
        print("-" * 60)
        
        decision = await engineering_manager.analyze_cycle_results(comparison_result)
        
        print(f"\n✨ Decision: {decision.selected_provider}")
        print(f"Confidence: {decision.confidence:.2%}")
        print(f"Rationale: {decision.rationale}")
        print(f"Risk Assessment: {decision.risk_assessment}")
        
        if decision.alternatives:
            print("\nAlternatives considered:")
            for alt_provider, reason in decision.alternatives:
                print(f"  • {alt_provider}: {reason}")
        
        if decision.recommendations:
            print("\nRecommendations:")
            for rec in decision.recommendations:
                print(f"  • {rec}")
        
        # Provider Profiles
        print("\n🏆 Provider Profiles:")
        print("-" * 60)
        
        for provider_name in ai_providers:
            report = engineering_manager.get_provider_report(provider_name.value)
            if report:
                print(f"\n{provider_name.value}:")
                perf = report['performance']
                print(f"  Cycles Run: {perf['total_cycles']}")
                print(f"  Average Grade: {perf['average_grade']:.2%}")
                print(f"  Success Rate: {perf['success_rate']:.2%}")
                
                if report['achievements']['badges']:
                    print(f"  Badges: {', '.join(report['achievements']['badges'])}")
        
        # Export results
        print("\n💾 Exporting results...")
        
        # Export comparison report
        comparison_report_path = "zealot_cycle_comparison_report.json"
        await cycle_manager.export_comparison_report(
            comparison_result,
            comparison_report_path
        )
        print(f"  Comparison report: {comparison_report_path}")
        
        # Export decision history
        decision_history_path = "zealot_engineering_decisions.json"
        await engineering_manager.export_decision_history(decision_history_path)
        print(f"  Decision history: {decision_history_path}")
        
        print("\n✅ Test completed successfully!")
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        # Cleanup
        if hasattr(engine.ai_client, 'close'):
            await engine.ai_client.close()

def _get_letter_grade(numeric_grade: float) -> str:
    """Convert numeric grade to letter grade"""
    if numeric_grade >= 0.97:
        return "A+"
    elif numeric_grade >= 0.93:
        return "A"
    elif numeric_grade >= 0.90:
        return "A-"
    elif numeric_grade >= 0.87:
        return "B+"
    elif numeric_grade >= 0.83:
        return "B"
    elif numeric_grade >= 0.80:
        return "B-"
    elif numeric_grade >= 0.70:
        return "C"
    else:
        return "D"

async def run_simple_test():
    """Run a simplified test for development"""
    print("🧪 Running simplified cycle test")
    
    # This is a mock test that simulates results
    # In production, this would actually run the cycles
    
    from src.zealot_cycles.cycle_manager import CycleResult, PerformanceMetrics
    
    # Create mock results
    mock_results = {
        AIProvider.OPENAI_GPT4.value: CycleResult(
            cycle_id="test-001",
            feature_id="feature-001",
            ai_provider=AIProvider.OPENAI_GPT4,
            success=True,
            grade=0.92,
            total_time=420.5,
            total_cost=2.35,
            metrics=PerformanceMetrics(
                build_time=180.2,
                review_time=120.3,
                test_time=120.0,
                total_time=420.5,
                total_cost=2.35,
                code_quality_score=0.88,
                test_coverage=0.85,
                test_pass_rate=0.95,
                security_score=0.90,
                performance_score=0.87
            )
        ),
        AIProvider.ANTHROPIC_CLAUDE.value: CycleResult(
            cycle_id="test-002",
            feature_id="feature-001",
            ai_provider=AIProvider.ANTHROPIC_CLAUDE,
            success=True,
            grade=0.95,
            total_time=380.2,
            total_cost=1.85,
            metrics=PerformanceMetrics(
                build_time=160.0,
                review_time=110.2,
                test_time=110.0,
                total_time=380.2,
                total_cost=1.85,
                code_quality_score=0.92,
                test_coverage=0.90,
                test_pass_rate=0.98,
                security_score=0.95,
                performance_score=0.90
            )
        ),
        AIProvider.CONTINUE_MIXED.value: CycleResult(
            cycle_id="test-003",
            feature_id="feature-001",
            ai_provider=AIProvider.CONTINUE_MIXED,
            success=True,
            grade=0.88,
            total_time=520.8,
            total_cost=1.20,
            metrics=PerformanceMetrics(
                build_time=220.3,
                review_time=150.5,
                test_time=150.0,
                total_time=520.8,
                total_cost=1.20,
                code_quality_score=0.85,
                test_coverage=0.82,
                test_pass_rate=0.90,
                security_score=0.85,
                performance_score=0.88
            )
        )
    }
    
    # Create comparison
    from src.zealot_cycles.grading import GradeComparator
    
    comparison = GradeComparator.compare_grades(mock_results)
    
    print("\n📊 Mock Results Summary:")
    for provider, result in mock_results.items():
        print(f"\n{provider}:")
        print(f"  Grade: {result.grade:.2%}")
        print(f"  Time: {result.total_time:.1f}s")
        print(f"  Cost: ${result.total_cost:.2f}")
    
    print(f"\n🏆 Best performer: {comparison['best_overall']['provider']}")
    print(f"   Grade: {comparison['best_overall']['grade']:.2%}")
    
    print("\n✅ Simple test completed!")

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Test Zealot Development Cycles")
    parser.add_argument(
        "--simple", 
        action="store_true", 
        help="Run simplified test with mock data"
    )
    
    args = parser.parse_args()
    
    if args.simple:
        asyncio.run(run_simple_test())
    else:
        asyncio.run(run_comparison_test())
