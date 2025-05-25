#!/usr/bin/env python3
"""
Test script for Lambda handler using mock API Gateway events

This script tests the actual Lambda handler function by creating mock API Gateway
events and calling the handler directly. It uses environment variables for auth.

Environment variables needed:
- SWML_BASIC_AUTH_USER (defaults to 'dev')
- SWML_BASIC_AUTH_PASSWORD (defaults to 'w00t')
"""

import os
import sys
import json
import base64

# Add the signalwire_agents module to the path if needed
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

# Import the lambda handler from our example
from lambda_agent import lambda_handler

def create_basic_auth_header():
    """Create Basic Auth header from environment variables"""
    username = os.environ.get('SWML_BASIC_AUTH_USER', 'dev')
    password = os.environ.get('SWML_BASIC_AUTH_PASSWORD', 'w00t')
    
    # Encode credentials
    credentials = f"{username}:{password}"
    encoded_credentials = base64.b64encode(credentials.encode()).decode()
    
    print(f"🔐 Using credentials: {username}:{password}")
    return f"Basic {encoded_credentials}"

def create_mock_api_gateway_event(method="GET", path="/health", body=None, query_params=None):
    """Create a mock API Gateway event"""
    auth_header = create_basic_auth_header()
    
    event = {
        "version": "2.0",
        "routeKey": f"{method} {path}",
        "rawPath": path,
        "rawQueryString": "",
        "headers": {
            "authorization": auth_header,
            "content-type": "application/json",
            "user-agent": "test-client/1.0",
            "host": "api.example.com",
            "x-forwarded-for": "127.0.0.1",
            "x-forwarded-port": "443",
            "x-forwarded-proto": "https"
        },
        "queryStringParameters": query_params,
        "pathParameters": None,
        "stageVariables": None,
        "body": json.dumps(body) if body else None,
        "isBase64Encoded": False,
        "requestContext": {
            "accountId": "123456789012",
            "apiId": "test-api-id", 
            "domainName": "api.example.com",
            "http": {
                "method": method,
                "path": path,
                "protocol": "HTTP/1.1",
                "sourceIp": "127.0.0.1",
                "userAgent": "test-client/1.0"
            },
            "requestId": "test-request-123",
            "routeKey": f"{method} {path}",
            "stage": "test",
            "time": "01/Jan/2025:00:00:00 +0000",
            "timeEpoch": 1735689600
        }
    }
    
    # If we have query params, add them to rawQueryString
    if query_params:
        query_string = "&".join([f"{k}={v}" for k, v in query_params.items()])
        event["rawQueryString"] = query_string
    
    return event

def create_mock_context():
    """Create a mock Lambda context"""
    class MockContext:
        def __init__(self):
            self.function_name = "test-lambda-agent"
            self.function_version = "$LATEST"
            self.invoked_function_arn = "arn:aws:lambda:us-east-1:123456789012:function:test-lambda-agent"
            self.memory_limit_in_mb = "512"
            self.remaining_time_in_millis = lambda: 30000
            self.log_group_name = "/aws/lambda/test-lambda-agent"
            self.log_stream_name = "2025/01/01/[$LATEST]abcdef123456"
            self.aws_request_id = "test-request-id-123"
    
    return MockContext()

def test_endpoint(method, path, body=None, query_params=None):
    """Test a specific endpoint"""
    print(f"\n🧪 Testing {method} {path}")
    print("=" * 50)
    
    # Create mock event and context
    event = create_mock_api_gateway_event(method, path, body, query_params)
    context = create_mock_context()
    
    try:
        # Call the Lambda handler
        response = lambda_handler(event, context)
        
        # Display results
        print(f"✅ Status Code: {response.get('statusCode', 'N/A')}")
        
        headers = response.get('headers', {})
        if headers:
            print(f"📋 Headers: {json.dumps(headers, indent=2)}")
        
        body_content = response.get('body', '')
        if body_content:
            try:
                # Try to parse as JSON for pretty printing
                parsed_body = json.loads(body_content)
                print(f"📄 Response Body:")
                print(json.dumps(parsed_body, indent=2))
            except:
                # If not JSON, print as-is
                print(f"📄 Response Body: {body_content}")
        
        return response
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return None

def main():
    """Run Lambda handler tests"""
    print("🚀 Testing Lambda Handler with Mock API Gateway Events")
    print("=" * 60)
    
    # Test 1: Health check
    test_endpoint("GET", "/health")
    
    # Test 2: Readiness check  
    test_endpoint("GET", "/ready")
    
    # Test 3: Root endpoint (SWML)
    test_endpoint("GET", "/")
    
    # Test 4: Root endpoint with call_id
    test_endpoint("GET", "/", query_params={"call_id": "test-call-123"})
    
    # Test 5: SWAIG endpoint (GET)
    test_endpoint("GET", "/swaig")
    
    # Test 6: SWAIG function call (POST)
    swaig_body = {
        "function": "greet_user",
        "argument": {
            "parsed": [{"name": "Lambda Tester"}]
        },
        "call_id": "test-call-123"
    }
    test_endpoint("POST", "/swaig", body=swaig_body)
    
    # Test 7: Another SWAIG function
    time_body = {
        "function": "get_time",
        "argument": {"parsed": [{}]},
        "call_id": "test-call-456"
    }
    test_endpoint("POST", "/swaig", body=time_body)
    
    # Test 8: Health status function
    health_body = {
        "function": "health_status", 
        "argument": {"parsed": [{}]},
        "call_id": "test-call-789"
    }
    test_endpoint("POST", "/swaig", body=health_body)
    
    # Test 9: Debug endpoint
    test_endpoint("GET", "/debug")
    
    print("\n🎉 Lambda handler testing complete!")

if __name__ == "__main__":
    main() 