#!/usr/bin/env python3
"""
Test script to demonstrate the difference between old and new prompt approaches
"""

from agents.feedback_parser import FeedbackParser

def test_prompt_transformation():
    """Test how feedback gets transformed into clean prompts"""
    
    parser = FeedbackParser()
    
    # Real feedback from our system
    feedback = """The test suite covers a good range of email formats and invalid inputs. 
    However, it lacks tests for more complex scenarios such as internationalized domains 
    and quoted strings. Additionally, the test suite could benefit from performance testing 
    to ensure the function scales well with large inputs. The execution issues need 
    immediate attention to ensure the test suite runs successfully."""
    
    original_task = "Create a simple Python function that validates email addresses using regex"
    
    print("🔄 PROMPT TRANSFORMATION COMPARISON")
    print("=" * 60)
    
    print("\n📝 ORIGINAL TASK:")
    print(f'"{original_task}"')
    
    print("\n💬 RAW FEEDBACK:")
    print(f'"{feedback}"')
    
    print("\n❌ OLD APPROACH (Raw Feedback Embedded):")
    old_prompt = f"""
    ORIGINAL TASK: {original_task}
    
    FEEDBACK FROM DOWNSTREAM AGENT: {feedback}
    
    Please address the feedback above while completing the original task.
    """
    print(f'"{old_prompt.strip()}"')
    
    print("\n✅ NEW APPROACH (Clean Enhanced Prompt):")
    enhanced_task = parser.create_clean_prompt_enhancement(original_task, feedback, "testing")
    print(f'"{enhanced_task}"')
    
    print("\n🎯 PARSED IMPROVEMENTS:")
    improvements = parser.parse_feedback(feedback, "testing")
    for i, imp in enumerate(improvements, 1):
        print(f"{i}. {imp.category}: {imp.improvement} (priority: {imp.priority})")
    
    print("\n" + "=" * 60)
    print("🎉 RESULT: Agent gets clean, specific requirements without knowing it's a retry!")

if __name__ == "__main__":
    test_prompt_transformation()
