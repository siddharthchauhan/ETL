#' ============================================================================
#' Program:    ie.R
#' Purpose:    Create SDTM IE domain from source data
#' Study:      MAXIS-08
#' Source:     ELIG.csv
#' Created:    2026-01-20
#' Author:     SDTM Pipeline (Auto-generated)
#' ============================================================================

source("r_programs/setup.R")

log_step("IE Domain - Starting transformation")

# -----------------------------------------------------------------------------
# Step 1: Read source data
# -----------------------------------------------------------------------------
elig_raw <- read_csv(
  file.path(raw_data_path, "ELIG.csv"),
  show_col_types = FALSE
) %>%
  clean_names(case = "all_caps")

log_step(sprintf("Read %d records from source", nrow(elig_raw)))

# -----------------------------------------------------------------------------
# Step 2: Apply mappings and transformations
# -----------------------------------------------------------------------------
ie_temp <- elig_raw %>%
  mutate(
    STUDYID = study_id,
    DOMAIN = "IE",
    USUBJID = pmap_chr(
      list(STUDY, INVSITE, PT),
      ~ gen_usubjid(..1, ..2, ..3)
    )
  ) %>%
  # No specific transformations defined

# -----------------------------------------------------------------------------
# Step 3: Generate sequence numbers
# -----------------------------------------------------------------------------
ie_temp <- ie_temp %>%
  add_seq("ie", sort_vars = c("USUBJID"))

# -----------------------------------------------------------------------------
# Step 4: Select and order final variables
# -----------------------------------------------------------------------------
ie <- ie_temp %>%
  select(everything()) %>%
  arrange(USUBJID, IESEQ)

log_step(sprintf("Created %d IE records", nrow(ie)))

# -----------------------------------------------------------------------------
# Step 5: Validation checks
# -----------------------------------------------------------------------------
# Check for required variables
ie_validation <- ie %>%
  assert(not_na, STUDYID, USUBJID, IESEQ) %>%
  verify(n_distinct(USUBJID) > 0)

# Check for duplicates
dup_check <- ie %>%
  group_by(USUBJID, IESEQ) %>%
  filter(n() > 1) %>%
  nrow()

if (dup_check > 0) {
  warning(sprintf("Found %d duplicate records by USUBJID + IESEQ", dup_check))
}

# -----------------------------------------------------------------------------
# Step 6: Save output
# -----------------------------------------------------------------------------
# Save as CSV
write_csv(ie, file.path(sdtm_output_path, "ie.csv"))

# Save as SAS transport (XPT) if haven is available
tryCatch({
  write_xpt(ie, file.path(sdtm_output_path, "ie.xpt"))
  log_step("Saved IE as XPT format")
}, error = function(e) {
  log_step("Could not save XPT format", "WARNING")
})

log_step("IE Domain - Complete", "SUCCESS")

# Return dataset for pipeline
ie
