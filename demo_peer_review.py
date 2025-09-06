#!/usr/bin/env python3
"""
Demo script for the peer review system.
"""

import asyncio
import logging
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def demo_peer_review_system():
    """Demonstrate the peer review system with a simple task"""
    
    print("🤖 Coding Agent - Peer Review System Demo")
    print("=" * 50)
    
    # Import here to ensure environment is loaded
    from main_peer_review import process_task_with_peer_review
    
    # Demo task
    task_description = "Create a Python function that calculates the factorial of a number with proper error handling"
    
    print(f"📝 Task: {task_description}")
    print("\n🔄 Processing through peer review workflow...")
    print("   1. Decomposer breaks down the task")
    print("   2. Code Generator validates decomposition and implements")
    print("   3. Testing Agent validates code and creates tests")
    print("   4. Quality Agent validates tests and assesses quality")
    print("\n⏳ This may take a few minutes...\n")
    
    try:
        result = await process_task_with_peer_review(
            task_description=task_description,
            language="python",
            priority=85
        )
        
        print("\n" + "=" * 50)
        print("📊 RESULTS")
        print("=" * 50)
        
        if result['success']:
            print("✅ Task completed successfully!")
            print(f"📊 Quality Score: {result.get('quality_score', 'N/A')}/10")
            print(f"🎯 Recommendation: {result.get('recommendation', 'N/A')}")
            
            # Show feedback summary
            feedback_summary = result.get('feedback_summary', {})
            if feedback_summary.get('total_feedback_instances', 0) > 0:
                print(f"\n💬 Peer Review Activity:")
                print(f"   Total feedback instances: {feedback_summary['total_feedback_instances']}")
                print(f"   Retry success rate: {feedback_summary['retry_success_rate']:.1%}")
                
                for agent, feedback_list in feedback_summary.get('feedback_by_agent', {}).items():
                    print(f"   {agent}: {len(feedback_list)} feedback instances")
            else:
                print("\n✨ No peer review feedback needed - all agents validated each other successfully!")
            
            print(f"\n📁 Generated Files:")
            print(f"   Implementation: implementations/{result['task_id']}_*.py")
            print(f"   Tests: tests/test_{result['task_id']}.py")
            print(f"   Quality Report: quality_reports/quality_report_{result['task_id']}.md")
            
        else:
            print("❌ Task failed!")
            print(f"Error: {result.get('error', 'Unknown error')}")
            print(f"Failed at: {result.get('failed_at', 'Unknown stage')}")
        
        print(f"\n⏱️ Total execution time: {result.get('execution_time', 0):.1f} seconds")
        
    except Exception as e:
        print(f"❌ Demo failed: {str(e)}")
        import traceback
        traceback.print_exc()
    
    print("\n🌐 Web Dashboard:")
    print("   Start with: python web_dashboard.py")
    print("   Then visit: http://localhost:8000")
    print("   Check 'Peer Review' tab for feedback analysis")
    
    print("\n🎉 Demo completed!")

if __name__ == "__main__":
    asyncio.run(demo_peer_review_system())
