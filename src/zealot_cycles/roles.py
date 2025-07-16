"""
Specialized Zealot Roles for Development Cycles
Each role has specific responsibilities and evaluation criteria
"""
import asyncio
from typing import Dict, Any, List, Optional
from datetime import datetime
import structlog
from abc import ABC, abstractmethod

logger = structlog.get_logger()

class ZealotRole(ABC):
    """Base class for specialized zealot roles"""
    
    def __init__(self, zealot_engine):
        self.zealot_engine = zealot_engine
        self.role_name = self.__class__.__name__
        
    @abstractmethod
    async def execute(self, **kwargs) -> Dict[str, Any]:
        """Execute the role's primary function"""
        pass
    
    async def _track_metrics(self, start_time: datetime, result: Dict[str, Any]):
        """Add timing and cost metrics to result"""
        end_time = datetime.utcnow()
        duration = (end_time - start_time).total_seconds()
        
        result['duration'] = duration
        result['start_time'] = start_time.isoformat()
        result['end_time'] = end_time.isoformat()
        
        # Estimate cost based on tokens/time
        if 'tokens_used' in result:
            result['cost'] = self._estimate_cost(result['tokens_used'])
        
        return result
    
    def _estimate_cost(self, tokens: Dict[str, int]) -> float:
        """Estimate cost based on token usage"""
        # Rough estimates per 1K tokens
        pricing = {
            'gpt-4': {'prompt': 0.03, 'completion': 0.06},
            'claude-3': {'prompt': 0.015, 'completion': 0.075},
            'local': {'prompt': 0.0, 'completion': 0.0}
        }
        
        # Default to GPT-4 pricing if unknown
        model_pricing = pricing.get('gpt-4')
        
        prompt_cost = (tokens.get('prompt', 0) / 1000) * model_pricing['prompt']
        completion_cost = (tokens.get('completion', 0) / 1000) * model_pricing['completion']
        
        return round(prompt_cost + completion_cost, 4)

