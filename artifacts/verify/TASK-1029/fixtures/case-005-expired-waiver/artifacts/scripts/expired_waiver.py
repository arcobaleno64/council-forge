# Fixture for TASK-1029 case-005 (expired waiver does not cover post-baseline drift) - SOURCE.
# Source and template differ; the synthetic policy provides a waiver with expires_at in the past.
# QC-SYNC-001 must remain blocking failure with reason_code
# post_baseline_new_pair_waiver_invalid:expired:<expires_at>.
DRIFT_SIDE = "source"
DRIFT_VALUE = "case-005-source-content"
