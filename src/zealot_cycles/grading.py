"""
Grading System for Development Cycles
Evaluates quality, performance, and efficiency
"""
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
import structlog

logger = structlog.get_logger()

@dataclass
class PerformanceMetrics:
    """Performance metrics for a development cycle"""
    build_time: float = 0.0
    review_time: float = 0.0
    test_time: float = 0.0
    total_time: float = 0.0
    total_cost: float = 0.0
    code_quality_score: float = 0.0
    test_coverage: float = 0.0
    test_pass_rate: float = 0.0
    security_score: float = 0.0
    performance_score: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return self.__dict__

class GradingSystem:
    """
    Comprehensive grading system for development cycles
    Evaluates multiple dimensions and provides weighted scores
    """
    
    def __init__(self, criteria: Optional[Dict[str, Any]] = None):
        # Default grading criteria and weights
        self.criteria = criteria or {
            'functionality': {
                'weight': 0.30,
                'sub_criteria': {
                    'requirements_met': 0.40,
                    'acceptance_criteria': 0.30,
                    'feature_completeness': 0.30
                }
            },
            'quality': {
                'weight': 0.25,
                'sub_criteria': {
                    'code_quality': 0.35,
                    'maintainability': 0.25,
                    'documentation': 0.20,
                    'best_practices': 0.20
                }
            },
            'testing': {
                'weight': 0.20,
                'sub_criteria': {
                    'test_coverage': 0.35,
                    'test_pass_rate': 0.35,
                    'edge_cases': 0.30
                }
            },
            'security': {
                'weight': 0.15,
                'sub_criteria': {
                    'vulnerability_scan': 0.50,
                    'security_practices': 0.50
                }
            },
            'efficiency': {
                'weight': 0.10,
                'sub_criteria': {
                    'time_efficiency': 0.40,
                    'cost_efficiency': 0.30,
                    'resource_usage': 0.30
                }
            }
        }
        
        # Ensure weights sum to 1.0
        self._normalize_weights()
    
    def _normalize_weights(self):
        """Normalize weights to sum to 1.0"""
        total_weight = sum(c['weight'] for c in self.criteria.values())
        if total_weight != 1.0:
            for category in self.criteria.values():
                category['weight'] = category['weight'] / total_weight
    
    async def grade_cycle(self, cycle_result: Any) -> float:
        """
        Grade a complete development cycle
        
        Returns:
            Grade between 0.0 and 1.0 (0-100%)
        """
        if not cycle_result.success:
            return 0.0
        
        grades = {}
        
        # Grade each category
        grades['functionality'] = self._grade_functionality(cycle_result)
        grades['quality'] = self._grade_quality(cycle_result)
        grades['testing'] = self._grade_testing(cycle_result)
        grades['security'] = self._grade_security(cycle_result)
        grades['efficiency'] = self._grade_efficiency(cycle_result)
        
        # Calculate weighted total
        total_grade = 0.0
        for category, grade in grades.items():
            weight = self.criteria[category]['weight']
            total_grade += grade * weight
        
        # Log detailed grading
        logger.info(f"Grading complete for cycle {cycle_result.cycle_id}",
                   grades=grades,
                   total_grade=round(total_grade, 3))
        
        return round(total_grade, 3)
    
    def _grade_functionality(self, result: Any) -> float:
        """Grade functionality aspects"""
        scores = {}
        
        # Requirements met
        review_stage = result.stages.get('review', {})
        if review_stage.get('meets_requirements'):
            scores['requirements_met'] = 1.0
        else:
            # Partial credit based on issues
            total_requirements = len(result.stages.get('build', {}).get('implementation', {}).get('requirements', []))
            requirement_issues = sum(
                1 for imp in review_stage.get('improvements', [])
                if imp.get('type') == 'requirement'
            )
            if total_requirements > 0:
                scores['requirements_met'] = max(0, 1 - (requirement_issues / total_requirements))
            else:
                scores['requirements_met'] = 0.5
        
        # Acceptance criteria
        # Simulated - would check against actual criteria
        test_pass_rate = result.stages.get('test', {}).get('pass_rate', 0)
        scores['acceptance_criteria'] = test_pass_rate
        
        # Feature completeness
        # Based on build confidence and review validation
        build_confidence = result.stages.get('build', {}).get('implementation', {}).get('confidence', 0)
        review_valid = result.stages.get('review', {}).get('valid', False)
        scores['feature_completeness'] = (build_confidence + (1.0 if review_valid else 0.5)) / 2
        
        return self._calculate_weighted_score(scores, self.criteria['functionality']['sub_criteria'])
    
    def _grade_quality(self, result: Any) -> float:
        """Grade code quality aspects"""
        scores = {}
        
        review_stage = result.stages.get('review', {})
        
        # Code quality score from review
        scores['code_quality'] = review_stage.get('quality_score', 0)
        
        # Maintainability (inverse of complexity)
        complexity = review_stage.get('metrics', {}).get('complexity', 10)
        scores['maintainability'] = max(0, 1 - (complexity / 50))  # 50 is max acceptable complexity
        
        # Documentation (based on comment ratio)
        # This would be from the review analysis
        scores['documentation'] = 0.7  # Placeholder
        
        # Best practices (based on code smells)
        code_smells = review_stage.get('metrics', {}).get('code_smells', 0)
        scores['best_practices'] = max(0, 1 - (code_smells / 20))  # 20 is max acceptable
        
        return self._calculate_weighted_score(scores, self.criteria['quality']['sub_criteria'])
    
    def _grade_testing(self, result: Any) -> float:
        """Grade testing aspects"""
        scores = {}
        
        test_stage = result.stages.get('test', {})
        
        # Direct metrics
        scores['test_coverage'] = test_stage.get('coverage', 0)
        scores['test_pass_rate'] = test_stage.get('pass_rate', 0)
        
        # Edge cases (based on test types)
        test_metrics = test_stage.get('metrics', {})
        edge_case_tests = test_metrics.get('edge_cases', 0)
        total_tests = test_metrics.get('total_tests', 1)
        
        # Good if at least 20% of tests are edge cases
        scores['edge_cases'] = min(1.0, (edge_case_tests / total_tests) * 5) if total_tests > 0 else 0
        
        return self._calculate_weighted_score(scores, self.criteria['testing']['sub_criteria'])
    
    def _grade_security(self, result: Any) -> float:
        """Grade security aspects"""
        scores = {}
        
        review_stage = result.stages.get('review', {})
        
        # Security score from review
        scores['vulnerability_scan'] = review_stage.get('security_score', 0)
        
        # Security practices (based on specific checks)
        # Count security improvements vs total improvements
        security_improvements = sum(
            1 for imp in review_stage.get('improvements', [])
            if imp.get('type') == 'security'
        )
        total_improvements = len(review_stage.get('improvements', []))
        
        # Good if security issues are minimal (< 20% of all issues)
        if total_improvements > 0:
            scores['security_practices'] = max(0, 1 - (security_improvements / total_improvements) * 5)
        else:
            scores['security_practices'] = 1.0
        
        return self._calculate_weighted_score(scores, self.criteria['security']['sub_criteria'])
    
    def _grade_efficiency(self, result: Any) -> float:
        """Grade efficiency aspects"""
        scores = {}
        
        if not result.metrics:
            return 0.5  # Default middle score if no metrics
        
        # Time efficiency (compare to benchmarks)
        total_time = result.metrics.total_time
        # Benchmark: 300 seconds (5 minutes) is excellent, 1800 seconds (30 minutes) is poor
        if total_time <= 300:
            scores['time_efficiency'] = 1.0
        elif total_time >= 1800:
            scores['time_efficiency'] = 0.2
        else:
            scores['time_efficiency'] = 1.0 - ((total_time - 300) / 1500)
        
        # Cost efficiency (compare to benchmarks)
        total_cost = result.metrics.total_cost
        # Benchmark: $0.50 is excellent, $5.00 is poor
        if total_cost <= 0.50:
            scores['cost_efficiency'] = 1.0
        elif total_cost >= 5.00:
            scores['cost_efficiency'] = 0.2
        else:
            scores['cost_efficiency'] = 1.0 - ((total_cost - 0.50) / 4.50)
        
        # Resource usage (based on performance test results)
        perf_results = result.stages.get('test', {}).get('performance_results', {})
        perf_score = perf_results.get('score', 0.5)
        scores['resource_usage'] = perf_score
        
        return self._calculate_weighted_score(scores, self.criteria['efficiency']['sub_criteria'])
    
    def _calculate_weighted_score(self, scores: Dict[str, float], weights: Dict[str, float]) -> float:
        """Calculate weighted score from sub-scores"""
        total = 0.0
        total_weight = 0.0
        
        for criterion, weight in weights.items():
            if criterion in scores:
                total += scores[criterion] * weight
                total_weight += weight
        
        # Normalize if weights don't sum to 1
        if total_weight > 0:
            return total / total_weight
        
        return 0.0
    
    def generate_grade_report(self, cycle_result: Any, grade: float) -> Dict[str, Any]:
        """Generate detailed grade report"""
        report = {
            'cycle_id': cycle_result.cycle_id,
            'ai_provider': cycle_result.ai_provider.value,
            'overall_grade': grade,
            'letter_grade': self._calculate_letter_grade(grade),
            'category_grades': {},
            'strengths': [],
            'weaknesses': [],
            'detailed_scores': {}
        }
        
        # Calculate category grades
        categories = ['functionality', 'quality', 'testing', 'security', 'efficiency']
        for category in categories:
            method_name = f'_grade_{category}'
            if hasattr(self, method_name):
                category_grade = getattr(self, method_name)(cycle_result)
                report['category_grades'][category] = {
                    'grade': round(category_grade, 3),
                    'weight': self.criteria[category]['weight'],
                    'weighted_contribution': round(
                        category_grade * self.criteria[category]['weight'], 3
                    )
                }
                
                # Identify strengths and weaknesses
                if category_grade >= 0.8:
                    report['strengths'].append(f"Strong {category} (grade: {category_grade:.2f})")
                elif category_grade < 0.6:
                    report['weaknesses'].append(f"Weak {category} (grade: {category_grade:.2f})")
        
        # Add specific feedback
        report['feedback'] = self._generate_feedback(cycle_result, report)
        
        return report
    
    def _calculate_letter_grade(self, numeric_grade: float) -> str:
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
        elif numeric_grade >= 0.77:
            return "C+"
        elif numeric_grade >= 0.73:
            return "C"
        elif numeric_grade >= 0.70:
            return "C-"
        elif numeric_grade >= 0.67:
            return "D+"
        elif numeric_grade >= 0.63:
            return "D"
        elif numeric_grade >= 0.60:
            return "D-"
        else:
            return "F"
    
    def _generate_feedback(self, cycle_result: Any, report: Dict[str, Any]) -> List[str]:
        """Generate specific feedback based on grades"""
        feedback = []
        
        # Overall performance
        if report['overall_grade'] >= 0.9:
            feedback.append("Excellent overall performance! Ready for production deployment.")
        elif report['overall_grade'] >= 0.8:
            feedback.append("Good performance with minor improvements needed.")
        elif report['overall_grade'] >= 0.7:
            feedback.append("Acceptable performance but several areas need improvement.")
        else:
            feedback.append("Significant improvements required before deployment.")
        
        # Category-specific feedback
        for category, data in report['category_grades'].items():
            if data['grade'] < 0.7:
                if category == 'functionality':
                    feedback.append("Focus on meeting all requirements and acceptance criteria.")
                elif category == 'quality':
                    feedback.append("Improve code quality through refactoring and better practices.")
                elif category == 'testing':
                    feedback.append("Increase test coverage and ensure all tests pass.")
                elif category == 'security':
                    feedback.append("Address security vulnerabilities and follow security best practices.")
                elif category == 'efficiency':
                    feedback.append("Optimize for better performance and cost efficiency.")
        
        # Specific metric feedback
        if cycle_result.metrics:
            if cycle_result.metrics.test_coverage < 0.8:
                feedback.append(f"Test coverage is {cycle_result.metrics.test_coverage*100:.1f}%. Aim for at least 80%.")
            
            if cycle_result.metrics.security_score < 0.8:
                feedback.append("Security score indicates potential vulnerabilities. Run security audit.")
            
            if cycle_result.metrics.total_cost > 3.0:
                feedback.append(f"High cost (${cycle_result.metrics.total_cost:.2f}). Consider optimization strategies.")
        
        return feedback

