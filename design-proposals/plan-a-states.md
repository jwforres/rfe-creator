# Plan A — State Transition Diagram

```mermaid
stateDiagram-v2
    direction TB

    [*] --> INIT
    INIT --> BOOTSTRAP
    BOOTSTRAP --> RESUME_CHECK

    state "Batch Loop" as batch_loop {
        BATCH_START --> FETCH
        FETCH --> SETUP
        SETUP --> ASSESS
        ASSESS --> REVIEW
        REVIEW --> REVISE
        REVISE --> FIXUP

        FIXUP --> REASSESS_CHECK

        state reassess_decision <<choice>>
        REASSESS_CHECK --> reassess_decision
        reassess_decision --> REASSESS_SAVE : IDs need re-scoring\n& cycle < 2
        reassess_decision --> COLLECT : none or cycle >= 2

        state "Reassess Loop" as reassess {
            REASSESS_SAVE --> REASSESS_ASSESS
            REASSESS_ASSESS --> REASSESS_REVIEW
            REASSESS_REVIEW --> REASSESS_RESTORE
            REASSESS_RESTORE --> REASSESS_REVISE
            REASSESS_REVISE --> REASSESS_FIXUP
        }
        REASSESS_FIXUP --> REASSESS_CHECK

        state collect_decision <<choice>>
        COLLECT --> collect_decision
        collect_decision --> SPLIT : split candidates exist
        collect_decision --> BATCH_DONE : no splits

        state "Split Sub-pipeline" as split_pipeline {
            SPLIT --> SPLIT_COLLECT
            SPLIT_COLLECT --> SPLIT_PIPELINE_START
            SPLIT_PIPELINE_START --> SPLIT_ASSESS
            SPLIT_ASSESS --> SPLIT_REVIEW
            SPLIT_REVIEW --> SPLIT_REVISE
            SPLIT_REVISE --> SPLIT_FIXUP
            SPLIT_FIXUP --> SPLIT_CORRECTION_CHECK

            state correction_decision <<choice>>
            SPLIT_CORRECTION_CHECK --> correction_decision
            correction_decision --> SPLIT : undersized\n& cycle < 1
            correction_decision --> BATCH_DONE : all pass or\ncycle >= 1
        }
    }

    RESUME_CHECK --> BATCH_START

    state batch_decision <<choice>>
    BATCH_DONE --> batch_decision
    batch_decision --> BATCH_START : more batches
    batch_decision --> RETRY_SETUP : errors exist
    batch_decision --> REPORT : no errors

    state "Retry Pipeline" as retry {
        RETRY_SETUP --> RETRY_FETCH
        RETRY_FETCH --> RETRY_ASSESS
        RETRY_ASSESS --> RETRY_REVIEW
        RETRY_REVIEW --> RETRY_REVISE
        RETRY_REVISE --> RETRY_FIXUP
        RETRY_FIXUP --> RETRY_COLLECT

        state retry_collect_decision <<choice>>
        RETRY_COLLECT --> retry_collect_decision
        retry_collect_decision --> RETRY_SPLIT : split candidates exist
        retry_collect_decision --> REPORT : no splits

        state "Retry Split Sub-pipeline" as retry_split {
            RETRY_SPLIT --> RETRY_SPLIT_COLLECT
            RETRY_SPLIT_COLLECT --> RETRY_SPLIT_ASSESS
            RETRY_SPLIT_ASSESS --> RETRY_SPLIT_REVIEW
            RETRY_SPLIT_REVIEW --> RETRY_SPLIT_REVISE
            RETRY_SPLIT_REVISE --> RETRY_SPLIT_FIXUP
            RETRY_SPLIT_FIXUP --> RETRY_SPLIT_CORRECTION_CHECK

            state retry_correction_decision <<choice>>
            RETRY_SPLIT_CORRECTION_CHECK --> retry_correction_decision
            retry_correction_decision --> RETRY_SPLIT : undersized\n& cycle < 1
            retry_correction_decision --> REPORT : all pass or\ncycle >= 1
        }
    }

    REPORT --> DONE
    DONE --> [*]
```
