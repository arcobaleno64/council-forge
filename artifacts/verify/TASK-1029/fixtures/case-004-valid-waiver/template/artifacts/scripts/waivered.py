# Fixture for TASK-1029 case-004 (valid unexpired waiver covers post-baseline drift) - TEMPLATE.
# Source and template differ; the synthetic policy provides a six-field waiver with
# expires_at in the future. QC-SYNC-001 must downgrade to skipped_with_reason_code.
DRIFT_SIDE = "template"
DRIFT_VALUE = "case-004-template-content"
