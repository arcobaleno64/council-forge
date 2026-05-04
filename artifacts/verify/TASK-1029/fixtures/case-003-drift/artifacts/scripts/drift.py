# Fixture for TASK-1029 case-003 (post-baseline source/template drift) - SOURCE side.
# Source and template both exist but content differs. QC-SYNC-001 Pass 2 must
# classify this as a blocking failure with reason_code post_baseline_new_pair_drift.
DRIFT_SIDE = "source"
DRIFT_VALUE = "case-003-source-content"
