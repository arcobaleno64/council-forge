# Fixture for TASK-1029 case-004 (valid unexpired waiver covers post-baseline drift) - SOURCE.
# Source and template differ; the synthetic policy provides a six-field waiver with
# expires_at in the future. QC-SYNC-001 must downgrade to skipped_with_reason_code with
# reason_code post_baseline_new_pair_waivered_until:<expires_at>.
DRIFT_SIDE = "source"
DRIFT_VALUE = "case-004-source-content"
