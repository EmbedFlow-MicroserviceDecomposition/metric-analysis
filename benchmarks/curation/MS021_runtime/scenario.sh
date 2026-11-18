#!/usr/bin/env bash
# Browses every TeaStore webui page as a shopper and an admin would (cookie session), one step at a time,
# so each burst of inter-service traffic can be attributed to the webui request that caused it.
W=${1:-http://localhost:8080/tools.descartes.teastore.webui}
J=$(mktemp)  # cookie jar (TeaStore keeps the session blob in cookies)
step() { echo; echo "### STEP $1  $(date -u +%H:%M:%S)"; }
get()  { curl -s -b $J -c $J -o /tmp/ms021_page.html -w "  GET  $1 -> HTTP %{http_code}\n" "$W$1"; }
post() { local p=$1; shift; curl -s -b $J -c $J -o /tmp/ms021_page.html -w "  POST $p $* -> HTTP %{http_code}\n" -X POST "$W$p" "$@"; }

step "1 index, login page";            get /; get /login
CAT=$(grep -oE 'category\?category=[0-9]+' /tmp/ms021_page.html | head -1 | grep -oE '[0-9]+$'); echo "  category id: $CAT"
step "2 login as user1";               post /loginAction -d username=user1 -d password=password
step "3 category page + page size";    get "/category?category=$CAT&page=1"
PIDS=($(grep -oE 'product\?id=[0-9]+' /tmp/ms021_page.html | grep -oE '[0-9]+$' | sort -un | head -2)); echo "  product ids: ${PIDS[*]}"
post /category -d number=20 -d page=1 -d category=$CAT
step "4 product page";                 get "/product?id=${PIDS[0]}"
step "5 cart: add two, update, remove one"
post /cartAction -d addToCart= -d productid=${PIDS[0]}
post /cartAction -d addToCart= -d productid=${PIDS[1]}
get /cart
post /cartAction -d updateCartQuantities= -d orderitem_${PIDS[0]}=3 -d orderitem_${PIDS[1]}=1
post /cartAction -d removeProduct_${PIDS[1]}=
step "6 checkout and confirm order"
post /cartAction -d proceedtoCheckout=
get /order
post /order
post /cartAction -d firstname=User -d lastname=User -d adress1=Road -d adress2=City -d cardtype=volvo -d cardnumber=314159265359 -d expirydate=12/2050 -d confirm=Confirm
step "7 profile, about, status, database, error pages"
get /profile; get /about; get /status; get /database; get /error
step "8 regenerate database (admin)";  get "/dataBaseAction?categories=2&products=5&users=5&orders=3&confirm=Start"
sleep 45
step "9 status after regeneration";    get /status
step "10 logout";                      post /loginAction -d logout=
echo; echo "### DONE $(date -u +%H:%M:%S)"; rm -f $J
