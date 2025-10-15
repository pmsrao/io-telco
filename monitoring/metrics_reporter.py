"""
Metrics Reporting and Analysis Module
Provides reporting, analysis, and export capabilities for collected metrics
"""

import json
import csv
import os
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Optional
from dataclasses import asdict
from .metrics_collector import QueryMetrics, get_metrics_collector
from .config import MetricsConfig


class MetricsReporter:
    """Generate reports and analysis from collected metrics"""
    
    def __init__(self, config: Optional[MetricsConfig] = None):
        self.config = config or MetricsConfig.from_env()
        self.collector = get_metrics_collector()
    
    def generate_summary_report(self, hours: int = 24) -> Dict[str, Any]:
        """Generate a summary report for the specified time period"""
        cutoff_time = datetime.now(timezone.utc) - timedelta(hours=hours)
        
        # Load metrics from JSON file
        metrics = self._load_metrics_from_file()
        
        # Filter by time period
        recent_metrics = [
            m for m in metrics 
            if datetime.fromisoformat(m['timestamp'].replace('Z', '+00:00')) >= cutoff_time
        ]
        
        if not recent_metrics:
            return {
                'period_hours': hours,
                'total_queries': 0,
                'message': 'No metrics found for the specified period'
            }
        
        # Calculate statistics
        total_queries = len(recent_metrics)
        successful_queries = sum(1 for m in recent_metrics if m['success'])
        failed_queries = total_queries - successful_queries
        
        # Agent usage statistics
        simple_agent_queries = sum(1 for m in recent_metrics if m['agent_type'] == 'simple')
        crewai_agent_queries = sum(1 for m in recent_metrics if m['agent_type'] == 'crewai')
        
        # Response time statistics
        response_times = [m['response_time_ms'] for m in recent_metrics]
        avg_response_time = sum(response_times) / len(response_times) if response_times else 0
        min_response_time = min(response_times) if response_times else 0
        max_response_time = max(response_times) if response_times else 0
        
        # Performance categories
        slow_queries = sum(1 for t in response_times if t > self.config.slow_query_threshold_ms)
        very_slow_queries = sum(1 for t in response_times if t > self.config.very_slow_query_threshold_ms)
        
        # Error analysis
        error_types = {}
        for m in recent_metrics:
            if not m['success'] and m['error_type']:
                error_types[m['error_type']] = error_types.get(m['error_type'], 0) + 1
        
        # Entity detection statistics
        entity_stats = {}
        for m in recent_metrics:
            for entity in m.get('entities_detected', []):
                entity_stats[entity] = entity_stats.get(entity, 0) + 1
        
        # Complexity analysis
        complexity_scores = [m['query_complexity_score'] for m in recent_metrics]
        avg_complexity = sum(complexity_scores) / len(complexity_scores) if complexity_scores else 0
        
        return {
            'period_hours': hours,
            'report_generated_at': datetime.now(timezone.utc).isoformat(),
            'total_queries': total_queries,
            'success_rate': successful_queries / total_queries if total_queries > 0 else 0,
            'failed_queries': failed_queries,
            'agent_usage': {
                'simple_agent': {
                    'count': simple_agent_queries,
                    'percentage': simple_agent_queries / total_queries if total_queries > 0 else 0
                },
                'crewai_agent': {
                    'count': crewai_agent_queries,
                    'percentage': crewai_agent_queries / total_queries if total_queries > 0 else 0
                }
            },
            'response_times': {
                'average_ms': round(avg_response_time, 2),
                'min_ms': min_response_time,
                'max_ms': max_response_time,
                'slow_queries': slow_queries,
                'very_slow_queries': very_slow_queries
            },
            'error_analysis': error_types,
            'entity_detection': entity_stats,
            'complexity_analysis': {
                'average_score': round(avg_complexity, 3),
                'high_complexity_queries': sum(1 for s in complexity_scores if s > 0.7)
            }
        }
    
    def generate_agent_performance_report(self) -> Dict[str, Any]:
        """Generate detailed performance report by agent type"""
        metrics = self._load_metrics_from_file()
        
        if not metrics:
            return {'message': 'No metrics available'}
        
        # Group by agent type
        simple_metrics = [m for m in metrics if m['agent_type'] == 'simple']
        crewai_metrics = [m for m in metrics if m['agent_type'] == 'crewai']
        
        def analyze_agent_metrics(agent_metrics: List[Dict], agent_name: str) -> Dict[str, Any]:
            if not agent_metrics:
                return {'agent': agent_name, 'total_queries': 0}
            
            total = len(agent_metrics)
            successful = sum(1 for m in agent_metrics if m['success'])
            response_times = [m['response_time_ms'] for m in agent_metrics]
            
            return {
                'agent': agent_name,
                'total_queries': total,
                'success_rate': successful / total if total > 0 else 0,
                'avg_response_time_ms': round(sum(response_times) / len(response_times), 2) if response_times else 0,
                'min_response_time_ms': min(response_times) if response_times else 0,
                'max_response_time_ms': max(response_times) if response_times else 0,
                'avg_tool_calls': round(sum(m['tool_calls_count'] for m in agent_metrics) / total, 2) if total > 0 else 0,
                'avg_graphql_queries': round(sum(m['graphql_queries_count'] for m in agent_metrics) / total, 2) if total > 0 else 0,
                'avg_complexity_score': round(sum(m['query_complexity_score'] for m in agent_metrics) / total, 3) if total > 0 else 0
            }
        
        return {
            'report_generated_at': datetime.now(timezone.utc).isoformat(),
            'simple_agent': analyze_agent_metrics(simple_metrics, 'simple'),
            'crewai_agent': analyze_agent_metrics(crewai_metrics, 'crewai'),
            'comparison': {
                'total_queries': len(metrics),
                'simple_agent_usage_percentage': len(simple_metrics) / len(metrics) if metrics else 0,
                'crewai_agent_usage_percentage': len(crewai_metrics) / len(metrics) if metrics else 0
            }
        }
    
    def export_metrics_to_csv(self, output_file: Optional[str] = None) -> str:
        """Export all metrics to a CSV file"""
        if output_file is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_file = f"monitoring/metrics_export_{timestamp}.csv"
        
        metrics = self._load_metrics_from_file()
        
        if not metrics:
            return f"No metrics to export to {output_file}"
        
        # Ensure output directory exists
        os.makedirs(os.path.dirname(output_file), exist_ok=True)
        
        with open(output_file, 'w', newline='') as f:
            if metrics:
                writer = csv.DictWriter(f, fieldnames=metrics[0].keys())
                writer.writeheader()
                writer.writerows(metrics)
        
        return f"Exported {len(metrics)} metrics to {output_file}"
    
    def get_performance_trends(self, days: int = 7) -> Dict[str, Any]:
        """Analyze performance trends over time"""
        cutoff_time = datetime.now(timezone.utc) - timedelta(days=days)
        
        metrics = self._load_metrics_from_file()
        recent_metrics = [
            m for m in metrics 
            if datetime.fromisoformat(m['timestamp'].replace('Z', '+00:00')) >= cutoff_time
        ]
        
        if not recent_metrics:
            return {'message': 'No metrics found for trend analysis'}
        
        # Group by day
        daily_stats = {}
        for metric in recent_metrics:
            date = datetime.fromisoformat(metric['timestamp'].replace('Z', '+00:00')).date()
            if date not in daily_stats:
                daily_stats[date] = {
                    'total_queries': 0,
                    'successful_queries': 0,
                    'response_times': [],
                    'simple_agent_queries': 0,
                    'crewai_agent_queries': 0
                }
            
            daily_stats[date]['total_queries'] += 1
            if metric['success']:
                daily_stats[date]['successful_queries'] += 1
            daily_stats[date]['response_times'].append(metric['response_time_ms'])
            
            if metric['agent_type'] == 'simple':
                daily_stats[date]['simple_agent_queries'] += 1
            else:
                daily_stats[date]['crewai_agent_queries'] += 1
        
        # Calculate daily averages
        trend_data = []
        for date, stats in sorted(daily_stats.items()):
            avg_response_time = sum(stats['response_times']) / len(stats['response_times']) if stats['response_times'] else 0
            success_rate = stats['successful_queries'] / stats['total_queries'] if stats['total_queries'] > 0 else 0
            
            trend_data.append({
                'date': date.isoformat(),
                'total_queries': stats['total_queries'],
                'success_rate': round(success_rate, 3),
                'avg_response_time_ms': round(avg_response_time, 2),
                'simple_agent_usage': stats['simple_agent_queries'] / stats['total_queries'] if stats['total_queries'] > 0 else 0,
                'crewai_agent_usage': stats['crewai_agent_queries'] / stats['total_queries'] if stats['total_queries'] > 0 else 0
            })
        
        return {
            'period_days': days,
            'trend_data': trend_data,
            'summary': {
                'total_days': len(trend_data),
                'avg_queries_per_day': round(sum(d['total_queries'] for d in trend_data) / len(trend_data), 2) if trend_data else 0,
                'avg_success_rate': round(sum(d['success_rate'] for d in trend_data) / len(trend_data), 3) if trend_data else 0,
                'avg_response_time_ms': round(sum(d['avg_response_time_ms'] for d in trend_data) / len(trend_data), 2) if trend_data else 0
            }
        }
    
    def _load_metrics_from_file(self) -> List[Dict[str, Any]]:
        """Load metrics from JSON file"""
        if not os.path.exists(self.config.json_file):
            return []
        
        try:
            with open(self.config.json_file, 'r') as f:
                return json.load(f)
        except Exception as e:
            print(f"Error loading metrics from file: {e}")
            return []
    
    def print_summary_report(self, hours: int = 24):
        """Print a formatted summary report to console"""
        report = self.generate_summary_report(hours)
        
        if 'message' in report:
            print(f"📊 Metrics Report: {report['message']}")
            return
        
        print("📊 Performance Metrics Summary Report")
        print("=" * 50)
        print(f"📅 Period: Last {report['period_hours']} hours")
        print(f"🕐 Generated: {report['report_generated_at']}")
        print()
        
        print("📈 Query Statistics:")
        print(f"  • Total Queries: {report['total_queries']}")
        print(f"  • Success Rate: {report['success_rate']:.1%}")
        print(f"  • Failed Queries: {report['failed_queries']}")
        print()
        
        print("🤖 Agent Usage:")
        print(f"  • Simple Agent: {report['agent_usage']['simple_agent']['count']} queries ({report['agent_usage']['simple_agent']['percentage']:.1%})")
        print(f"  • CrewAI Agent: {report['agent_usage']['crewai_agent']['count']} queries ({report['agent_usage']['crewai_agent']['percentage']:.1%})")
        print()
        
        print("⏱️  Response Times:")
        print(f"  • Average: {report['response_times']['average_ms']:.0f}ms")
        print(f"  • Range: {report['response_times']['min_ms']}ms - {report['response_times']['max_ms']}ms")
        print(f"  • Slow Queries (>5s): {report['response_times']['slow_queries']}")
        print(f"  • Very Slow Queries (>30s): {report['response_times']['very_slow_queries']}")
        print()
        
        if report['error_analysis']:
            print("❌ Error Analysis:")
            for error_type, count in report['error_analysis'].items():
                print(f"  • {error_type}: {count}")
            print()
        
        if report['entity_detection']:
            print("🏷️  Entity Detection:")
            for entity, count in sorted(report['entity_detection'].items(), key=lambda x: x[1], reverse=True):
                print(f"  • {entity}: {count}")
            print()
        
        print("🧠 Complexity Analysis:")
        print(f"  • Average Complexity Score: {report['complexity_analysis']['average_score']:.3f}")
        print(f"  • High Complexity Queries: {report['complexity_analysis']['high_complexity_queries']}")
        print()
    
    def print_agent_performance_report(self):
        """Print a formatted agent performance report to console"""
        report = self.generate_agent_performance_report()
        
        if 'message' in report:
            print(f"🤖 Agent Performance Report: {report['message']}")
            return
        
        print("🤖 Agent Performance Comparison Report")
        print("=" * 50)
        print(f"🕐 Generated: {report['report_generated_at']}")
        print()
        
        for agent_name in ['simple_agent', 'crewai_agent']:
            agent_data = report[agent_name]
            print(f"📊 {agent_data['agent'].title()} Agent:")
            print(f"  • Total Queries: {agent_data['total_queries']}")
            print(f"  • Success Rate: {agent_data['success_rate']:.1%}")
            print(f"  • Avg Response Time: {agent_data['avg_response_time_ms']:.0f}ms")
            print(f"  • Response Time Range: {agent_data['min_response_time_ms']}ms - {agent_data['max_response_time_ms']}ms")
            print(f"  • Avg Tool Calls: {agent_data['avg_tool_calls']}")
            print(f"  • Avg GraphQL Queries: {agent_data['avg_graphql_queries']}")
            print(f"  • Avg Complexity Score: {agent_data['avg_complexity_score']:.3f}")
            print()
        
        print("📈 Usage Comparison:")
        print(f"  • Total Queries: {report['comparison']['total_queries']}")
        print(f"  • Simple Agent Usage: {report['comparison']['simple_agent_usage_percentage']:.1%}")
        print(f"  • CrewAI Agent Usage: {report['comparison']['crewai_agent_usage_percentage']:.1%}")
        print()
