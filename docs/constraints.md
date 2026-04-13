 # Project constraints

 - Reading List (Notion) is immutable and is the canonical source of truth.
 - All writes must go to: local snapshots, fixtures, or staging Notion structures.
 - No destructive migration or in-place edits of Reading List pages.
 - Any ambiguous mapping must be documented and escalated before structural changes.