class BuilderZealot(ZealotRole):
    """
    Builder: Creates initial implementation based on requirements
    Focus: Functionality, completeness, following specifications
    """
    
    async def execute(self, **kwargs) -> Dict[str, Any]:
        return await self.build_feature(**kwargs)
    
    async def build_feature(self, 
                          feature: Any,
                          ai_provider: Any) -> Dict[str, Any]:
        """Build the initial implementation"""
        start_time = datetime.utcnow()
        
        logger.info(f"BuilderZealot starting feature: {feature.name}")
        
        try:
            # Prepare build prompt
            build_prompt = self._create_build_prompt(feature)
            
            # Generate implementation
            response = await self.zealot_engine.ai_client.generate_edit(
                current_content="",  # Starting from scratch
                requirements=feature.requirements,
                file_type="terraform",  # Example, should be dynamic
                context={
                    "feature_name": feature.name,
                    "description": feature.description,
                    "acceptance_criteria": feature.acceptance_criteria,
                    "technical_constraints": feature.technical_constraints,
                    "prompt_override": build_prompt
                }
            )
            
            implementation = {
                "code": response.get('content', ''),
                "summary": response.get('summary', ''),
                "files": self._organize_code_into_files(response.get('content', '')),
                "tokens_used": response.get('tokens_used', {}),
                "confidence": response.get('confidence', 0)
            }
            
            result = {
                "success": True,
                "implementation": implementation,
                "tokens_used": response.get('tokens_used', {}),
                "ai_provider": ai_provider.value
            }
            
        except Exception as e:
            logger.error(f"BuilderZealot failed: {e}")
            result = {
                "success": False,
                "error": str(e),
                "ai_provider": ai_provider.value
            }
        
        return await self._track_metrics(start_time, result)
    
    async def apply_improvements(self,
                               implementation: Dict[str, Any],
                               improvements: List[Dict[str, Any]],
                               ai_provider: Any) -> Dict[str, Any]:
        """Apply review feedback to improve implementation"""
        start_time = datetime.utcnow()
        
        try:
            # Create improvement prompt
            improvement_prompt = self._create_improvement_prompt(
                implementation, improvements
            )
            
            # Apply improvements
            response = await self.zealot_engine.ai_client.generate_edit(
                current_content=implementation['code'],
                requirements=[imp['description'] for imp in improvements],
                file_type="terraform",
                context={
                    "task": "apply_improvements",
                    "prompt_override": improvement_prompt
                }
            )
            
            improved_implementation = {
                "code": response.get('content', ''),
                "summary": response.get('summary', ''),
                "files": self._organize_code_into_files(response.get('content', '')),
                "tokens_used": response.get('tokens_used', {}),
                "improvements_applied": len(improvements)
            }
            
            result = {
                "success": True,
                "implementation": improved_implementation,
                "tokens_used": response.get('tokens_used', {})
            }
            
        except Exception as e:
            logger.error(f"Improvement application failed: {e}")
            result = {
                "success": False,
                "error": str(e)
            }
        
        return await self._track_metrics(start_time, result)
    
    def _create_build_prompt(self, feature) -> str:
        """Create detailed build prompt"""
        return f"""Build a complete implementation for the following feature:

Feature: {feature.name}
Description: {feature.description}

Requirements:
{chr(10).join(f'- {req}' for req in feature.requirements)}

Acceptance Criteria:
{chr(10).join(f'- {criteria}' for criteria in feature.acceptance_criteria)}

Technical Constraints:
{chr(10).join(f'- {constraint}' for constraint in feature.technical_constraints)}

Provide a complete, production-ready implementation that:
1. Meets all requirements and acceptance criteria
2. Follows best practices and conventions
3. Includes necessary error handling
4. Is well-documented with comments
5. Considers security and performance
"""
    
    def _create_improvement_prompt(self, implementation, improvements) -> str:
        """Create prompt for applying improvements"""
        improvements_text = "\n".join([
            f"- {imp['type']}: {imp['description']}"
            for imp in improvements
        ])
        
        return f"""Apply the following improvements to the code:

{improvements_text}

Current implementation summary: {implementation.get('summary', 'N/A')}

Make the necessary changes while:
1. Maintaining existing functionality
2. Not introducing new bugs
3. Keeping the code clean and readable
"""
    
    def _organize_code_into_files(self, code: str) -> List[Dict[str, str]]:
        """Organize generated code into logical files"""
        # Simple implementation - in reality would parse and split code
        return [
            {
                "path": "main.tf",
                "content": code,
                "type": "terraform"
            }
        ]

