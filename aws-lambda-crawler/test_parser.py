#!/usr/bin/env python3
import sys
sys.path.insert(0, '.')
from crawler.parser import parse_html

# Test with sample HTML content that has various media types
test_html = '''<!DOCTYPE html>
<html>
<head>
    <title>Test Page with Media</title>
</head>
<body>
    <h1>Welcome to Test Page</h1>
    <p>This is a test page with various media elements.</p>
    
    <!-- Images -->
    <img src="/images/logo.png" alt="Company Logo" title="Our Logo" width="100" height="50">
    <img src="https://example.com/photo.jpg" alt="Sample Photo">
    
    <!-- Videos -->
    <video controls width="320" height="240" poster="/images/poster.jpg">
        <source src="/videos/sample.mp4" type="video/mp4">
        <source src="/videos/sample.webm" type="video/webm">
    </video>
    
    <!-- Links/References -->
    <a href="https://example.com" title="External Link">Visit Example</a>
    <a href="/about" title="About Us">About Page</a>
    <a href="mailto:contact@example.com">Contact Us</a>
    
    <!-- Embedded content -->
    <iframe src="https://www.youtube.com/embed/12345" width="560" height="315" title="YouTube video"></iframe>
    
    <p>More content here for testing text extraction.</p>
</body>
</html>'''

try:
    result = parse_html(test_html, extract_resources=True, base_url='https://testsite.com')
    
    print('Parsed result keys:', list(result.keys()))
    print(f'Title: {result.get("title")}')
    print(f'Text snippet: {result.get("text_snippet", "")[:100]}...')
    print()
    
    print(f'Images found: {len(result.get("images", []))}')
    for i, img in enumerate(result.get('images', [])):
        print(f'  {i+1}. {img}')
    print()
    
    print(f'Videos found: {len(result.get("videos", []))}')
    for i, video in enumerate(result.get('videos', [])):
        print(f'  {i+1}. {video}')
    print()
    
    print(f'References found: {len(result.get("references", []))}')
    for i, ref in enumerate(result.get('references', [])):
        print(f'  {i+1}. {ref}')
    print()
    
    print(f'Embedded items found: {len(result.get("embedded", []))}')
    for i, embed in enumerate(result.get('embedded', [])):
        print(f'  {i+1}. {embed}')
        
except Exception as e:
    print(f'Error: {e}')
    import traceback
    traceback.print_exc()