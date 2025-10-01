#!/usr/bin/env python3
"""
Diagnose why S3 presigned URLs for images cannot be opened.
This script checks:
1. If the object exists in S3
2. The Content-Type metadata
3. If the bytes are valid image data
4. If presigned URLs work correctly
"""
import os
import sys
import boto3
from botocore.config import Config as BotoConfig
import requests
from io import BytesIO

def diagnose_s3_object(bucket, key):
    """Diagnose an S3 object and its presigned URL."""
    print("=" * 70)
    print(f"Diagnosing S3 Object")
    print(f"  Bucket: {bucket}")
    print(f"  Key: {key}")
    print("=" * 70)
    
    # Create S3 client
    region = os.getenv("REGION") or os.getenv("AWS_DEFAULT_REGION") or "us-east-1"
    s3_config = BotoConfig(signature_version="s3v4", region_name=region)
    s3_client = boto3.client("s3", config=s3_config)
    
    # 1. Check if object exists and get metadata
    print("\n1. Checking S3 Object Metadata...")
    try:
        response = s3_client.head_object(Bucket=bucket, Key=key)
        print(f"   ✓ Object exists")
        print(f"   - Size: {response.get('ContentLength')} bytes")
        print(f"   - Content-Type: {response.get('ContentType')}")
        print(f"   - Last Modified: {response.get('LastModified')}")
        print(f"   - ETag: {response.get('ETag')}")
        
        content_type = response.get('ContentType')
        size = response.get('ContentLength', 0)
        
        if not content_type or content_type == 'binary/octet-stream':
            print("   ⚠ WARNING: Content-Type not set or is binary/octet-stream")
            print("      This will cause browsers to download instead of display!")
        elif not content_type.startswith('image/'):
            print(f"   ⚠ WARNING: Content-Type '{content_type}' is not an image type")
        
        if size == 0:
            print("   ✗ ERROR: File is empty (0 bytes)!")
            return False
            
    except Exception as e:
        print(f"   ✗ ERROR: Cannot access object: {e}")
        return False
    
    # 2. Download and check actual bytes
    print("\n2. Downloading Object from S3...")
    try:
        obj_response = s3_client.get_object(Bucket=bucket, Key=key)
        data = obj_response['Body'].read()
        print(f"   ✓ Downloaded {len(data)} bytes")
        print(f"   - First 16 bytes (hex): {data[:16].hex()}")
        
        # Check if it's a valid image by looking at magic bytes
        is_valid_image, detected_type = check_image_magic_bytes(data)
        if is_valid_image:
            print(f"   ✓ Valid image detected: {detected_type}")
        else:
            print(f"   ✗ WARNING: Does not appear to be a valid image file")
            print(f"      Expected image magic bytes, got: {data[:16].hex()}")
            
    except Exception as e:
        print(f"   ✗ ERROR: Cannot download object: {e}")
        return False
    
    # 3. Test presigned URL (without ResponseContentType)
    print("\n3. Testing Presigned URL (Standard)...")
    try:
        presigned = s3_client.generate_presigned_url(
            'get_object',
            Params={'Bucket': bucket, 'Key': key},
            ExpiresIn=3600
        )
        print(f"   ✓ Generated presigned URL")
        print(f"   URL: {presigned[:100]}...")
        
        # Try to fetch via presigned URL
        resp = requests.get(presigned, timeout=10)
        resp.raise_for_status()
        print(f"   ✓ Presigned URL is accessible")
        print(f"   - Response Content-Type: {resp.headers.get('content-type')}")
        print(f"   - Response Size: {len(resp.content)} bytes")
        
        if resp.content != data:
            print(f"   ✗ ERROR: Downloaded data doesn't match S3 object!")
        else:
            print(f"   ✓ Data matches S3 object")
            
    except Exception as e:
        print(f"   ✗ ERROR: Presigned URL failed: {e}")
    
    # 4. Test presigned URL with ResponseContentType override
    print("\n4. Testing Presigned URL (with ResponseContentType)...")
    try:
        # Determine correct content type
        if detected_type:
            override_type = detected_type
        elif content_type and content_type.startswith('image/'):
            override_type = content_type
        else:
            # Guess from key extension
            if key.lower().endswith('.jpg') or key.lower().endswith('.jpeg'):
                override_type = 'image/jpeg'
            elif key.lower().endswith('.png'):
                override_type = 'image/png'
            elif key.lower().endswith('.gif'):
                override_type = 'image/gif'
            elif key.lower().endswith('.webp'):
                override_type = 'image/webp'
            else:
                override_type = 'image/jpeg'  # default guess
        
        presigned_typed = s3_client.generate_presigned_url(
            'get_object',
            Params={
                'Bucket': bucket,
                'Key': key,
                'ResponseContentType': override_type
            },
            ExpiresIn=3600
        )
        print(f"   ✓ Generated presigned URL with ResponseContentType={override_type}")
        print(f"   URL: {presigned_typed[:100]}...")
        
        resp = requests.get(presigned_typed, timeout=10)
        resp.raise_for_status()
        print(f"   ✓ Presigned URL is accessible")
        print(f"   - Response Content-Type: {resp.headers.get('content-type')}")
        
        # Try to verify it's a valid image
        try:
            from PIL import Image
            img = Image.open(BytesIO(resp.content))
            print(f"   ✓ PIL can open image: {img.format} {img.size} {img.mode}")
        except ImportError:
            print(f"   ⚠ PIL not installed, cannot verify image (pip install pillow)")
        except Exception as img_err:
            print(f"   ✗ PIL cannot open image: {img_err}")
            
    except Exception as e:
        print(f"   ✗ ERROR: Presigned URL with ResponseContentType failed: {e}")
    
    # 5. Recommendations
    print("\n" + "=" * 70)
    print("RECOMMENDATIONS:")
    print("=" * 70)
    
    if not content_type or content_type == 'binary/octet-stream':
        print("⚠ ISSUE: S3 object has no Content-Type metadata")
        print("  FIX: Re-upload with correct Content-Type")
        print(f"  Command: aws s3 cp s3://{bucket}/{key} s3://{bucket}/{key} \\")
        print(f"           --content-type '{override_type}' --metadata-directive REPLACE")
    
    if is_valid_image and detected_type and content_type != detected_type:
        print(f"⚠ ISSUE: Content-Type mismatch")
        print(f"  - Stored: {content_type}")
        print(f"  - Actual: {detected_type}")
        print(f"  FIX: Update metadata to match actual type")
    
    print("\n✓ Use the presigned URL with ResponseContentType parameter:")
    print(f"  {presigned_typed}")
    
    return True

def check_image_magic_bytes(data):
    """Check if data starts with known image format magic bytes."""
    if len(data) < 16:
        return False, None
    
    # JPEG
    if data[:2] == b'\xff\xd8':
        return True, 'image/jpeg'
    # PNG
    if data[:8] == b'\x89PNG\r\n\x1a\n':
        return True, 'image/png'
    # GIF
    if data[:6] in (b'GIF87a', b'GIF89a'):
        return True, 'image/gif'
    # WebP
    if data[8:12] == b'WEBP':
        return True, 'image/webp'
    # BMP
    if data[:2] == b'BM':
        return True, 'image/bmp'
    # TIFF
    if data[:2] in (b'II', b'MM'):
        return True, 'image/tiff'
    
    return False, None

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python diagnose_s3_images.py BUCKET KEY")
        print("Example: python diagnose_s3_images.py my-bucket abc123_image.jpg")
        sys.exit(1)
    
    bucket = sys.argv[1]
    key = sys.argv[2]
    
    success = diagnose_s3_object(bucket, key)
    sys.exit(0 if success else 1)
