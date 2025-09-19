#!/usr/bin/env bash
set -euo pipefail

# Test deployment helper for aws-lambda-crawler
# Usage: ./scripts/test_deploy.sh [--profile PROFILE] [--stack STACK_NAME] [--region REGION]

PROFILE_ARG=""
STACK_NAME="aws-lambda-crawler"
REGION="ap-southeast-2"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --profile)
      PROFILE_ARG="--profile $2"
      shift 2
      ;;
    --stack)
      STACK_NAME="$2"
      shift 2
      ;;
    --region)
      REGION="$2"
      shift 2
      ;;
    -h|--help)
      echo "Usage: $0 [--profile PROFILE] [--stack STACK_NAME] [--region REGION]"
      exit 0
      ;;
    *)
      echo "Unknown arg: $1"
      echo "Usage: $0 [--profile PROFILE] [--stack STACK_NAME] [--region REGION]"
      exit 1
      ;;
  esac
done

echo "Using stack: $STACK_NAME  region: $REGION ${PROFILE_ARG}" >&2

echo "Fetching CloudFormation outputs..." >&2
OUTPUTS=$(aws cloudformation describe-stacks --stack-name "$STACK_NAME" --region "$REGION" $PROFILE_ARG --query "Stacks[0].Outputs" --output json 2>/dev/null) || {
  echo "Failed to read CloudFormation outputs for stack $STACK_NAME" >&2
  exit 2
}

if [[ -z "$OUTPUTS" || "$OUTPUTS" == "null" ]]; then
  echo "No outputs found for stack $STACK_NAME" >&2
  exit 3
fi

# Extract the first output value that looks like an API Gateway URL (execute-api),
# otherwise use the first output value.
API_BASE_URL=$(echo "$OUTPUTS" | python3 - <<'PY'
import sys, json, re
data=json.load(sys.stdin)
for item in data:
    v=item.get('OutputValue','')
    if isinstance(v, str) and re.search(r'https?://.+execute-api\.', v):
        print(v.rstrip('/'))
        sys.exit(0)
if data:
    print(data[0].get('OutputValue',''))
    sys.exit(0)
sys.exit(1)
PY
)

if [[ -z "$API_BASE_URL" || "$API_BASE_URL" == "null" ]]; then
  echo "Couldn't determine API base URL from stack outputs." >&2
  echo "Outputs: $OUTPUTS" >&2
  exit 4
fi

echo "Found API base URL: $API_BASE_URL" >&2

TEST_URL='https://vnexpress.net'
echo "Invoking POST $API_BASE_URL/crawl with payload {\"url\":\"$TEST_URL\"}..." >&2
curl -s -X POST "$API_BASE_URL/crawl" -H "Content-Type: application/json" -d "{\"url\": \"$TEST_URL\"}" || echo "curl failed" >&2

echo "\nTailing CloudWatch logs for function 'aws-lambda-crawler' (press Ctrl+C to stop)" >&2
if command -v sam >/dev/null 2>&1; then
  sam logs -n aws-lambda-crawler --stack-name "$STACK_NAME" --tail --profile "${PROFILE_ARG#--profile }" || true
else
  # Fallback to aws logs (requires AWS CLI v2)
  aws logs tail "/aws/lambda/aws-lambda-crawler" --follow --region "$REGION" $PROFILE_ARG || true
fi
