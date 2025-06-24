#!/bin/bash
# Review and merge Dependabot PRs for DEAN repository

echo "=== Dependabot PR Review Process ==="
echo "This script helps review and process Dependabot pull requests"
echo

# Check if gh CLI is installed
if ! command -v gh &> /dev/null; then
    echo "Error: GitHub CLI (gh) is not installed."
    echo "Install with: brew install gh"
    echo "Then authenticate with: gh auth login"
    exit 1
fi

# Get all Dependabot PR numbers
echo "Fetching Dependabot PRs..."
PR_DATA=$(gh pr list --author "app/dependabot" --json number,title,createdAt,url 2>/dev/null)

if [ $? -ne 0 ]; then
    echo "Error: Failed to fetch PRs. Make sure you're in the DEAN repository and authenticated with gh."
    exit 1
fi

# Count PRs
PR_COUNT=$(echo "$PR_DATA" | jq length)
echo "Found $PR_COUNT Dependabot PRs"
echo

if [ "$PR_COUNT" -eq 0 ]; then
    echo "No Dependabot PRs to process!"
    exit 0
fi

# Process each PR
echo "$PR_DATA" | jq -r '.[] | @base64' | while read -r pr_encoded; do
    # Decode PR data
    pr_json=$(echo "$pr_encoded" | base64 --decode)
    pr_number=$(echo "$pr_json" | jq -r '.number')
    pr_title=$(echo "$pr_json" | jq -r '.title')
    pr_date=$(echo "$pr_json" | jq -r '.createdAt' | cut -d'T' -f1)
    pr_url=$(echo "$pr_json" | jq -r '.url')
    
    echo "----------------------------------------"
    echo "PR #$pr_number: $pr_title"
    echo "Created: $pr_date"
    echo "URL: $pr_url"
    echo
    
    # Get more details
    echo "Fetching PR details..."
    PR_DETAILS=$(gh pr view $pr_number --json files,additions,deletions,mergeable,reviews)
    
    files_changed=$(echo "$PR_DETAILS" | jq '.files | length')
    additions=$(echo "$PR_DETAILS" | jq '.additions')
    deletions=$(echo "$PR_DETAILS" | jq '.deletions')
    mergeable=$(echo "$PR_DETAILS" | jq -r '.mergeable')
    
    echo "Files changed: $files_changed"
    echo "Lines added: $additions, removed: $deletions"
    echo "Mergeable: $mergeable"
    echo
    
    # Show options
    echo "Options:"
    echo "1) Merge this PR"
    echo "2) Close this PR" 
    echo "3) Skip to next"
    echo "4) View full diff"
    echo "5) Exit review"
    
    read -p "Choice (1-5): " choice
    
    case $choice in
        1)
            echo "Merging PR #$pr_number..."
            gh pr merge $pr_number --merge --auto
            if [ $? -eq 0 ]; then
                echo "✅ Successfully merged PR #$pr_number"
            else
                echo "❌ Failed to merge PR #$pr_number"
            fi
            ;;
        2)
            read -p "Are you sure you want to close PR #$pr_number? (y/N): " confirm
            if [[ $confirm =~ ^[Yy]$ ]]; then
                echo "Closing PR #$pr_number..."
                gh pr close $pr_number
                echo "✅ Closed PR #$pr_number"
            else
                echo "Skipping close operation"
            fi
            ;;
        3)
            echo "Skipping PR #$pr_number..."
            ;;
        4)
            echo "Showing diff for PR #$pr_number..."
            gh pr diff $pr_number
            echo
            read -p "Press Enter to continue..."
            # Re-show the same PR
            continue
            ;;
        5)
            echo "Exiting review process"
            break
            ;;
        *)
            echo "Invalid choice, skipping..."
            ;;
    esac
    
    echo
done

echo
echo "=== Review Summary ==="
echo "Remaining Dependabot PRs:"
gh pr list --author dependabot --json number,title --jq '.[] | "PR #\(.number): \(.title)"'
echo
echo "Review complete!"