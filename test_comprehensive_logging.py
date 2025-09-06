#!/usr/bin/env python3
"""
Test comprehensive logging system
"""

import asyncio
import logging
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def test_logging_system():
    """Test the comprehensive logging system"""
    
    print("🧪 Testing Comprehensive Logging System")
    print("=" * 50)
    
    # Import here to ensure environment is loaded
    from main_peer_review import process_task_with_peer_review
    from models.prompt_logger import prompt_logger
    
    # Simple task to test logging
    task_description = "Create a Python function that calculates the square of a number"
    
    print(f"📝 Task: {task_description}")
    print("\n🔄 Processing with comprehensive logging...")
    
    try:
        result = await process_task_with_peer_review(
            task_description=task_description,
            language="python",
            priority=70
        )
        
        print(f"\n✅ Task completed: {result['success']}")
        
        # Show logging analysis
        print("\n📊 LOGGING ANALYSIS")
        print("=" * 30)
        
        # Get success rates for each agent
        agents = ["decomposer", "code_generation", "testing", "quality_assessment"]
        
        for agent in agents:
            success_rate = prompt_logger.get_prompt_success_rate(agent, hours=1)
            feedback_analysis = prompt_logger.get_feedback_analysis(agent)
            
            print(f"\n🤖 {agent.upper()}:")
            print(f"  First-shot success rate: {success_rate['success_rate']:.1%}")
            print(f"  Total attempts: {success_rate['total_attempts']}")
            print(f"  Retry attempts: {success_rate['retry_attempts']}")
            
            if feedback_analysis['total_feedback'] > 0:
                print(f"  Received feedback: {feedback_analysis['total_feedback']} times")
                print(f"  Avg feedback confidence: {feedback_analysis['avg_confidence']:.2f}")
                print(f"  Retry rate: {feedback_analysis['retry_rate']:.1%}")
                
                if feedback_analysis['common_themes']:
                    top_theme = feedback_analysis['common_themes'][0]
                    print(f"  Top feedback theme: '{top_theme['theme']}' ({top_theme['count']} times)")
        
        # Export detailed analysis
        prompt_logger.export_analysis("test_analysis.json")
        print(f"\n📄 Detailed analysis exported to test_analysis.json")
        
        # Show what files were created
        print(f"\n📁 Log Files Created:")
        from pathlib import Path
        
        prompt_logs = list(Path("logs/prompts").glob("*.jsonl"))
        feedback_logs = list(Path("logs/feedback").glob("*.jsonl"))
        
        for log_file in prompt_logs:
            print(f"  📝 {log_file}")
        
        for log_file in feedback_logs:
            print(f"  💬 {log_file}")
        
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

def show_sample_logs():
    """Show sample of what gets logged"""
    print("\n📋 SAMPLE LOG ENTRIES")
    print("=" * 30)
    
    from pathlib import Path
    import json
    
    # Show sample prompt log
    prompt_logs = list(Path("logs/prompts").glob("*.jsonl"))
    if prompt_logs:
        print("\n📝 PROMPT LOG SAMPLE:")
        with open(prompt_logs[0]) as f:
            lines = f.readlines()
            if lines:
                sample = json.loads(lines[0])
                print(f"  Task ID: {sample['task_id']}")
                print(f"  Agent: {sample['agent_type']}")
                print(f"  Attempt: #{sample['attempt_number']}")
                print(f"  Success: {sample['success']}")
                print(f"  Execution time: {sample['execution_time']:.1f}s")
                print(f"  Prompt length: {len(sample['prompt'])} chars")
                print(f"  Response length: {len(sample['response'])} chars")
                if sample['received_feedback']:
                    print(f"  Feedback confidence: {sample['feedback_confidence']:.2f}")
                    print(f"  Needs retry: {sample['needs_retry']}")
    
    # Show sample feedback log
    feedback_logs = list(Path("logs/feedback").glob("*.jsonl"))
    if feedback_logs:
        print("\n💬 FEEDBACK LOG SAMPLE:")
        with open(feedback_logs[0]) as f:
            lines = f.readlines()
            if lines:
                sample = json.loads(lines[-1])  # Get latest
                print(f"  From: {sample['from_agent']} → To: {sample['to_agent']}")
                print(f"  Task ID: {sample['task_id']}")
                print(f"  Confidence: {sample['validation_confidence']:.2f}")
                print(f"  Feedback: {sample['feedback'][:100]}...")

async def main():
    """Main test function"""
    success = await test_logging_system()
    
    if success:
        show_sample_logs()
        print("\n🎉 Comprehensive logging system is working!")
        print("\nNow you can analyze:")
        print("  📊 First-shot success rates by agent")
        print("  💬 Feedback patterns and themes")
        print("  🔄 Prompt-response-feedback cycles")
        print("  📈 Performance trends over time")
    else:
        print("\n❌ Logging system needs debugging")

if __name__ == "__main__":
    asyncio.run(main())
