"""
Unit tests for state management modules
"""

import pytest
import os
import tempfile
import json
import time
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta

from signalwire_agents.core.state.state_manager import StateManager
from signalwire_agents.core.state.file_state_manager import FileStateManager


class MockStateManager(StateManager):
    """Mock implementation of StateManager for testing"""
    
    def __init__(self):
        self.data = {}
        self.timestamps = {}
    
    def store(self, call_id: str, data: dict) -> bool:
        self.data[call_id] = data.copy()
        self.timestamps[call_id] = time.time()
        return True
    
    def retrieve(self, call_id: str) -> dict:
        return self.data.get(call_id)
    
    def update(self, call_id: str, data: dict) -> bool:
        if call_id in self.data:
            self.data[call_id].update(data)
            self.timestamps[call_id] = time.time()
            return True
        return False
    
    def delete(self, call_id: str) -> bool:
        if call_id in self.data:
            del self.data[call_id]
            del self.timestamps[call_id]
            return True
        return False
    
    def cleanup_expired(self) -> int:
        # Mock cleanup - remove items older than 1 hour
        current_time = time.time()
        expired = []
        for call_id, timestamp in self.timestamps.items():
            if current_time - timestamp > 3600:  # 1 hour
                expired.append(call_id)
        
        for call_id in expired:
            self.delete(call_id)
        
        return len(expired)


class TestStateManagerInterface:
    """Test StateManager abstract interface"""
    
    def test_abstract_methods_exist(self):
        """Test that StateManager defines required abstract methods"""
        # Should not be able to instantiate abstract class directly
        with pytest.raises(TypeError):
            StateManager()
    
    def test_exists_method_default_implementation(self):
        """Test the default implementation of exists method"""
        manager = MockStateManager()
        
        # Should return False for non-existent call
        assert manager.exists("nonexistent") is False
        
        # Should return True for existing call
        manager.store("test_call", {"key": "value"})
        assert manager.exists("test_call") is True
    
    def test_mock_implementation_basic_operations(self):
        """Test basic operations with mock implementation"""
        manager = MockStateManager()
        
        # Test store
        result = manager.store("call_123", {"user": "test", "step": 1})
        assert result is True
        
        # Test retrieve
        data = manager.retrieve("call_123")
        assert data == {"user": "test", "step": 1}
        
        # Test update
        result = manager.update("call_123", {"step": 2, "new_field": "value"})
        assert result is True
        
        # Verify update
        data = manager.retrieve("call_123")
        assert data == {"user": "test", "step": 2, "new_field": "value"}
        
        # Test delete
        result = manager.delete("call_123")
        assert result is True
        
        # Verify deletion
        data = manager.retrieve("call_123")
        assert data is None
    
    def test_mock_implementation_edge_cases(self):
        """Test edge cases with mock implementation"""
        manager = MockStateManager()
        
        # Test update on non-existent call
        result = manager.update("nonexistent", {"key": "value"})
        assert result is False
        
        # Test delete on non-existent call
        result = manager.delete("nonexistent")
        assert result is False
        
        # Test retrieve on non-existent call
        data = manager.retrieve("nonexistent")
        assert data is None


