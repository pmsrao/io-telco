"""
Core Metrics Collection Module
Handles collection, storage, and management of performance metrics
"""

import json
import csv
import uuid
import time
import os
import random
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, asdict
from .config import MetricsConfig


@dataclass
class QueryMetrics:
    """Metrics for a single query execution"""
    query_id: str
    timestamp: str
    agent_type: str  # "simple" or "crewai"
    query_text: str
    response_time_ms: int
    success: bool
    error_type: Optional[str] = None
    error_message: Optional[str] = None
    entities_detected: List[str] = None
    query_complexity_score: float = 0.0
    agent_selection_time_ms: int = 0
    query_execution_time_ms: int = 0
    tool_calls_count: int = 0
    graphql_queries_count: int = 0
    result_size_bytes: int = 0
    
    def __post_init__(self):
        if self.entities_detected is None:
            self.entities_detected = []


class MetricsCollector:
    """Centralized metrics collection and storage"""
    
    def __init__(self, config: Optional[MetricsConfig] = None):
        self.config = config or MetricsConfig.from_env()
        self.metrics_buffer: List[QueryMetrics] = []
        self._ensure_directories()
    
    def _ensure_directories(self):
        """Ensure monitoring directories exist"""
        os.makedirs(os.path.dirname(self.config.json_file), exist_ok=True)
        os.makedirs(os.path.dirname(self.config.csv_file), exist_ok=True)
    
    def should_collect(self) -> bool:
        """Check if metrics should be collected based on sampling rate"""
        if not self.config.enabled:
            return False
        return random.random() < self.config.sampling_rate
    
    def start_query(self, query_text: str, agent_type: str) -> str:
        """Start tracking a new query and return query ID"""
        if not self.should_collect():
            return ""
        
        query_id = str(uuid.uuid4())
        self._current_query = {
            'query_id': query_id,
            'query_text': query_text,
            'agent_type': agent_type,
            'start_time': time.time(),
            'agent_selection_start': time.time(),
            'query_execution_start': None,
            'entities_detected': [],
            'tool_calls_count': 0,
            'graphql_queries_count': 0,
        }
        return query_id
    
    def record_agent_selection(self, query_id: str, selected_agent: str):
        """Record agent selection timing"""
        if not query_id or not hasattr(self, '_current_query'):
            return
        
        if self._current_query['query_id'] == query_id:
            self._current_query['agent_selection_time'] = time.time() - self._current_query['agent_selection_start']
            self._current_query['selected_agent'] = selected_agent
    
    def record_query_execution_start(self, query_id: str):
        """Record when query execution starts"""
        if not query_id or not hasattr(self, '_current_query'):
            return
        
        if self._current_query['query_id'] == query_id:
            self._current_query['query_execution_start'] = time.time()
    
    def record_tool_call(self, query_id: str):
        """Record a tool call"""
        if not query_id or not hasattr(self, '_current_query'):
            return
        
        if self._current_query['query_id'] == query_id:
            self._current_query['tool_calls_count'] += 1
    
    def record_graphql_query(self, query_id: str):
        """Record a GraphQL query execution"""
        if not query_id or not hasattr(self, '_current_query'):
            return
        
        if self._current_query['query_id'] == query_id:
            self._current_query['graphql_queries_count'] += 1
    
    def record_entities_detected(self, query_id: str, entities: List[str]):
        """Record detected entities"""
        if not query_id or not hasattr(self, '_current_query'):
            return
        
        if self._current_query['query_id'] == query_id:
            self._current_query['entities_detected'] = entities
    
    def finish_query(self, query_id: str, success: bool, error_type: Optional[str] = None, 
                    error_message: Optional[str] = None, result_size_bytes: int = 0) -> Optional[QueryMetrics]:
        """Finish tracking a query and return metrics"""
        if not query_id or not hasattr(self, '_current_query'):
            return None
        
        if self._current_query['query_id'] != query_id:
            return None
        
        # Calculate timing metrics
        total_time = time.time() - self._current_query['start_time']
        agent_selection_time = self._current_query.get('agent_selection_time', 0) * 1000
        query_execution_time = 0
        
        if self._current_query.get('query_execution_start'):
            query_execution_time = (time.time() - self._current_query['query_execution_start']) * 1000
        
        # Calculate complexity score
        complexity_score = self._calculate_complexity_score(self._current_query['query_text'])
        
        # Create metrics object
        metrics = QueryMetrics(
            query_id=query_id,
            timestamp=datetime.now(timezone.utc).isoformat(),
            agent_type=self._current_query['agent_type'],
            query_text=self._current_query['query_text'],
            response_time_ms=int(total_time * 1000),
            success=success,
            error_type=error_type,
            error_message=error_message,
            entities_detected=self._current_query['entities_detected'],
            query_complexity_score=complexity_score,
            agent_selection_time_ms=int(agent_selection_time),
            query_execution_time_ms=int(query_execution_time),
            tool_calls_count=self._current_query['tool_calls_count'],
            graphql_queries_count=self._current_query['graphql_queries_count'],
            result_size_bytes=result_size_bytes
        )
        
        # Store metrics
        self._store_metrics(metrics)
        
        # Clean up current query
        delattr(self, '_current_query')
        
        return metrics
    
    def _calculate_complexity_score(self, query_text: str) -> float:
        """Calculate a complexity score for the query (0.0 to 1.0)"""
        query_lower = query_text.lower()
        score = 0.0
        
        # Length factor
        if len(query_text) > 100:
            score += 0.2
        elif len(query_text) > 50:
            score += 0.1
        
        # Entity count factor
        entities = ['payment', 'bill', 'customer', 'account', 'subscription']
        entity_count = sum(1 for entity in entities if entity in query_lower)
        score += min(entity_count * 0.15, 0.4)
        
        # Complexity indicators
        complexity_words = ['and', 'or', 'with', 'including', 'compare', 'analyze', 'trend', 'pattern']
        complexity_count = sum(1 for word in complexity_words if word in query_lower)
        score += min(complexity_count * 0.1, 0.3)
        
        # Time range complexity
        time_words = ['last', 'between', 'from', 'to', 'since', 'until']
        time_count = sum(1 for word in time_words if word in query_lower)
        score += min(time_count * 0.05, 0.1)
        
        return min(score, 1.0)
    
    def _store_metrics(self, metrics: QueryMetrics):
        """Store metrics to files"""
        # Add to buffer
        self.metrics_buffer.append(metrics)
        
        # Write to JSON file
        self._write_json_metrics(metrics)
        
        # Write to CSV file
        self._write_csv_metrics(metrics)
        
        # Check if we need to rotate files
        if len(self.metrics_buffer) >= self.config.max_records_per_file:
            self._rotate_files()
    
    def _write_json_metrics(self, metrics: QueryMetrics):
        """Write metrics to JSON file"""
        try:
            # Read existing data
            data = []
            if os.path.exists(self.config.json_file):
                with open(self.config.json_file, 'r') as f:
                    data = json.load(f)
            
            # Add new metrics
            data.append(asdict(metrics))
            
            # Write back
            with open(self.config.json_file, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            print(f"Error writing JSON metrics: {e}")
    
    def _write_csv_metrics(self, metrics: QueryMetrics):
        """Write metrics to CSV file"""
        try:
            file_exists = os.path.exists(self.config.csv_file)
            
            with open(self.config.csv_file, 'a', newline='') as f:
                writer = csv.DictWriter(f, fieldnames=asdict(metrics).keys())
                
                if not file_exists:
                    writer.writeheader()
                
                writer.writerow(asdict(metrics))
        except Exception as e:
            print(f"Error writing CSV metrics: {e}")
    
    def _rotate_files(self):
        """Rotate metrics files when they get too large"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Rotate JSON file
        if os.path.exists(self.config.json_file):
            rotated_json = f"{self.config.json_file}.{timestamp}"
            os.rename(self.config.json_file, rotated_json)
        
        # Rotate CSV file
        if os.path.exists(self.config.csv_file):
            rotated_csv = f"{self.config.csv_file}.{timestamp}"
            os.rename(self.config.csv_file, rotated_csv)
        
        # Clear buffer
        self.metrics_buffer.clear()
    
    def get_recent_metrics(self, limit: int = 100) -> List[QueryMetrics]:
        """Get recent metrics from buffer"""
        return self.metrics_buffer[-limit:] if self.metrics_buffer else []
    
    def get_metrics_summary(self) -> Dict[str, Any]:
        """Get summary statistics from recent metrics"""
        if not self.metrics_buffer:
            return {}
        
        recent_metrics = self.get_recent_metrics(1000)  # Last 1000 queries
        
        total_queries = len(recent_metrics)
        successful_queries = sum(1 for m in recent_metrics if m.success)
        simple_agent_queries = sum(1 for m in recent_metrics if m.agent_type == 'simple')
        crewai_agent_queries = sum(1 for m in recent_metrics if m.agent_type == 'crewai')
        
        response_times = [m.response_time_ms for m in recent_metrics]
        avg_response_time = sum(response_times) / len(response_times) if response_times else 0
        
        return {
            'total_queries': total_queries,
            'success_rate': successful_queries / total_queries if total_queries > 0 else 0,
            'simple_agent_usage': simple_agent_queries / total_queries if total_queries > 0 else 0,
            'crewai_agent_usage': crewai_agent_queries / total_queries if total_queries > 0 else 0,
            'avg_response_time_ms': avg_response_time,
            'slow_queries': sum(1 for t in response_times if t > self.config.slow_query_threshold_ms),
            'very_slow_queries': sum(1 for t in response_times if t > self.config.very_slow_query_threshold_ms),
        }


# Global metrics collector instance
_metrics_collector: Optional[MetricsCollector] = None


def get_metrics_collector() -> MetricsCollector:
    """Get the global metrics collector instance"""
    global _metrics_collector
    if _metrics_collector is None:
        _metrics_collector = MetricsCollector()
    return _metrics_collector


def collect_metrics(func):
    """Decorator to automatically collect metrics for a function"""
    def wrapper(*args, **kwargs):
        collector = get_metrics_collector()
        if not collector.should_collect():
            return func(*args, **kwargs)
        
        # Extract query info from function arguments
        query_text = ""
        agent_type = "unknown"
        
        if args and isinstance(args[0], str):
            query_text = args[0]
        elif 'user_input' in kwargs:
            query_text = kwargs['user_input']
        elif 'query' in kwargs:
            query_text = kwargs['query']
        
        # Determine agent type from function name or class
        if hasattr(func, '__self__'):
            class_name = func.__self__.__class__.__name__.lower()
            if 'simple' in class_name:
                agent_type = 'simple'
            elif 'crewai' in class_name:
                agent_type = 'crewai'
        
        query_id = collector.start_query(query_text, agent_type)
        
        try:
            result = func(*args, **kwargs)
            collector.finish_query(query_id, success=True, result_size_bytes=len(str(result)))
            return result
        except Exception as e:
            collector.finish_query(query_id, success=False, error_type=type(e).__name__, error_message=str(e))
            raise
    
    return wrapper
