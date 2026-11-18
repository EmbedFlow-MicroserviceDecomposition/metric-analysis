#!/usr/bin/env bash
# Exercises every MS032 REST endpoint through the edge gateway, one step at a time,
# so each runtime effect can be attributed to a single request.
E=${1:-localhost:9000}
step() { echo; echo "### STEP $1  $(date -u +%H:%M:%S)"; }
call() { echo "\$ $*"; curl -s -w '  [HTTP %{http_code}]\n' "$@"; echo; }

step "1 createUser x3 (expect: Kafka user topic -> UserProcessor USER_CREATED)"
IDS=()
for n in "Ada Lovelace" "Alan Turing" "Grace Hopper"; do
  set -- $n
  R=$(curl -s -X POST "http://$E/user/v1/users" -H 'Content-Type: application/json' -d "{\"firstName\":\"$1\",\"lastName\":\"$2\"}")
  echo "$R"; IDS+=($(echo "$R" | python3 -c 'import sys,json;print(json.load(sys.stdin)["id"])'))
done
A=${IDS[0]}; B=${IDS[1]}; C=${IDS[2]}; echo "ids: $A $B $C"
sleep 5

step "2 getUser (expect: no cross-service effect)"
call "http://$E/user/v1/users/$A"

step "3 updateUser (expect: Kafka user topic -> UserProcessor USER_UPDATED)"
call -X PUT "http://$E/user/v1/users/$A" -H 'Content-Type: application/json' -d "{\"id\":$A,\"firstName\":\"Augusta\",\"lastName\":\"Lovelace\"}"
sleep 5

step "4 addFriend 1-2, 2-3 (expect: friend-service GET user-service x2 each; Kafka friend topic -> FriendProcessor FRIEND_ADDED)"
call -X POST "http://$E/friend/v1/users/$A/commands/addFriend?friendId=$B"
call -X POST "http://$E/friend/v1/users/$B/commands/addFriend?friendId=$C"
sleep 5

step "5 getFriend / getFriends (expect: no cross-service effect)"
call "http://$E/friend/v1/friends/$(curl -s "http://$E/friend/v1/users/$A/friends" | python3 -c 'import sys,json;print(json.load(sys.stdin)[0]["id"])')"
call "http://$E/friend/v1/users/$A/friends"

step "6 findMutualFriends 1,3 / recommendFriends 1 (expect: no cross-service effect; data proves Kafka projection)"
call "http://$E/recommendation/v1/users/$A/commands/findMutualFriends?friendId=$C"
call "http://$E/recommendation/v1/users/$A/commands/recommendFriends"

step "7 removeFriend 1-2 (expect: Kafka friend topic -> FriendProcessor FRIEND_REMOVED)"
call -X POST "http://$E/friend/v1/users/$A/commands/removeFriend?friendId=$B"
sleep 5

step "8 addFriend with unknown user 999 (expect: friend-service GET user-service -> 404, no Kafka event)"
call -X POST "http://$E/friend/v1/users/$A/commands/addFriend?friendId=999"
sleep 3
echo; echo "### DONE $(date -u +%H:%M:%S)"