class TestFileStateManager:
    """Test FileStateManager implementation"""
    
    def test_initialization_default_directory(self):
        """Test initialization with default directory"""
        manager = FileStateManager()
        
        # Should use temp directory by default
        assert manager.storage_dir.startswith(tempfile.gettempdir())
        assert "signalwire_state" in manager.storage_dir
        assert manager.expiry_days == 1.0
        
        # Directory should be created
        assert os.path.exists(manager.storage_dir)
    
    def test_initialization_custom_directory(self):
        """Test initialization with custom directory"""
        with tempfile.TemporaryDirectory() as temp_dir:
            custom_dir = os.path.join(temp_dir, "custom_state")
            manager = FileStateManager(storage_dir=custom_dir, expiry_days=2.0)
            
            assert manager.storage_dir == custom_dir
            assert manager.expiry_days == 2.0
            assert os.path.exists(custom_dir)
    
    def test_file_path_generation(self):
        """Test file path generation and sanitization"""
        with tempfile.TemporaryDirectory() as temp_dir:
            manager = FileStateManager(storage_dir=temp_dir)
            
            # Test normal call ID
            path = manager._get_file_path("call_123")
            expected = os.path.join(temp_dir, "call_123.json")
            assert path == expected
            
            # Test call ID with special characters (should be sanitized)
            path = manager._get_file_path("call/with\\special:chars")
            # The actual implementation removes non-alphanumeric chars except -_.
            assert "callwithspecialchars.json" in path
            assert os.path.dirname(path) == temp_dir
    
    def test_store_and_retrieve(self):
        """Test storing and retrieving data"""
        with tempfile.TemporaryDirectory() as temp_dir:
            manager = FileStateManager(storage_dir=temp_dir)
            
            # Store data
            test_data = {"user": "test_user", "step": 1, "data": {"nested": "value"}}
            result = manager.store("test_call", test_data)
            assert result is True
            
            # Verify file was created
            file_path = manager._get_file_path("test_call")
            assert os.path.exists(file_path)
            
            # Retrieve data
            retrieved_data = manager.retrieve("test_call")
            assert retrieved_data == test_data
    
    def test_update_existing_data(self):
        """Test updating existing data"""
        with tempfile.TemporaryDirectory() as temp_dir:
            manager = FileStateManager(storage_dir=temp_dir)
            
            # Store initial data
            initial_data = {"user": "test", "step": 1}
            manager.store("test_call", initial_data)
            
            # Update data
            update_data = {"step": 2, "new_field": "new_value"}
            result = manager.update("test_call", update_data)
            assert result is True
            
            # Verify update
            retrieved_data = manager.retrieve("test_call")
            expected = {"user": "test", "step": 2, "new_field": "new_value"}
            assert retrieved_data == expected
    
    def test_update_nonexistent_data(self):
        """Test updating non-existent data"""
        with tempfile.TemporaryDirectory() as temp_dir:
            manager = FileStateManager(storage_dir=temp_dir)
            
            # Try to update non-existent call - FileStateManager creates new data
            result = manager.update("nonexistent", {"key": "value"})
            assert result is True  # FileStateManager creates new data if it doesn't exist
            
            # Verify data was created
            retrieved_data = manager.retrieve("nonexistent")
            assert retrieved_data == {"key": "value"}
    
    def test_delete_data(self):
        """Test deleting data"""
        with tempfile.TemporaryDirectory() as temp_dir:
            manager = FileStateManager(storage_dir=temp_dir)
            
            # Store data
            manager.store("test_call", {"key": "value"})
            file_path = manager._get_file_path("test_call")
            assert os.path.exists(file_path)
            
            # Delete data
            result = manager.delete("test_call")
            assert result is True
            assert not os.path.exists(file_path)
            
            # Verify data is gone
            retrieved_data = manager.retrieve("test_call")
            assert retrieved_data is None
    
    def test_delete_nonexistent_data(self):
        """Test deleting non-existent data"""
        with tempfile.TemporaryDirectory() as temp_dir:
            manager = FileStateManager(storage_dir=temp_dir)
            
            # Try to delete non-existent call
            result = manager.delete("nonexistent")
            assert result is False
    
    def test_exists_method(self):
        """Test exists method"""
        with tempfile.TemporaryDirectory() as temp_dir:
            manager = FileStateManager(storage_dir=temp_dir)
            
            # Should not exist initially
            assert manager.exists("test_call") is False
            
            # Should exist after storing
            manager.store("test_call", {"key": "value"})
            assert manager.exists("test_call") is True
            
            # Should not exist after deleting
            manager.delete("test_call")
            assert manager.exists("test_call") is False
    
    def test_cleanup_expired_files(self):
        """Test cleanup of expired files"""
        with tempfile.TemporaryDirectory() as temp_dir:
            manager = FileStateManager(storage_dir=temp_dir, expiry_days=0.001)  # Very short expiry
            
            # Store some data
            manager.store("call_1", {"key": "value1"})
            manager.store("call_2", {"key": "value2"})
            
            # Manually modify file timestamps to make them appear old
            import time
            old_time = time.time() - (0.002 * 24 * 60 * 60)  # 0.002 days ago
            
            for call_id in ["call_1", "call_2"]:
                file_path = manager._get_file_path(call_id)
                # Read and modify the JSON to have old timestamp
                with open(file_path, 'r') as f:
                    data = json.load(f)
                data['created_at'] = datetime.fromtimestamp(old_time).isoformat()
                with open(file_path, 'w') as f:
                    json.dump(data, f)
            
            # Store fresh data
            manager.store("call_3", {"key": "value3"})
            
            # Run cleanup
            cleaned_count = manager.cleanup_expired()
            
            # Should have cleaned up the expired files
            assert cleaned_count == 2
            assert not manager.exists("call_1")
            assert not manager.exists("call_2")
            assert manager.exists("call_3")  # Fresh data should remain
    
    def test_cleanup_with_no_expired_files(self):
        """Test cleanup when no files are expired"""
        with tempfile.TemporaryDirectory() as temp_dir:
            manager = FileStateManager(storage_dir=temp_dir, expiry_days=1.0)
            
            # Store some recent data
            manager.store("call_1", {"key": "value1"})
            manager.store("call_2", {"key": "value2"})
            
            # Run cleanup immediately
            cleaned_count = manager.cleanup_expired()
            
            # Should not have cleaned anything
            assert cleaned_count == 0
            assert manager.exists("call_1")
            assert manager.exists("call_2")
    
    def test_error_handling_invalid_json(self):
        """Test error handling with invalid JSON files"""
        with tempfile.TemporaryDirectory() as temp_dir:
            manager = FileStateManager(storage_dir=temp_dir)
            
            # Create a file with invalid JSON
            file_path = manager._get_file_path("invalid_call")
            with open(file_path, 'w') as f:
                f.write("invalid json content")
            
            # Should handle gracefully
            retrieved_data = manager.retrieve("invalid_call")
            assert retrieved_data is None
    
    def test_error_handling_permission_denied(self):
        """Test error handling with permission issues"""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Test with a directory that doesn't exist and can't be created
            with patch('os.makedirs', side_effect=PermissionError("Permission denied")):
                with pytest.raises(PermissionError):
                    FileStateManager(storage_dir="/root/nonexistent")
    
    def test_concurrent_access_simulation(self):
        """Test simulation of concurrent access"""
        with tempfile.TemporaryDirectory() as temp_dir:
            manager = FileStateManager(storage_dir=temp_dir)
            
            # Simulate multiple operations on the same call
            call_id = "concurrent_call"
            
            # Store initial data
            manager.store(call_id, {"counter": 0})
            
            # Simulate multiple updates
            for i in range(10):
                current_data = manager.retrieve(call_id)
                current_data["counter"] += 1
                manager.update(call_id, current_data)
            
            # Verify final state
            final_data = manager.retrieve(call_id)
            assert final_data["counter"] == 10
    
    def test_large_data_storage(self):
        """Test storing large amounts of data"""
        with tempfile.TemporaryDirectory() as temp_dir:
            manager = FileStateManager(storage_dir=temp_dir)
            
            # Create large data structure
            large_data = {
                "users": [{"id": i, "name": f"user_{i}", "data": "x" * 100} for i in range(100)],
                "metadata": {"created": "2023-01-01", "version": "1.0"},
                "config": {"setting_" + str(i): f"value_{i}" for i in range(50)}
            }
            
            # Store and retrieve
            result = manager.store("large_call", large_data)
            assert result is True
            
            retrieved_data = manager.retrieve("large_call")
            assert retrieved_data == large_data
    
    def test_special_characters_in_data(self):
        """Test handling special characters in data"""
        with tempfile.TemporaryDirectory() as temp_dir:
            manager = FileStateManager(storage_dir=temp_dir)
            
            # Data with special characters
            special_data = {
                "unicode": "Hello 世界 🌍",
                "quotes": 'He said "Hello" and she said \'Hi\'',
                "newlines": "Line 1\nLine 2\rLine 3",
                "json_chars": '{"key": "value", "array": [1, 2, 3]}'
            }
            
            # Store and retrieve
            manager.store("special_call", special_data)
            retrieved_data = manager.retrieve("special_call")
            assert retrieved_data == special_data


