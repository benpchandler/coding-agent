#!/usr/bin/env python3
"""
Test script to verify the enhanced dashboard features work
"""

import requests
import time

def test_dashboard_endpoints():
    """Test all the new dashboard endpoints"""
    
    base_url = "http://localhost:8000"
    
    endpoints = [
        ("/", "Main Dashboard"),
        ("/peer_review_console", "🔄 Peer Review Console"),
        ("/prompt_analytics", "📊 Prompt Analytics"),
        ("/feedback_dashboard", "💬 Feedback Dashboard"),
        ("/peer_review_stats", "📈 Peer Review Stats"),
        ("/api_key_settings", "⚙️ API Settings")
    ]
    
    print("🧪 Testing Enhanced Dashboard Features")
    print("=" * 50)
    
    for endpoint, name in endpoints:
        try:
            print(f"\n🔍 Testing {name} ({endpoint})")
            response = requests.get(f"{base_url}{endpoint}", timeout=10)
            
            if response.status_code == 200:
                content_length = len(response.text)
                print(f"   ✅ SUCCESS - {content_length} characters loaded")
                
                # Check for key content
                if "peer_review_console" in endpoint:
                    if "Peer Review Console" in response.text and "Live Statistics" in response.text:
                        print("   ✅ Console content verified")
                    else:
                        print("   ⚠️ Console content missing")
                
                elif "prompt_analytics" in endpoint:
                    if "Prompt Analytics" in response.text and "Agent Performance" in response.text:
                        print("   ✅ Analytics content verified")
                    else:
                        print("   ⚠️ Analytics content missing")
                
                elif "feedback_dashboard" in endpoint:
                    if "Feedback Dashboard" in response.text:
                        print("   ✅ Feedback content verified")
                    else:
                        print("   ⚠️ Feedback content missing")
                        
            else:
                print(f"   ❌ FAILED - Status code: {response.status_code}")
                
        except requests.exceptions.RequestException as e:
            print(f"   ❌ ERROR - {str(e)}")
        
        time.sleep(0.5)  # Be nice to the server
    
    print(f"\n🎉 Dashboard testing completed!")
    print(f"Visit {base_url} to see the enhanced dashboard")

def show_dashboard_features():
    """Show what features are available"""
    print("\n📋 ENHANCED DASHBOARD FEATURES")
    print("=" * 40)
    
    features = [
        "🔄 Peer Review Console - Interactive peer review system",
        "📊 Prompt Analytics - First-shot success rate analysis", 
        "💬 Feedback Dashboard - Agent feedback history",
        "📈 Peer Review Stats - Detailed statistics",
        "🎯 Live Performance Monitoring - Real-time agent metrics",
        "🚀 Task Testing Interface - Test peer review on demand",
        "📋 Feedback Pattern Analysis - Common themes and issues",
        "⚡ Quick Actions - Easy access to key functions"
    ]
    
    for feature in features:
        print(f"  {feature}")
    
    print(f"\n🌐 Access at: http://localhost:8000")

if __name__ == "__main__":
    print("🚀 Starting dashboard feature test...")
    print("Make sure the dashboard is running: python web_dashboard.py")
    
    # Wait a moment for user to start dashboard if needed
    input("\nPress Enter when dashboard is running...")
    
    test_dashboard_endpoints()
    show_dashboard_features()
    
    print("\n💡 TIP: The dashboard now showcases the peer review system!")
    print("   - Navigate to 'Peer Review' to see the console")
    print("   - Check 'Analytics' for performance insights")
    print("   - View 'Feedback History' for detailed agent interactions")
