#!/bin/bash
# EnergyPlus v0.4 Webhook Test Script (Bash)
# Usage: ./test-webhook.sh [-t] [-s <scenario>]
#
# -t: Use n8n test webhook URL instead of production webhook URL
# -s: Skip menu and run specific scenario (1-5)

set -e

# Configuration
N8N_BASE="https://n8n.panicle.org"
WEBHOOK_PATH="energyplus-building"
TEST_MODE=false
SCENARIO=0

# Parse arguments
while getopts "ts:" opt; do
    case $opt in
        t) TEST_MODE=true ;;
        s) SCENARIO=$OPTARG ;;
        *) echo "Usage: $0 [-t] [-s <scenario>]"; exit 1 ;;
    esac
done

# Set webhook URL
if [ "$TEST_MODE" = true ]; then
    WEBHOOK_URL="${N8N_BASE}/webhook-test/${WEBHOOK_PATH}"
    echo -e "\n\033[33m[TEST MODE] Using n8n test webhook URL\033[0m"
else
    WEBHOOK_URL="${N8N_BASE}/webhook/${WEBHOOK_PATH}"
    echo -e "\n\033[32m[PRODUCTION] Using production webhook URL\033[0m"
fi

echo -e "\033[36mWebhook URL: ${WEBHOOK_URL}\033[0m\n"

# Generate timestamp for session_id
TIMESTAMP=$(date '+%Y-%m-%d_%H-%M')

# Define scenario JSON bodies
scenario_1() {
    cat <<EOF
{
  "session_id": "Test_Cambridge-${TIMESTAMP}",
  "analysis_type": "Building",
  "latitude": 52.2053,
  "longitude": 0.1218,
  "location_name": "Cambridge_UK",
  "project_name": "Cambridge Test Data Center",
  "building_type": "manufacturing",
  "data_center": { "rack_count": 25, "watts_per_rack": 2000 },
  "simulation": { "annual": false, "design_day": true },
  "export": { "supabase": true, "google_drive": false }
}
EOF
}

scenario_2() {
    cat <<EOF
{
  "session_id": "Test_London-${TIMESTAMP}",
  "analysis_type": "Building",
  "latitude": 51.5074,
  "longitude": -0.1278,
  "location_name": "London_UK",
  "project_name": "London Office Building",
  "building_type": "manufacturing",
  "data_center": { "rack_count": 10, "watts_per_rack": 1500 },
  "simulation": { "annual": false, "design_day": true },
  "export": { "supabase": true, "google_drive": false }
}
EOF
}

scenario_3() {
    cat <<EOF
{
  "session_id": "Test_Frankfurt-${TIMESTAMP}",
  "analysis_type": "Building",
  "latitude": 50.1109,
  "longitude": 8.6821,
  "location_name": "Frankfurt_DE",
  "project_name": "Frankfurt Data Center",
  "building_type": "manufacturing",
  "data_center": { "rack_count": 50, "watts_per_rack": 3000 },
  "simulation": { "annual": true, "design_day": false },
  "export": { "supabase": false, "google_drive": false }
}
EOF
}

scenario_4() {
    cat <<EOF
{
  "session_id": "Test_Cambridge-${TIMESTAMP}",
  "analysis_type": "Building",
  "latitude": 52.2053,
  "longitude": 0.1218,
  "location_name": "Cambridge_UK",
  "project_name": "Cambridge Factory",
  "building_type": "manufacturing",
  "data_center": { "rack_count": 25, "watts_per_rack": 2000 },
  "simulation": { "annual": false, "design_day": true },
  "export": { "supabase": true, "google_drive": false }
}
EOF
}

# Show menu or use provided scenario
if [ "$SCENARIO" -eq 0 ]; then
    echo "========================================"
    echo " EnergyPlus v0.4 Webhook Test Scenarios"
    echo "========================================"
    echo ""
    echo "  1) Cambridge UK Data Center (Design Day)"
    echo "  2) London Office (Design Day)"
    echo "  3) Frankfurt DC (Annual Simulation)"
    echo "  4) Cambridge Factory (Supabase Export)"
    echo "  5) Custom JSON"
    echo ""
    read -p "Select scenario (1-5): " SCENARIO
