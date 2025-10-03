#!/usr/bin/env python3
"""
Test script to verify S3 image uploads work correctly.
This helps diagnose if images are corrupted during upload.
"""
import os
import sys
import hashlib
import mimetypes
from urllib.parse import urlparse, unquote
import boto3
from botocore.config import Config as BotoConfig
from botocore.exceptions import ClientError

def test_upload(test_url="https://via.placeholder.com/150", bucket=None):
    """Download a test image and upload to S3 to verify it works."""
    import requests
    
    if not bucket:
        bucket = os.getenv("S3_UPLOAD_BUCKET") or os.getenv("BUCKET_NAME")
    
    if not bucket:
        print("ERROR: No S3 bucket specified. Set S3_UPLOAD_BUCKET or BUCKET_NAME env var")
        return False
    
    # Download test image
    print(f"Downloading test image from: {test_url}")
    try:
        resp = requests.get(test_url, timeout=10)
        resp.raise_for_status()
        image_bytes = resp.content
        print(f"✓ Downloaded {len(image_bytes)} bytes")
        print(f"  Content-Type from response: {resp.headers.get('content-type')}")
        print(f"  Data type: {type(image_bytes)}")
        print(f"  First 16 bytes (hex): {image_bytes[:16].hex()}")
    except Exception as e:
        print(f"✗ Failed to download: {e}")
        return False
    
    # Upload to S3 (mimic handler logic)
    region = os.getenv("REGION") or os.getenv("AWS_DEFAULT_REGION") or "ap-southeast-2"
    s3_config = BotoConfig(signature_version="s3v4", region_name=region)
    s3_client = boto3.client("s3", config=s3_config)
    
    # Create key name like handler does
    parsed_name = urlparse(test_url).path.split("/")[-1] or "test_image.png"
    parsed_name = unquote(parsed_name)
    sha = hashlib.sha256(test_url.encode("utf-8")).hexdigest()[:10]
    key = f"test/{sha}_{parsed_name}"
    
    # Guess content type
    content_type = mimetypes.guess_type(parsed_name)[0] or "image/png"
    print(f"\nUploading to S3:")
    print(f"  Bucket: {bucket}")
    print(f"  Key: {key}")
    print(f"  Content-Type: {content_type}")
    print(f"  Size: {len(image_bytes)} bytes")
    
    try:
        # Try with ACL first, fallback without if bucket blocks ACLs
        put_kwargs = {
            "Bucket": bucket,
            "Key": key,
            "Body": image_bytes,
            "ContentType": content_type
        }
        try:
            s3_client.put_object(**put_kwargs, ACL="private")
            print("✓ Uploaded with ACL=private")
        except ClientError as acl_err:
            if "AccessControlListNotSupported" in str(acl_err):
                s3_client.put_object(**put_kwargs)
                print("✓ Uploaded without ACL (bucket has BPA enabled)")
            else:
                raise
        
        # Generate presigned URL
        presigned = s3_client.generate_presigned_url(
            "get_object",
            Params={"Bucket": bucket, "Key": key},
            ExpiresIn=3600
        )
        print(f"✓ Presigned URL: {presigned}")
        
        # Verify by downloading back
        print("\nVerifying upload by downloading back...")
        verify_resp = s3_client.get_object(Bucket=bucket, Key=key)
        downloaded_bytes = verify_resp["Body"].read()
        print(f"✓ Downloaded {len(downloaded_bytes)} bytes from S3")
        print(f"  Content-Type from S3: {verify_resp.get('ContentType')}")
        
        if downloaded_bytes == image_bytes:
            print("✓ SUCCESS: Bytes match! Upload/download working correctly")
            print(f"\nYou can test opening the image at: {presigned}")
            return True
        else:
            print(f"✗ FAILURE: Bytes don't match!")
            print(f"  Original: {len(image_bytes)} bytes")
            print(f"  Downloaded: {len(downloaded_bytes)} bytes")
            return False
            
    except Exception as e:
        print(f"✗ Upload failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    test_url = sys.argv[1] if len(sys.argv) > 1 else "https://via.placeholder.com/150"
    bucket = sys.argv[2] if len(sys.argv) > 2 else None
    
    print("S3 Image Upload Test")
    print("=" * 60)
    success = test_upload(test_url, bucket)
    sys.exit(0 if success else 1)