class GradeComparator:
    """Compare grades across different AI providers"""
    
    @staticmethod
    def compare_grades(results: Dict[str, Any]) -> Dict[str, Any]:
        """Compare grading results across providers"""
        comparison = {
            'best_overall': None,
            'best_by_category': {},
            'statistical_analysis': {},
            'recommendations': []
        }
        
        # Find best overall
        best_grade = 0
        best_provider = None
        
        grades_by_provider = {}
        for provider, result in results.items():
            if result.grade:
                grades_by_provider[provider] = result.grade
                if result.grade > best_grade:
                    best_grade = result.grade
                    best_provider = provider
        
        comparison['best_overall'] = {
            'provider': best_provider,
            'grade': best_grade
        }
        
        # Statistical analysis
        if grades_by_provider:
            grades_list = list(grades_by_provider.values())
            comparison['statistical_analysis'] = {
                'mean': sum(grades_list) / len(grades_list),
                'max': max(grades_list),
                'min': min(grades_list),
                'range': max(grades_list) - min(grades_list),
                'variance': GradeComparator._calculate_variance(grades_list)
            }
        
        # Generate recommendations
        comparison['recommendations'] = GradeComparator._generate_comparison_recommendations(
            grades_by_provider, comparison['statistical_analysis']
        )
        
        return comparison
    
    @staticmethod
    def _calculate_variance(grades: List[float]) -> float:
        """Calculate variance of grades"""
        if not grades:
            return 0.0
        
        mean = sum(grades) / len(grades)
        variance = sum((g - mean) ** 2 for g in grades) / len(grades)
        return round(variance, 4)
    
    @staticmethod
    def _generate_comparison_recommendations(grades: Dict[str, float], 
                                           stats: Dict[str, float]) -> List[str]:
        """Generate recommendations based on grade comparison"""
        recommendations = []
        
        # High variance indicates inconsistent performance
        if stats.get('variance', 0) > 0.01:  # More than 1% variance
            recommendations.append(
                "High variance in grades indicates inconsistent AI performance. "
                "Consider standardizing prompts and evaluation criteria."
            )
        
        # If all grades are below threshold
        if stats.get('max', 0) < 0.8:
            recommendations.append(
                "All providers scored below 80%. Consider refining requirements "
                "or breaking down the feature into smaller components."
            )
        
        # If there's a clear winner
        if stats.get('range', 0) > 0.15:  # More than 15% difference
            recommendations.append(
                "Significant performance gap between providers. The best performer "
                "shows clear advantages for this type of task."
            )
        
        # Cost-performance analysis
        recommendations.append(
            "Analyze cost-performance ratio to determine the most efficient provider "
            "for production use."
        )
        
        return recommendations