fi

# Get JSON body based on scenario
case $SCENARIO in
    1)
        echo -e "\n\033[35mScenario: Cambridge UK Data Center (Design Day)\033[0m"
        JSON_BODY=$(scenario_1)
        ;;
    2)
        echo -e "\n\033[35mScenario: London Office (Design Day)\033[0m"
        JSON_BODY=$(scenario_2)
        ;;
    3)
        echo -e "\n\033[35mScenario: Frankfurt DC (Annual Simulation)\033[0m"
        JSON_BODY=$(scenario_3)
        ;;
    4)
        echo -e "\n\033[35mScenario: No Supabase Export (Cambridge)\033[0m"
        JSON_BODY=$(scenario_4)
        ;;
    5)
        echo -e "\n\033[33mEnter custom JSON body (press Ctrl+D when done):\033[0m"
        JSON_BODY=$(cat)
        # Validate JSON
        if ! echo "$JSON_BODY" | python3 -m json.tool > /dev/null 2>&1; then
            echo -e "\033[31mInvalid JSON!\033[0m"
            exit 1
        fi
        echo -e "\033[32mJSON validated successfully.\033[0m"
        ;;
    *)
        echo -e "\033[31mInvalid scenario. Please select 1-5.\033[0m"
        exit 1
        ;;
esac

# Display request
echo -e "\033[90m--- Request Body ---\033[0m"
echo "$JSON_BODY" | python3 -m json.tool 2>/dev/null || echo "$JSON_BODY"
echo -e "\033[90m--------------------\033[0m\n"

# Send webhook request
echo -e "\033[36mSending POST to ${WEBHOOK_URL} ...\033[0m\n"

START_TIME=$(date +%s)

HTTP_RESPONSE=$(curl -s -w "\n%{http_code}" \
    -X POST \
    -H "Content-Type: application/json" \
    -d "$JSON_BODY" \
    --max-time 600 \
    "$WEBHOOK_URL")

END_TIME=$(date +%s)
ELAPSED=$((END_TIME - START_TIME))

# Split response body and status code
HTTP_CODE=$(echo "$HTTP_RESPONSE" | tail -n 1)
RESPONSE_BODY=$(echo "$HTTP_RESPONSE" | sed '$d')

if [ "$HTTP_CODE" -ge 200 ] && [ "$HTTP_CODE" -lt 300 ]; then
    echo -e "\033[32m=== Response (${ELAPSED}s, HTTP ${HTTP_CODE}) ===\033[0m"
    echo "$RESPONSE_BODY" | python3 -m json.tool 2>/dev/null || echo "$RESPONSE_BODY"

    # Display summary if available
    WORKFLOW_NAME=$(echo "$RESPONSE_BODY" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('workflow_name',''))" 2>/dev/null || echo "")
    if [ -n "$WORKFLOW_NAME" ]; then
        SESSION_ID=$(echo "$RESPONSE_BODY" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('session_id',''))" 2>/dev/null)
        ANALYSIS_TYPE=$(echo "$RESPONSE_BODY" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('analysis_type',''))" 2>/dev/null)
        STATUS=$(echo "$RESPONSE_BODY" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('status',''))" 2>/dev/null)
        PROJECT=$(echo "$RESPONSE_BODY" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('project_name',''))" 2>/dev/null)
        LOCATION=$(echo "$RESPONSE_BODY" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('location',''))" 2>/dev/null)

        echo -e "\n\033[36m--- Summary ---\033[0m"
        echo "  Workflow:    $WORKFLOW_NAME"
        echo "  Status:      $STATUS"
        echo "  Session:     $SESSION_ID"
        echo "  Analysis:    $ANALYSIS_TYPE"
        echo "  Project:     $PROJECT"
        echo "  Location:    $LOCATION"
        echo -e "\033[36m---------------\033[0m"
    fi
else
    echo -e "\033[31m=== Request Failed (${ELAPSED}s, HTTP ${HTTP_CODE}) ===\033[0m"
    echo "$RESPONSE_BODY" | python3 -m json.tool 2>/dev/null || echo "$RESPONSE_BODY"
    exit 1
fi
