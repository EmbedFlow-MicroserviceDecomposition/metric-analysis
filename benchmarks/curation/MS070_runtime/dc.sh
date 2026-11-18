#!/usr/bin/env bash
export PATH="/Applications/Docker.app/Contents/Resources/bin:$PATH"
export BOULDER_TOOLS_TAG=go1.27.2_2026-10-14 BOULDER_VTCOMBOSERVER_TAG=vitessv24.0.3_2026-09-24 BOULDER_SUNLIGHT_TAG=sunlightv0.10.0_2026-09-24
export DOCKER_DEFAULT_PLATFORM=linux/amd64
cd <scratchpad>/runtime_MS070/boulder
exec docker compose -p ms070 "$@"
