#' ============================================================================
#' Program:    ex.R
#' Purpose:    Create SDTM EX domain from source data
#' Study:      MAXIS-08
#' Source:     DOSE.csv
#' Created:    2026-01-21
#' Author:     SDTM Pipeline (Auto-generated)
#' ============================================================================

source("r_programs/setup.R")

log_step("EX Domain - Starting transformation")

# -----------------------------------------------------------------------------
# Step 1: Read source data
# -----------------------------------------------------------------------------
dose_raw <- read_csv(
  file.path(raw_data_path, "DOSE.csv"),
  show_col_types = FALSE
) %>%
  clean_names(case = "all_caps")

log_step(sprintf("Read %d records from source", nrow(dose_raw)))

# -----------------------------------------------------------------------------
# Step 2: Apply mappings and transformations
# -----------------------------------------------------------------------------
ex_temp <- dose_raw %>%
  mutate(
    STUDYID = study_id,
    DOMAIN = "EX",
    USUBJID = pmap_chr(
      list(STUDY, INVSITE, PT),
      ~ gen_usubjid(..1, ..2, ..3)
    )
  ) %>%
  # No specific transformations defined

# -----------------------------------------------------------------------------
# Step 3: Generate sequence numbers
# -----------------------------------------------------------------------------
ex_temp <- ex_temp %>%
  add_seq("ex", sort_vars = c("USUBJID"))

# -----------------------------------------------------------------------------
# Step 4: Select and order final variables
# -----------------------------------------------------------------------------
ex <- ex_temp %>%
  select(everything()) %>%
  arrange(USUBJID, EXSEQ)

log_step(sprintf("Created %d EX records", nrow(ex)))

# -----------------------------------------------------------------------------
# Step 5: Validation checks
# -----------------------------------------------------------------------------
# Check for required variables
ex_validation <- ex %>%
  assert(not_na, STUDYID, USUBJID, EXSEQ) %>%
  verify(n_distinct(USUBJID) > 0)

# Check for duplicates
dup_check <- ex %>%
  group_by(USUBJID, EXSEQ) %>%
  filter(n() > 1) %>%
  nrow()

if (dup_check > 0) {
  warning(sprintf("Found %d duplicate records by USUBJID + EXSEQ", dup_check))
}

# -----------------------------------------------------------------------------
# Step 6: Save output
# -----------------------------------------------------------------------------
# Save as CSV
write_csv(ex, file.path(sdtm_output_path, "ex.csv"))

# Save as SAS transport (XPT) if haven is available
tryCatch({
  write_xpt(ex, file.path(sdtm_output_path, "ex.xpt"))
  log_step("Saved EX as XPT format")
}, error = function(e) {
  log_step("Could not save XPT format", "WARNING")
})

log_step("EX Domain - Complete", "SUCCESS")

# Return dataset for pipeline
ex
