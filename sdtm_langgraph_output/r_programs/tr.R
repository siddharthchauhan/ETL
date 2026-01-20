#' ============================================================================
#' Program:    tr.R
#' Purpose:    Create SDTM TR domain from source data
#' Study:      MAXIS-08
#' Source:     TARTUMR.csv
#' Created:    2026-01-20
#' Author:     SDTM Pipeline (Auto-generated)
#' ============================================================================

source("r_programs/setup.R")

log_step("TR Domain - Starting transformation")

# -----------------------------------------------------------------------------
# Step 1: Read source data
# -----------------------------------------------------------------------------
tartumr_raw <- read_csv(
  file.path(raw_data_path, "TARTUMR.csv"),
  show_col_types = FALSE
) %>%
  clean_names(case = "all_caps")

log_step(sprintf("Read %d records from source", nrow(tartumr_raw)))

# -----------------------------------------------------------------------------
# Step 2: Apply mappings and transformations
# -----------------------------------------------------------------------------
tr_temp <- tartumr_raw %>%
  mutate(
    STUDYID = study_id,
    DOMAIN = "TR",
    USUBJID = pmap_chr(
      list(STUDY, INVSITE, PT),
      ~ gen_usubjid(..1, ..2, ..3)
    )
  ) %>%
  # No specific transformations defined

# -----------------------------------------------------------------------------
# Step 3: Generate sequence numbers
# -----------------------------------------------------------------------------
tr_temp <- tr_temp %>%
  add_seq("tr", sort_vars = c("USUBJID"))

# -----------------------------------------------------------------------------
# Step 4: Select and order final variables
# -----------------------------------------------------------------------------
tr <- tr_temp %>%
  select(everything()) %>%
  arrange(USUBJID, TRSEQ)

log_step(sprintf("Created %d TR records", nrow(tr)))

# -----------------------------------------------------------------------------
# Step 5: Validation checks
# -----------------------------------------------------------------------------
# Check for required variables
tr_validation <- tr %>%
  assert(not_na, STUDYID, USUBJID, TRSEQ) %>%
  verify(n_distinct(USUBJID) > 0)

# Check for duplicates
dup_check <- tr %>%
  group_by(USUBJID, TRSEQ) %>%
  filter(n() > 1) %>%
  nrow()

if (dup_check > 0) {
  warning(sprintf("Found %d duplicate records by USUBJID + TRSEQ", dup_check))
}

# -----------------------------------------------------------------------------
# Step 6: Save output
# -----------------------------------------------------------------------------
# Save as CSV
write_csv(tr, file.path(sdtm_output_path, "tr.csv"))

# Save as SAS transport (XPT) if haven is available
tryCatch({
  write_xpt(tr, file.path(sdtm_output_path, "tr.xpt"))
  log_step("Saved TR as XPT format")
}, error = function(e) {
  log_step("Could not save XPT format", "WARNING")
})

log_step("TR Domain - Complete", "SUCCESS")

# Return dataset for pipeline
tr
