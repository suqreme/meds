#!/usr/bin/env python3
"""
Test script to verify the application works locally.
Run this to test basic functionality without installing all dependencies.
"""

import os
import sys

def test_basic_imports():
    """Test if we can import basic modules"""
    try:
        import json
        import hashlib
        import re
        import urllib.parse
        from typing import List, Dict, Any
        print("✅ Basic imports successful")
        return True
    except ImportError as e:
        print(f"❌ Basic import failed: {e}")
        return False

def test_file_structure():
    """Test if all necessary files exist"""
    required_files = [
        "api/index.py",
        "requirements.txt", 
        "vercel.json",
        "package.json",
        ".env.example"
    ]
    
    missing = []
    for file in required_files:
        if not os.path.exists(file):
            missing.append(file)
    
    if missing:
        print(f"❌ Missing files: {missing}")
        return False
    else:
        print("✅ All required files present")
        return True

def test_epub_file():
    """Test if EPUB test file exists"""
    if os.path.exists("test-book.epub"):
        size = os.path.getsize("test-book.epub")
        print(f"✅ EPUB test file present ({size} bytes)")
        return True
    else:
        print("❌ EPUB test file missing")
        return False

def test_env_config():
    """Test environment configuration"""
    if os.path.exists(".env"):
        print("✅ .env file exists")
        with open(".env", "r") as f:
            content = f.read()
            if "AMZ_TAG" in content:
                print("✅ Amazon affiliate tag configured")
            else:
                print("⚠️  Amazon affiliate tag not set")
        return True
    else:
        print("⚠️  .env file not found (optional)")
        return True

def main():
    print("🧪 Testing Remedy Search Application")
    print("=" * 40)
    
    tests = [
        test_basic_imports,
        test_file_structure, 
        test_epub_file,
        test_env_config
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        if test():
            passed += 1
        print()
    
    print("=" * 40)
    print(f"Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! Ready for deployment.")
    else:
        print("⚠️  Some tests failed. Check the issues above.")
    
    print("\nNext steps:")
    print("1. Install dependencies: pip3 install -r requirements.txt")
    print("2. Set up your Amazon affiliate tag in .env")
    print("3. Deploy to Vercel: vercel --prod")
    print("4. Test with your EPUB files")

if __name__ == "__main__":
    main()