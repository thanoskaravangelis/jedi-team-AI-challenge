#!/usr/bin/env python3
"""
Jedi Agent Evaluation Statistics Extractor

This script analyzes the database and extracts comprehensive evaluation statistics
including performance metrics, tool usage, user feedback, and improvement recommendations.
"""

import os
import sys
import json
import sqlite3
from datetime import datetime, timedelta
from typing import Dict, Any, List
import statistics
from collections import defaultdict, Counter

# Add the project root to Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.db.database import DATABASE_URL, SessionLocal
from app.db.models import (
    Conversation, Message, ToolInvocation, UserFeedback, EvaluationScore
)
from sqlalchemy import func, desc
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class JediAgentEvaluator:
    """Comprehensive evaluation statistics extractor for Jedi Agent."""
    
    def __init__(self):
        self.db = SessionLocal()
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.db.close()
    
    def generate_full_report(self, days: int = 30) -> Dict[str, Any]:
        """Generate a comprehensive evaluation report."""
        logger.info(f"📊 Generating evaluation report for last {days} days...")
        
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=days)
        
        report = {
            "report_metadata": {
                "generated_at": end_date.isoformat(),
                "period": f"Last {days} days",
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat()
            },
            "overview": self._get_overview_stats(start_date, end_date),
            "conversation_metrics": self._get_conversation_metrics(start_date, end_date),
            "tool_performance": self._get_tool_performance(start_date, end_date),
            "evaluation_scores": self._get_evaluation_scores(start_date, end_date),
            "user_feedback": self._get_user_feedback_analysis(start_date, end_date),
            "response_quality": self._get_response_quality_analysis(start_date, end_date),
            "performance_trends": self._get_performance_trends(start_date, end_date),
            "improvement_recommendations": self._get_improvement_recommendations(start_date, end_date)
        }
        
        return report
    
    def _get_overview_stats(self, start_date: datetime, end_date: datetime) -> Dict[str, Any]:
        """Get high-level overview statistics."""
        try:
            # Total conversations and messages
            total_conversations = self.db.query(Conversation).filter(
                Conversation.created_at >= start_date,
                Conversation.created_at <= end_date
            ).count()
            
            total_messages = self.db.query(Message).filter(
                Message.created_at >= start_date,
                Message.created_at <= end_date
            ).count()
            
            user_messages = self.db.query(Message).filter(
                Message.role == 'user',
                Message.created_at >= start_date,
                Message.created_at <= end_date
            ).count()
            
            assistant_messages = self.db.query(Message).filter(
                Message.role == 'assistant',
                Message.created_at >= start_date,
                Message.created_at <= end_date
            ).count()
            
            # Tool invocations
            total_tool_invocations = self.db.query(ToolInvocation).filter(
                ToolInvocation.created_at >= start_date,
                ToolInvocation.created_at <= end_date
            ).count()
            
            successful_invocations = self.db.query(ToolInvocation).filter(
                ToolInvocation.success == True,
                ToolInvocation.created_at >= start_date,
                ToolInvocation.created_at <= end_date
            ).count()
            
            # Unique users
            unique_users = self.db.query(Conversation.user_id).filter(
                Conversation.created_at >= start_date,
                Conversation.created_at <= end_date
            ).distinct().count()
            
            # Average conversation length
            avg_conv_length = self.db.query(func.avg(
                self.db.query(func.count(Message.id)).filter(
                    Message.conversation_id == Conversation.id
                ).scalar_subquery()
            )).join(Message).filter(
                Conversation.created_at >= start_date,
                Conversation.created_at <= end_date
            ).scalar() or 0
            
            return {
                "total_conversations": total_conversations,
                "total_messages": total_messages,
                "user_messages": user_messages,
                "assistant_messages": assistant_messages,
                "unique_users": unique_users,
                "average_conversation_length": round(float(avg_conv_length), 2),
                "total_tool_invocations": total_tool_invocations,
                "successful_tool_invocations": successful_invocations,
                "tool_success_rate": round((successful_invocations / total_tool_invocations * 100), 2) if total_tool_invocations > 0 else 0
            }
        except Exception as e:
            logger.error(f"Error getting overview stats: {e}")
            return {"error": str(e)}
    
    def _get_conversation_metrics(self, start_date: datetime, end_date: datetime) -> Dict[str, Any]:
        """Get detailed conversation metrics."""
        try:
            conversations = self.db.query(Conversation).filter(
                Conversation.created_at >= start_date,
                Conversation.created_at <= end_date
            ).all()
            
            if not conversations:
                return {"message": "No conversations found in the specified period"}
            
            # Conversation lengths
            conv_lengths = []
            for conv in conversations:
                msg_count = self.db.query(Message).filter(
                    Message.conversation_id == conv.id
                ).count()
                conv_lengths.append(msg_count)
            
            # Daily conversation counts
            daily_counts = defaultdict(int)
            for conv in conversations:
                day = conv.created_at.date().isoformat()
                daily_counts[day] += 1
            
            return {
                "total_conversations": len(conversations),
                "average_length": round(statistics.mean(conv_lengths), 2) if conv_lengths else 0,
                "median_length": round(statistics.median(conv_lengths), 2) if conv_lengths else 0,
                "min_length": min(conv_lengths) if conv_lengths else 0,
                "max_length": max(conv_lengths) if conv_lengths else 0,
                "conversations_with_titles": len([c for c in conversations if c.title]),
                "daily_conversation_counts": dict(sorted(daily_counts.items())),
                "busiest_day": max(daily_counts.items(), key=lambda x: x[1]) if daily_counts else None
            }
        except Exception as e:
            logger.error(f"Error getting conversation metrics: {e}")
            return {"error": str(e)}
    
    def _get_tool_performance(self, start_date: datetime, end_date: datetime) -> Dict[str, Any]:
        """Get detailed tool performance analytics."""
        try:
            tool_stats = self.db.query(
                ToolInvocation.tool_name,
                func.count(ToolInvocation.id).label('total_uses'),
                func.sum(func.case((ToolInvocation.success == True, 1), else_=0)).label('successful_uses'),
                func.avg(ToolInvocation.execution_time).label('avg_execution_time'),
                func.min(ToolInvocation.execution_time).label('min_execution_time'),
                func.max(ToolInvocation.execution_time).label('max_execution_time')
            ).filter(
                ToolInvocation.created_at >= start_date,
                ToolInvocation.created_at <= end_date
            ).group_by(ToolInvocation.tool_name).all()
            
            tool_performance = {}
            total_uses = 0
            
            for stat in tool_stats:
                success_rate = (stat.successful_uses / stat.total_uses * 100) if stat.total_uses > 0 else 0
                total_uses += stat.total_uses
                
                tool_performance[stat.tool_name] = {
                    "total_uses": stat.total_uses,
                    "successful_uses": stat.successful_uses,
                    "success_rate": round(success_rate, 2),
                    "avg_execution_time_ms": round(float(stat.avg_execution_time or 0), 2),
                    "min_execution_time_ms": float(stat.min_execution_time or 0),
                    "max_execution_time_ms": float(stat.max_execution_time or 0)
                }
            
            # Tool usage distribution
            usage_distribution = {}
            for tool_name, stats in tool_performance.items():
                percentage = (stats["total_uses"] / total_uses * 100) if total_uses > 0 else 0
                usage_distribution[tool_name] = round(percentage, 2)
            
            return {
                "tool_performance": tool_performance,
                "usage_distribution": usage_distribution,
                "most_used_tool": max(tool_performance.items(), key=lambda x: x[1]["total_uses"])[0] if tool_performance else None,
                "fastest_tool": min(tool_performance.items(), key=lambda x: x[1]["avg_execution_time_ms"])[0] if tool_performance else None,
                "most_reliable_tool": max(tool_performance.items(), key=lambda x: x[1]["success_rate"])[0] if tool_performance else None
            }
        except Exception as e:
            logger.error(f"Error getting tool performance: {e}")
            return {"error": str(e)}
    
    def _get_evaluation_scores(self, start_date: datetime, end_date: datetime) -> Dict[str, Any]:
        """Get evaluation score analytics."""
        try:
            evaluations = self.db.query(EvaluationScore).filter(
                EvaluationScore.created_at >= start_date,
                EvaluationScore.created_at <= end_date
            ).all()
            
            if not evaluations:
                return {"message": "No evaluation scores found in the specified period"}
            
            # Extract scores
            relevance_scores = [e.relevance_score for e in evaluations if e.relevance_score]
            accuracy_scores = [e.accuracy_score for e in evaluations if e.accuracy_score]
            completeness_scores = [e.completeness_score for e in evaluations if e.completeness_score]
            overall_scores = [e.overall_score for e in evaluations if e.overall_score]
            
            def score_stats(scores):
                if not scores:
                    return None
                return {
                    "average": round(statistics.mean(scores), 2),
                    "median": round(statistics.median(scores), 2),
                    "min": min(scores),
                    "max": max(scores),
                    "std_dev": round(statistics.stdev(scores), 2) if len(scores) > 1 else 0,
                    "distribution": dict(Counter(scores))
                }
            
            return {
                "total_evaluations": len(evaluations),
                "relevance_scores": score_stats(relevance_scores),
                "accuracy_scores": score_stats(accuracy_scores),
                "completeness_scores": score_stats(completeness_scores),
                "overall_scores": score_stats(overall_scores),
                "excellent_responses": len([s for s in overall_scores if s >= 4.5]),
                "good_responses": len([s for s in overall_scores if 3.5 <= s < 4.5]),
                "average_responses": len([s for s in overall_scores if 2.5 <= s < 3.5]),
                "poor_responses": len([s for s in overall_scores if s < 2.5])
            }
        except Exception as e:
            logger.error(f"Error getting evaluation scores: {e}")
            return {"error": str(e)}
    
    def _get_user_feedback_analysis(self, start_date: datetime, end_date: datetime) -> Dict[str, Any]:
        """Get user feedback analysis."""
        try:
            feedback = self.db.query(UserFeedback).join(Message).filter(
                Message.created_at >= start_date,
                Message.created_at <= end_date
            ).all()
            
            if not feedback:
                return {"message": "No user feedback found in the specified period"}
            
            feedback_counts = Counter([f.feedback_type for f in feedback])
            total_feedback = len(feedback)
            
            # Calculate satisfaction rate
            positive_feedback = feedback_counts.get('thumbs_up', 0)
            negative_feedback = feedback_counts.get('thumbs_down', 0)
            satisfaction_rate = (positive_feedback / total_feedback * 100) if total_feedback > 0 else 0
            
            # Comments analysis
            comments = [f.comment for f in feedback if f.comment and f.comment.strip()]
            
            return {
                "total_feedback": total_feedback,
                "feedback_distribution": dict(feedback_counts),
                "satisfaction_rate": round(satisfaction_rate, 2),
                "positive_feedback": positive_feedback,
                "negative_feedback": negative_feedback,
                "neutral_feedback": total_feedback - positive_feedback - negative_feedback,
                "feedback_with_comments": len(comments),
                "recent_comments": comments[-5:] if comments else []  # Last 5 comments
            }
        except Exception as e:
            logger.error(f"Error getting user feedback: {e}")
            return {"error": str(e)}
    
    def _get_response_quality_analysis(self, start_date: datetime, end_date: datetime) -> Dict[str, Any]:
        """Analyze response quality trends."""
        try:
            # Get messages with evaluation scores
            messages_with_scores = self.db.query(Message, EvaluationScore).join(
                EvaluationScore, Message.id == EvaluationScore.message_id
            ).filter(
                Message.role == 'assistant',
                Message.created_at >= start_date,
                Message.created_at <= end_date
            ).all()
            
            if not messages_with_scores:
                return {"message": "No evaluated messages found in the specified period"}
            
            # Analyze response lengths
            response_lengths = [len(msg.content) for msg, _ in messages_with_scores]
            
            # Analyze tool usage correlation with quality
            tool_quality_correlation = defaultdict(list)
            for message, score in messages_with_scores:
                # Get tools used for this message
                tools_used = self.db.query(ToolInvocation).filter(
                    ToolInvocation.message_id == message.id
                ).all()
                
                tool_names = [t.tool_name for t in tools_used]
                
                if score.overall_score:
                    if not tool_names:
                        tool_quality_correlation['no_tools'].append(score.overall_score)
                    else:
                        for tool_name in tool_names:
                            tool_quality_correlation[tool_name].append(score.overall_score)
            
            # Calculate average quality by tool usage
            tool_quality_avg = {}
            for tool, scores in tool_quality_correlation.items():
                if scores:
                    tool_quality_avg[tool] = round(statistics.mean(scores), 2)
            
            return {
                "evaluated_responses": len(messages_with_scores),
                "average_response_length": round(statistics.mean(response_lengths), 2) if response_lengths else 0,
                "median_response_length": round(statistics.median(response_lengths), 2) if response_lengths else 0,
                "tool_quality_correlation": tool_quality_avg,
                "responses_with_citations": len([msg for msg, _ in messages_with_scores if "Citation" in msg.content or "[Citation" in msg.content]),
                "responses_with_multiple_tools": len([
                    msg for msg, _ in messages_with_scores 
                    if self.db.query(ToolInvocation).filter(ToolInvocation.message_id == msg.id).count() > 1
                ])
            }
        except Exception as e:
            logger.error(f"Error getting response quality analysis: {e}")
            return {"error": str(e)}
    
    def _get_performance_trends(self, start_date: datetime, end_date: datetime) -> Dict[str, Any]:
        """Get performance trends over time."""
        try:
            # Daily metrics
            daily_metrics = defaultdict(lambda: {
                'conversations': 0,
                'messages': 0,
                'tool_invocations': 0,
                'avg_scores': []
            })
            
            # Group data by day
            for delta in range((end_date - start_date).days + 1):
                day = start_date + timedelta(days=delta)
                day_str = day.date().isoformat()
                
                # Count conversations
                conv_count = self.db.query(Conversation).filter(
                    func.date(Conversation.created_at) == day.date()
                ).count()
                
                # Count messages
                msg_count = self.db.query(Message).filter(
                    func.date(Message.created_at) == day.date()
                ).count()
                
                # Count tool invocations
                tool_count = self.db.query(ToolInvocation).filter(
                    func.date(ToolInvocation.created_at) == day.date()
                ).count()
                
                # Get average scores for the day
                day_scores = self.db.query(EvaluationScore.overall_score).filter(
                    func.date(EvaluationScore.created_at) == day.date(),
                    EvaluationScore.overall_score.isnot(None)
                ).all()
                
                avg_score = statistics.mean([s[0] for s in day_scores]) if day_scores else None
                
                daily_metrics[day_str] = {
                    'conversations': conv_count,
                    'messages': msg_count,
                    'tool_invocations': tool_count,
                    'avg_score': round(avg_score, 2) if avg_score else None
                }
            
            return {
                "daily_metrics": dict(daily_metrics),
                "trend_summary": {
                    "most_active_day": max(daily_metrics.items(), key=lambda x: x[1]['messages'])[0] if daily_metrics else None,
                    "best_quality_day": max(
                        [(day, metrics) for day, metrics in daily_metrics.items() if metrics['avg_score']],
                        key=lambda x: x[1]['avg_score']
                    )[0] if any(m['avg_score'] for m in daily_metrics.values()) else None
                }
            }
        except Exception as e:
            logger.error(f"Error getting performance trends: {e}")
            return {"error": str(e)}
    
    def _get_improvement_recommendations(self, start_date: datetime, end_date: datetime) -> List[str]:
        """Generate improvement recommendations based on data analysis."""
        recommendations = []
        
        try:
            # Check tool success rates
            tool_stats = self.db.query(
                ToolInvocation.tool_name,
                func.count(ToolInvocation.id).label('total'),
                func.sum(func.case((ToolInvocation.success == True, 1), else_=0)).label('successful')
            ).filter(
                ToolInvocation.created_at >= start_date,
                ToolInvocation.created_at <= end_date
            ).group_by(ToolInvocation.tool_name).all()
            
            for stat in tool_stats:
                success_rate = (stat.successful / stat.total) if stat.total > 0 else 0
                if success_rate < 0.8:
                    recommendations.append(
                        f"⚠️ {stat.tool_name} tool has low success rate ({success_rate*100:.1f}%). "
                        f"Consider debugging or improving error handling."
                    )
            
            # Check evaluation scores
            low_scores = self.db.query(EvaluationScore).filter(
                EvaluationScore.overall_score < 3.0,
                EvaluationScore.created_at >= start_date,
                EvaluationScore.created_at <= end_date
            ).count()
            
            total_scores = self.db.query(EvaluationScore).filter(
                EvaluationScore.created_at >= start_date,
                EvaluationScore.created_at <= end_date
            ).count()
            
            if total_scores > 0 and (low_scores / total_scores) > 0.2:
                recommendations.append(
                    f"📉 {low_scores}/{total_scores} responses scored below 3.0. "
                    f"Consider improving prompt engineering or adding more context."
                )
            
            # Check user feedback
            negative_feedback = self.db.query(UserFeedback).join(Message).filter(
                UserFeedback.feedback_type == 'thumbs_down',
                Message.created_at >= start_date,
                Message.created_at <= end_date
            ).count()
            
            total_feedback = self.db.query(UserFeedback).join(Message).filter(
                Message.created_at >= start_date,
                Message.created_at <= end_date
            ).count()
            
            if total_feedback > 0 and (negative_feedback / total_feedback) > 0.3:
                recommendations.append(
                    f"👎 High negative feedback rate ({negative_feedback}/{total_feedback}). "
                    f"Review recent responses and user comments for patterns."
                )
            
            # Check conversation engagement
            avg_length = self.db.query(func.avg(
                self.db.query(func.count(Message.id)).filter(
                    Message.conversation_id == Conversation.id
                ).scalar_subquery()
            )).join(Message).filter(
                Conversation.created_at >= start_date,
                Conversation.created_at <= end_date
            ).scalar()
            
            if avg_length and avg_length < 3:
                recommendations.append(
                    f"📊 Low average conversation length ({avg_length:.1f} messages). "
                    f"Users might not be finding initial responses helpful enough to continue."
                )
            
            # Check tool usage patterns
            unused_tools = []
            all_tools = ['similarity_search', 'web_search', 'answer_evaluator']
            used_tools = [stat.tool_name for stat in tool_stats]
            
            for tool in all_tools:
                if tool not in used_tools:
                    unused_tools.append(tool)
            
            if unused_tools:
                recommendations.append(
                    f"🛠️ Tools not being used: {', '.join(unused_tools)}. "
                    f"Consider investigating why these tools aren't being selected."
                )
            
            if not recommendations:
                recommendations.append("✅ System performance looks good! No specific improvements needed at this time.")
            
            return recommendations
            
        except Exception as e:
            logger.error(f"Error generating recommendations: {e}")
            return [f"❌ Error generating recommendations: {str(e)}"]

