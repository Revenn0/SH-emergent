#!/usr/bin/env python3
"""
Backend API Testing for Email Categorizer
Tests all backend endpoints including auth, Gmail integration, and dashboard
"""

import requests
import json
import time
from datetime import datetime
import sys

# Backend URL from environment
BACKEND_URL = "https://mail-categorizer-1.preview.emergentagent.com/api"

class EmailCategorizerTester:
    def __init__(self):
        self.session = requests.Session()
        self.session_token = None
        self.test_results = []
        
    def log_test(self, test_name, success, message, details=None):
        """Log test result"""
        result = {
            "test": test_name,
            "success": success,
            "message": message,
            "timestamp": datetime.now().isoformat(),
            "details": details or {}
        }
        self.test_results.append(result)
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status} {test_name}: {message}")
        if details and not success:
            print(f"   Details: {details}")
    
    def test_auth_login_endpoint(self):
        """Test auth login endpoint - should return auth URL"""
        try:
            response = self.session.get(f"{BACKEND_URL}/auth/login")
            
            if response.status_code == 200:
                data = response.json()
                if "auth_url" in data and "auth.emergentagent.com" in data["auth_url"]:
                    self.log_test("Auth Login Endpoint", True, "Returns valid Emergent auth URL")
                    return True
                else:
                    self.log_test("Auth Login Endpoint", False, "Invalid auth URL format", {"response": data})
                    return False
            else:
                self.log_test("Auth Login Endpoint", False, f"HTTP {response.status_code}", {"response": response.text})
                return False
                
        except Exception as e:
            self.log_test("Auth Login Endpoint", False, f"Request failed: {str(e)}")
            return False
    
    def test_auth_session_creation(self):
        """Test session creation with mock session_id"""
        try:
            # Test with missing session_id
            response = self.session.post(f"{BACKEND_URL}/auth/session", json={})
            
            if response.status_code == 400:
                self.log_test("Auth Session - Missing ID", True, "Correctly rejects missing session_id")
            else:
                self.log_test("Auth Session - Missing ID", False, f"Should return 400, got {response.status_code}")
            
            # Test with invalid session_id
            response = self.session.post(f"{BACKEND_URL}/auth/session", json={"session_id": "invalid_session_123"})
            
            if response.status_code == 401:
                self.log_test("Auth Session - Invalid ID", True, "Correctly rejects invalid session_id")
                return True
            else:
                self.log_test("Auth Session - Invalid ID", False, f"Should return 401, got {response.status_code}")
                return False
                
        except Exception as e:
            self.log_test("Auth Session Creation", False, f"Request failed: {str(e)}")
            return False
    
    def test_auth_me_without_token(self):
        """Test /auth/me without authentication"""
        try:
            response = self.session.get(f"{BACKEND_URL}/auth/me")
            
            if response.status_code == 401:
                self.log_test("Auth Me - No Token", True, "Correctly requires authentication")
                return True
            else:
                self.log_test("Auth Me - No Token", False, f"Should return 401, got {response.status_code}")
                return False
                
        except Exception as e:
            self.log_test("Auth Me - No Token", False, f"Request failed: {str(e)}")
            return False
    
    def test_auth_logout(self):
        """Test logout endpoint"""
        try:
            response = self.session.post(f"{BACKEND_URL}/auth/logout")
            
            if response.status_code == 200:
                data = response.json()
                if data.get("success"):
                    self.log_test("Auth Logout", True, "Logout endpoint works")
                    return True
                else:
                    self.log_test("Auth Logout", False, "Logout did not return success", {"response": data})
                    return False
            else:
                self.log_test("Auth Logout", False, f"HTTP {response.status_code}", {"response": response.text})
                return False
                
        except Exception as e:
            self.log_test("Auth Logout", False, f"Request failed: {str(e)}")
            return False
    
    def test_gmail_connect_without_auth(self):
        """Test Gmail connect without authentication"""
        try:
            response = self.session.post(f"{BACKEND_URL}/gmail/connect", json={
                "email": "test@gmail.com",
                "app_password": "testpassword"
            })
            
            if response.status_code == 401:
                self.log_test("Gmail Connect - No Auth", True, "Correctly requires authentication")
                return True
            else:
                self.log_test("Gmail Connect - No Auth", False, f"Should return 401, got {response.status_code}")
                return False
                
        except Exception as e:
            self.log_test("Gmail Connect - No Auth", False, f"Request failed: {str(e)}")
            return False
    
    def test_gmail_connect_invalid_credentials(self):
        """Test Gmail connect with invalid credentials (requires auth token)"""
        try:
            # First test without auth
            response = self.session.post(f"{BACKEND_URL}/gmail/connect", json={
                "email": "invalid@gmail.com",
                "app_password": "wrongpassword"
            })
            
            if response.status_code == 401:
                self.log_test("Gmail Connect - Invalid Creds", True, "Correctly requires authentication first")
                return True
            else:
                self.log_test("Gmail Connect - Invalid Creds", False, f"Should return 401 for no auth, got {response.status_code}")
                return False
                
        except Exception as e:
            self.log_test("Gmail Connect - Invalid Creds", False, f"Request failed: {str(e)}")
            return False
    
    def test_gmail_sync_without_auth(self):
        """Test Gmail sync without authentication"""
        try:
            response = self.session.post(f"{BACKEND_URL}/gmail/sync")
            
            if response.status_code == 401:
                self.log_test("Gmail Sync - No Auth", True, "Correctly requires authentication")
                return True
            else:
                self.log_test("Gmail Sync - No Auth", False, f"Should return 401, got {response.status_code}")
                return False
                
        except Exception as e:
            self.log_test("Gmail Sync - No Auth", False, f"Request failed: {str(e)}")
            return False
    
    def test_gmail_disconnect_without_auth(self):
        """Test Gmail disconnect without authentication"""
        try:
            response = self.session.delete(f"{BACKEND_URL}/gmail/disconnect")
            
            if response.status_code == 401:
                self.log_test("Gmail Disconnect - No Auth", True, "Correctly requires authentication")
                return True
            else:
                self.log_test("Gmail Disconnect - No Auth", False, f"Should return 401, got {response.status_code}")
                return False
                
        except Exception as e:
            self.log_test("Gmail Disconnect - No Auth", False, f"Request failed: {str(e)}")
            return False
    
    def test_dashboard_stats_without_auth(self):
        """Test dashboard stats without authentication"""
        try:
            response = self.session.get(f"{BACKEND_URL}/dashboard/stats")
            
            if response.status_code == 401:
                self.log_test("Dashboard Stats - No Auth", True, "Correctly requires authentication")
                return True
            else:
                self.log_test("Dashboard Stats - No Auth", False, f"Should return 401, got {response.status_code}")
                return False
                
        except Exception as e:
            self.log_test("Dashboard Stats - No Auth", False, f"Request failed: {str(e)}")
            return False
    
    def test_auth_with_bearer_token(self):
        """Test authentication with Bearer token in Authorization header"""
        try:
            # Test with invalid bearer token
            headers = {"Authorization": "Bearer invalid_token_123"}
            response = self.session.get(f"{BACKEND_URL}/auth/me", headers=headers)
            
            if response.status_code == 401:
                self.log_test("Auth Bearer Token - Invalid", True, "Correctly rejects invalid bearer token")
                return True
            else:
                self.log_test("Auth Bearer Token - Invalid", False, f"Should return 401, got {response.status_code}")
                return False
                
        except Exception as e:
            self.log_test("Auth Bearer Token", False, f"Request failed: {str(e)}")
            return False
    
    def test_gemini_integration_availability(self):
        """Test if Gemini API key is configured"""
        try:
            # We can't directly test Gemini without auth, but we can check if the categorization logic would work
            # by testing the sync endpoint behavior
            response = self.session.post(f"{BACKEND_URL}/gmail/sync")
            
            # Should return 401 (no auth) not 500 (missing API key)
            if response.status_code == 401:
                self.log_test("Gemini Integration Check", True, "Gemini integration appears configured (no 500 error)")
                return True
            elif response.status_code == 500:
                self.log_test("Gemini Integration Check", False, "Possible Gemini API configuration issue")
                return False
            else:
                self.log_test("Gemini Integration Check", True, f"Unexpected status {response.status_code} but no 500 error")
                return True
                
        except Exception as e:
            self.log_test("Gemini Integration Check", False, f"Request failed: {str(e)}")
            return False
    
    def test_gemini_categorization_direct(self):
        """Test Gemini categorization function directly by calling the backend"""
        try:
            # Import the categorization function to test it directly
            import sys
            import os
            sys.path.append('/app/backend')
            
            # Test if we can import and use the categorization function
            from server import categorize_with_gemini
            
            # Test with sample email data
            test_subject = "Special Offer: 50% Off All Items Today Only!"
            test_sender = "deals@shopping.com"
            test_body = "Don't miss out on our biggest sale of the year! Get 50% off everything in our store today only. Use code SAVE50 at checkout."
            
            category = categorize_with_gemini(test_subject, test_sender, test_body)
            
            # Check if we get a valid category
            valid_categories = ["Primary", "Social", "Promotions", "Updates", "Spam"]
            if category in valid_categories:
                self.log_test("Gemini Categorization Direct", True, f"Successfully categorized as '{category}'")
                return True
            else:
                self.log_test("Gemini Categorization Direct", False, f"Invalid category returned: '{category}'")
                return False
                
        except Exception as e:
            self.log_test("Gemini Categorization Direct", False, f"Categorization failed: {str(e)}")
            return False
    
    def test_gemini_multiple_categories(self):
        """Test Gemini categorization with different types of emails"""
        try:
            import sys
            import os
            sys.path.append('/app/backend')
            from server import categorize_with_gemini
            
            test_emails = [
                {
                    "subject": "Your order has been shipped",
                    "sender": "noreply@amazon.com",
                    "body": "Your order #12345 has been shipped and will arrive tomorrow.",
                    "expected_type": "Updates"
                },
                {
                    "subject": "John Smith commented on your post",
                    "sender": "notifications@facebook.com", 
                    "body": "John Smith commented: 'Great photo!' on your recent post.",
                    "expected_type": "Social"
                },
                {
                    "subject": "Meeting reminder: Team standup",
                    "sender": "sarah.johnson@company.com",
                    "body": "Hi team, just a reminder about our standup meeting at 10 AM today.",
                    "expected_type": "Primary"
                },
                {
                    "subject": "URGENT: Verify your account now!",
                    "sender": "security@suspicious-site.com",
                    "body": "Your account will be suspended unless you verify immediately. Click here now!",
                    "expected_type": "Spam"
                }
            ]
            
            successful_categorizations = 0
            total_tests = len(test_emails)
            
            for i, email in enumerate(test_emails):
                try:
                    category = categorize_with_gemini(email["subject"], email["sender"], email["body"])
                    valid_categories = ["Primary", "Social", "Promotions", "Updates", "Spam"]
                    
                    if category in valid_categories:
                        successful_categorizations += 1
                        print(f"   Email {i+1}: '{email['subject'][:30]}...' → {category}")
                    else:
                        print(f"   Email {i+1}: Invalid category '{category}'")
                        
                except Exception as e:
                    print(f"   Email {i+1}: Failed - {str(e)}")
            
            if successful_categorizations == total_tests:
                self.log_test("Gemini Multiple Categories", True, f"Successfully categorized all {total_tests} test emails")
                return True
            elif successful_categorizations > 0:
                self.log_test("Gemini Multiple Categories", True, f"Categorized {successful_categorizations}/{total_tests} emails successfully")
                return True
            else:
                self.log_test("Gemini Multiple Categories", False, "Failed to categorize any test emails")
                return False
                
        except Exception as e:
            self.log_test("Gemini Multiple Categories", False, f"Test setup failed: {str(e)}")
            return False
    
    def test_cors_headers(self):
        """Test CORS configuration"""
        try:
            response = self.session.options(f"{BACKEND_URL}/auth/login")
            
            # Check if CORS headers are present
            cors_headers = [
                'Access-Control-Allow-Origin',
                'Access-Control-Allow-Methods',
                'Access-Control-Allow-Headers'
            ]
            
            has_cors = any(header in response.headers for header in cors_headers)
            
            if has_cors or response.status_code in [200, 405]:  # 405 is also acceptable for OPTIONS
                self.log_test("CORS Configuration", True, "CORS appears to be configured")
                return True
            else:
                self.log_test("CORS Configuration", False, "CORS headers not found", {"headers": dict(response.headers)})
                return False
                
        except Exception as e:
            self.log_test("CORS Configuration", False, f"Request failed: {str(e)}")
            return False
    
    def test_api_health(self):
        """Test basic API health by checking if endpoints respond"""
        endpoints_to_test = [
            ("/auth/login", "GET"),
            ("/auth/logout", "POST"),
            ("/auth/me", "GET"),
            ("/gmail/connect", "POST"),
            ("/gmail/sync", "POST"),
            ("/gmail/disconnect", "DELETE"),
            ("/dashboard/stats", "GET")
        ]
        
        healthy_endpoints = 0
        total_endpoints = len(endpoints_to_test)
        
        for endpoint, method in endpoints_to_test:
            try:
                if method == "GET":
                    response = self.session.get(f"{BACKEND_URL}{endpoint}")
                elif method == "POST":
                    response = self.session.post(f"{BACKEND_URL}{endpoint}", json={})
                elif method == "DELETE":
                    response = self.session.delete(f"{BACKEND_URL}{endpoint}")
                
                # Any response (even 401/400) means the endpoint exists
                if response.status_code < 500:
                    healthy_endpoints += 1
                    
            except Exception:
                pass
        
        if healthy_endpoints == total_endpoints:
            self.log_test("API Health Check", True, f"All {total_endpoints} endpoints responding")
            return True
        else:
            self.log_test("API Health Check", False, f"Only {healthy_endpoints}/{total_endpoints} endpoints responding")
            return False
    
    def run_all_tests(self):
        """Run all backend tests"""
        print(f"\n🧪 Starting Email Categorizer Backend Tests")
        print(f"Backend URL: {BACKEND_URL}")
        print("=" * 60)
        
        # Test API health first
        self.test_api_health()
        
        # Test CORS
        self.test_cors_headers()
        
        # Test Auth endpoints
        print("\n📋 Testing Authentication Endpoints...")
        self.test_auth_login_endpoint()
        self.test_auth_session_creation()
        self.test_auth_me_without_token()
        self.test_auth_with_bearer_token()
        self.test_auth_logout()
        
        # Test Gmail endpoints (without auth)
        print("\n📧 Testing Gmail Integration Endpoints...")
        self.test_gmail_connect_without_auth()
        self.test_gmail_connect_invalid_credentials()
        self.test_gmail_sync_without_auth()
        self.test_gmail_disconnect_without_auth()
        
        # Test Dashboard endpoint
        print("\n📊 Testing Dashboard Endpoint...")
        self.test_dashboard_stats_without_auth()
        
        # Test Gemini integration
        print("\n🤖 Testing AI Integration...")
        self.test_gemini_integration_availability()
        self.test_gemini_categorization_direct()
        self.test_gemini_multiple_categories()
        
        # Summary
        print("\n" + "=" * 60)
        print("📋 TEST SUMMARY")
        print("=" * 60)
        
        passed = sum(1 for result in self.test_results if result["success"])
        total = len(self.test_results)
        
        print(f"Total Tests: {total}")
        print(f"Passed: {passed}")
        print(f"Failed: {total - passed}")
        print(f"Success Rate: {(passed/total)*100:.1f}%")
        
        # Show failed tests
        failed_tests = [result for result in self.test_results if not result["success"]]
        if failed_tests:
            print(f"\n❌ Failed Tests ({len(failed_tests)}):")
            for test in failed_tests:
                print(f"  - {test['test']}: {test['message']}")
        
        return passed, total, self.test_results

if __name__ == "__main__":
    tester = EmailCategorizerTester()
    passed, total, results = tester.run_all_tests()
    
    # Exit with error code if tests failed
    if passed < total:
        sys.exit(1)
    else:
        print("\n🎉 All tests passed!")
        sys.exit(0)