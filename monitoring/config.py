"""
Configuration for Performance Monitoring & Metrics
"""

import os
from dataclasses import dataclass
from typing import Optional


@dataclass
class MetricsConfig:
    """Configuration for metrics collection and storage"""
    
    # Collection settings
    enabled: bool = True
    sampling_rate: float = 1.0  # 1.0 = collect all, 0.5 = collect 50%
    
    # Storage settings
    json_file: str = "monitoring/metrics.json"
    csv_file: str = "monitoring/metrics.csv"
    max_file_size_mb: int = 100
    max_records_per_file: int = 10000
    
    # Performance thresholds
    slow_query_threshold_ms: int = 5000  # 5 seconds
    very_slow_query_threshold_ms: int = 30000  # 30 seconds
    
    # Reporting settings
    report_interval_hours: int = 24
    auto_export_enabled: bool = True
    
    @classmethod
    def from_env(cls) -> 'MetricsConfig':
        """Create config from environment variables"""
        return cls(
            enabled=os.getenv('METRICS_ENABLED', 'true').lower() == 'true',
            sampling_rate=float(os.getenv('METRICS_SAMPLING_RATE', '1.0')),
            json_file=os.getenv('METRICS_JSON_FILE', 'monitoring/metrics.json'),
            csv_file=os.getenv('METRICS_CSV_FILE', 'monitoring/metrics.csv'),
            slow_query_threshold_ms=int(os.getenv('METRICS_SLOW_THRESHOLD_MS', '5000')),
            very_slow_query_threshold_ms=int(os.getenv('METRICS_VERY_SLOW_THRESHOLD_MS', '30000')),
        )
    
    def is_slow_query(self, response_time_ms: int) -> bool:
        """Check if query is considered slow"""
        return response_time_ms > self.slow_query_threshold_ms
    
    def is_very_slow_query(self, response_time_ms: int) -> bool:
        """Check if query is considered very slow"""
        return response_time_ms > self.very_slow_query_threshold_ms
