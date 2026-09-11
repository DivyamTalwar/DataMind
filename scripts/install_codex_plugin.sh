#!/usr/bin/env bash
set -euo pipefail

# Install the Codex adapter that ships with this DataMind checkout.
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd -P)"
exec "${REPO_ROOT}/plugins/datamind-context/install.sh" --repo-root "${REPO_ROOT}" "$@"