def print_report(report: Dict[str, Any]):
    """Print a nicely formatted report."""
    print("\n" + "="*80)
    print("🤖 JEDI AGENT EVALUATION REPORT")
    print("="*80)
    
    # Report metadata
    metadata = report.get("report_metadata", {})
    print(f"\n📅 Report Period: {metadata.get('period', 'Unknown')}")
    print(f"📊 Generated: {metadata.get('generated_at', 'Unknown')}")
    
    # Overview
    overview = report.get("overview", {})
    print(f"\n📈 OVERVIEW")
    print("-" * 40)
    print(f"Total Conversations: {overview.get('total_conversations', 0)}")
    print(f"Total Messages: {overview.get('total_messages', 0)}")
    print(f"Unique Users: {overview.get('unique_users', 0)}")
    print(f"Tool Success Rate: {overview.get('tool_success_rate', 0)}%")
    print(f"Average Conversation Length: {overview.get('average_conversation_length', 0)} messages")
    
    # Tool Performance
    tool_perf = report.get("tool_performance", {})
    if "tool_performance" in tool_perf:
        print(f"\n🛠️  TOOL PERFORMANCE")
        print("-" * 40)
        for tool, stats in tool_perf["tool_performance"].items():
            print(f"{tool}:")
            print(f"  Uses: {stats['total_uses']} | Success: {stats['success_rate']}% | Avg Time: {stats['avg_execution_time_ms']}ms")
        
        if "most_used_tool" in tool_perf:
            print(f"\nMost Used Tool: {tool_perf['most_used_tool']}")
            print(f"Most Reliable Tool: {tool_perf.get('most_reliable_tool', 'N/A')}")
    
    # Evaluation Scores
    eval_scores = report.get("evaluation_scores", {})
    if eval_scores and "overall_scores" in eval_scores and eval_scores["overall_scores"]:
        print(f"\n⭐ EVALUATION SCORES")
        print("-" * 40)
        overall = eval_scores["overall_scores"]
        print(f"Average Overall Score: {overall['average']}/5")
        print(f"Excellent Responses (4.5+): {eval_scores.get('excellent_responses', 0)}")
        print(f"Good Responses (3.5-4.5): {eval_scores.get('good_responses', 0)}")
        print(f"Poor Responses (<2.5): {eval_scores.get('poor_responses', 0)}")
    
    # User Feedback
    feedback = report.get("user_feedback", {})
    if feedback and "total_feedback" in feedback:
        print(f"\n👥 USER FEEDBACK")
        print("-" * 40)
        print(f"Total Feedback: {feedback['total_feedback']}")
        print(f"Satisfaction Rate: {feedback.get('satisfaction_rate', 0)}%")
        print(f"Positive: {feedback.get('positive_feedback', 0)} | Negative: {feedback.get('negative_feedback', 0)}")
    
    # Improvement Recommendations
    recommendations = report.get("improvement_recommendations", [])
    if recommendations:
        print(f"\n💡 IMPROVEMENT RECOMMENDATIONS")
        print("-" * 40)
        for i, rec in enumerate(recommendations, 1):
            print(f"{i}. {rec}")
    
    print("\n" + "="*80)

def main():
    """Main function to run the evaluation."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Jedi Agent Evaluation Statistics")
    parser.add_argument("--days", type=int, default=30, help="Number of days to analyze (default: 30)")
    parser.add_argument("--format", choices=["text", "json"], default="text", help="Output format")
    parser.add_argument("--output", type=str, help="Output file (optional)")
    
    args = parser.parse_args()
    
    try:
        with JediAgentEvaluator() as evaluator:
            report = evaluator.generate_full_report(days=args.days)
            
            if args.format == "json":
                output = json.dumps(report, indent=2, default=str)
            else:
                output = None
                print_report(report)
            
            if args.output:
                with open(args.output, 'w') as f:
                    if args.format == "json":
                        f.write(output)
                    else:
                        # For text format, we'd need to capture the print output
                        f.write("Use --format json for file output\n")
                print(f"\n💾 Report saved to: {args.output}")
            elif args.format == "json":
                print(output)
                
    except Exception as e:
        logger.error(f"Error running evaluation: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
