#!/usr/bin/env bash
# Exercises every MS020 REST endpoint through the Zuul gateway as a browser user would,
# one step at a time, so each runtime effect can be attributed to a single request.
G=${1:-localhost:4000}
U=ravi$RANDOM; P=password1
step() { echo; echo "### STEP $1  $(date -u +%H:%M:%S)"; }
call() { echo "\$ curl $*"; curl -s -w '  [HTTP %{http_code}]\n' "$@" | cut -c1-300; echo; }

step "1 createNewAccount $U (expect: account -> auth POST /uaa/users)"
call -X POST "http://$G/accounts/" -H 'Content-Type: application/json' -d "{\"username\":\"$U\",\"password\":\"$P\"}"
sleep 2

step "2 login: password grant via gateway (OAuth2 plumbing, excluded D3)"
TOKEN=$(curl -s -X POST "http://$G/uaa/oauth/token" -u browser: -d "grant_type=password&scope=ui&username=$U&password=$P" \
  | python3 -c 'import sys,json;print(json.load(sys.stdin)["access_token"])')
echo "token acquired: ${TOKEN:0:8}..."
A="Authorization: Bearer $TOKEN"

step "3 getUser via gateway (auth-service, no cross-service effect)"
call "http://$G/uaa/users/current" -H "$A"

step "4 getCurrentAccount (expect: only token validation account -> auth, excluded D3)"
call "http://$G/accounts/current" -H "$A"

step "5 saveCurrentAccount (expect: account -> statistics PUT /statistics/$U)"
call -X PUT "http://$G/accounts/current" -H "$A" -H 'Content-Type: application/json' -d '{
  "incomes":[{"title":"Salary","amount":4000,"currency":"USD","period":"MONTH","icon":"wallet"}],
  "expenses":[{"title":"Rent","amount":1200,"currency":"EUR","period":"MONTH","icon":"home"}],
  "saving":{"amount":1500,"currency":"USD","interest":3.5,"deposit":true,"capitalization":false},
  "note":"runtime check"}'
sleep 3

step "6 getCurrentAccountStatistics (no cross-service effect beyond token validation)"
call "http://$G/statistics/current" -H "$A"

step "7 getAccountByName demo / getStatisticsByAccountName demo (public demo account)"
call "http://$G/accounts/demo" -H "$A"
call "http://$G/statistics/demo" -H "$A"

step "8 saveCurrentNotificationsSettings with BACKUP due (sets up scheduled notification -> account call)"
call -X PUT "http://$G/notifications/recipients/current" -H "$A" -H 'Content-Type: application/json' -d '{
  "email":"ravi@example.com",
  "scheduledNotifications":{
    "BACKUP":{"active":true,"frequency":"WEEKLY","lastNotified":"2020-01-01T00:00:00.000+0000"},
    "REMIND":{"active":false,"frequency":"WEEKLY"}}}'

step "9 getCurrentNotificationsSettings"
call "http://$G/notifications/recipients/current" -H "$A"

step "10 wait for backup cron (every minute; expect: notification -> account GET /accounts/$U)"
sleep 130
echo; echo "### DONE $(date -u +%H:%M:%S)  user=$U"
