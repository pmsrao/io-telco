#!/usr/bin/env python3
"""
CLI tool for Performance Monitoring & Metrics
Provides command-line interface for viewing reports and managing metrics
"""

import argparse
import sys
import os
from typing import Optional
from .metrics_reporter import MetricsReporter
from .config import MetricsConfig


def main():
    """Main CLI entry point"""
    parser = argparse.ArgumentParser(description='Performance Monitoring & Metrics CLI')
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Report command
    report_parser = subparsers.add_parser('report', help='Generate performance reports')
    report_parser.add_argument('--hours', type=int, default=24, help='Hours to include in report (default: 24)')
    report_parser.add_argument('--format', choices=['console', 'json'], default='console', help='Output format')
    report_parser.add_argument('--output', help='Output file for JSON format')
    
    # Stats command
    stats_parser = subparsers.add_parser('stats', help='Show current statistics')
    stats_parser.add_argument('--agent', choices=['simple', 'crewai', 'all'], default='all', help='Agent type to analyze')
    
    # Export command
    export_parser = subparsers.add_parser('export', help='Export metrics to CSV')
    export_parser.add_argument('--output', help='Output CSV file path')
    
    # Trends command
    trends_parser = subparsers.add_parser('trends', help='Show performance trends')
    trends_parser.add_argument('--days', type=int, default=7, help='Days to analyze (default: 7)')
    trends_parser.add_argument('--format', choices=['console', 'json'], default='console', help='Output format')
    
    # Config command
    config_parser = subparsers.add_parser('config', help='Show current configuration')
    
    # Clean command
    clean_parser = subparsers.add_parser('clean', help='Clean old metrics files')
    clean_parser.add_argument('--days', type=int, default=30, help='Keep files newer than N days (default: 30)')
    clean_parser.add_argument('--dry-run', action='store_true', help='Show what would be deleted without actually deleting')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    try:
        if args.command == 'report':
            handle_report_command(args)
        elif args.command == 'stats':
            handle_stats_command(args)
        elif args.command == 'export':
            handle_export_command(args)
        elif args.command == 'trends':
            handle_trends_command(args)
        elif args.command == 'config':
            handle_config_command()
        elif args.command == 'clean':
            handle_clean_command(args)
        else:
            parser.print_help()
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


def handle_report_command(args):
    """Handle the report command"""
    reporter = MetricsReporter()
    
    if args.format == 'console':
        reporter.print_summary_report(args.hours)
    else:  # json
        report = reporter.generate_summary_report(args.hours)
        output = args.output or f"monitoring/report_{args.hours}h.json"
        
        import json
        os.makedirs(os.path.dirname(output), exist_ok=True)
        with open(output, 'w') as f:
            json.dump(report, f, indent=2)
        
        print(f"Report saved to {output}")


def handle_stats_command(args):
    """Handle the stats command"""
    reporter = MetricsReporter()
    
    if args.agent == 'all':
        reporter.print_agent_performance_report()
    else:
        # Generate agent-specific report
        agent_report = reporter.generate_agent_performance_report()
        agent_data = agent_report.get(f'{args.agent}_agent', {})
        
        if not agent_data:
            print(f"No data available for {args.agent} agent")
            return
        
        print(f"📊 {args.agent.title()} Agent Statistics")
        print("=" * 40)
        print(f"Total Queries: {agent_data['total_queries']}")
        print(f"Success Rate: {agent_data['success_rate']:.1%}")
        print(f"Avg Response Time: {agent_data['avg_response_time_ms']:.0f}ms")
        print(f"Avg Tool Calls: {agent_data['avg_tool_calls']}")
        print(f"Avg GraphQL Queries: {agent_data['avg_graphql_queries']}")
        print(f"Avg Complexity Score: {agent_data['avg_complexity_score']:.3f}")


def handle_export_command(args):
    """Handle the export command"""
    reporter = MetricsReporter()
    result = reporter.export_metrics_to_csv(args.output)
    print(result)


def handle_trends_command(args):
    """Handle the trends command"""
    reporter = MetricsReporter()
    
    if args.format == 'console':
        trends = reporter.get_performance_trends(args.days)
        
        if 'message' in trends:
            print(f"📈 Trends Analysis: {trends['message']}")
            return
        
        print(f"📈 Performance Trends (Last {args.days} days)")
        print("=" * 50)
        print(f"📅 Period: {trends['period_days']} days")
        print()
        
        summary = trends['summary']
        print("📊 Summary:")
        print(f"  • Total Days: {summary['total_days']}")
        print(f"  • Avg Queries/Day: {summary['avg_queries_per_day']}")
        print(f"  • Avg Success Rate: {summary['avg_success_rate']:.1%}")
        print(f"  • Avg Response Time: {summary['avg_response_time_ms']:.0f}ms")
        print()
        
        print("📅 Daily Breakdown:")
        for day_data in trends['trend_data']:
            print(f"  {day_data['date']}: {day_data['total_queries']} queries, "
                  f"{day_data['success_rate']:.1%} success, "
                  f"{day_data['avg_response_time_ms']:.0f}ms avg")
    else:  # json
        trends = reporter.get_performance_trends(args.days)
        output = args.output or f"monitoring/trends_{args.days}d.json"
        
        import json
        os.makedirs(os.path.dirname(output), exist_ok=True)
        with open(output, 'w') as f:
            json.dump(trends, f, indent=2)
        
        print(f"Trends data saved to {output}")


def handle_config_command():
    """Handle the config command"""
    config = MetricsConfig.from_env()
    
    print("⚙️  Metrics Configuration")
    print("=" * 30)
    print(f"Enabled: {config.enabled}")
    print(f"Sampling Rate: {config.sampling_rate:.1%}")
    print(f"JSON File: {config.json_file}")
    print(f"CSV File: {config.csv_file}")
    print(f"Slow Query Threshold: {config.slow_query_threshold_ms}ms")
    print(f"Very Slow Query Threshold: {config.very_slow_query_threshold_ms}ms")
    print(f"Max File Size: {config.max_file_size_mb}MB")
    print(f"Max Records Per File: {config.max_records_per_file}")


def handle_clean_command(args):
    """Handle the clean command"""
    import glob
    from datetime import datetime, timedelta
    
    cutoff_date = datetime.now() - timedelta(days=args.days)
    files_to_delete = []
    
    # Find old metrics files
    patterns = [
        "monitoring/metrics.json.*",
        "monitoring/metrics.csv.*",
        "monitoring/metrics_export_*.csv",
        "monitoring/report_*.json",
        "monitoring/trends_*.json"
    ]
    
    for pattern in patterns:
        for file_path in glob.glob(pattern):
            try:
                file_time = datetime.fromtimestamp(os.path.getmtime(file_path))
                if file_time < cutoff_date:
                    files_to_delete.append(file_path)
            except OSError:
                continue
    
    if not files_to_delete:
        print("No old metrics files found to clean")
        return
    
    print(f"Found {len(files_to_delete)} files older than {args.days} days:")
    for file_path in files_to_delete:
        print(f"  {file_path}")
    
    if args.dry_run:
        print("\nDry run - no files were deleted")
    else:
        deleted_count = 0
        for file_path in files_to_delete:
            try:
                os.remove(file_path)
                deleted_count += 1
            except OSError as e:
                print(f"Error deleting {file_path}: {e}")
        
        print(f"\nDeleted {deleted_count} files")


if __name__ == '__main__':
    main()
