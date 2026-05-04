# Fixture for TASK-1029 case-003 (post-baseline source/template drift) - TEMPLATE side.
# Source and template both exist but content differs. QC-SYNC-001 Pass 2 must
# classify this as a blocking failure with reason_code post_baseline_new_pair_drift.
DRIFT_SIDE = "template"
DRIFT_VALUE = "case-003-template-content"
