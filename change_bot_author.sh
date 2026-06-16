#!/bin/bash

# Configuration for new author
CORRECT_NAME="toxicbishop"
CORRECT_EMAIL="pranavarun19@gmail.com"

git filter-branch -f --env-filter '
# Match any of the specified bot names
if [ "$GIT_COMMITTER_NAME" = "dependabot[bot]" ] || \
   [ "$GIT_COMMITTER_NAME" = "copilot-swe-agent[bot]" ] || \
   [ "$GIT_COMMITTER_NAME" = "Copilot" ] || \
   [ "$GIT_COMMITTER_NAME" = "github-advanced-security[bot]" ]; then
    export GIT_COMMITTER_NAME="$CORRECT_NAME"
    export GIT_COMMITTER_EMAIL="$CORRECT_EMAIL"
fi

if [ "$GIT_AUTHOR_NAME" = "dependabot[bot]" ] || \
   [ "$GIT_AUTHOR_NAME" = "copilot-swe-agent[bot]" ] || \
   [ "$GIT_AUTHOR_NAME" = "Copilot" ] || \
   [ "$GIT_AUTHOR_NAME" = "github-advanced-security[bot]" ]; then
    export GIT_AUTHOR_NAME="$CORRECT_NAME"
    export GIT_AUTHOR_EMAIL="$CORRECT_EMAIL"
fi
' --tag-name-filter cat -- --branches --tags
