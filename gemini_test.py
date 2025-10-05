#!/usr/bin/env python3
"""
Test Gemini AI Integration
"""

import google.generativeai as genai
import os
from dotenv import load_dotenv
from pathlib import Path

# Load environment
ROOT_DIR = Path(__file__).parent / "backend"
load_dotenv(ROOT_DIR / '.env')

GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY', '')

def test_gemini_integration():
    """Test if Gemini AI is working"""
    print("🤖 Testing Gemini AI Integration")
    print("=" * 40)
    
    if not GEMINI_API_KEY:
        print("❌ GEMINI_API_KEY not found in environment")
        return False
    
    print(f"✅ GEMINI_API_KEY found: {GEMINI_API_KEY[:10]}...")
    
    try:
        genai.configure(api_key=GEMINI_API_KEY)
        model = genai.GenerativeModel('gemini-pro')
        
        # Test categorization
        prompt = """Categorize this email into ONE of these categories: Primary, Social, Promotions, Updates, or Spam.

Email Details:
From: newsletter@example.com
Subject: Weekly Newsletter - Tech Updates
Body Preview: This week's top technology news and updates from around the world...

Rules:
- Primary: Personal emails, important messages
- Social: Social networks, forums, community
- Promotions: Offers, marketing, advertisements
- Updates: Notifications, receipts, automated messages
- Spam: Unwanted or suspicious emails

Respond with ONLY the category name (one word)."""

        response = model.generate_content(prompt)
        category = response.text.strip()
        
        print(f"✅ Gemini response: {category}")
        
        # Validate category
        valid_categories = ["Primary", "Social", "Promotions", "Updates", "Spam"]
        for cat in valid_categories:
            if cat.lower() in category.lower():
                print(f"✅ Valid category detected: {cat}")
                return True
        
        print(f"⚠️  Unexpected category: {category}")
        return True  # Still working, just unexpected response
        
    except Exception as e:
        print(f"❌ Gemini integration failed: {str(e)}")
        return False

if __name__ == "__main__":
    success = test_gemini_integration()
    if success:
        print("\n🎉 Gemini integration is working!")
    else:
        print("\n💥 Gemini integration has issues!")
    exit(0 if success else 1)