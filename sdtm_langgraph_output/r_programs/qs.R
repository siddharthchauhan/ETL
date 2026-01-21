#' ============================================================================
#' Program:    qs.R
#' Purpose:    Create SDTM QS domain from source data
#' Study:      MAXIS-08
#' Source:     QS.csv
#' Created:    2026-01-21
#' Author:     SDTM Pipeline (Auto-generated)
#' ============================================================================

source("r_programs/setup.R")

log_step("QS Domain - Starting transformation")

# -----------------------------------------------------------------------------
# Step 1: Read source data
# -----------------------------------------------------------------------------
qs_raw <- read_csv(
  file.path(raw_data_path, "QS.csv"),
  show_col_types = FALSE
) %>%
  clean_names(case = "all_caps")

log_step(sprintf("Read %d records from source", nrow(qs_raw)))

# -----------------------------------------------------------------------------
# Step 2: Apply mappings and transformations
# -----------------------------------------------------------------------------
qs_temp <- qs_raw %>%
  mutate(
    STUDYID = study_id,
    DOMAIN = "QS",
    USUBJID = pmap_chr(
      list(STUDY, INVSITE, PT),
      ~ gen_usubjid(..1, ..2, ..3)
    )
  ) %>%
  # No specific transformations defined

# -----------------------------------------------------------------------------
# Step 3: Generate sequence numbers
# -----------------------------------------------------------------------------
qs_temp <- qs_temp %>%
  add_seq("qs", sort_vars = c("USUBJID"))

# -----------------------------------------------------------------------------
# Step 4: Select and order final variables
# -----------------------------------------------------------------------------
qs <- qs_temp %>%
  select(everything()) %>%
  arrange(USUBJID, QSSEQ)

log_step(sprintf("Created %d QS records", nrow(qs)))

# -----------------------------------------------------------------------------
# Step 5: Validation checks
# -----------------------------------------------------------------------------
# Check for required variables
qs_validation <- qs %>%
  assert(not_na, STUDYID, USUBJID, QSSEQ) %>%
  verify(n_distinct(USUBJID) > 0)

# Check for duplicates
dup_check <- qs %>%
  group_by(USUBJID, QSSEQ) %>%
  filter(n() > 1) %>%
  nrow()

if (dup_check > 0) {
  warning(sprintf("Found %d duplicate records by USUBJID + QSSEQ", dup_check))
}

# -----------------------------------------------------------------------------
# Step 6: Save output
# -----------------------------------------------------------------------------
# Save as CSV
write_csv(qs, file.path(sdtm_output_path, "qs.csv"))

# Save as SAS transport (XPT) if haven is available
tryCatch({
  write_xpt(qs, file.path(sdtm_output_path, "qs.xpt"))
  log_step("Saved QS as XPT format")
}, error = function(e) {
  log_step("Could not save XPT format", "WARNING")
})

log_step("QS Domain - Complete", "SUCCESS")

# Return dataset for pipeline
qs
