#!/usr/bin/env bash
# Sends wallet-spa's 7 requests exactly as written in src/store/*.js (lowercase paths, FormData bodies)
# to accounts-api and records which controller action ASP.NET routed each one to.
export PATH="/Applications/Docker.app/Contents/Resources/bin:$PATH"
B=${1:-http://localhost:5080}
n=0
req() {  # $1 = SPA function, rest = curl args
  local fn=$1; shift; n=$((n+1))
  local before=$(docker logs ms078-api 2>&1 | wc -l)
  local out=$(curl -s -w '\n%{http_code}' "$@")
  sleep 1
  local ep=$(docker logs ms078-api 2>&1 | tail -n +$((before+1)) | grep -oE "Executing endpoint '[^']+'" | head -1 | sed "s/Executing endpoint //")
  printf '%s. %-13s %-62s HTTP %s  -> %s\n' "$n" "$fn" "$(echo "$@" | grep -oE '(-X [A-Z]+ )?[^ ]*/api/[^ ]*' | sed "s|$B||")" "$(echo "$out" | tail -1)" "$ep"
  BODY=$(echo "$out" | sed '$d')
}
req getAccounts "$B/api/v1/accounts";                              ID=$(echo "$BODY" | python3 -c 'import sys,json;print(json.load(sys.stdin)["accounts"][0]["accountId"])')
req getAccount  "$B/api/v1/accounts/$ID"
req openAccount -X POST "$B/api/v1/accounts" -F amount=100 -F currency=USD; NEW=$(echo "$BODY" | python3 -c 'import sys,json;print(json.load(sys.stdin)["account"]["accountId"])')
req deposit     -X PATCH "$B/api/v1/transactions/$NEW/deposit" -F amount=50 -F currency=USD
req withdraw    -X PATCH "$B/api/v1/transactions/$NEW/withdraw" -F amount=20 -F currency=USD
req transfer    -X PATCH "$B/api/v1/transactions/$NEW/$ID" -F amount=130 -F currency=USD
req closeAccount -X DELETE "$B/api/v1/accounts/$NEW"
