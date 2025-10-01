#!/usr/bin/env python3
"""
Debug why all images have the same size (4303 bytes).
This suggests the fetcher is downloading HTML error pages instead of actual images.
"""
import sys
import os
import hashlib
from urllib.parse import urlparse, urljoin

# Add current directory to path so we can import crawler modules
sys.path.insert(0, '/Users/dung.ho/Documents/Training/Python/BytescribeTeam/aws-lambda-crawler')

from crawler.fetcher import fetch_all_content
from crawler.parser import parse_html

def debug_image_fetching(url):
    """Debug what's actually being fetched for images."""
    print("="*70)
    print(f"Debugging Image Fetching for: {url}")
    print("="*70)
    
    # 1. Fetch the full content (HTML + resources)
    print("\n1. Fetching HTML and resources...")
    try:
        result = fetch_all_content(url)
        if not result:
            print("✗ Failed to fetch content")
            return False
            
        html = result.get("html", "")
        resources = result.get("resources", {})
        failed = result.get("failed", [])
        
        print(f"✓ HTML fetched: {len(html)} characters")
        print(f"✓ Resources found: {len(resources)}")
        print(f"✗ Failed resources: {len(failed)}")
        
        if failed:
            print("Failed URLs:")
            for f in failed:
                print(f"  - {f}")
        
    except Exception as e:
        print(f"✗ Error fetching content: {e}")
        return False
    
    # 2. Parse HTML to find images
    print("\n2. Parsing HTML for images...")
    try:
        parsed = parse_html(html, extract_resources=True, base_url=url)
        images = parsed.get("images", [])
        print(f"✓ Images found in HTML: {len(images)}")
        
        for i, img in enumerate(images[:5]):  # Show first 5
            print(f"  Image {i+1}: {img.get('src', 'NO_SRC')} (alt: {img.get('alt', 'NO_ALT')})")
            
    except Exception as e:
        print(f"✗ Error parsing HTML: {e}")
        images = []
    
    # 3. Analyze downloaded resources
    print("\n3. Analyzing downloaded resources...")
    base_domain = urlparse(url).netloc
    
    for res_url, data in resources.items():
        # Check if this looks like an image URL
        is_image_url = any(ext in res_url.lower() for ext in ['.jpg', '.jpeg', '.png', '.gif', '.webp', '.svg'])
        res_domain = urlparse(res_url).netloc
        
        print(f"\nResource: {res_url}")
        print(f"  Domain: {res_domain} (same as base: {res_domain == base_domain})")
        print(f"  Size: {len(data)} bytes")
        print(f"  Looks like image URL: {is_image_url}")
        print(f"  First 32 bytes (hex): {data[:32].hex()}")
        
        # Try to detect what this actually is
        if len(data) > 0:
            # Check for HTML
            try:
                text_start = data[:200].decode('utf-8', errors='ignore').strip()
                if text_start.startswith('<!DOCTYPE') or text_start.startswith('<html'):
                    print(f"  ⚠ WARNING: This is HTML, not an image!")
                    print(f"    Content preview: {text_start[:100]}...")
                elif text_start.startswith('{"') or text_start.startswith('['):
                    print(f"  ⚠ WARNING: This is JSON, not an image!")
                    print(f"    Content preview: {text_start[:100]}...")
                elif data[:2] == b'\xff\xd8':
                    print(f"  ✓ Valid JPEG image")
                elif data[:8] == b'\x89PNG\r\n\x1a\n':
                    print(f"  ✓ Valid PNG image")
                elif data[:6] in (b'GIF87a', b'GIF89a'):
                    print(f"  ✓ Valid GIF image")
                else:
                    print(f"  ? Unknown file type")
            except:
                print(f"  ? Binary data (cannot decode as text)")
        
        # If this is supposed to be an image but has suspicious size/content
        if is_image_url and len(data) == 4303:
            print(f"  🚨 SUSPICIOUS: Size matches your problematic uploads!")
            # Save this to a file for manual inspection
            safe_name = hashlib.md5(res_url.encode()).hexdigest()[:8]
            debug_file = f"/tmp/debug_resource_{safe_name}.bin"
            with open(debug_file, 'wb') as f:
                f.write(data)
            print(f"  📁 Saved to {debug_file} for manual inspection")
    
    # 4. Summary
    print("\n" + "="*70)
    print("SUMMARY & RECOMMENDATIONS")
    print("="*70)
    
    image_resources = [url for url in resources.keys() if any(ext in url.lower() for ext in ['.jpg', '.jpeg', '.png', '.gif', '.webp'])]
    same_size_count = sum(1 for data in resources.values() if len(data) == 4303)
    
    if same_size_count > 1:
        print(f"🚨 PROBLEM: {same_size_count} resources have identical size (4303 bytes)")
        print("   This suggests they're all the same content (likely error pages)")
        
    if any(urlparse(url).netloc.endswith('.atlassian.net') for url in image_resources):
        print("\n💡 CONFLUENCE DETECTED:")
        print("   - Make sure CONFLUENCE_USER and CONFLUENCE_API_TOKEN are set")
        print("   - Or set up AWS Secrets Manager with Confluence credentials")
        print("   - Image URLs may require authentication")
        
    print(f"\n📊 STATISTICS:")
    print(f"   - Total resources: {len(resources)}")
    print(f"   - Image-like URLs: {len(image_resources)}")
    print(f"   - Resources with size 4303: {same_size_count}")
    print(f"   - Failed downloads: {len(failed)}")
    
    return True

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python debug_image_fetch.py <URL>")
        print("Example: python debug_image_fetch.py https://example.atlassian.net/wiki/spaces/PROJECT/pages/123456/Page")
        sys.exit(1)
    
    url = sys.argv[1]
    success = debug_image_fetching(url)
    sys.exit(0 if success else 1)