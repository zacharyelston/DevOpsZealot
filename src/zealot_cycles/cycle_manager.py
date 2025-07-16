"""
Core Development Cycle Manager
Orchestrates multi-stage development cycles with different AI providers
"""
import asyncio
import uuid
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum
import structlog
import json

from ..ai.continue_integration.hybrid_client import ModelProvider
from .roles import BuilderZealot, ReviewerZealot, TesterZealot, ReporterZealot
from .grading import GradingSystem, PerformanceMetrics

logger = structlog.get_logger()

class CycleStage(Enum):
    """Stages in the development cycle"""
    BUILD = "build"
    REVIEW = "review" 
    TEST = "test"
    REPORT = "report"
    COMPLETE = "complete"

class AIProvider(Enum):
    """Available AI providers for testing"""
    OPENAI_GPT4 = "openai-gpt4"
    ANTHROPIC_CLAUDE = "anthropic-claude"
    CONTINUE_MIXED = "continue-mixed"
    LOCAL_LLAMA = "local-llama"
    
@dataclass
class Feature:
    """Feature specification"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    description: str = ""
    requirements: List[str] = field(default_factory=list)
    acceptance_criteria: List[str] = field(default_factory=list)
    technical_constraints: List[str] = field(default_factory=list)
    test_scenarios: List[str] = field(default_factory=list)
    
@dataclass
class CycleResult:
    """Result from a single development cycle"""
    cycle_id: str
    feature_id: str
    ai_provider: AIProvider
    stages: Dict[str, Any] = field(default_factory=dict)
    metrics: Optional[PerformanceMetrics] = None
    grade: Optional[float] = None
    total_time: Optional[float] = None
    total_cost: Optional[float] = None
    success: bool = False
    
@dataclass
class DevelopmentCycle:
    """A complete development cycle for a feature"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    feature: Feature = None
    ai_provider: AIProvider = AIProvider.OPENAI_GPT4
    current_stage: CycleStage = CycleStage.BUILD
    stage_results: Dict[str, Any] = field(default_factory=dict)
    started_at: datetime = field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None
    
