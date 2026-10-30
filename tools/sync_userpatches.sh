#!/bin/bash
# Project userpatches/ is the source of truth; push it into the Armbian build tree before a build.
set -e
# --delete: files removed from the project must not linger in the build tree (Armbian recreates its skeleton).
rsync -a --delete --exclude=__pycache__ --itemize-changes "$(dirname "$(readlink -f "$0")")/../userpatches/" ~/mangopi_mqpro/build/userpatches/
