#!/bin/bash
# Check if local main is behind jwforres/rfe-creator main
UPSTREAM_URL="https://github.com/jwforres/rfe-creator.git"

UPSTREAM_MAIN=$(git ls-remote "$UPSTREAM_URL" refs/heads/main 2>/dev/null | cut -f1) || exit 0
[ -z "$UPSTREAM_MAIN" ] && exit 0

LOCAL_MAIN=$(git rev-parse main 2>/dev/null) || exit 0

if [ "$LOCAL_MAIN" = "$UPSTREAM_MAIN" ]; then
  echo "OK: local main is up to date with upstream."
  exit 0
fi

# Check if upstream commit is an ancestor (local is ahead or diverged) vs behind
if git merge-base --is-ancestor "$UPSTREAM_MAIN" main 2>/dev/null; then
  echo "OK: local main is ahead of upstream (or equal)."
  exit 0
fi

echo "WARNING: Your local 'main' branch is behind https://github.com/jwforres/rfe-creator main."
echo "Consider running: git pull <upstream-remote> main (on your main branch)"
