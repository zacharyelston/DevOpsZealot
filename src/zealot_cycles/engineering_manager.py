"""
Engineering Manager - Makes decisions based on cycle results
"""
import asyncio
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
from dataclasses import dataclass
import structlog
import json

from .grading import GradeComparator

logger = structlog.get_logger()

@dataclass
class AIProviderProfile:
    """Profile for an AI provider based on historical performance"""
    provider_name: str
    total_cycles: int = 0
    average_grade: float = 0.0
    average_cost: float = 0.0
    average_time: float = 0.0
    success_rate: float = 0.0
    specialties: List[str] = None
    weaknesses: List[str] = None
    badges: List[str] = None
    
    def __post_init__(self):
        if self.specialties is None:
            self.specialties = []
        if self.weaknesses is None:
            self.weaknesses = []
        if self.badges is None:
            self.badges = []

@dataclass
class Decision:
    """Engineering decision based on analysis"""
    selected_provider: str
    rationale: str
    confidence: float
    alternatives: List[Tuple[str, str]]  # (provider, reason_not_selected)
    recommendations: List[str]
    risk_assessment: str

class EngineeringManager:
    """
    Makes strategic decisions based on development cycle results
    Manages AI provider profiles and performance tracking
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.provider_profiles: Dict[str, AIProviderProfile] = {}
        self.decision_history: List[Decision] = []
        self.performance_thresholds = {
            'minimum_grade': 0.75,
            'excellent_grade': 0.90,
            'max_acceptable_cost': 5.00,
            'max_acceptable_time': 1800,  # 30 minutes
            'minimum_success_rate': 0.80
        }
        
        logger.info("EngineeringManager initialized")
    
    async def analyze_cycle_results(self, 
                                  comparison_result: Dict[str, Any]) -> Decision:
        """
        Analyze cycle results and make a decision
        
        Args:
            comparison_result: Output from CycleManager.run_feature_comparison
            
        Returns:
            Decision object with selected provider and rationale
        """
        logger.info("Analyzing cycle results for decision making")
        
        # Update provider profiles
        await self._update_provider_profiles(comparison_result['results'])
        
        # Grade comparison
        grade_comparison = GradeComparator.compare_grades(comparison_result['results'])
        
        # Multi-criteria decision analysis
        provider_scores = await self._calculate_provider_scores(
            comparison_result['results'],
            comparison_result['comparison']
        )
        
        # Make decision
        decision = await self._make_decision(
            provider_scores,
            comparison_result,
            grade_comparison
        )
        
        # Update badges
        await self._update_provider_badges(comparison_result['results'])
        
        # Store decision
        self.decision_history.append(decision)
        
        # Generate report
        await self._generate_decision_report(decision, comparison_result)
        
        return decision
    
    async def _update_provider_profiles(self, results: Dict[str, Any]):
        """Update provider profiles with new results"""
        for provider_name, result in results.items():
            if provider_name not in self.provider_profiles:
                self.provider_profiles[provider_name] = AIProviderProfile(
                    provider_name=provider_name
                )
            
            profile = self.provider_profiles[provider_name]
            
            # Update cycle count
            profile.total_cycles += 1
            
            # Update success rate
            if result.success:
                profile.success_rate = (
                    (profile.success_rate * (profile.total_cycles - 1) + 1) / 
                    profile.total_cycles
                )
            else:
                profile.success_rate = (
                    (profile.success_rate * (profile.total_cycles - 1)) / 
                    profile.total_cycles
                )
            
            # Update averages if successful
            if result.success and result.grade is not None:
                # Rolling average for grade
                profile.average_grade = (
                    (profile.average_grade * (profile.total_cycles - 1) + result.grade) / 
                    profile.total_cycles
                )
                
                # Rolling average for cost
                if result.total_cost is not None:
                    profile.average_cost = (
                        (profile.average_cost * (profile.total_cycles - 1) + result.total_cost) / 
                        profile.total_cycles
                    )
                
                # Rolling average for time
                if result.total_time is not None:
                    profile.average_time = (
                        (profile.average_time * (profile.total_cycles - 1) + result.total_time) / 
                        profile.total_cycles
                    )
            
            # Update specialties and weaknesses
            await self._analyze_provider_strengths(profile, result)
    
    async def _analyze_provider_strengths(self, 
                                        profile: AIProviderProfile, 
                                        result: Any):
        """Analyze and update provider strengths and weaknesses"""
        if not result.success:
            return
        
        # Analyze by category grades
        if hasattr(result, 'grade_report'):
            report = result.grade_report
            
            # Identify specialties (categories with grade > 0.85)
            for category, data in report.get('category_grades', {}).items():
                if data['grade'] > 0.85:
                    specialty = f"excellent_{category}"
                    if specialty not in profile.specialties:
                        profile.specialties.append(specialty)
                        logger.info(f"Added specialty {specialty} to {profile.provider_name}")
            
            # Identify weaknesses (categories with grade < 0.70)
            for category, data in report.get('category_grades', {}).items():
                if data['grade'] < 0.70:
                    weakness = f"weak_{category}"
                    if weakness not in profile.weaknesses:
                        profile.weaknesses.append(weakness)
                        logger.info(f"Added weakness {weakness} to {profile.provider_name}")
    
    async def _calculate_provider_scores(self, 
                                       results: Dict[str, Any],
                                       comparison: Dict[str, Any]) -> Dict[str, float]:
        """
        Calculate multi-criteria scores for each provider
        
        Criteria:
        - Grade (40%)
        - Cost efficiency (25%)
        - Time efficiency (20%)
        - Reliability (15%)
        """
        scores = {}
        
        # Get successful results
        successful_results = {
            provider: result 
            for provider, result in results.items() 
            if result.success
        }
        
        if not successful_results:
            return scores
        
        # Calculate max values for normalization
        max_grade = max(r.grade for r in successful_results.values() if r.grade)
        min_cost = min(r.total_cost for r in successful_results.values() if r.total_cost)
        min_time = min(r.total_time for r in successful_results.values() if r.total_time)
        
        for provider, result in successful_results.items():
            score_components = {}
            
            # Grade score (higher is better)
            if result.grade and max_grade > 0:
                score_components['grade'] = (result.grade / max_grade) * 0.40
            else:
                score_components['grade'] = 0
            
            # Cost efficiency (lower is better)
            if result.total_cost and min_cost > 0:
                score_components['cost'] = (min_cost / result.total_cost) * 0.25
            else:
                score_components['cost'] = 0
            
            # Time efficiency (lower is better)
            if result.total_time and min_time > 0:
                score_components['time'] = (min_time / result.total_time) * 0.20
            else:
                score_components['time'] = 0
            
            # Reliability (from profile)
            profile = self.provider_profiles.get(provider)
            if profile:
                score_components['reliability'] = profile.success_rate * 0.15
            else:
                score_components['reliability'] = 0.10  # Default for new providers
            
            # Total score
            scores[provider] = sum(score_components.values())
            
            logger.info(f"Provider {provider} scores: {score_components}, total: {scores[provider]}")
        
        return scores
    
    async def _make_decision(self, 
                           provider_scores: Dict[str, float],
                           comparison_result: Dict[str, Any],
                           grade_comparison: Dict[str, Any]) -> Decision:
        """Make the final decision on provider selection"""
        
        if not provider_scores:
            return Decision(
                selected_provider="none",
                rationale="No successful providers to choose from",
                confidence=0.0,
                alternatives=[],
                recommendations=["All providers failed. Review requirements and retry."],
                risk_assessment="High risk - no viable options"
            )
        
        # Sort providers by score
        sorted_providers = sorted(
            provider_scores.items(), 
            key=lambda x: x[1], 
            reverse=True
        )
        
        selected_provider = sorted_providers[0][0]
        selected_score = sorted_providers[0][1]
        
        # Build rationale
        result = comparison_result['results'][selected_provider]
        rationale_parts = [
            f"{selected_provider} selected as the best performer",
            f"Overall score: {selected_score:.3f}",
            f"Grade: {result.grade:.2f} ({self._get_letter_grade(result.grade)})",
            f"Cost: ${result.total_cost:.2f}",
            f"Time: {result.total_time:.1f}s"
        ]
        
        # Add profile information
        profile = self.provider_profiles.get(selected_provider)
        if profile and profile.total_cycles > 1:
            rationale_parts.extend([
                f"Historical success rate: {profile.success_rate*100:.1f}%",
                f"Average grade: {profile.average_grade:.2f}"
            ])
        
        rationale = ". ".join(rationale_parts)
        
        # Calculate confidence
        confidence = self._calculate_decision_confidence(
            selected_score, 
            sorted_providers,
            result
        )
        
        # Build alternatives list
        alternatives = []
        for provider, score in sorted_providers[1:3]:  # Top 3 alternatives
            alt_result = comparison_result['results'][provider]
            reason = self._get_rejection_reason(provider, alt_result, selected_provider, result)
            alternatives.append((provider, reason))
        
        # Generate recommendations
        recommendations = self._generate_recommendations(
            selected_provider,
            result,
            comparison_result
        )
        
        # Risk assessment
        risk_assessment = self._assess_risk(result, profile)
        
        return Decision(
            selected_provider=selected_provider,
            rationale=rationale,
            confidence=confidence,
            alternatives=alternatives,
            recommendations=recommendations,
            risk_assessment=risk_assessment
        )
    
    def _calculate_decision_confidence(self, 
                                     selected_score: float,
                                     sorted_providers: List[Tuple[str, float]],
                                     result: Any) -> float:
        """Calculate confidence in the decision"""
        confidence = 0.5  # Base confidence
        
        # Score margin (how much better than second best)
        if len(sorted_providers) > 1:
            margin = selected_score - sorted_providers[1][1]
            confidence += min(margin * 2, 0.3)  # Up to 30% boost for clear winner
        else:
            confidence += 0.3  # Only one option
        
        # Grade quality
        if result.grade >= 0.9:
            confidence += 0.1
        elif result.grade < 0.75:
            confidence -= 0.1
        
        # Historical performance
        profile = self.provider_profiles.get(sorted_providers[0][0])
        if profile and profile.total_cycles > 5:
            if profile.success_rate > 0.9:
                confidence += 0.1
            elif profile.success_rate < 0.7:
                confidence -= 0.1
        
        return max(0.0, min(1.0, confidence))
    
    def _get_rejection_reason(self, provider: str, result: Any, 
                            selected_provider: str, selected_result: Any) -> str:
        """Generate reason why a provider wasn't selected"""
        reasons = []
        
        if not result.success:
            return "Failed to complete cycle"
        
        if result.grade < selected_result.grade:
            diff = (selected_result.grade - result.grade) * 100
            reasons.append(f"Lower grade by {diff:.1f}%")
        
        if result.total_cost > selected_result.total_cost * 1.5:
            reasons.append(f"Higher cost (${result.total_cost:.2f} vs ${selected_result.total_cost:.2f})")
        
        if result.total_time > selected_result.total_time * 1.5:
            reasons.append(f"Slower ({result.total_time:.1f}s vs {selected_result.total_time:.1f}s)")
        
        return "; ".join(reasons) if reasons else "Slightly lower overall score"
    
    def _generate_recommendations(self, 
                                provider: str,
                                result: Any,
                                comparison_result: Dict[str, Any]) -> List[str]:
        """Generate actionable recommendations"""
        recommendations = []
        
        # Performance recommendations
        if result.grade < self.performance_thresholds['minimum_grade']:
            recommendations.append(
                f"Selected provider grade ({result.grade:.2f}) is below minimum threshold. "
                "Consider additional review before production deployment."
            )
        
        # Cost recommendations
        if result.total_cost > self.performance_thresholds['max_acceptable_cost']:
            recommendations.append(
                f"Cost (${result.total_cost:.2f}) exceeds threshold. "
                "Monitor usage and consider optimization for high-volume use."
            )
        
        # Profile-based recommendations
        profile = self.provider_profiles.get(provider)
        if profile:
            if profile.total_cycles < 5:
                recommendations.append(
                    "Limited historical data for this provider. "
                    "Continue monitoring performance across more cycles."
                )
            
            if profile.weaknesses:
                weak_areas = ", ".join(w.replace('weak_', '') for w in profile.weaknesses)
                recommendations.append(
                    f"Provider shows weaknesses in: {weak_areas}. "
                    "Consider alternative providers for these aspects."
                )
        
        # Comparison-based recommendations
        comparison = comparison_result.get('comparison', {})
        if comparison.get('recommendations'):
            recommendations.extend(comparison['recommendations'][:2])  # Top 2
        
        return recommendations
    
    def _assess_risk(self, result: Any, profile: Optional[AIProviderProfile]) -> str:
        """Assess risk level of using selected provider"""
        risk_factors = []
        
        # Grade-based risk
        if result.grade < 0.7:
            risk_factors.append("low quality score")
        elif result.grade < 0.8:
            risk_factors.append("moderate quality score")
        
        # Cost-based risk
        if result.total_cost > 3.0:
            risk_factors.append("high cost")
        
        # Profile-based risk
        if profile:
            if profile.success_rate < 0.8:
                risk_factors.append("low historical success rate")
            if profile.total_cycles < 3:
                risk_factors.append("limited track record")
        else:
            risk_factors.append("no historical data")
        
        # Determine risk level
        if len(risk_factors) >= 3:
            return f"High risk - {', '.join(risk_factors)}"
        elif len(risk_factors) >= 1:
            return f"Medium risk - {', '.join(risk_factors)}"
        else:
            return "Low risk - provider shows consistent good performance"
    
    async def _update_provider_badges(self, results: Dict[str, Any]):
        """Award badges based on performance"""
        for provider_name, result in results.items():
            if not result.success:
                continue
            
            profile = self.provider_profiles.get(provider_name)
            if not profile:
                continue
            
            # Performance badges
            if result.grade >= 0.95:
                badge = "🏆 Excellence"
                if badge not in profile.badges:
                    profile.badges.append(badge)
                    logger.info(f"Awarded {badge} to {provider_name}")
            
            elif result.grade >= 0.90:
                badge = "⭐ High Performer"
                if badge not in profile.badges:
                    profile.badges.append(badge)
            
            # Efficiency badges
            if result.total_cost < 1.0:
                badge = "💰 Cost Efficient"
                if badge not in profile.badges:
                    profile.badges.append(badge)
            
            if result.total_time < 300:  # Under 5 minutes
                badge = "⚡ Speed Demon"
                if badge not in profile.badges:
                    profile.badges.append(badge)
            
            # Reliability badges
            if profile.total_cycles >= 10 and profile.success_rate >= 0.95:
                badge = "🛡️ Rock Solid"
                if badge not in profile.badges:
                    profile.badges.append(badge)
            
            # Specialization badges
            if result.metrics:
                if result.metrics.test_coverage >= 0.95:
                    badge = "🧪 Testing Master"
                    if badge not in profile.badges:
                        profile.badges.append(badge)
                
                if result.metrics.security_score >= 0.95:
                    badge = "🔒 Security Expert"
                    if badge not in profile.badges:
                        profile.badges.append(badge)
    
    async def _generate_decision_report(self, 
                                      decision: Decision,
                                      comparison_result: Dict[str, Any]):
        """Generate detailed decision report"""
        report = {
            "timestamp": datetime.utcnow().isoformat(),
            "feature": {
                "name": comparison_result['feature'].name,
                "id": comparison_result['feature'].id
            },
            "decision": {
                "selected_provider": decision.selected_provider,
                "rationale": decision.rationale,
                "confidence": decision.confidence,
                "risk_assessment": decision.risk_assessment
            },
            "alternatives": [
                {"provider": alt[0], "reason_not_selected": alt[1]}
                for alt in decision.alternatives
            ],
            "recommendations": decision.recommendations,
            "provider_profiles": {
                name: {
                    "total_cycles": profile.total_cycles,
                    "average_grade": round(profile.average_grade, 3),
                    "average_cost": round(profile.average_cost, 2),
                    "average_time": round(profile.average_time, 1),
                    "success_rate": round(profile.success_rate, 3),
                    "badges": profile.badges,
                    "specialties": profile.specialties,
                    "weaknesses": profile.weaknesses
                }
                for name, profile in self.provider_profiles.items()
            }
        }
        
        # Log the decision
        logger.info("Engineering decision made",
                   selected=decision.selected_provider,
                   confidence=decision.confidence,
                   risk=decision.risk_assessment)
        
        return report
    
    def _get_letter_grade(self, numeric_grade: float) -> str:
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
    
    def get_provider_report(self, provider_name: str) -> Optional[Dict[str, Any]]:
        """Get detailed report for a specific provider"""
        profile = self.provider_profiles.get(provider_name)
        if not profile:
            return None
        
        return {
            "provider": provider_name,
            "performance": {
                "total_cycles": profile.total_cycles,
                "average_grade": round(profile.average_grade, 3),
                "average_cost": round(profile.average_cost, 2),
                "average_time": round(profile.average_time, 1),
                "success_rate": round(profile.success_rate, 3)
            },
            "achievements": {
                "badges": profile.badges,
                "specialties": profile.specialties
            },
            "areas_for_improvement": profile.weaknesses,
            "recommendation": self._get_provider_recommendation(profile)
        }
    
    def _get_provider_recommendation(self, profile: AIProviderProfile) -> str:
        """Generate recommendation for a provider"""
        if profile.average_grade >= 0.9 and profile.success_rate >= 0.9:
            return "Excellent provider for critical tasks"
        elif profile.average_grade >= 0.8 and profile.success_rate >= 0.8:
            return "Good provider for standard tasks"
        elif profile.average_cost < 1.0 and profile.average_grade >= 0.75:
            return "Cost-effective option for non-critical tasks"
        elif profile.average_time < 300 and profile.average_grade >= 0.75:
            return "Fast option for time-sensitive tasks"
        else:
            return "Use with caution, monitor performance"
    
    async def export_decision_history(self, output_path: str):
        """Export complete decision history"""
        history = {
            "export_date": datetime.utcnow().isoformat(),
            "total_decisions": len(self.decision_history),
            "provider_profiles": {
                name: profile.__dict__
                for name, profile in self.provider_profiles.items()
            },
            "decisions": [
                {
                    "selected_provider": d.selected_provider,
                    "rationale": d.rationale,
                    "confidence": d.confidence,
                    "risk_assessment": d.risk_assessment,
                    "alternatives": d.alternatives,
                    "recommendations": d.recommendations
                }
                for d in self.decision_history
            ],
            "performance_summary": self._generate_performance_summary()
        }
        
        with open(output_path, 'w') as f:
            json.dump(history, f, indent=2, default=str)
        
        logger.info(f"Decision history exported to {output_path}")
    
    def _generate_performance_summary(self) -> Dict[str, Any]:
        """Generate overall performance summary"""
        if not self.provider_profiles:
            return {}
        
        return {
            "best_overall_performer": max(
                self.provider_profiles.items(),
                key=lambda x: x[1].average_grade
            )[0] if self.provider_profiles else None,
            
            "most_cost_effective": min(
                self.provider_profiles.items(),
                key=lambda x: x[1].average_cost if x[1].average_cost > 0 else float('inf')
            )[0] if self.provider_profiles else None,
            
            "fastest_provider": min(
                self.provider_profiles.items(),
                key=lambda x: x[1].average_time if x[1].average_time > 0 else float('inf')
            )[0] if self.provider_profiles else None,
            
            "most_reliable": max(
                self.provider_profiles.items(),
                key=lambda x: x[1].success_rate
            )[0] if self.provider_profiles else None,
            
            "total_cycles_run": sum(p.total_cycles for p in self.provider_profiles.values()),
            
            "average_success_rate": sum(p.success_rate for p in self.provider_profiles.values()) / 
                                   len(self.provider_profiles) if self.provider_profiles else 0
        }
