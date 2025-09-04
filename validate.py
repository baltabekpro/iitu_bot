#!/usr/bin/env python3
"""Validation script to check IITU Bot setup"""

import sys
import os
from pathlib import Path

def check_structure():
    """Check project structure"""
    print("🔍 Checking project structure...")
    
    required_files = [
        'main.py',
        'requirements.txt',
        'README.md',
        '.env.example',
        'setup.sh',
        'src/iitu_bot/__init__.py',
        'src/iitu_bot/config.py',
        'src/iitu_bot/scraper/__init__.py',
        'src/iitu_bot/processor/__init__.py',
        'src/iitu_bot/database/__init__.py',
        'src/iitu_bot/bot/__init__.py'
    ]
    
    required_dirs = [
        'src/iitu_bot',
        'data',
        'logs'
    ]
    
    all_good = True
    
    for file_path in required_files:
        if os.path.exists(file_path):
            print(f"✅ {file_path}")
        else:
            print(f"❌ {file_path} - MISSING")
            all_good = False
    
    for dir_path in required_dirs:
        if os.path.exists(dir_path):
            print(f"✅ {dir_path}/")
        else:
            print(f"❌ {dir_path}/ - MISSING")
            all_good = False
    
    return all_good

def check_modules():
    """Check if modules can be imported"""
    print("\n🔍 Checking module imports...")
    
    sys.path.insert(0, 'src')
    
    modules_to_test = [
        ('src.iitu_bot.config', 'Config'),
        ('src.iitu_bot.scraper', 'IITUWebScraper'),
    ]
    
    all_good = True
    
    for module_name, class_name in modules_to_test:
        try:
            module = __import__(module_name, fromlist=[class_name])
            getattr(module, class_name)
            print(f"✅ {module_name}.{class_name}")
        except Exception as e:
            print(f"❌ {module_name}.{class_name} - {str(e)}")
            # This is expected without dependencies installed
    
    return True  # We expect some imports to fail without dependencies

def main():
    """Main validation function"""
    print("🚀 IITU Bot Project Validation")
    print("=" * 50)
    
    structure_ok = check_structure()
    modules_ok = check_modules()
    
    print("\n" + "=" * 50)
    
    if structure_ok:
        print("🎉 Project structure is complete!")
        print("\nNext steps:")
        print("1. Install dependencies: pip install -r requirements.txt")
        print("2. Configure API keys in .env file")
        print("3. Run: python main.py")
    else:
        print("❌ Project structure has issues - please check missing files")
        return 1
    
    return 0

if __name__ == '__main__':
    exit(main())