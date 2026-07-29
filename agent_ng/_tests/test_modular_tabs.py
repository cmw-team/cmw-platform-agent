"""
Test Modular Tabs Implementation
===============================

Test the new modular tab structure to ensure it works correctly.
"""

import sys
import os
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

def test_tab_imports():
    """Test that visible tab modules can be imported correctly."""
    try:
        from agent_ng.tabs import ChatTab, ConfigTab, DownloadsTab, HomeTab, StatsTab
        print("✅ Tab imports successful")
        return True
    except ImportError as e:
        print(f"❌ Tab import failed: {e}")
        return False

def test_tab_creation():
    """Test that visible tab instances can be created."""
    try:
        from agent_ng.tabs import ChatTab, ConfigTab, DownloadsTab, HomeTab, StatsTab

        # Create mock event handlers
        event_handlers = {
            "stream_message": lambda x, y: (y, ""),
            "clear_chat": lambda: ([], ""),
            "refresh_stats": lambda: "Test stats",
            "update_status": lambda: "Test status",
            "quick_math": lambda: "Test math",
            "quick_code": lambda: "Test code",
            "quick_explain": lambda: "Test explain",
            "quick_create_attr": lambda: "Test create attr",
            "quick_edit_mask": lambda: "Test edit mask",
            "quick_list_apps": lambda: "Test list apps",
        }

        ChatTab(event_handlers)
        ConfigTab(event_handlers)
        DownloadsTab(event_handlers)
        HomeTab(event_handlers)
        StatsTab(event_handlers)
        print("✅ Visible tab creation successful")

        return True
    except Exception as e:
        print(f"❌ Tab creation failed: {e}")
        return False

def test_modular_app_import():
    """Test that the modular app can be imported"""
    try:
        from agent_ng.app_ng_modular import NextGenApp
        print("✅ Modular app import successful")
        return True
    except ImportError as e:
        print(f"❌ Modular app import failed: {e}")
        return False

def main():
    """Run all tests"""
    print("🧪 Testing Modular Tabs Implementation")
    print("=" * 50)

    tests = [
        test_tab_imports,
        test_tab_creation,
        test_modular_app_import,
    ]

    passed = 0
    total = len(tests)

    for test in tests:
        if test():
            passed += 1
        print()

    print("=" * 50)
    print(f"Tests passed: {passed}/{total}")

    if passed == total:
        print("🎉 All tests passed! Modular tabs implementation is working correctly.")
        return True
    else:
        print("❌ Some tests failed. Check the implementation.")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
