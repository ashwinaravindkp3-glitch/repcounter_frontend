#!/usr/bin/env python3
"""
DIAGNOSTIC SCRIPT - Find out what's going on!
"""
import os
import sys

print("\n" + "="*70)
print("🔍 DIAGNOSTIC SCRIPT - Let's find the problem!")
print("="*70 + "\n")

# Check current directory
cwd = os.getcwd()
print(f"1. Current directory: {cwd}")

# Check if SETS folder exists
sets_path = os.path.join(cwd, "SETS")
if os.path.exists(sets_path):
    print(f"   ✓ SETS folder found at: {sets_path}")
else:
    print(f"   ✗ SETS folder NOT FOUND!")
    print(f"   You need to cd to: /home/user/repcounter_frontend")
    sys.exit(1)

# Check templates
templates_path = os.path.join(sets_path, "templates", "login.html")
if os.path.exists(templates_path):
    print(f"   ✓ login.html found")

    # Check if it has SETS branding
    with open(templates_path, 'r') as f:
        content = f.read()
        if "SETS" in content and "NEW CODE LOADED" in content:
            print(f"   ✓ login.html has SETS branding AND diagnostic banner!")
        elif "SETS" in content:
            print(f"   ⚠️ login.html has SETS but missing diagnostic banner")
        else:
            print(f"   ✗ login.html might be old!")
else:
    print(f"   ✗ login.html NOT FOUND!")

# Check CSS files
css_path = os.path.join(sets_path, "static", "css")
if os.path.exists(css_path):
    css_files = os.listdir(css_path)
    print(f"\n2. CSS files in static/css:")
    for f in css_files:
        print(f"   - {f}")

    if "futuristic.css" in css_files:
        print("   ✓ futuristic.css exists (GOOD!)")
    if "main.css" in css_files or "main.css.OLD_BACKUP" in css_files:
        print("   ⚠️ OLD CSS FILE STILL EXISTS! This might be the problem!")

# Check if any Python processes running
print(f"\n3. Instructions:")
print(f"   Step 1: Close ALL browser windows")
print(f"   Step 2: Kill any running Python: Ctrl+C or pkill -f python")
print(f"   Step 3: cd /home/user/repcounter_frontend/SETS")
print(f"   Step 4: python main.py")
print(f"   Step 5: Look for RED BANNER at top saying 'NEW CODE LOADED'")
print(f"\n4. What you should see:")
print(f"   ✓ RED banner at top: 'NEW CODE LOADED'")
print(f"   ✓ Title: 'SETS'")
print(f"   ✓ Magenta banner with version number")
print(f"   ✓ Dark purple background")
print(f"\n5. What you should NOT see:")
print(f"   ✗ 'Fitness Tracker Pro'")
print(f"   ✗ No red banner")
print(f"   ✗ Different styling")

print(f"\n6. If you STILL see 'Fitness Tracker Pro':")
print(f"   - You might be on the WRONG PORT!")
print(f"   - Check the URL - should be: localhost:5000")
print(f"   - NOT 127.0.0.1:8000 or any other port")
print(f"   - Close incognito tab, let Python open fresh browser")

print("\n" + "="*70)
print("🧪 Run python TEST_PAGE.py for a simpler test (port 8888)")
print("="*70 + "\n")
