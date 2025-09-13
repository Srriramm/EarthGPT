"""Monitoring and metrics collection for the Sustainability Assistant."""

import time
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from collections import defaultdict, deque
from loguru import logger
import json
import os


@dataclass
class InteractionMetrics:
    """Metrics for a single interaction."""
    timestamp: datetime
    session_id: str
    query_length: int
    response_length: int
    processing_time: float
    guardrail_triggered: bool
    guardrail_reason: Optional[str] = None
    is_summary: bool = False
    is_detailed: bool = False
    model_used: str = "mock"  # Will be actual model name in production


@dataclass
class SystemMetrics:
    """System-wide metrics."""
    total_interactions: int = 0
    total_sessions: int = 0
    guardrail_rejections: int = 0
    summary_responses: int = 0
    detailed_responses: int = 0
    average_response_time: float = 0.0
    total_processing_time: float = 0.0
    error_count: int = 0
    uptime_start: datetime = field(default_factory=datetime.utcnow)
    
    # Time-based metrics
    interactions_by_hour: Dict[int, int] = field(default_factory=lambda: defaultdict(int))
    guardrail_rejections_by_hour: Dict[int, int] = field(default_factory=lambda: defaultdict(int))
    
    # Topic-based metrics
    sustainability_topics: Dict[str, int] = field(default_factory=lambda: defaultdict(int))
    non_sustainability_queries: List[str] = field(default_factory=list)


