#' ============================================================================
#' Program:    eg.R
#' Purpose:    Create SDTM EG domain from source data
#' Study:      MAXIS-08
#' Source:     ECG.csv
#' Created:    2026-01-20
#' Author:     SDTM Pipeline (Auto-generated)
#' ============================================================================

source("r_programs/setup.R")

log_step("EG Domain - Starting transformation")

# -----------------------------------------------------------------------------
# Step 1: Read source data
# -----------------------------------------------------------------------------
ecg_raw <- read_csv(
  file.path(raw_data_path, "ECG.csv"),
  show_col_types = FALSE
) %>%
  clean_names(case = "all_caps")

log_step(sprintf("Read %d records from source", nrow(ecg_raw)))

# -----------------------------------------------------------------------------
# Step 2: Apply mappings and transformations
# -----------------------------------------------------------------------------
eg_temp <- ecg_raw %>%
  mutate(
    STUDYID = study_id,
    DOMAIN = "EG",
    USUBJID = pmap_chr(
      list(STUDY, INVSITE, PT),
      ~ gen_usubjid(..1, ..2, ..3)
    )
  ) %>%
  # No specific transformations defined

# -----------------------------------------------------------------------------
# Step 3: Generate sequence numbers
# -----------------------------------------------------------------------------
eg_temp <- eg_temp %>%
  add_seq("eg", sort_vars = c("USUBJID"))

# -----------------------------------------------------------------------------
# Step 4: Select and order final variables
# -----------------------------------------------------------------------------
eg <- eg_temp %>%
  select(everything()) %>%
  arrange(USUBJID, EGSEQ)

log_step(sprintf("Created %d EG records", nrow(eg)))

# -----------------------------------------------------------------------------
# Step 5: Validation checks
# -----------------------------------------------------------------------------
# Check for required variables
eg_validation <- eg %>%
  assert(not_na, STUDYID, USUBJID, EGSEQ) %>%
  verify(n_distinct(USUBJID) > 0)

# Check for duplicates
dup_check <- eg %>%
  group_by(USUBJID, EGSEQ) %>%
  filter(n() > 1) %>%
  nrow()

if (dup_check > 0) {
  warning(sprintf("Found %d duplicate records by USUBJID + EGSEQ", dup_check))
}

# -----------------------------------------------------------------------------
# Step 6: Save output
# -----------------------------------------------------------------------------
# Save as CSV
write_csv(eg, file.path(sdtm_output_path, "eg.csv"))

# Save as SAS transport (XPT) if haven is available
tryCatch({
  write_xpt(eg, file.path(sdtm_output_path, "eg.xpt"))
  log_step("Saved EG as XPT format")
}, error = function(e) {
  log_step("Could not save XPT format", "WARNING")
})

log_step("EG Domain - Complete", "SUCCESS")

# Return dataset for pipeline
eg
