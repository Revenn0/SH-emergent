#!/usr/bin/env python3
"""
Backend Smoke Tests for Alert Tracker System
Tests the Neon-only setup with cookie-based authentication
"""

import requests
import json
import sys
from datetime import datetime

# Get backend URL from frontend .env
def get_backend_url():
    try:
        with open('/app/frontend/.env', 'r') as f:
            for line in f:
                if line.startswith('REACT_APP_BACKEND_URL='):
                    return line.split('=', 1)[1].strip()
    except Exception as e:
        print(f"Error reading frontend .env: {e}")
        return None

BASE_URL = get_backend_url()
if not BASE_URL:
    print("ERROR: Could not get REACT_APP_BACKEND_URL from frontend/.env")
    sys.exit(1)

API_URL = f"{BASE_URL}/api"
print(f"Testing backend at: {API_URL}")

class BackendTester:
    def __init__(self):
        self.session = requests.Session()
        self.test_results = []
        
    def log_test(self, test_name, success, message, response=None):
        """Log test result"""
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status} {test_name}: {message}")
        
        result = {
            "test": test_name,
            "success": success,
            "message": message,
            "timestamp": datetime.now().isoformat()
        }
        
        if response:
            result["status_code"] = response.status_code
            result["headers"] = dict(response.headers)
            
        self.test_results.append(result)
        return success
    
    def test_login_authentication(self):
        """Test 1: POST /api/auth/login with admin/dimension credentials"""
        print("\n=== Test 1: Login Authentication ===")
        
        try:
            login_data = {
                "username": "admin",
                "password": "dimension"
            }
            
            response = self.session.post(f"{API_URL}/auth/login", json=login_data)
            
            if response.status_code == 200:
                data = response.json()
                
                # Check for user object
                if "user" not in data:
                    return self.log_test("Login Auth", False, "Response missing 'user' object", response)
                
                user = data["user"]
                required_fields = ["id", "username", "email"]
                missing_fields = [field for field in required_fields if field not in user]
                
                if missing_fields:
                    return self.log_test("Login Auth", False, f"User object missing fields: {missing_fields}", response)
                
                # Check for Set-Cookie headers
                set_cookie_headers = [h for h in response.headers.keys() if h.lower() == 'set-cookie']
                if not set_cookie_headers and 'Set-Cookie' not in response.headers:
                    return self.log_test("Login Auth", False, "No Set-Cookie headers found", response)
                
                # Verify username matches
                if user["username"] != "admin":
                    return self.log_test("Login Auth", False, f"Expected username 'admin', got '{user['username']}'", response)
                
                return self.log_test("Login Auth", True, f"Login successful, user: {user['username']}, cookies set", response)
            
            else:
                return self.log_test("Login Auth", False, f"Login failed with status {response.status_code}: {response.text}", response)
                
        except Exception as e:
            return self.log_test("Login Auth", False, f"Exception during login: {str(e)}")
    
    def test_alerts_categories(self):
        """Test 2: GET /api/alerts/categories with auth cookie"""
        print("\n=== Test 2: Alerts Categories with Auth ===")
        
        try:
            response = self.session.get(f"{API_URL}/alerts/categories")
            
            if response.status_code == 200:
                data = response.json()
                
                if "categories" not in data:
                    return self.log_test("Alerts Categories", False, "Response missing 'categories' array", response)
                
                categories = data["categories"]
                if not isinstance(categories, list):
                    return self.log_test("Alerts Categories", False, "Categories is not an array", response)
                
                if len(categories) == 0:
                    return self.log_test("Alerts Categories", False, "Categories array is empty", response)
                
                return self.log_test("Alerts Categories", True, f"Categories retrieved successfully, count: {len(categories)}", response)
            
            else:
                return self.log_test("Alerts Categories", False, f"Categories request failed with status {response.status_code}: {response.text}", response)
                
        except Exception as e:
            return self.log_test("Alerts Categories", False, f"Exception during categories request: {str(e)}")
    
    def test_alerts_list_basic(self):
        """Test 3: GET /api/alerts/list with limit=5"""
        print("\n=== Test 3: Alerts List Basic (limit=5) ===")
        
        try:
            response = self.session.get(f"{API_URL}/alerts/list?limit=5")
            
            if response.status_code == 200:
                data = response.json()
                
                if "alerts" not in data:
                    return self.log_test("Alerts List Basic", False, "Response missing 'alerts' array", response)
                
                alerts = data["alerts"]
                if not isinstance(alerts, list):
                    return self.log_test("Alerts List Basic", False, "Alerts is not an array", response)
                
                # Check created_at ISO format for each alert
                for i, alert in enumerate(alerts):
                    if "created_at" not in alert:
                        return self.log_test("Alerts List Basic", False, f"Alert {i} missing 'created_at' field", response)
                    
                    created_at = alert["created_at"]
                    if created_at is None:
                        continue  # Allow null values
                    
                    # Try to parse as ISO format
                    try:
                        datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                    except (ValueError, AttributeError):
                        return self.log_test("Alerts List Basic", False, f"Alert {i} 'created_at' not in ISO format: {created_at}", response)
                
                return self.log_test("Alerts List Basic", True, f"Alerts list retrieved successfully, count: {len(alerts)}, all have valid created_at", response)
            
            else:
                return self.log_test("Alerts List Basic", False, f"Alerts list request failed with status {response.status_code}: {response.text}", response)
                
        except Exception as e:
            return self.log_test("Alerts List Basic", False, f"Exception during alerts list request: {str(e)}")
    
    def test_bikes_list(self):
        """Test 4: GET /api/bikes/list with auth cookie"""
        print("\n=== Test 4: Bikes List with Auth ===")
        
        try:
            response = self.session.get(f"{API_URL}/bikes/list")
            
            if response.status_code == 200:
                data = response.json()
                
                if "bikes" not in data:
                    return self.log_test("Bikes List", False, "Response missing 'bikes' array", response)
                
                bikes = data["bikes"]
                if not isinstance(bikes, list):
                    return self.log_test("Bikes List", False, "Bikes is not an array", response)
                
                return self.log_test("Bikes List", True, f"Bikes list retrieved successfully, count: {len(bikes)}", response)
            
            else:
                return self.log_test("Bikes List", False, f"Bikes list request failed with status {response.status_code}: {response.text}", response)
                
        except Exception as e:
            return self.log_test("Bikes List", False, f"Exception during bikes list request: {str(e)}")
    
    def test_gmail_connect_error_handling(self):
        """Test 5: POST /api/gmail/connect with dummy payload should fail gracefully"""
        print("\n=== Test 5: Gmail Connect Error Handling ===")
        
        try:
            dummy_payload = {
                "email": "invalid@test.com",
                "app_password": "invalid_password"
            }
            
            response = self.session.post(f"{API_URL}/gmail/connect", json=dummy_payload)
            
            # Should fail with 400 and error message
            if response.status_code == 400:
                try:
                    data = response.json()
                    if "detail" in data and isinstance(data["detail"], str):
                        return self.log_test("Gmail Connect Error", True, f"Gmail connect failed gracefully with error: {data['detail']}", response)
                    else:
                        return self.log_test("Gmail Connect Error", False, "400 response but missing proper error message format", response)
                except:
                    return self.log_test("Gmail Connect Error", False, "400 response but invalid JSON", response)
            
            elif response.status_code == 401:
                return self.log_test("Gmail Connect Error", False, "Gmail connect returned 401 (auth issue) instead of 400 (validation error)", response)
            
            elif response.status_code == 200:
                return self.log_test("Gmail Connect Error", False, "Gmail connect unexpectedly succeeded with invalid credentials", response)
            
            else:
                return self.log_test("Gmail Connect Error", False, f"Gmail connect returned unexpected status {response.status_code}: {response.text}", response)
                
        except Exception as e:
            return self.log_test("Gmail Connect Error", False, f"Exception during gmail connect test: {str(e)}")
    
    def test_alerts_list_high_limit(self):
        """Test 6: GET /api/alerts/list with limit=5000 (verify no 200 cap enforcement)"""
        print("\n=== Test 6: Alerts List High Limit (limit=5000) ===")
        
        try:
            response = self.session.get(f"{API_URL}/alerts/list?limit=5000")
            
            if response.status_code == 200:
                data = response.json()
                
                if "alerts" not in data:
                    return self.log_test("Alerts List High Limit", False, "Response missing 'alerts' array", response)
                
                alerts = data["alerts"]
                if not isinstance(alerts, list):
                    return self.log_test("Alerts List High Limit", False, "Alerts is not an array", response)
                
                # Check pagination info if available
                pagination_info = ""
                if "pagination" in data:
                    pagination = data["pagination"]
                    pagination_info = f", pagination: limit={pagination.get('limit')}, total={pagination.get('total')}"
                
                # The key test: verify it's not capped at 200
                alert_count = len(alerts)
                if alert_count == 200 and "pagination" in data and data["pagination"].get("total", 0) > 200:
                    return self.log_test("Alerts List High Limit", False, f"Alerts list appears to be capped at 200 despite limit=5000{pagination_info}", response)
                
                return self.log_test("Alerts List High Limit", True, f"Alerts list with limit=5000 works correctly, returned: {alert_count} alerts{pagination_info}", response)
            
            else:
                return self.log_test("Alerts List High Limit", False, f"Alerts list high limit request failed with status {response.status_code}: {response.text}", response)
                
        except Exception as e:
            return self.log_test("Alerts List High Limit", False, f"Exception during alerts list high limit test: {str(e)}")
    
    def run_all_tests(self):
        """Run all backend smoke tests"""
        print(f"🚀 Starting Backend Smoke Tests")
        print(f"Backend URL: {API_URL}")
        print("=" * 60)
        
        # Test 1: Login (must succeed for subsequent tests)
        login_success = self.test_login_authentication()
        
        if not login_success:
            print("\n❌ LOGIN FAILED - Cannot proceed with authenticated tests")
            return False
        
        # Test 2-6: Other endpoints (can run even if some fail)
        self.test_alerts_categories()
        self.test_alerts_list_basic()
        self.test_bikes_list()
        self.test_gmail_connect_error_handling()
        self.test_alerts_list_high_limit()
        
        # Summary
        print("\n" + "=" * 60)
        print("🏁 TEST SUMMARY")
        print("=" * 60)
        
        passed = sum(1 for result in self.test_results if result["success"])
        total = len(self.test_results)
        
        print(f"Total Tests: {total}")
        print(f"Passed: {passed}")
        print(f"Failed: {total - passed}")
        
        if passed == total:
            print("🎉 ALL TESTS PASSED!")
            return True
        else:
            print("⚠️  SOME TESTS FAILED")
            print("\nFailed Tests:")
            for result in self.test_results:
                if not result["success"]:
                    print(f"  - {result['test']}: {result['message']}")
            return False

if __name__ == "__main__":
    tester = BackendTester()
    success = tester.run_all_tests()
    sys.exit(0 if success else 1)