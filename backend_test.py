#!/usr/bin/env python3
"""
Tech Haven E-commerce Backend API Tests
Tests all backend functionality according to test_result.md requirements
"""

import requests
import json
import sys
from typing import Dict, Any, Optional

# Configuration
BASE_URL = "https://3a6dc992-ed94-4c9b-927a-1c2947dfb8e4.preview.emergentagent.com/api"
TEST_USER = {
    "email": "test@test.com",
    "password": "password123",
    "full_name": "Full Name Test",
    "phone": "+1234567890"
}

class TechHavenTester:
    def __init__(self):
        self.base_url = BASE_URL
        self.auth_token = None
        self.test_user_id = None
        self.product_ids = []
        self.cart_items = []
        self.order_id = None
        self.results = {
            "init_data": False,
            "auth_register": False,
            "auth_login": False,
            "auth_me": False,
            "products_list": False,
            "products_filters": False,
            "products_categories": False,
            "products_detail": False,
            "cart_add": False,
            "cart_get": False,
            "cart_update": False,
            "cart_remove": False,
            "orders_create": False,
            "reviews_create": False,
            "reviews_get": False
        }
        
    def log(self, message: str, success: bool = True):
        """Log test results"""
        status = "✅" if success else "❌"
        print(f"{status} {message}")
        
    def make_request(self, method: str, endpoint: str, data: Optional[Dict] = None, 
                    auth: bool = False) -> requests.Response:
        """Make HTTP request with optional authentication"""
        url = f"{self.base_url}{endpoint}"
        headers = {"Content-Type": "application/json"}
        
        if auth and self.auth_token:
            headers["Authorization"] = f"Bearer {self.auth_token}"
            
        try:
            if method.upper() == "GET":
                response = requests.get(url, headers=headers, timeout=30)
            elif method.upper() == "POST":
                response = requests.post(url, headers=headers, json=data, timeout=30)
            elif method.upper() == "PUT":
                response = requests.put(url, headers=headers, json=data, timeout=30)
            elif method.upper() == "DELETE":
                response = requests.delete(url, headers=headers, timeout=30)
            else:
                raise ValueError(f"Unsupported method: {method}")
                
            return response
        except requests.exceptions.RequestException as e:
            self.log(f"Request failed: {e}", False)
            raise
    
    def test_init_data(self) -> bool:
        """Test sample data initialization"""
        self.log("Testing sample data initialization...")
        
        try:
            response = self.make_request("POST", "/init-data")
            
            if response.status_code in [200, 201]:
                data = response.json()
                if "message" in data:
                    self.log("Sample data initialization successful")
                    self.results["init_data"] = True
                    return True
            
            self.log(f"Init data failed: {response.status_code} - {response.text}", False)
            return False
            
        except Exception as e:
            self.log(f"Init data error: {e}", False)
            return False
    
    def test_auth_register(self) -> bool:
        """Test user registration"""
        self.log("Testing user registration...")
        
        try:
            response = self.make_request("POST", "/register", TEST_USER)
            
            if response.status_code in [200, 201]:
                data = response.json()
                if "message" in data:
                    self.log("User registration successful")
                    self.results["auth_register"] = True
                    return True
            elif response.status_code == 400 and "already registered" in response.text:
                self.log("User already exists (expected for repeated tests)")
                self.results["auth_register"] = True
                return True
                
            self.log(f"Registration failed: {response.status_code} - {response.text}", False)
            return False
            
        except Exception as e:
            self.log(f"Registration error: {e}", False)
            return False
    
    def test_auth_login(self) -> bool:
        """Test user login"""
        self.log("Testing user login...")
        
        try:
            login_data = {
                "email": TEST_USER["email"],
                "password": TEST_USER["password"]
            }
            response = self.make_request("POST", "/login", login_data)
            
            if response.status_code == 200:
                data = response.json()
                if "access_token" in data and "token_type" in data:
                    self.auth_token = data["access_token"]
                    self.log("User login successful")
                    self.results["auth_login"] = True
                    return True
                    
            self.log(f"Login failed: {response.status_code} - {response.text}", False)
            return False
            
        except Exception as e:
            self.log(f"Login error: {e}", False)
            return False
    
    def test_auth_me(self) -> bool:
        """Test get current user profile"""
        self.log("Testing get user profile...")
        
        try:
            response = self.make_request("GET", "/me", auth=True)
            
            if response.status_code == 200:
                data = response.json()
                if "id" in data and "email" in data and "full_name" in data:
                    self.test_user_id = data["id"]
                    self.log("Get user profile successful")
                    self.results["auth_me"] = True
                    return True
                    
            self.log(f"Get profile failed: {response.status_code} - {response.text}", False)
            return False
            
        except Exception as e:
            self.log(f"Get profile error: {e}", False)
            return False
    
    def test_products_list(self) -> bool:
        """Test get all products"""
        self.log("Testing get all products...")
        
        try:
            response = self.make_request("GET", "/products")
            
            if response.status_code == 200:
                data = response.json()
                if isinstance(data, list) and len(data) > 0:
                    # Store product IDs for later tests
                    self.product_ids = [product["id"] for product in data[:3]]
                    self.log(f"Get products successful - found {len(data)} products")
                    self.results["products_list"] = True
                    return True
                    
            self.log(f"Get products failed: {response.status_code} - {response.text}", False)
            return False
            
        except Exception as e:
            self.log(f"Get products error: {e}", False)
            return False
    
    def test_products_filters(self) -> bool:
        """Test product filtering"""
        self.log("Testing product filters...")
        
        try:
            # Test category filter
            response = self.make_request("GET", "/products?category=Gaming")
            if response.status_code != 200:
                self.log(f"Category filter failed: {response.status_code}", False)
                return False
                
            # Test brand filter
            response = self.make_request("GET", "/products?brand=Apple")
            if response.status_code != 200:
                self.log(f"Brand filter failed: {response.status_code}", False)
                return False
                
            # Test price filter
            response = self.make_request("GET", "/products?min_price=1000&max_price=2000")
            if response.status_code != 200:
                self.log(f"Price filter failed: {response.status_code}", False)
                return False
                
            # Test search
            response = self.make_request("GET", "/products?search=MacBook")
            if response.status_code != 200:
                self.log(f"Search filter failed: {response.status_code}", False)
                return False
                
            # Test featured filter
            response = self.make_request("GET", "/products?featured=true")
            if response.status_code == 200:
                self.log("Product filters successful")
                self.results["products_filters"] = True
                return True
                
            self.log(f"Featured filter failed: {response.status_code}", False)
            return False
            
        except Exception as e:
            self.log(f"Product filters error: {e}", False)
            return False
    
    def test_products_categories(self) -> bool:
        """Test get categories and brands"""
        self.log("Testing get categories and brands...")
        
        try:
            response = self.make_request("GET", "/categories")
            
            if response.status_code == 200:
                data = response.json()
                if "categories" in data and "brands" in data:
                    self.log("Get categories successful")
                    self.results["products_categories"] = True
                    return True
                    
            self.log(f"Get categories failed: {response.status_code} - {response.text}", False)
            return False
            
        except Exception as e:
            self.log(f"Get categories error: {e}", False)
            return False
    
    def test_products_detail(self) -> bool:
        """Test get product detail"""
        self.log("Testing get product detail...")
        
        if not self.product_ids:
            self.log("No product IDs available for detail test", False)
            return False
            
        try:
            product_id = self.product_ids[0]
            response = self.make_request("GET", f"/products/{product_id}")
            
            if response.status_code == 200:
                data = response.json()
                if "id" in data and "name" in data and "price" in data:
                    self.log("Get product detail successful")
                    self.results["products_detail"] = True
                    return True
                    
            self.log(f"Get product detail failed: {response.status_code} - {response.text}", False)
            return False
            
        except Exception as e:
            self.log(f"Get product detail error: {e}", False)
            return False
    
    def test_cart_add(self) -> bool:
        """Test add item to cart"""
        self.log("Testing add item to cart...")
        
        if not self.product_ids:
            self.log("No product IDs available for cart test", False)
            return False
            
        try:
            cart_item = {
                "product_id": self.product_ids[0],
                "quantity": 2
            }
            response = self.make_request("POST", "/cart/add", cart_item, auth=True)
            
            if response.status_code in [200, 201]:
                data = response.json()
                if "message" in data:
                    self.cart_items.append(cart_item)
                    self.log("Add to cart successful")
                    self.results["cart_add"] = True
                    return True
                    
            self.log(f"Add to cart failed: {response.status_code} - {response.text}", False)
            return False
            
        except Exception as e:
            self.log(f"Add to cart error: {e}", False)
            return False
    
    def test_cart_get(self) -> bool:
        """Test get cart"""
        self.log("Testing get cart...")
        
        try:
            response = self.make_request("GET", "/cart", auth=True)
            
            if response.status_code == 200:
                data = response.json()
                if "id" in data and "user_id" in data and "items" in data:
                    self.log("Get cart successful")
                    self.results["cart_get"] = True
                    return True
                    
            self.log(f"Get cart failed: {response.status_code} - {response.text}", False)
            return False
            
        except Exception as e:
            self.log(f"Get cart error: {e}", False)
            return False
    
    def test_cart_update(self) -> bool:
        """Test update cart item"""
        self.log("Testing update cart item...")
        
        if not self.product_ids:
            self.log("No product IDs available for cart update test", False)
            return False
            
        try:
            cart_item = {
                "product_id": self.product_ids[0],
                "quantity": 3
            }
            response = self.make_request("PUT", "/cart/update", cart_item, auth=True)
            
            if response.status_code == 200:
                data = response.json()
                if "message" in data:
                    self.log("Update cart successful")
                    self.results["cart_update"] = True
                    return True
                    
            self.log(f"Update cart failed: {response.status_code} - {response.text}", False)
            return False
            
        except Exception as e:
            self.log(f"Update cart error: {e}", False)
            return False
    
    def test_cart_remove(self) -> bool:
        """Test remove item from cart"""
        self.log("Testing remove item from cart...")
        
        if not self.product_ids:
            self.log("No product IDs available for cart remove test", False)
            return False
            
        try:
            # Add another item first
            cart_item = {
                "product_id": self.product_ids[1] if len(self.product_ids) > 1 else self.product_ids[0],
                "quantity": 1
            }
            self.make_request("POST", "/cart/add", cart_item, auth=True)
            
            # Now remove it
            product_id = cart_item["product_id"]
            response = self.make_request("DELETE", f"/cart/remove/{product_id}", auth=True)
            
            if response.status_code == 200:
                data = response.json()
                if "message" in data:
                    self.log("Remove from cart successful")
                    self.results["cart_remove"] = True
                    return True
                    
            self.log(f"Remove from cart failed: {response.status_code} - {response.text}", False)
            return False
            
        except Exception as e:
            self.log(f"Remove from cart error: {e}", False)
            return False
    
    def test_orders_create(self) -> bool:
        """Test create order"""
        self.log("Testing create order...")
        
        try:
            # Ensure we have items in cart
            if self.product_ids:
                cart_item = {
                    "product_id": self.product_ids[0],
                    "quantity": 1
                }
                self.make_request("POST", "/cart/add", cart_item, auth=True)
            
            order_data = {
                "shipping_address": {
                    "street": "123 Tech Street",
                    "city": "San Francisco",
                    "state": "CA",
                    "zip_code": "94105",
                    "country": "USA"
                }
            }
            response = self.make_request("POST", "/orders", order_data, auth=True)
            
            if response.status_code in [200, 201]:
                data = response.json()
                if "id" in data and "total_amount" in data and "items" in data:
                    self.order_id = data["id"]
                    self.log("Create order successful")
                    self.results["orders_create"] = True
                    return True
                    
            self.log(f"Create order failed: {response.status_code} - {response.text}", False)
            return False
            
        except Exception as e:
            self.log(f"Create order error: {e}", False)
            return False
    
    def test_reviews_create(self) -> bool:
        """Test create review"""
        self.log("Testing create review...")
        
        if not self.product_ids:
            self.log("No product IDs available for review test", False)
            return False
            
        try:
            review_data = {
                "product_id": self.product_ids[0],
                "rating": 5,
                "comment": "Excellent laptop! Great performance and build quality. Highly recommended for professional use."
            }
            response = self.make_request("POST", "/reviews", review_data, auth=True)
            
            if response.status_code in [200, 201]:
                data = response.json()
                if "id" in data and "rating" in data and "comment" in data:
                    self.log("Create review successful")
                    self.results["reviews_create"] = True
                    return True
            elif response.status_code == 400 and "already reviewed" in response.text:
                self.log("User already reviewed this product (expected for repeated tests)")
                self.results["reviews_create"] = True
                return True
                    
            self.log(f"Create review failed: {response.status_code} - {response.text}", False)
            return False
            
        except Exception as e:
            self.log(f"Create review error: {e}", False)
            return False
    
    def test_reviews_get(self) -> bool:
        """Test get product reviews"""
        self.log("Testing get product reviews...")
        
        if not self.product_ids:
            self.log("No product IDs available for reviews get test", False)
            return False
            
        try:
            product_id = self.product_ids[0]
            response = self.make_request("GET", f"/products/{product_id}/reviews")
            
            if response.status_code == 200:
                data = response.json()
                if isinstance(data, list):
                    self.log(f"Get reviews successful - found {len(data)} reviews")
                    self.results["reviews_get"] = True
                    return True
                    
            self.log(f"Get reviews failed: {response.status_code} - {response.text}", False)
            return False
            
        except Exception as e:
            self.log(f"Get reviews error: {e}", False)
            return False
    
    def run_all_tests(self):
        """Run all backend tests in sequence"""
        print("🚀 Starting Tech Haven Backend API Tests")
        print(f"📍 Base URL: {self.base_url}")
        print("=" * 60)
        
        # Test sequence as per requirements
        tests = [
            ("Sample Data Initialization", self.test_init_data),
            ("User Registration", self.test_auth_register),
            ("User Login", self.test_auth_login),
            ("Get User Profile", self.test_auth_me),
            ("Get All Products", self.test_products_list),
            ("Product Filters", self.test_products_filters),
            ("Get Categories", self.test_products_categories),
            ("Get Product Detail", self.test_products_detail),
            ("Add to Cart", self.test_cart_add),
            ("Get Cart", self.test_cart_get),
            ("Update Cart", self.test_cart_update),
            ("Remove from Cart", self.test_cart_remove),
            ("Create Order", self.test_orders_create),
            ("Create Review", self.test_reviews_create),
            ("Get Reviews", self.test_reviews_get),
        ]
        
        passed = 0
        failed = 0
        
        for test_name, test_func in tests:
            print(f"\n📋 {test_name}")
            try:
                if test_func():
                    passed += 1
                else:
                    failed += 1
            except Exception as e:
                self.log(f"Test {test_name} crashed: {e}", False)
                failed += 1
        
        print("\n" + "=" * 60)
        print("📊 TEST SUMMARY")
        print("=" * 60)
        
        for key, value in self.results.items():
            status = "✅ PASS" if value else "❌ FAIL"
            print(f"{key.replace('_', ' ').title()}: {status}")
        
        print(f"\n🎯 Total: {passed + failed} tests")
        print(f"✅ Passed: {passed}")
        print(f"❌ Failed: {failed}")
        print(f"📈 Success Rate: {(passed/(passed+failed)*100):.1f}%")
        
        return passed, failed, self.results

if __name__ == "__main__":
    tester = TechHavenTester()
    passed, failed, results = tester.run_all_tests()
    
    # Exit with error code if any tests failed
    sys.exit(0 if failed == 0 else 1)