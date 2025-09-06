#!/usr/bin/env python3
"""
Test script for the peer review system.
"""

import os
import sys
import asyncio
import logging
from datetime import datetime

# Add project root to Python path
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

from models.task import Task, TaskStatus
from agents.feedback_orchestrator import FeedbackOrchestrator
from models.validation import FeedbackTracker

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def test_basic_workflow():
    """Test basic peer review workflow"""
    logger.info("🧪 Testing basic peer review workflow")
    
    # Create a simple test task
    task = Task(
        description="Create a simple Python function that adds two numbers and returns the result",
        language="python",
        priority=80
    )
    
    # Initialize orchestrator
    orchestrator = FeedbackOrchestrator()
    
    try:
        # Process task through peer review workflow
        result = await orchestrator.process_task_with_feedback(task)
        
        logger.info(f"✅ Workflow completed: {result['success']}")
        logger.info(f"📊 Quality Score: {result.get('quality_score', 'N/A')}")
        logger.info(f"🎯 Recommendation: {result.get('recommendation', 'N/A')}")
        
        # Print feedback summary
        feedback_summary = result.get('feedback_summary', {})
        if feedback_summary.get('total_feedback_instances', 0) > 0:
            logger.info(f"💬 Total Feedback Instances: {feedback_summary['total_feedback_instances']}")
            logger.info(f"🔄 Retry Success Rate: {feedback_summary['retry_success_rate']:.1%}")
        
        return result
        
    except Exception as e:
        logger.error(f"❌ Workflow failed: {str(e)}")
        return None

async def test_validation_failure():
    """Test validation failure and retry mechanism"""
    logger.info("🧪 Testing validation failure scenario")
    
    # Create a task that might cause validation issues
    task = Task(
        description="Build a complex machine learning model with advanced features",
        language="python",
        priority=90
    )
    
    orchestrator = FeedbackOrchestrator()
    
    try:
        result = await orchestrator.process_task_with_feedback(task)
        
        logger.info(f"✅ Complex task completed: {result['success']}")
        
        # Check for feedback instances
        feedback_summary = result.get('feedback_summary', {})
        if feedback_summary.get('total_feedback_instances', 0) > 0:
            logger.info("💬 Feedback was generated during processing:")
            for agent, feedback_list in feedback_summary.get('feedback_by_agent', {}).items():
                logger.info(f"  {agent}: {len(feedback_list)} feedback instances")
        
        return result
        
    except Exception as e:
        logger.error(f"❌ Complex task failed: {str(e)}")
        return None

def test_feedback_tracking():
    """Test feedback tracking functionality"""
    logger.info("🧪 Testing feedback tracking")
    
    tracker = FeedbackTracker()
    
    # Check if we have any feedback data
    stats = tracker.get_feedback_stats()
    recent_feedback = tracker.get_recent_feedback(limit=5)
    
    logger.info(f"📊 Feedback Statistics:")
    logger.info(f"  Agents with feedback: {len(stats)}")
    logger.info(f"  Recent feedback entries: {len(recent_feedback)}")
    
    if stats:
        for agent, agent_stats in stats.items():
            logger.info(f"  {agent}: {agent_stats['received_count']} feedback instances")
    
    if recent_feedback:
        logger.info("📝 Recent feedback samples:")
        for feedback in recent_feedback[:3]:
            logger.info(f"  {feedback['from_agent']} → {feedback['to_agent']}: {feedback['feedback'][:50]}...")

def test_web_dashboard():
    """Test web dashboard functionality"""
    logger.info("🧪 Testing web dashboard")
    
    try:
        # Import dashboard functions
        from web_dashboard import generate_feedback_dashboard, generate_peer_review_stats
        
        # Test feedback dashboard generation
        dashboard_html = generate_feedback_dashboard()
        logger.info(f"✅ Feedback dashboard generated: {len(dashboard_html)} characters")
        
        # Test stats generation
        stats_html = generate_peer_review_stats()
        logger.info(f"✅ Peer review stats generated: {len(stats_html)} characters")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Dashboard test failed: {str(e)}")
        return False

async def run_comprehensive_test():
    """Run comprehensive test suite"""
    logger.info("🚀 Starting comprehensive peer review system test")
    
    # Check API key
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key or not api_key.startswith('sk-'):
        logger.error("❌ No valid OpenAI API key found. Please set OPENAI_API_KEY environment variable.")
        return
    
    logger.info("✅ API key found")
    
    # Test 1: Basic workflow
    logger.info("\n" + "="*50)
    result1 = await test_basic_workflow()
    
    # Test 2: Validation failure scenario
    logger.info("\n" + "="*50)
    result2 = await test_validation_failure()
    
    # Test 3: Feedback tracking
    logger.info("\n" + "="*50)
    test_feedback_tracking()
    
    # Test 4: Web dashboard
    logger.info("\n" + "="*50)
    dashboard_ok = test_web_dashboard()
    
    # Summary
    logger.info("\n" + "="*50)
    logger.info("📋 TEST SUMMARY")
    logger.info(f"  Basic workflow: {'✅ PASS' if result1 and result1['success'] else '❌ FAIL'}")
    logger.info(f"  Complex workflow: {'✅ PASS' if result2 and result2['success'] else '❌ FAIL'}")
    logger.info(f"  Web dashboard: {'✅ PASS' if dashboard_ok else '❌ FAIL'}")
    
    if result1 and result1['success']:
        logger.info(f"  Quality score achieved: {result1.get('quality_score', 'N/A')}")
    
    logger.info("\n🎉 Peer review system test completed!")

def main():
    """Main test function"""
    try:
        # Load environment variables
        from dotenv import load_dotenv
        load_dotenv()
        
        # Run tests
        asyncio.run(run_comprehensive_test())
        
    except KeyboardInterrupt:
        logger.info("\n⏹️ Test interrupted by user")
    except Exception as e:
        logger.error(f"❌ Test suite failed: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
