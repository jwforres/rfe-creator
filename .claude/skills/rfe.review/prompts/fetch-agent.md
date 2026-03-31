# Fetch Agent Instructions

Fetch Jira issue {KEY} and write artifacts. Steps:

1. Call mcp__atlassian__getJiraIssue with cloudId="https://redhat.atlassian.net", issueIdOrKey="{KEY}", fields=["summary","description","priority","labels","status","comment"], responseContentFormat="markdown". If MCP fails, run: python3 scripts/fetch_issue.py {KEY} --fields summary,description,priority,labels,status,comment --markdown

2. Write the Jira description to artifacts/rfe-tasks/{KEY}.md as-is — preserve the original markdown structure, headings, and content exactly as fetched. Do not restructure, reformat, or fit it into any template. Do not add a title heading — the title lives in frontmatter only.

3. Run: python3 scripts/frontmatter.py schema rfe-task
   Then: python3 scripts/frontmatter.py set artifacts/rfe-tasks/{KEY}.md rfe_id={KEY} title="<title>" priority=<priority> size=<inferred> status=Ready

4. Save a raw copy of just the description to artifacts/rfe-originals/{KEY}.md (create directory if needed). This file is the baseline for before/after analysis and submit-time conflict detection. It is never modified after creation.

5. Write comments to artifacts/rfe-tasks/{KEY}-comments.md formatted as:
   # Comments: {KEY}
   ## <Author> — <date>
   <body>
   If no comments, write "No comments found."
   This file provides stakeholder context. It is NOT part of the RFE content and must NOT be pushed back to Jira during submission.

Do not return a summary. Your work is complete when the output files exist.
