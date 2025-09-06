#!/usr/bin/env python3
"""
Main entry point for the peer review system.
"""

import os
import sys
import asyncio
import argparse
import logging
from datetime import datetime
from dotenv import load_dotenv

# Add project root to Python path
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

from models.task import Task, TaskStatus
from agents.feedback_orchestrator import FeedbackOrchestrator
from models.validation import FeedbackTracker

# Load environment variables
load_dotenv()

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def process_task_with_peer_review(task_description: str, project_id: str = "DEFAULT", 
                                      language: str = "python", priority: int = 80) -> dict:
    """Process a task using the peer review system"""
    
    # Create task
    task = Task(
        description=task_description,
        language=language,
        priority=priority
    )
    
    logger.info(f"🚀 Processing task: {task.task_id}")
    logger.info(f"📝 Description: {task_description}")
    
    # Initialize orchestrator
    orchestrator = FeedbackOrchestrator()
    
    # Process task
    result = await orchestrator.process_task_with_feedback(task)
    
    # Log results
    if result['success']:
        logger.info(f"✅ Task completed successfully!")
        logger.info(f"📊 Quality Score: {result.get('quality_score', 'N/A')}/10")
        logger.info(f"🎯 Recommendation: {result.get('recommendation', 'N/A')}")
        
        # Show feedback summary
        feedback_summary = result.get('feedback_summary', {})
        if feedback_summary.get('total_feedback_instances', 0) > 0:
            logger.info(f"💬 Peer Review Summary:")
            logger.info(f"  Total feedback instances: {feedback_summary['total_feedback_instances']}")
            logger.info(f"  Retry success rate: {feedback_summary['retry_success_rate']:.1%}")
            
            for agent, feedback_list in feedback_summary.get('feedback_by_agent', {}).items():
                logger.info(f"  {agent}: {len(feedback_list)} feedback instances")
    else:
        logger.error(f"❌ Task failed: {result.get('error', 'Unknown error')}")
        logger.error(f"Failed at: {result.get('failed_at', 'Unknown stage')}")
    
    return result

def show_feedback_stats():
    """Show current feedback statistics"""
    logger.info("📊 Current Feedback Statistics")
    
    tracker = FeedbackTracker()
    stats = tracker.get_feedback_stats()
    recent_feedback = tracker.get_recent_feedback(limit=10)
    
    if not stats and not recent_feedback:
        logger.info("No feedback data available yet. Run some tasks first!")
        return
    
    if stats:
        logger.info("\n🤖 Agent Performance:")
        for agent, agent_stats in stats.items():
            logger.info(f"  {agent.replace('_', ' ').title()}:")
            logger.info(f"    Feedback received: {agent_stats['received_count']} times")
            logger.info(f"    Retry success rate: {agent_stats['retry_success_rate']:.1%}")
            logger.info(f"    Average confidence: {agent_stats['avg_confidence']:.2f}")
            if agent_stats['common_issues']:
                logger.info(f"    Common issues: {', '.join(agent_stats['common_issues'][:3])}")
    
    if recent_feedback:
        logger.info(f"\n📝 Recent Feedback ({len(recent_feedback)} entries):")
        for feedback in recent_feedback[:5]:
            logger.info(f"  {feedback['from_agent']} → {feedback['to_agent']}")
            logger.info(f"    {feedback['feedback'][:100]}...")
            if feedback.get('retry_successful') is not None:
                status = "✅ Success" if feedback['retry_successful'] else "❌ Failed"
                logger.info(f"    Retry: {status}")

async def main():
    """Main function"""
    parser = argparse.ArgumentParser(description="Peer Review System")
    parser.add_argument("--task", type=str, help="Task description to process")
    parser.add_argument("--project", type=str, default="DEFAULT", help="Project ID")
    parser.add_argument("--language", type=str, default="python", help="Programming language")
    parser.add_argument("--priority", type=int, default=80, help="Task priority (0-100)")
    parser.add_argument("--stats", action="store_true", help="Show feedback statistics")
    parser.add_argument("--test", action="store_true", help="Run test suite")
    
    args = parser.parse_args()
    
    # Check API key
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key or not api_key.startswith('sk-'):
        logger.error("❌ No valid OpenAI API key found.")
        logger.error("Please set OPENAI_API_KEY environment variable or create .env file")
        return
    
    logger.info("✅ OpenAI API key loaded")
    
    if args.stats:
        show_feedback_stats()
    elif args.test:
        logger.info("🧪 Running test suite...")
        from test_peer_review_system import run_comprehensive_test
        await run_comprehensive_test()
    elif args.task:
        result = await process_task_with_peer_review(
            args.task, args.project, args.language, args.priority
        )
        
        # Show where files were saved
        if result['success']:
            logger.info("\n📁 Generated Files:")
            logger.info(f"  Implementation: implementations/{result['task_id']}_*.py")
            logger.info(f"  Tests: tests/test_{result['task_id']}.py")
            logger.info(f"  Quality Report: quality_reports/quality_report_{result['task_id']}.md")
            logger.info(f"  Feedback Log: logs/feedback/")
    else:
        # Interactive mode
        logger.info("🎯 Peer Review System - Interactive Mode")
        logger.info("Enter task descriptions (or 'quit' to exit, 'stats' for statistics)")
        
        while True:
            try:
                task_input = input("\n📝 Task: ").strip()
                
                if task_input.lower() in ['quit', 'exit', 'q']:
                    break
                elif task_input.lower() == 'stats':
                    show_feedback_stats()
                    continue
                elif not task_input:
                    continue
                
                result = await process_task_with_peer_review(task_input)
                
                if result['success']:
                    print(f"\n✅ Task completed! Quality Score: {result.get('quality_score', 'N/A')}/10")
                else:
                    print(f"\n❌ Task failed: {result.get('error', 'Unknown error')}")
                
            except KeyboardInterrupt:
                break
            except Exception as e:
                logger.error(f"Error: {str(e)}")
    
    logger.info("👋 Goodbye!")

if __name__ == "__main__":
    asyncio.run(main())