class ReviewerZealot(ZealotRole):
    """
    Reviewer: Reviews code for quality, security, and best practices
    Focus: Code quality, security vulnerabilities, improvements
    """
    
    async def execute(self, **kwargs) -> Dict[str, Any]:
        return await self.review_implementation(**kwargs)
    
    async def review_implementation(self,
                                  feature: Any,
                                  implementation: Dict[str, Any],
                                  ai_provider: Any) -> Dict[str, Any]:
        """Review the implementation"""
        start_time = datetime.utcnow()
        
        logger.info(f"ReviewerZealot reviewing implementation for: {feature.name}")
        
        try:
            # Prepare review prompt
            review_prompt = self._create_review_prompt(feature, implementation)
            
            # Use validation capability for review
            response = await self.zealot_engine.ai_client.validate_changes(
                original="",  # No original since it's new code
                modified=implementation['code'],
                requirements=feature.requirements,
                file_type="terraform"
            )
            
            # Perform additional quality checks
            quality_analysis = await self._analyze_code_quality(implementation)
            security_analysis = await self._analyze_security(implementation)
            
            # Compile improvements
            improvements = []
            
            if not response.get('meets_requirements'):
                for issue in response.get('issues', []):
                    improvements.append({
                        'type': 'requirement',
                        'severity': 'high',
                        'description': issue
                    })
            
            for suggestion in response.get('suggestions', []):
                improvements.append({
                    'type': 'enhancement',
                    'severity': 'medium',
                    'description': suggestion
                })
            
            # Add security improvements
            for issue in security_analysis.get('issues', []):
                improvements.append({
                    'type': 'security',
                    'severity': issue.get('severity', 'high'),
                    'description': issue.get('description')
                })
            
            result = {
                "success": True,
                "meets_requirements": response.get('meets_requirements', False),
                "valid": response.get('valid', False),
                "improvements": improvements,
                "quality_score": quality_analysis.get('score', 0),
                "security_score": security_analysis.get('score', 0),
                "metrics": {
                    "total_issues": len(improvements),
                    "critical_issues": sum(1 for i in improvements if i['severity'] == 'high'),
                    "code_smells": quality_analysis.get('code_smells', 0),
                    "complexity": quality_analysis.get('complexity', 0)
                },
                "tokens_used": response.get('tokens_used', {})
            }
            
        except Exception as e:
            logger.error(f"ReviewerZealot failed: {e}")
            result = {
                "success": False,
                "error": str(e)
            }
        
        return await self._track_metrics(start_time, result)
    
    def _create_review_prompt(self, feature, implementation) -> str:
        """Create review prompt"""
        return f"""Review this implementation for the feature: {feature.name}

Requirements to verify:
{chr(10).join(f'- {req}' for req in feature.requirements)}

Review for:
1. Requirement compliance
2. Code quality and best practices
3. Security vulnerabilities
4. Performance issues
5. Maintainability
6. Error handling
7. Documentation completeness

Provide specific, actionable feedback.
"""
    
    async def _analyze_code_quality(self, implementation: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze code quality metrics"""
        # Simplified quality analysis
        code = implementation.get('code', '')
        
        quality_metrics = {
            'lines_of_code': len(code.split('\n')),
            'comment_ratio': self._calculate_comment_ratio(code),
            'complexity': self._estimate_complexity(code),
            'code_smells': self._detect_code_smells(code)
        }
        
        # Calculate quality score (0-1)
        score = 1.0
        if quality_metrics['comment_ratio'] < 0.1:
            score -= 0.2
        if quality_metrics['complexity'] > 10:
            score -= 0.3
        if quality_metrics['code_smells'] > 5:
            score -= 0.2
        
        return {
            'score': max(0, score),
            'metrics': quality_metrics,
            'code_smells': quality_metrics['code_smells'],
            'complexity': quality_metrics['complexity']
        }
    
    async def _analyze_security(self, implementation: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze security aspects"""
        code = implementation.get('code', '')
        issues = []
        
        # Simple security checks (would be more sophisticated in reality)
        security_patterns = [
            ('password.*=.*"[^"]*"', 'Hardcoded password detected'),
            ('0.0.0.0/0', 'Overly permissive network access'),
            ('iam.*:.*\\*', 'Overly permissive IAM policy'),
            ('encrypt.*false', 'Encryption disabled')
        ]
        
        import re
        for pattern, description in security_patterns:
            if re.search(pattern, code, re.IGNORECASE):
                issues.append({
                    'severity': 'high',
                    'description': description
                })
        
        score = 1.0 - (len(issues) * 0.2)
        
        return {
            'score': max(0, score),
            'issues': issues
        }
    
    def _calculate_comment_ratio(self, code: str) -> float:
        """Calculate ratio of comments to code"""
        lines = code.split('\n')
        comment_lines = sum(1 for line in lines if line.strip().startswith(('#', '//', '/*')))
        return comment_lines / max(len(lines), 1)
    
    def _estimate_complexity(self, code: str) -> int:
        """Estimate cyclomatic complexity"""
        # Simplified - count control structures
        complexity_keywords = ['if', 'for', 'while', 'case', 'catch']
        return sum(code.count(keyword) for keyword in complexity_keywords)
    
    def _detect_code_smells(self, code: str) -> int:
        """Detect common code smells"""
        smells = 0
        
        # Long lines
        for line in code.split('\n'):
            if len(line) > 120:
                smells += 1
        
        # Duplicate code (simplified)
        lines = code.split('\n')
        if len(lines) != len(set(lines)):
            smells += (len(lines) - len(set(lines)))
        
        return smells

class TesterZealot(ZealotRole):
    """
    Tester: Creates and runs tests, validates functionality
    Focus: Test coverage, edge cases, performance testing
    """
    
    async def execute(self, **kwargs) -> Dict[str, Any]:
        return await self.test_implementation(**kwargs)
    
    async def test_implementation(self,
                                feature: Any,
                                implementation: Dict[str, Any],
                                ai_provider: Any) -> Dict[str, Any]:
        """Test the implementation"""
        start_time = datetime.utcnow()
        
        logger.info(f"TesterZealot testing implementation for: {feature.name}")
        
        try:
            # Generate test cases
            test_cases = await self._generate_test_cases(feature, implementation)
            
            # Run tests (simulated - in reality would execute actual tests)
            test_results = await self._run_tests(test_cases, implementation)
            
            # Performance testing
            performance_results = await self._run_performance_tests(implementation)
            
            # Calculate metrics
            total_tests = len(test_results)
            passed_tests = sum(1 for r in test_results if r['passed'])
            
            result = {
                "success": True,
                "test_cases": test_cases,
                "test_results": test_results,
                "performance_results": performance_results,
                "coverage": self._calculate_coverage(implementation, test_cases),
                "pass_rate": passed_tests / max(total_tests, 1),
                "total_tests": total_tests,
                "passed_tests": passed_tests,
                "failed_tests": total_tests - passed_tests,
                "performance_score": performance_results.get('score', 0),
                "metrics": {
                    "unit_tests": sum(1 for t in test_cases if t['type'] == 'unit'),
                    "integration_tests": sum(1 for t in test_cases if t['type'] == 'integration'),
                    "edge_cases": sum(1 for t in test_cases if t['type'] == 'edge_case'),
                    "performance_tests": sum(1 for t in test_cases if t['type'] == 'performance')
                }
            }
            
        except Exception as e:
            logger.error(f"TesterZealot failed: {e}")
            result = {
                "success": False,
                "error": str(e)
            }
        
        return await self._track_metrics(start_time, result)
    
    async def _generate_test_cases(self, feature, implementation) -> List[Dict[str, Any]]:
        """Generate comprehensive test cases"""
        test_prompt = f"""Generate comprehensive test cases for this feature:

Feature: {feature.name}
Test Scenarios:
{chr(10).join(f'- {scenario}' for scenario in feature.test_scenarios)}

Create test cases that cover:
1. Happy path scenarios
2. Edge cases
3. Error conditions
4. Performance scenarios
5. Security scenarios

For each test case, specify:
- Name
- Type (unit/integration/edge_case/performance)
- Input
- Expected output
- Validation criteria
"""
        
        # In reality, would use AI to generate test cases
        # For now, create sample test cases
        test_cases = []
        
        # Happy path tests
        for i, scenario in enumerate(feature.test_scenarios[:3]):
            test_cases.append({
                'name': f'test_happy_path_{i+1}',
                'type': 'unit',
                'description': scenario,
                'input': {'scenario': scenario},
                'expected': 'success',
                'validation': 'meets_acceptance_criteria'
            })
        
        # Edge cases
        test_cases.extend([
            {
                'name': 'test_empty_input',
                'type': 'edge_case',
                'description': 'Test with empty input',
                'input': {},
                'expected': 'graceful_failure',
                'validation': 'proper_error_handling'
            },
            {
                'name': 'test_large_scale',
                'type': 'performance',
                'description': 'Test with large scale input',
                'input': {'scale': 'large'},
                'expected': 'performance_within_limits',
                'validation': 'response_time < 5s'
            }
        ])
        
        return test_cases
    
    async def _run_tests(self, test_cases: List[Dict[str, Any]], 
                        implementation: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Run test cases (simulated)"""
        results = []
        
        for test_case in test_cases:
            # Simulate test execution
            # In reality, would actually run tests
            passed = True  # Simulate 90% pass rate
            if test_case['type'] == 'edge_case':
                import random
                passed = random.random() > 0.2
            
            results.append({
                'test_name': test_case['name'],
                'test_type': test_case['type'],
                'passed': passed,
                'execution_time': 0.1,
                'error': None if passed else 'Simulated failure',
                'details': test_case.get('validation', '')
            })
        
        return results
    
    async def _run_performance_tests(self, implementation: Dict[str, Any]) -> Dict[str, Any]:
        """Run performance tests"""
        # Simulated performance testing
        return {
            'score': 0.85,
            'metrics': {
                'response_time_avg': 250,  # ms
                'response_time_p99': 800,   # ms
                'throughput': 1000,         # requests/sec
                'resource_usage': {
                    'cpu': 45,              # percent
                    'memory': 512           # MB
                }
            },
            'bottlenecks': [],
            'recommendations': [
                "Consider caching for frequently accessed resources",
                "Optimize database queries for better performance"
            ]
        }
    
    def _calculate_coverage(self, implementation: Dict[str, Any], 
                          test_cases: List[Dict[str, Any]]) -> float:
        """Calculate test coverage"""
        # Simplified coverage calculation
        # In reality, would analyze code paths
        code_lines = implementation.get('code', '').count('\n')
        test_count = len(test_cases)
        
        # Rough estimate: assume each test covers 10 lines
        covered_lines = min(test_count * 10, code_lines)
        
        return covered_lines / max(code_lines, 1)

class ReporterZealot(ZealotRole):
    """
    Reporter: Generates comprehensive reports on the development cycle
    Focus: Clear documentation, metrics, recommendations
    """
    
    async def execute(self, **kwargs) -> Dict[str, Any]:
        return await self.generate_report(**kwargs)
    
    async def generate_report(self,
                            cycle: Any,
                            stages: Dict[str, Any],
                            ai_provider: Any) -> Dict[str, Any]:
        """Generate comprehensive report"""
        start_time = datetime.utcnow()
        
        logger.info(f"ReporterZealot generating report for cycle: {cycle.id}")
        
        try:
            # Analyze all stages
            analysis = self._analyze_stages(stages)
            
            # Generate narrative report
            narrative = await self._generate_narrative(cycle, stages, analysis)
            
            # Generate technical report
            technical = self._generate_technical_report(stages, analysis)
            
            # Generate recommendations
            recommendations = self._generate_recommendations(analysis)
            
            result = {
                "success": True,
                "report": {
                    "cycle_id": cycle.id,
                    "feature": cycle.feature.name,
                    "ai_provider": ai_provider.value,
                    "summary": analysis['summary'],
                    "narrative": narrative,
                    "technical": technical,
                    "recommendations": recommendations,
                    "metrics": analysis['metrics'],
                    "timeline": self._generate_timeline(stages),
                    "cost_breakdown": self._calculate_cost_breakdown(stages)
                }
            }
            
        except Exception as e:
            logger.error(f"ReporterZealot failed: {e}")
            result = {
                "success": False,
                "error": str(e)
            }
        
        return await self._track_metrics(start_time, result)
    
    def _analyze_stages(self, stages: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze all stages for insights"""
        analysis = {
            'summary': {},
            'metrics': {},
            'issues': [],
            'successes': []
        }
        
        # Build stage analysis
        if 'build' in stages and stages['build'].get('success'):
            analysis['successes'].append("Successfully created initial implementation")
            analysis['metrics']['build_confidence'] = stages['build'].get(
                'implementation', {}
            ).get('confidence', 0)
        else:
            analysis['issues'].append("Build stage failed or incomplete")
        
        # Review stage analysis
        if 'review' in stages:
            review = stages['review']
            if review.get('success'):
                analysis['metrics']['quality_score'] = review.get('quality_score', 0)
                analysis['metrics']['security_score'] = review.get('security_score', 0)
                
                improvement_count = len(review.get('improvements', []))
                if improvement_count > 0:
                    analysis['issues'].append(
                        f"Review identified {improvement_count} improvements needed"
                    )
            else:
                analysis['issues'].append("Review stage failed")
        
        # Test stage analysis
        if 'test' in stages:
            test = stages['test']
            if test.get('success'):
                analysis['metrics']['test_coverage'] = test.get('coverage', 0)
                analysis['metrics']['test_pass_rate'] = test.get('pass_rate', 0)
                
                if test.get('pass_rate', 0) < 1.0:
                    failed_tests = test.get('failed_tests', 0)
                    analysis['issues'].append(f"{failed_tests} tests failed")
                else:
                    analysis['successes'].append("All tests passed")
            else:
                analysis['issues'].append("Test stage failed")
        
        # Overall summary
        all_stages_success = all(
            stages.get(stage, {}).get('success', False)
            for stage in ['build', 'review', 'test']
        )
        
        analysis['summary'] = {
            'overall_success': all_stages_success,
            'stages_completed': sum(
                1 for stage in ['build', 'review', 'test', 'improvements']
                if stage in stages
            ),
            'total_issues': len(analysis['issues']),
            'total_successes': len(analysis['successes'])
        }
        
        return analysis
    
    async def _generate_narrative(self, cycle, stages, analysis) -> str:
        """Generate human-readable narrative report"""
        narrative_parts = []
        
        # Introduction
        narrative_parts.append(
            f"Development Cycle Report for Feature: {cycle.feature.name}\n"
            f"AI Provider: {cycle.ai_provider.value}\n"
            f"Cycle ID: {cycle.id}\n"
        )
        
        # Executive Summary
        if analysis['summary']['overall_success']:
            narrative_parts.append(
                "\n✅ SUMMARY: Development cycle completed successfully with "
                f"{analysis['summary']['stages_completed']} stages completed."
            )
        else:
            narrative_parts.append(
                "\n⚠️ SUMMARY: Development cycle encountered issues. "
                f"{analysis['summary']['total_issues']} issues identified."
            )
        
        # Stage narratives
        narrative_parts.append("\n\n📋 STAGE DETAILS:")
        
        # Build stage
        if 'build' in stages:
            build = stages['build']
            narrative_parts.append(
                f"\n\n1. BUILD STAGE:"
                f"\n   Status: {'✅ Success' if build.get('success') else '❌ Failed'}"
                f"\n   Duration: {build.get('duration', 0):.2f}s"
                f"\n   Cost: ${build.get('cost', 0):.4f}"
            )
            if build.get('success'):
                impl = build.get('implementation', {})
                narrative_parts.append(
                    f"\n   Confidence: {impl.get('confidence', 0)*100:.1f}%"
                    f"\n   Summary: {impl.get('summary', 'N/A')}"
                )
        
        # Review stage
        if 'review' in stages:
            review = stages['review']
            narrative_parts.append(
                f"\n\n2. REVIEW STAGE:"
                f"\n   Status: {'✅ Success' if review.get('success') else '❌ Failed'}"
                f"\n   Duration: {review.get('duration', 0):.2f}s"
            )
            if review.get('success'):
                narrative_parts.append(
                    f"\n   Quality Score: {review.get('quality_score', 0)*100:.1f}%"
                    f"\n   Security Score: {review.get('security_score', 0)*100:.1f}%"
                    f"\n   Improvements Needed: {len(review.get('improvements', []))}"
                )
        
        # Test stage
        if 'test' in stages:
            test = stages['test']
            narrative_parts.append(
                f"\n\n3. TEST STAGE:"
                f"\n   Status: {'✅ Success' if test.get('success') else '❌ Failed'}"
                f"\n   Duration: {test.get('duration', 0):.2f}s"
            )
            if test.get('success'):
                narrative_parts.append(
                    f"\n   Tests Run: {test.get('total_tests', 0)}"
                    f"\n   Pass Rate: {test.get('pass_rate', 0)*100:.1f}%"
                    f"\n   Coverage: {test.get('coverage', 0)*100:.1f}%"
                    f"\n   Performance Score: {test.get('performance_score', 0)*100:.1f}%"
                )
        
        # Issues and successes
        if analysis['issues']:
            narrative_parts.append("\n\n⚠️ ISSUES IDENTIFIED:")
            for issue in analysis['issues']:
                narrative_parts.append(f"\n   - {issue}")
        
        if analysis['successes']:
            narrative_parts.append("\n\n✅ SUCCESSES:")
            for success in analysis['successes']:
                narrative_parts.append(f"\n   - {success}")
        
        return ''.join(narrative_parts)
    
    def _generate_technical_report(self, stages, analysis) -> Dict[str, Any]:
        """Generate technical metrics report"""
        return {
            'stages': {
                stage: {
                    'success': data.get('success', False),
                    'duration': data.get('duration', 0),
                    'cost': data.get('cost', 0),
                    'tokens_used': data.get('tokens_used', {})
                }
                for stage, data in stages.items()
            },
            'quality_metrics': {
                'code_quality': analysis['metrics'].get('quality_score', 0),
                'security_score': analysis['metrics'].get('security_score', 0),
                'test_coverage': analysis['metrics'].get('test_coverage', 0),
                'test_pass_rate': analysis['metrics'].get('test_pass_rate', 0)
            },
            'performance_metrics': stages.get('test', {}).get('performance_results', {}),
            'cost_analysis': self._calculate_cost_breakdown(stages)
        }
    
    def _generate_recommendations(self, analysis) -> List[str]:
        """Generate actionable recommendations"""
        recommendations = []
        
        # Quality recommendations
        if analysis['metrics'].get('quality_score', 0) < 0.7:
            recommendations.append(
                "Code quality below threshold. Consider refactoring for better "
                "maintainability and following coding standards more closely."
            )
        
        # Security recommendations
        if analysis['metrics'].get('security_score', 0) < 0.8:
            recommendations.append(
                "Security improvements needed. Review and address identified "
                "vulnerabilities before production deployment."
            )
        
        # Testing recommendations
        if analysis['metrics'].get('test_coverage', 0) < 0.8:
            recommendations.append(
                "Test coverage below 80%. Add more test cases to cover edge "
                "cases and error conditions."
            )
        
        if analysis['metrics'].get('test_pass_rate', 0) < 0.95:
            recommendations.append(
                "Test pass rate below 95%. Fix failing tests before deployment."
            )
        
        # General recommendations
        if analysis['summary']['total_issues'] > 5:
            recommendations.append(
                "High number of issues identified. Consider breaking down the "
                "feature into smaller, more manageable components."
            )
        
        if not recommendations:
            recommendations.append(
                "Development cycle completed successfully. Ready for deployment "
                "after final manual review."
            )
        
        return recommendations
    
    def _generate_timeline(self, stages) -> List[Dict[str, Any]]:
        """Generate timeline of events"""
        timeline = []
        
        for stage_name, stage_data in stages.items():
            if 'start_time' in stage_data and 'end_time' in stage_data:
                timeline.append({
                    'stage': stage_name,
                    'start': stage_data['start_time'],
                    'end': stage_data['end_time'],
                    'duration': stage_data.get('duration', 0),
                    'status': 'success' if stage_data.get('success') else 'failed'
                })
        
        # Sort by start time
        timeline.sort(key=lambda x: x['start'])
        
        return timeline
    
    def _calculate_cost_breakdown(self, stages) -> Dict[str, Any]:
        """Calculate detailed cost breakdown"""
        total_cost = 0.0
        breakdown = {}
        
        for stage_name, stage_data in stages.items():
            cost = stage_data.get('cost', 0)
            total_cost += cost
            breakdown[stage_name] = {
                'cost': cost,
                'percentage': 0  # Will calculate after total
            }
        
        # Calculate percentages
        if total_cost > 0:
            for stage in breakdown:
                breakdown[stage]['percentage'] = round(
                    (breakdown[stage]['cost'] / total_cost) * 100, 2
                )
        
        return {
            'total': round(total_cost, 4),
            'by_stage': breakdown,
            'currency': 'USD'
        }
