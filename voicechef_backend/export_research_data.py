"""
Export research data from sessions to JSONL format for analysis.

This script exports interaction logs and session analytics for research analysis
(NASA-TLX, SUS, completion time, error rates, etc.).

Usage:
    python export_research_data.py --session-id abc-123
    python export_research_data.py --all
"""

import argparse
import json
import sys
from datetime import datetime
import requests


API_BASE_URL = "http://localhost:8000"


def export_session_analytics(session_id: str, output_file: str = None):
    """
    Export analytics for a single session.
    
    Args:
        session_id: Session identifier
        output_file: Optional output file path (default: session_{id}_analytics.jsonl)
    """
    try:
        # Fetch analytics
        response = requests.get(f"{API_BASE_URL}/session/{session_id}/analytics")
        response.raise_for_status()
        
        data = response.json()
        
        # Generate output filename if not provided
        if output_file is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_file = f"session_{session_id[:8]}_analytics_{timestamp}.jsonl"
        
        # Write to JSONL (one JSON object per line)
        with open(output_file, 'w') as f:
            # Write session summary
            summary = {
                "type": "session_summary",
                "session_id": data["session_id"],
                "recipe": data["recipe"],
                "total_steps": data["total_steps"],
                "current_step": data["current_step"],
                "total_interactions": data["total_interactions"],
                "interaction_breakdown": data["interaction_breakdown"],
                "is_complete": data["is_complete"],
                "exported_at": datetime.now().isoformat()
            }
            f.write(json.dumps(summary) + '\n')
            
            # Write each interaction log entry
            for log_entry in data["interaction_log"]:
                log_entry["type"] = "interaction"
                log_entry["session_id"] = session_id
                f.write(json.dumps(log_entry) + '\n')
        
        print(f"✓ Exported session {session_id} to {output_file}")
        print(f"  - Total interactions: {data['total_interactions']}")
        print(f"  - Recipe: {data['recipe']}")
        print(f"  - Complete: {data['is_complete']}")
        
        return output_file
    
    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 404:
            print(f"✗ Session {session_id} not found", file=sys.stderr)
        else:
            print(f"✗ HTTP error: {e}", file=sys.stderr)
        return None
    except Exception as e:
        print(f"✗ Error exporting session: {e}", file=sys.stderr)
        return None


def calculate_metrics(jsonl_file: str):
    """
    Calculate research metrics from JSONL file.
    
    Metrics:
    - Task completion time
    - Total interactions
    - Error rate (repeats + unclear commands)
    - Command distribution
    """
    try:
        with open(jsonl_file, 'r') as f:
            lines = f.readlines()
        
        summary = None
        interactions = []
        
        for line in lines:
            data = json.loads(line)
            if data.get("type") == "session_summary":
                summary = data
            elif data.get("type") == "interaction":
                interactions.append(data)
        
        if not summary or not interactions:
            print("✗ Invalid JSONL format", file=sys.stderr)
            return
        
        # Calculate completion time
        start_time = datetime.fromisoformat(interactions[0]["timestamp"])
        end_time = datetime.fromisoformat(interactions[-1]["timestamp"])
        completion_time = (end_time - start_time).total_seconds()
        
        # Calculate error rate
        errors = sum(1 for i in interactions if i.get("type") in ["repeat_step", "error"])
        error_rate = (errors / len(interactions)) * 100 if interactions else 0
        
        # Print metrics
        print("\n" + "="*50)
        print("RESEARCH METRICS")
        print("="*50)
        print(f"Session ID: {summary['session_id']}")
        print(f"Recipe: {summary['recipe']}")
        print(f"Total Steps: {summary['total_steps']}")
        print(f"Completed: {summary['is_complete']}")
        print(f"\nTask Completion Time: {completion_time:.2f} seconds ({completion_time/60:.2f} minutes)")
        print(f"Total Interactions: {len(interactions)}")
        print(f"Error Rate: {error_rate:.2f}%")
        print(f"\nCommand Distribution:")
        for cmd_type, count in summary['interaction_breakdown'].items():
            percentage = (count / len(interactions)) * 100
            print(f"  - {cmd_type}: {count} ({percentage:.1f}%)")
        print("="*50 + "\n")
        
    except Exception as e:
        print(f"✗ Error calculating metrics: {e}", file=sys.stderr)


def main():
    parser = argparse.ArgumentParser(
        description="Export VoiceChef research data for analysis"
    )
    parser.add_argument(
        "--session-id",
        type=str,
        help="Export specific session by ID"
    )
    parser.add_argument(
        "--output",
        type=str,
        help="Output file path (default: auto-generated)"
    )
    parser.add_argument(
        "--metrics",
        action="store_true",
        help="Calculate and display metrics after export"
    )
    
    args = parser.parse_args()
    
    if not args.session_id:
        print("Error: --session-id is required", file=sys.stderr)
        parser.print_help()
        sys.exit(1)
    
    # Export session data
    output_file = export_session_analytics(args.session_id, args.output)
    
    if output_file and args.metrics:
        calculate_metrics(output_file)


if __name__ == "__main__":
    main()




