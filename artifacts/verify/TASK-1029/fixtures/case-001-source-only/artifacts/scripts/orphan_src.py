# Fixture for TASK-1029 case-001 (post-baseline source-only addition).
# This file simulates a NEW source script that has no template mirror counterpart
# under template/artifacts/scripts/. QC-SYNC-001 Pass 2 must classify this as
# a blocking failure with reason_code post_baseline_new_pair_missing_template.
ORPHAN_SOURCE_MARKER = "TASK-1029 case-001 orphan source"
