#!/usr/bin/env python3
"""
Debug script to test title extraction with various HTML scenarios
"""
import sys
sys.path.insert(0, '.')
from crawler.parser import parse_html

# Test cases that might cause title extraction issues
test_cases = [
    {
        "name": "Normal HTML",
        "html": """<!DOCTYPE html>
<html>
<head>
    <title>Normal Title</title>
</head>
<body>
    <p>Content</p>
</body>
</html>"""
    },
    {
        "name": "No title tag",
        "html": """<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
</head>
<body>
    <h1>Page Header</h1>
    <p>Content</p>
</body>
</html>"""
    },
    {
        "name": "Empty title tag",
        "html": """<!DOCTYPE html>
<html>
<head>
    <title></title>
</head>
<body>
    <p>Content</p>
</body>
</html>"""
    },
    {
        "name": "Title with whitespace",
        "html": """<!DOCTYPE html>
<html>
<head>
    <title>   Whitespace Title   </title>
</head>
<body>
    <p>Content</p>
</body>
</html>"""
    },
    {
        "name": "Title with newlines",
        "html": """<!DOCTYPE html>
<html>
<head>
    <title>
        Title with
        Newlines
    </title>
</head>
<body>
    <p>Content</p>
</body>
</html>"""
    },
    {
        "name": "Multiple title tags",
        "html": """<!DOCTYPE html>
<html>
<head>
    <title>First Title</title>
    <title>Second Title</title>
</head>
<body>
    <p>Content</p>
</body>
</html>"""
    },
    {
        "name": "Malformed HTML",
        "html": """<html>
<head>
<title>Malformed Title
<body>
<p>Content</p>
</html>"""
    },
    {
        "name": "Confluence-style HTML fragment (no title)",
        "html": """<div>
<h1>Page Title in H1</h1>
<p>This is like Confluence API content that doesn't have a title tag</p>
</div>"""
    },
    {
        "name": "JavaScript-heavy page",
        "html": """<!DOCTYPE html>
<html>
<head>
    <title>JS Page</title>
    <script>
        document.title = "Dynamic Title";
    </script>
</head>
<body>
    <div id="content">Loading...</div>
    <script>
        document.getElementById('content').innerHTML = "Content loaded";
    </script>
</body>
</html>"""
    },
    {
        "name": "Title with special characters",
        "html": """<!DOCTYPE html>
<html>
<head>
    <title>Special Characters: &amp; &lt; &gt; &quot; &#39;</title>
</head>
<body>
    <p>Content</p>
</body>
</html>"""
    }
]

print("Testing title extraction with various HTML scenarios:\n")

for i, test_case in enumerate(test_cases, 1):
    print(f"{i}. Testing: {test_case['name']}")
    
    try:
        result = parse_html(test_case['html'])
        title = result.get('title', '')
        
        print(f"   Title: '{title}'")
        print(f"   Title length: {len(title)}")
        
        if not title:
            print("   ⚠️  NO TITLE EXTRACTED!")
        elif title.strip() != title:
            print(f"   ⚠️  Title has leading/trailing whitespace")
        else:
            print("   ✅ Title extracted successfully")
            
    except Exception as e:
        print(f"   ❌ Error: {e}")
    
    print()

print("Done!")