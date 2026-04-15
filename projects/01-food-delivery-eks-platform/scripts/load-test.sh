#!/usr/bin/env bash
set -euo pipefail

BASE_URL="${BASE_URL:-http://localhost:8080}"
TOTAL_REQUESTS="${TOTAL_REQUESTS:-300}"
CONCURRENCY="${CONCURRENCY:-10}"
DURATION_MINUTES=3

echo "============================================"
echo "  FoodRush — Load Test"
echo "  Target:       ${BASE_URL}"
echo "  Requests:     ${TOTAL_REQUESTS}"
echo "  Concurrency:  ${CONCURRENCY}"
echo "  Duration:     ~${DURATION_MINUTES} minutes"
echo "============================================"

SUCCESS_COUNT=0
FAIL_COUNT=0
START_TIME=$(date +%s)

# Pick a random menu item that we know exists (Butter Chicken, id=1, from restaurant 1)
ORDER_PAYLOAD='{
  "user_id": 1,
  "restaurant_id": 1,
  "items": [
    {"menu_item_id": 1, "name": "Butter Chicken", "quantity": 1, "unit_price": 16.99}
  ],
  "delivery_address": "Load Test Ave, Brooklyn, NY 11201"
}'

send_order() {
  local status
  status=$(curl -s -o /dev/null -w "%{http_code}" \
    -X POST "${BASE_URL}/api/orders" \
    -H "Content-Type: application/json" \
    -d "${ORDER_PAYLOAD}" \
    --connect-timeout 5 \
    --max-time 10 || echo "000")
  echo "${status}"
}

echo "Starting load test at $(date)..."
echo ""

batch=0
while [ $((SUCCESS_COUNT + FAIL_COUNT)) -lt $TOTAL_REQUESTS ]; do
  batch=$((batch + 1))
  batch_success=0
  batch_fail=0

  # Fire CONCURRENCY requests in parallel
  pids=()
  tmpfiles=()
  for j in $(seq 1 $CONCURRENCY); do
    remaining=$((TOTAL_REQUESTS - SUCCESS_COUNT - FAIL_COUNT))
    if [ $remaining -le 0 ]; then
      break
    fi
    tmpfile=$(mktemp)
    tmpfiles+=("$tmpfile")
    send_order > "$tmpfile" &
    pids+=($!)
  done

  for i in "${!pids[@]}"; do
    wait "${pids[$i]}" 2>/dev/null || true
    status=$(cat "${tmpfiles[$i]}" 2>/dev/null || echo "000")
    rm -f "${tmpfiles[$i]}"
    if [ "$status" = "200" ] || [ "$status" = "201" ]; then
      SUCCESS_COUNT=$((SUCCESS_COUNT + 1))
      batch_success=$((batch_success + 1))
    else
      FAIL_COUNT=$((FAIL_COUNT + 1))
      batch_fail=$((batch_fail + 1))
    fi
  done

  total_done=$((SUCCESS_COUNT + FAIL_COUNT))
  elapsed=$(( $(date +%s) - START_TIME ))
  rps=$(echo "scale=1; ${total_done} / (${elapsed} + 1)" | bc 2>/dev/null || echo "?")

  printf "  Batch %3d | Progress: %3d/%d | Success: %3d | Failed: %3d | %.1f req/s\n" \
    "$batch" "$total_done" "$TOTAL_REQUESTS" "$SUCCESS_COUNT" "$FAIL_COUNT" "${rps:-0}"
done

END_TIME=$(date +%s)
ELAPSED=$((END_TIME - START_TIME))
TOTAL_DONE=$((SUCCESS_COUNT + FAIL_COUNT))

echo ""
echo "============================================"
echo "  Load Test Complete"
echo "============================================"
printf "  Total Requests:   %d\n" "$TOTAL_DONE"
printf "  Successful (2xx): %d  (%.1f%%)\n" "$SUCCESS_COUNT" "$(echo "scale=1; ${SUCCESS_COUNT} * 100 / ${TOTAL_DONE}" | bc)"
printf "  Failed:           %d  (%.1f%%)\n" "$FAIL_COUNT" "$(echo "scale=1; ${FAIL_COUNT} * 100 / ${TOTAL_DONE}" | bc)"
printf "  Elapsed:          %ds\n" "$ELAPSED"
printf "  Avg req/s:        %.1f\n" "$(echo "scale=1; ${TOTAL_DONE} / (${ELAPSED} + 1)" | bc)"
echo "============================================"
echo ""
echo "Check Grafana at http://localhost:3000 to see the traffic spike!"
echo "  Dashboard: Food Delivery Platform"
echo "  Panel: Order Throughput / Error Rate"
