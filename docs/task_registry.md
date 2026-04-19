# Task Registry

The task registry is a rule-driven mapping from reading-list fixture items to
`ReferenceTask` types. Rules are small predicates that inspect table headings,
column names, and other contextual signals.

Registry responsibilities:
- Determine applicable tasks for a given page/table
- Provide parser hooks that emit extraction objects
- Be deterministic and unit-testable