class CycleManager:
    """
    Manages development cycles across multiple AI providers
    Implements build/review/test/report workflow
    """
    
    def __init__(self, zealot_engine, config: Dict[str, Any]):
        self.zealot_engine = zealot_engine
        self.config = config
        self.grading_system = GradingSystem(config.get('grading_criteria', {}))
        
        # Initialize zealot roles
        self.builder = BuilderZealot(zealot_engine)
        self.reviewer = ReviewerZealot(zealot_engine)
        self.tester = TesterZealot(zealot_engine)
        self.reporter = ReporterZealot(zealot_engine)
        
        # Results storage
        self.cycle_results: Dict[str, CycleResult] = {}
        
        logger.info("CycleManager initialized")
    
    async def run_feature_comparison(self, 
                                   feature: Feature,
                                   ai_providers: List[AIProvider]) -> Dict[str, CycleResult]:
        """
        Run the same feature through multiple AI providers
        
        Args:
            feature: Feature specification
            ai_providers: List of AI providers to test
            
        Returns:
            Dict mapping provider name to cycle result
        """
        logger.info(f"Starting feature comparison: {feature.name}",
                   providers=[p.value for p in ai_providers])
        
        results = {}
        tasks = []
        
        # Run cycles concurrently for each provider
        for provider in ai_providers:
            task = asyncio.create_task(
                self._run_single_cycle(feature, provider)
            )
            tasks.append((provider, task))
        
        # Wait for all cycles to complete
        for provider, task in tasks:
            try:
                result = await task
                results[provider.value] = result
                logger.info(f"Completed cycle for {provider.value}",
                          success=result.success,
                          grade=result.grade)
            except Exception as e:
                logger.error(f"Cycle failed for {provider.value}: {e}")
                results[provider.value] = CycleResult(
                    cycle_id=str(uuid.uuid4()),
                    feature_id=feature.id,
                    ai_provider=provider,
                    success=False,
                    stages={"error": str(e)}
                )
        
        # Compare and analyze results
        comparison = await self._compare_results(results)
        
        return {
            "results": results,
            "comparison": comparison,
            "feature": feature
        }
    
    async def _run_single_cycle(self, 
                              feature: Feature,
                              ai_provider: AIProvider) -> CycleResult:
        """
        Run a complete development cycle for a single AI provider
        
        Stages:
        1. Build - Create implementation
        2. Review - Code review and improvements  
        3. Test - Run tests and validate
        4. Report - Generate comprehensive report
        """
        cycle = DevelopmentCycle(
            feature=feature,
            ai_provider=ai_provider
        )
        
        result = CycleResult(
            cycle_id=cycle.id,
            feature_id=feature.id,
            ai_provider=ai_provider
        )
        
        start_time = datetime.utcnow()
        total_cost = 0.0
        
        try:
            # Configure AI provider
            await self._configure_ai_provider(ai_provider)
            
            # Stage 1: Build
            logger.info(f"Starting BUILD stage for {ai_provider.value}")
            build_result = await self.builder.build_feature(
                feature=feature,
                ai_provider=ai_provider
            )
            result.stages['build'] = build_result
            total_cost += build_result.get('cost', 0)
            
            if not build_result.get('success'):
                raise ValueError(f"Build failed: {build_result.get('error')}")
            
            # Stage 2: Review
            logger.info(f"Starting REVIEW stage for {ai_provider.value}")
            review_result = await self.reviewer.review_implementation(
                feature=feature,
                implementation=build_result['implementation'],
                ai_provider=ai_provider
            )
            result.stages['review'] = review_result
            total_cost += review_result.get('cost', 0)
            
            # Apply review feedback if needed
            if review_result.get('improvements'):
                improved_impl = await self.builder.apply_improvements(
                    implementation=build_result['implementation'],
                    improvements=review_result['improvements'],
                    ai_provider=ai_provider
                )
                result.stages['improvements'] = improved_impl
                total_cost += improved_impl.get('cost', 0)
            
            # Stage 3: Test
            logger.info(f"Starting TEST stage for {ai_provider.value}")
            test_result = await self.tester.test_implementation(
                feature=feature,
                implementation=result.stages.get('improvements', build_result)['implementation'],
                ai_provider=ai_provider
            )
            result.stages['test'] = test_result
            total_cost += test_result.get('cost', 0)
            
            # Stage 4: Report
            logger.info(f"Starting REPORT stage for {ai_provider.value}")
            report_result = await self.reporter.generate_report(
                cycle=cycle,
                stages=result.stages,
                ai_provider=ai_provider
            )
            result.stages['report'] = report_result
            total_cost += report_result.get('cost', 0)
            
            # Calculate metrics
            end_time = datetime.utcnow()
            total_time = (end_time - start_time).total_seconds()
            
            # Grade the result
            grade = await self.grading_system.grade_cycle(result)
            
            # Collect performance metrics
            metrics = PerformanceMetrics(
                build_time=result.stages['build'].get('duration', 0),
                review_time=result.stages['review'].get('duration', 0),
                test_time=result.stages['test'].get('duration', 0),
                total_time=total_time,
                total_cost=total_cost,
                code_quality_score=review_result.get('quality_score', 0),
                test_coverage=test_result.get('coverage', 0),
                test_pass_rate=test_result.get('pass_rate', 0),
                security_score=review_result.get('security_score', 0),
                performance_score=test_result.get('performance_score', 0)
            )
            
            result.metrics = metrics
            result.grade = grade
            result.total_time = total_time
            result.total_cost = total_cost
            result.success = True
            
            logger.info(f"Cycle completed for {ai_provider.value}",
                       grade=grade,
                       time=total_time,
                       cost=total_cost)
            
        except Exception as e:
            logger.error(f"Cycle failed for {ai_provider.value}: {e}")
            result.success = False
            result.stages['error'] = str(e)
            result.total_time = (datetime.utcnow() - start_time).total_seconds()
        
        # Store result
        self.cycle_results[cycle.id] = result
        
        return result
    
    async def _configure_ai_provider(self, ai_provider: AIProvider):
        """Configure the AI client for specific provider"""
        provider_config = {
            AIProvider.OPENAI_GPT4: {
                "model": "gpt-4",
                "provider": ModelProvider.OPENAI,
                "temperature": 0.3
            },
            AIProvider.ANTHROPIC_CLAUDE: {
                "model": "claude-3-opus",
                "provider": ModelProvider.CONTINUE,
                "temperature": 0.2
            },
            AIProvider.CONTINUE_MIXED: {
                "model": "auto",
                "provider": ModelProvider.AUTO,
                "temperature": 0.3
            },
            AIProvider.LOCAL_LLAMA: {
                "model": "codellama",
                "provider": ModelProvider.CONTINUE,
                "temperature": 0.4,
                "use_local": True
            }
        }
        
        config = provider_config.get(ai_provider, {})
        
        # Update AI client configuration
        if hasattr(self.zealot_engine.ai_client, 'config'):
            for key, value in config.items():
                if key == 'provider':
                    self.zealot_engine.ai_client.config.default_provider = value
                elif key == 'use_local':
                    self.zealot_engine.ai_client.config.use_local_models = value
                # Add other configuration updates as needed
    
    async def _compare_results(self, results: Dict[str, CycleResult]) -> Dict[str, Any]:
        """
        Compare results across different AI providers
        
        Returns comparative analysis including:
        - Performance rankings
        - Cost efficiency
        - Quality metrics
        - Recommendations
        """
        comparison = {
            "rankings": {},
            "metrics_comparison": {},
            "cost_analysis": {},
            "time_analysis": {},
            "quality_analysis": {},
            "recommendations": []
        }
        
        # Extract successful results
        successful_results = {
            provider: result 
            for provider, result in results.items() 
            if result.success and result.metrics
        }
        
        if not successful_results:
            return {"error": "No successful results to compare"}
        
        # Calculate rankings
        rankings = {}
        
        # Grade ranking
        grade_ranking = sorted(
            successful_results.items(),
            key=lambda x: x[1].grade or 0,
            reverse=True
        )
        rankings['by_grade'] = [provider for provider, _ in grade_ranking]
        
        # Cost ranking (lower is better)
        cost_ranking = sorted(
            successful_results.items(),
            key=lambda x: x[1].total_cost or float('inf')
        )
        rankings['by_cost'] = [provider for provider, _ in cost_ranking]
        
        # Time ranking (lower is better)
        time_ranking = sorted(
            successful_results.items(),
            key=lambda x: x[1].total_time or float('inf')
        )
        rankings['by_time'] = [provider for provider, _ in time_ranking]
        
        # Quality ranking (composite score)
        quality_ranking = sorted(
            successful_results.items(),
            key=lambda x: self._calculate_quality_score(x[1]),
            reverse=True
        )
        rankings['by_quality'] = [provider for provider, _ in quality_ranking]
        
        comparison['rankings'] = rankings
        
        # Detailed metrics comparison
        for provider, result in successful_results.items():
            if result.metrics:
                comparison['metrics_comparison'][provider] = {
                    'build_time': result.metrics.build_time,
                    'review_time': result.metrics.review_time,
                    'test_time': result.metrics.test_time,
                    'total_time': result.metrics.total_time,
                    'total_cost': result.metrics.total_cost,
                    'code_quality': result.metrics.code_quality_score,
                    'test_coverage': result.metrics.test_coverage,
                    'test_pass_rate': result.metrics.test_pass_rate,
                    'security_score': result.metrics.security_score,
                    'performance_score': result.metrics.performance_score
                }
        
        # Cost efficiency analysis
        if grade_ranking:
            best_grade = grade_ranking[0][1].grade
            for provider, result in successful_results.items():
                cost_per_grade_point = result.total_cost / (result.grade or 1)
                comparison['cost_analysis'][provider] = {
                    'total_cost': result.total_cost,
                    'cost_per_grade_point': round(cost_per_grade_point, 4),
                    'cost_efficiency_score': round(best_grade / cost_per_grade_point, 2)
                }
        
        # Generate recommendations
        comparison['recommendations'] = self._generate_recommendations(
            rankings, comparison['metrics_comparison']
        )
        
        return comparison
    
    def _calculate_quality_score(self, result: CycleResult) -> float:
        """Calculate composite quality score"""
        if not result.metrics:
            return 0.0
        
        weights = {
            'code_quality': 0.3,
            'test_coverage': 0.2,
            'test_pass_rate': 0.2,
            'security_score': 0.2,
            'performance_score': 0.1
        }
        
        score = 0.0
        for metric, weight in weights.items():
            value = getattr(result.metrics, f"{metric}_score", 0)
            if metric in ['test_coverage', 'test_pass_rate']:
                value = getattr(result.metrics, metric, 0)
            score += value * weight
        
        return score
    
    def _generate_recommendations(self, 
                                rankings: Dict[str, List[str]], 
                                metrics: Dict[str, Any]) -> List[str]:
        """Generate recommendations based on comparison"""
        recommendations = []
        
        # Best overall performer
        if rankings.get('by_grade'):
            best_overall = rankings['by_grade'][0]
            recommendations.append(
                f"Best overall performer: {best_overall} - "
                f"Highest quality results with balanced metrics"
            )
        
        # Most cost-effective
        if rankings.get('by_cost') and rankings.get('by_grade'):
            # Find provider with good grade and low cost
            grade_positions = {p: i for i, p in enumerate(rankings['by_grade'])}
            cost_positions = {p: i for i, p in enumerate(rankings['by_cost'])}
            
            efficiency_scores = {}
            for provider in grade_positions:
                if provider in cost_positions:
                    # Lower combined position is better
                    efficiency_scores[provider] = (
                        grade_positions[provider] + cost_positions[provider]
                    )
            
            if efficiency_scores:
                most_efficient = min(efficiency_scores, key=efficiency_scores.get)
                recommendations.append(
                    f"Most cost-effective: {most_efficient} - "
                    f"Best balance of quality and cost"
                )
        
        # Fastest provider
        if rankings.get('by_time'):
            fastest = rankings['by_time'][0]
            recommendations.append(
                f"Fastest completion: {fastest} - "
                f"Best for time-critical tasks"
            )
        
        # Quality leader
        if rankings.get('by_quality'):
            quality_leader = rankings['by_quality'][0]
            recommendations.append(
                f"Highest code quality: {quality_leader} - "
                f"Best for mission-critical applications"
            )
        
        # Specific recommendations based on metrics
        for provider, provider_metrics in metrics.items():
            if provider_metrics.get('test_coverage', 0) < 0.8:
                recommendations.append(
                    f"⚠️ {provider}: Consider improving test coverage "
                    f"(currently {provider_metrics.get('test_coverage', 0)*100:.1f}%)"
                )
            
            if provider_metrics.get('security_score', 0) < 0.7:
                recommendations.append(
                    f"⚠️ {provider}: Security improvements needed "
                    f"(score: {provider_metrics.get('security_score', 0)*100:.1f}%)"
                )
        
        return recommendations
    
    async def export_comparison_report(self, 
                                     comparison_result: Dict[str, Any],
                                     output_path: str):
        """Export detailed comparison report"""
        report = {
            "timestamp": datetime.utcnow().isoformat(),
            "feature": {
                "name": comparison_result['feature'].name,
                "description": comparison_result['feature'].description,
                "requirements": comparison_result['feature'].requirements
            },
            "results": {},
            "comparison": comparison_result['comparison'],
            "summary": {
                "total_providers_tested": len(comparison_result['results']),
                "successful_completions": sum(
                    1 for r in comparison_result['results'].values() 
                    if r.success
                ),
                "best_performer": comparison_result['comparison']['rankings'].get(
                    'by_grade', ['N/A']
                )[0],
                "most_cost_effective": comparison_result['comparison']['rankings'].get(
                    'by_cost', ['N/A']
                )[0],
                "fastest": comparison_result['comparison']['rankings'].get(
                    'by_time', ['N/A']
                )[0]
            }
        }
        
        # Add detailed results for each provider
        for provider, result in comparison_result['results'].items():
            report['results'][provider] = {
                "success": result.success,
                "grade": result.grade,
                "total_time": result.total_time,
                "total_cost": result.total_cost,
                "stages": result.stages,
                "metrics": result.metrics.__dict__ if result.metrics else None
            }
        
        # Write report
        with open(output_path, 'w') as f:
            json.dump(report, f, indent=2, default=str)
        
        logger.info(f"Comparison report exported to {output_path}")
        
        return report