class MetricsCollector:
    """Collects and manages system metrics."""
    
    def __init__(self, max_interactions: int = 10000):
        self.metrics = SystemMetrics()
        self.recent_interactions: deque = deque(maxlen=max_interactions)
        self.metrics_file = "metrics.json"
        
        # Load existing metrics if available
        self._load_metrics()
        
        logger.info("Metrics collector initialized")
    
    def record_interaction(self, interaction: InteractionMetrics) -> None:
        """Record a new interaction."""
        self.metrics.total_interactions += 1
        self.metrics.total_processing_time += interaction.processing_time
        
        # Update average response time
        self.metrics.average_response_time = (
            self.metrics.total_processing_time / self.metrics.total_interactions
        )
        
        # Record time-based metrics
        hour = interaction.timestamp.hour
        self.metrics.interactions_by_hour[hour] += 1
        
        # Record guardrail metrics
        if interaction.guardrail_triggered:
            self.metrics.guardrail_rejections += 1
            self.metrics.guardrail_rejections_by_hour[hour] += 1
        
        # Record response type metrics
        if interaction.is_summary:
            self.metrics.summary_responses += 1
        if interaction.is_detailed:
            self.metrics.detailed_responses += 1
        
        # Store recent interaction
        self.recent_interactions.append(interaction)
        
        # Save metrics periodically
        if self.metrics.total_interactions % 100 == 0:
            self._save_metrics()
        
        logger.debug(f"Recorded interaction: {interaction.session_id}")
    
    def record_error(self, error_type: str, error_message: str) -> None:
        """Record an error occurrence."""
        self.metrics.error_count += 1
        logger.error(f"Error recorded: {error_type} - {error_message}")
    
    def record_sustainability_topic(self, topic: str) -> None:
        """Record a sustainability topic mention."""
        self.metrics.sustainability_topics[topic] += 1
    
    def record_non_sustainability_query(self, query: str) -> None:
        """Record a non-sustainability query."""
        self.metrics.non_sustainability_queries.append(query)
        # Keep only recent non-sustainability queries
        if len(self.metrics.non_sustainability_queries) > 100:
            self.metrics.non_sustainability_queries = self.metrics.non_sustainability_queries[-100:]
    
    def get_metrics_summary(self) -> Dict[str, Any]:
        """Get a summary of current metrics."""
        uptime = datetime.utcnow() - self.metrics.uptime_start
        
        return {
            "system": {
                "uptime_seconds": uptime.total_seconds(),
                "total_interactions": self.metrics.total_interactions,
                "total_sessions": self.metrics.total_sessions,
                "average_response_time": round(self.metrics.average_response_time, 3),
                "error_count": self.metrics.error_count
            },
            "guardrails": {
                "total_rejections": self.metrics.guardrail_rejections,
                "rejection_rate": round(
                    self.metrics.guardrail_rejections / max(self.metrics.total_interactions, 1) * 100, 2
                )
            },
            "responses": {
                "summary_responses": self.metrics.summary_responses,
                "detailed_responses": self.metrics.detailed_responses,
                "summary_rate": round(
                    self.metrics.summary_responses / max(self.metrics.total_interactions, 1) * 100, 2
                )
            },
            "topics": dict(self.metrics.sustainability_topics),
            "recent_activity": {
                "interactions_last_hour": self._get_recent_interactions_count(hours=1),
                "interactions_last_24h": self._get_recent_interactions_count(hours=24)
            }
        }
    
    def get_performance_metrics(self) -> Dict[str, Any]:
        """Get performance-related metrics."""
        if not self.recent_interactions:
            return {"message": "No interactions recorded yet"}
        
        recent_interactions = list(self.recent_interactions)
        response_times = [i.processing_time for i in recent_interactions]
        
        return {
            "response_times": {
                "min": min(response_times),
                "max": max(response_times),
                "average": sum(response_times) / len(response_times),
                "median": sorted(response_times)[len(response_times) // 2]
            },
            "throughput": {
                "interactions_per_minute": len(recent_interactions) / max(
                    (recent_interactions[-1].timestamp - recent_interactions[0].timestamp).total_seconds() / 60, 1
                )
            },
            "error_rate": self.metrics.error_count / max(self.metrics.total_interactions, 1) * 100
        }
    
    def get_guardrail_analytics(self) -> Dict[str, Any]:
        """Get guardrail-specific analytics."""
        return {
            "rejection_reasons": self._get_rejection_reasons(),
            "non_sustainability_queries": self.metrics.non_sustainability_queries[-10:],  # Last 10
            "rejection_trend": self._get_rejection_trend()
        }
    
    def _get_recent_interactions_count(self, hours: int) -> int:
        """Get count of interactions in the last N hours."""
        cutoff_time = datetime.utcnow() - timedelta(hours=hours)
        return sum(
            1 for interaction in self.recent_interactions
            if interaction.timestamp >= cutoff_time
        )
    
    def _get_rejection_reasons(self) -> Dict[str, int]:
        """Get count of rejection reasons."""
        reasons = defaultdict(int)
        for interaction in self.recent_interactions:
            if interaction.guardrail_triggered and interaction.guardrail_reason:
                reasons[interaction.guardrail_reason] += 1
        return dict(reasons)
    
    def _get_rejection_trend(self) -> List[Dict[str, Any]]:
        """Get rejection trend over time."""
        # Group by hour for the last 24 hours
        trend = []
        for i in range(24):
            hour = (datetime.utcnow() - timedelta(hours=i)).hour
            interactions = self.metrics.interactions_by_hour.get(hour, 0)
            rejections = self.metrics.guardrail_rejections_by_hour.get(hour, 0)
            
            trend.append({
                "hour": hour,
                "interactions": interactions,
                "rejections": rejections,
                "rejection_rate": round(rejections / max(interactions, 1) * 100, 2)
            })
        
        return list(reversed(trend))  # Most recent first
    
    def _save_metrics(self) -> None:
        """Save metrics to file."""
        try:
            metrics_data = {
                "system_metrics": {
                    "total_interactions": self.metrics.total_interactions,
                    "total_sessions": self.metrics.total_sessions,
                    "guardrail_rejections": self.metrics.guardrail_rejections,
                    "summary_responses": self.metrics.summary_responses,
                    "detailed_responses": self.metrics.detailed_responses,
                    "average_response_time": self.metrics.average_response_time,
                    "total_processing_time": self.metrics.total_processing_time,
                    "error_count": self.metrics.error_count,
                    "uptime_start": self.metrics.uptime_start.isoformat()
                },
                "sustainability_topics": dict(self.metrics.sustainability_topics),
                "last_updated": datetime.utcnow().isoformat()
            }
            
            with open(self.metrics_file, 'w') as f:
                json.dump(metrics_data, f, indent=2)
                
        except Exception as e:
            logger.error(f"Failed to save metrics: {e}")
    
    def _load_metrics(self) -> None:
        """Load metrics from file."""
        try:
            if os.path.exists(self.metrics_file):
                with open(self.metrics_file, 'r') as f:
                    data = json.load(f)
                
                # Restore system metrics
                system_metrics = data.get("system_metrics", {})
                self.metrics.total_interactions = system_metrics.get("total_interactions", 0)
                self.metrics.total_sessions = system_metrics.get("total_sessions", 0)
                self.metrics.guardrail_rejections = system_metrics.get("guardrail_rejections", 0)
                self.metrics.summary_responses = system_metrics.get("summary_responses", 0)
                self.metrics.detailed_responses = system_metrics.get("detailed_responses", 0)
                self.metrics.average_response_time = system_metrics.get("average_response_time", 0.0)
                self.metrics.total_processing_time = system_metrics.get("total_processing_time", 0.0)
                self.metrics.error_count = system_metrics.get("error_count", 0)
                
                # Restore sustainability topics
                topics = data.get("sustainability_topics", {})
                self.metrics.sustainability_topics = defaultdict(int, topics)
                
                logger.info("Metrics loaded from file")
                
        except Exception as e:
            logger.error(f"Failed to load metrics: {e}")


# Global metrics collector instance
metrics_collector = MetricsCollector()
