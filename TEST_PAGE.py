#!/usr/bin/env python3
"""
Quick test to verify which page is loading
Run this to test WITHOUT selenium/serial complications
"""
from flask import Flask, render_template

app = Flask(__name__, template_folder='SETS/templates', static_folder='SETS/static')
app.secret_key = 'test'

# Inject cache version
@app.context_processor
def inject_cache_version():
    import time
    return dict(v=int(time.time()))

# Disable caching
@app.after_request
def add_header(response):
    response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '-1'
    return response

@app.route('/')
def test():
    return render_template('login.html')

if __name__ == '__main__':
    print("\n" + "="*60)
    print("🧪 SIMPLE TEST SERVER")
    print("="*60)
    print("\nOpen your browser to: http://localhost:8888")
    print("\nWhat you SHOULD see:")
    print("  ✓ Title: 'SETS'")
    print("  ✓ Bright MAGENTA banner with VERSION number")
    print("  ✓ Dark purple/black background")
    print("  ✓ Cyan neon effects")
    print("\nWhat you should NOT see:")
    print("  ✗ 'Fitness Tracker Pro'")
    print("  ✗ Old styling")
    print("\nPress Ctrl+C to stop")
    print("="*60 + "\n")

    app.run(host='0.0.0.0', port=8888, debug=True)
