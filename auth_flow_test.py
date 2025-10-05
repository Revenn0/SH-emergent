#!/usr/bin/env python3
"""
Advanced Auth Flow Testing for Email Categorizer
Tests authenticated endpoints with mock session tokens
"""

import requests
import json
from datetime import datetime, timezone, timedelta
import uuid

BACKEND_URL = "https://mail-categorizer-1.preview.emergentagent.com/api"

class AuthFlowTester:
    def __init__(self):
        self.session = requests.Session()
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
    
    def test_gmail_connect_with_invalid_credentials(self):
        """Test Gmail connect with invalid credentials but valid auth"""
        try:
            # Create a mock session token (this won't work for real auth but tests the endpoint)
            mock_token = str(uuid.uuid4())
            headers = {"Authorization": f"Bearer {mock_token}"}
            
            response = self.session.post(f"{BACKEND_URL}/gmail/connect", 
                                       json={
                                           "email": "test@gmail.com",
                                           "app_password": "invalid_password"
                                       },
                                       headers=headers)
            
            # Should return 401 because the session token is invalid
            if response.status_code == 401:
                self.log_test("Gmail Connect - Mock Auth", True, "Correctly validates session token before Gmail connection")
                return True
            else:
                self.log_test("Gmail Connect - Mock Auth", False, f"Expected 401, got {response.status_code}")
                return False
                
        except Exception as e:
            self.log_test("Gmail Connect - Mock Auth", False, f"Request failed: {str(e)}")
            return False
    
    def test_dashboard_stats_structure(self):
        """Test dashboard stats endpoint structure with mock auth"""
        try:
            mock_token = str(uuid.uuid4())
            headers = {"Authorization": f"Bearer {mock_token}"}
            
            response = self.session.get(f"{BACKEND_URL}/dashboard/stats", headers=headers)
            
            # Should return 401 for invalid token
            if response.status_code == 401:
                self.log_test("Dashboard Stats Structure", True, "Correctly validates auth before returning stats")
                return True
            else:
                self.log_test("Dashboard Stats Structure", False, f"Expected 401, got {response.status_code}")
                return False
                
        except Exception as e:
            self.log_test("Dashboard Stats Structure", False, f"Request failed: {str(e)}")
            return False
    
    def test_session_validation_edge_cases(self):
        """Test various session validation edge cases"""
        test_cases = [
            ("Empty Bearer", "Bearer ", 401),
            ("Malformed Bearer", "Bearer", 401),
            ("Invalid Bearer", "Bearer invalid_token_123", 401),
            ("Wrong Auth Type", "Basic dGVzdDp0ZXN0", 401),
            ("No Auth Header", None, 401)
        ]
        
        passed = 0
        total = len(test_cases)
        
        for case_name, auth_header, expected_status in test_cases:
            try:
                headers = {}
                if auth_header:
                    headers["Authorization"] = auth_header
                
                response = self.session.get(f"{BACKEND_URL}/auth/me", headers=headers)
                
                if response.status_code == expected_status:
                    passed += 1
                    print(f"  ✅ {case_name}: Correct status {response.status_code}")
                else:
                    print(f"  ❌ {case_name}: Expected {expected_status}, got {response.status_code}")
                    
            except Exception as e:
                print(f"  ❌ {case_name}: Request failed - {str(e)}")
        
        success = passed == total
        self.log_test("Session Validation Edge Cases", success, f"{passed}/{total} edge cases handled correctly")
        return success
    
    def test_email_sync_without_connection(self):
        """Test email sync when no Gmail is connected"""
        try:
            mock_token = str(uuid.uuid4())
            headers = {"Authorization": f"Bearer {mock_token}"}
            
            response = self.session.post(f"{BACKEND_URL}/gmail/sync", headers=headers)
            
            # Should return 401 for invalid session token
            if response.status_code == 401:
                self.log_test("Email Sync - No Connection", True, "Correctly validates auth before checking Gmail connection")
                return True
            else:
                self.log_test("Email Sync - No Connection", False, f"Expected 401, got {response.status_code}")
                return False
                
        except Exception as e:
            self.log_test("Email Sync - No Connection", False, f"Request failed: {str(e)}")
            return False
    
    def test_request_body_validation(self):
        """Test request body validation for various endpoints"""
        test_cases = [
            ("Gmail Connect - Empty Body", "/gmail/connect", "POST", {}, 401),  # Should fail auth first
            ("Gmail Connect - Missing Email", "/gmail/connect", "POST", {"app_password": "test"}, 401),
            ("Gmail Connect - Missing Password", "/gmail/connect", "POST", {"email": "test@gmail.com"}, 401),
            ("Auth Session - Empty Body", "/auth/session", "POST", {}, 400),
            ("Auth Session - Invalid JSON", "/auth/session", "POST", "invalid", 400),
        ]
        
        passed = 0
        total = len(test_cases)
        
        for case_name, endpoint, method, body, expected_status in test_cases:
            try:
                url = f"{BACKEND_URL}{endpoint}"
                
                if method == "POST":
                    if isinstance(body, str):
                        # Test invalid JSON
                        response = self.session.post(url, data=body, headers={"Content-Type": "application/json"})
                    else:
                        response = self.session.post(url, json=body)
                
                if response.status_code == expected_status:
                    passed += 1
                    print(f"  ✅ {case_name}: Correct status {response.status_code}")
                else:
                    print(f"  ❌ {case_name}: Expected {expected_status}, got {response.status_code}")
                    
            except Exception as e:
                print(f"  ❌ {case_name}: Request failed - {str(e)}")
        
        success = passed == total
        self.log_test("Request Body Validation", success, f"{passed}/{total} validation cases handled correctly")
        return success
    
    def test_http_methods(self):
        """Test correct HTTP methods for endpoints"""
        test_cases = [
            ("Auth Login - POST", "/auth/login", "POST", 405),  # Should be GET
            ("Auth Me - POST", "/auth/me", "POST", 405),  # Should be GET
            ("Gmail Connect - GET", "/gmail/connect", "GET", 405),  # Should be POST
            ("Gmail Sync - GET", "/gmail/sync", "GET", 405),  # Should be POST
            ("Dashboard Stats - POST", "/dashboard/stats", "POST", 405),  # Should be GET
        ]
        
        passed = 0
        total = len(test_cases)
        
        for case_name, endpoint, method, expected_status in test_cases:
            try:
                url = f"{BACKEND_URL}{endpoint}"
                
                if method == "GET":
                    response = self.session.get(url)
                elif method == "POST":
                    response = self.session.post(url, json={})
                
                if response.status_code == expected_status:
                    passed += 1
                    print(f"  ✅ {case_name}: Correct status {response.status_code}")
                else:
                    print(f"  ❌ {case_name}: Expected {expected_status}, got {response.status_code}")
                    
            except Exception as e:
                print(f"  ❌ {case_name}: Request failed - {str(e)}")
        
        success = passed == total
        self.log_test("HTTP Methods", success, f"{passed}/{total} method validations correct")
        return success
    
    def run_advanced_tests(self):
        """Run all advanced authentication and endpoint tests"""
        print(f"\n🔐 Advanced Email Categorizer Backend Tests")
        print(f"Backend URL: {BACKEND_URL}")
        print("=" * 60)
        
        print("\n🔑 Testing Authentication Edge Cases...")
        self.test_session_validation_edge_cases()
        
        print("\n📧 Testing Gmail Integration...")
        self.test_gmail_connect_with_invalid_credentials()
        self.test_email_sync_without_connection()
        
        print("\n📊 Testing Dashboard...")
        self.test_dashboard_stats_structure()
        
        print("\n🔍 Testing Request Validation...")
        self.test_request_body_validation()
        
        print("\n🌐 Testing HTTP Methods...")
        self.test_http_methods()
        
        # Summary
        print("\n" + "=" * 60)
        print("📋 ADVANCED TEST SUMMARY")
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
    tester = AuthFlowTester()
    passed, total, results = tester.run_advanced_tests()
    
    if passed < total:
        exit(1)
    else:
        print("\n🎉 All advanced tests passed!")
        exit(0)