class TestStateManagerIntegration:
    """Test integration scenarios for state managers"""
    
    def test_state_manager_interface_compliance(self):
        """Test that FileStateManager properly implements StateManager interface"""
        manager = FileStateManager()
        
        # Should implement all required methods
        assert hasattr(manager, 'store')
        assert hasattr(manager, 'retrieve')
        assert hasattr(manager, 'update')
        assert hasattr(manager, 'delete')
        assert hasattr(manager, 'cleanup_expired')
        assert hasattr(manager, 'exists')
        
        # Methods should be callable
        assert callable(manager.store)
        assert callable(manager.retrieve)
        assert callable(manager.update)
        assert callable(manager.delete)
        assert callable(manager.cleanup_expired)
        assert callable(manager.exists)
    
    def test_state_manager_workflow(self):
        """Test complete workflow with state manager"""
        with tempfile.TemporaryDirectory() as temp_dir:
            manager = FileStateManager(storage_dir=temp_dir)
            
            call_id = "workflow_call"
            
            # Step 1: Initialize call state
            initial_state = {
                "call_id": call_id,
                "user_id": "user_123",
                "step": "greeting",
                "data_collected": {}
            }
            assert manager.store(call_id, initial_state) is True
            
            # Step 2: Update with user input
            manager.update(call_id, {
                "step": "collecting_name",
                "data_collected": {"name": "John Doe"}
            })
            
            # Step 3: Add more data
            current_state = manager.retrieve(call_id)
            current_state["data_collected"]["email"] = "john@example.com"
            current_state["step"] = "collecting_phone"
            manager.update(call_id, current_state)
            
            # Step 4: Finalize
            manager.update(call_id, {
                "step": "completed",
                "data_collected": {
                    **current_state["data_collected"],
                    "phone": "+1234567890"
                }
            })
            
            # Verify final state
            final_state = manager.retrieve(call_id)
            assert final_state["step"] == "completed"
            assert final_state["data_collected"]["name"] == "John Doe"
            assert final_state["data_collected"]["email"] == "john@example.com"
            assert final_state["data_collected"]["phone"] == "+1234567890"
            
            # Cleanup
            assert manager.delete(call_id) is True
            assert not manager.exists(call_id)
    
    def test_multiple_calls_isolation(self):
        """Test that multiple calls are properly isolated"""
        with tempfile.TemporaryDirectory() as temp_dir:
            manager = FileStateManager(storage_dir=temp_dir)
            
            # Create multiple call states
            calls = {
                "call_1": {"user": "user_1", "step": 1},
                "call_2": {"user": "user_2", "step": 2},
                "call_3": {"user": "user_3", "step": 3}
            }
            
            # Store all calls
            for call_id, data in calls.items():
                manager.store(call_id, data)
            
            # Verify isolation - update one call shouldn't affect others
            manager.update("call_2", {"step": 10, "modified": True})
            
            # Check all calls
            call_1_data = manager.retrieve("call_1")
            call_2_data = manager.retrieve("call_2")
            call_3_data = manager.retrieve("call_3")
            
            assert call_1_data == {"user": "user_1", "step": 1}
            assert call_2_data == {"user": "user_2", "step": 10, "modified": True}
            assert call_3_data == {"user": "user_3", "step": 3}
    
    def test_error_recovery(self):
        """Test error recovery scenarios"""
        with tempfile.TemporaryDirectory() as temp_dir:
            manager = FileStateManager(storage_dir=temp_dir)
            
            # Store valid data
            manager.store("valid_call", {"key": "value"})
            
            # Simulate file corruption by writing invalid JSON
            file_path = manager._get_file_path("corrupted_call")
            with open(file_path, 'w') as f:
                f.write("corrupted json {")
            
            # Manager should handle corrupted file gracefully
            assert manager.retrieve("corrupted_call") is None
            assert not manager.exists("corrupted_call")
            
            # Valid data should still work
            assert manager.retrieve("valid_call") == {"key": "value"}
            assert manager.exists("valid_call") 