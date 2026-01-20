#' ============================================================================
#' Program:    suppcm.R
#' Purpose:    Create SDTM SUPPCM domain from source data
#' Study:      MAXIS-08
#' Source:     CAMED19C.csv
#' Created:    2026-01-20
#' Author:     SDTM Pipeline (Auto-generated)
#' ============================================================================

source("r_programs/setup.R")

log_step("SUPPCM Domain - Starting transformation")

# -----------------------------------------------------------------------------
# Step 1: Read source data
# -----------------------------------------------------------------------------
camed19c_raw <- read_csv(
  file.path(raw_data_path, "CAMED19C.csv"),
  show_col_types = FALSE
) %>%
  clean_names(case = "all_caps")

log_step(sprintf("Read %d records from source", nrow(camed19c_raw)))

# -----------------------------------------------------------------------------
# Step 2: Apply mappings and transformations
# -----------------------------------------------------------------------------
suppcm_temp <- camed19c_raw %>%
  mutate(
    STUDYID = study_id,
    DOMAIN = "SUPPCM",
    USUBJID = pmap_chr(
      list(STUDY, INVSITE, PT),
      ~ gen_usubjid(..1, ..2, ..3)
    )
  ) %>%
  # No specific transformations defined

# -----------------------------------------------------------------------------
# Step 3: Generate sequence numbers
# -----------------------------------------------------------------------------
suppcm_temp <- suppcm_temp %>%
  add_seq("suppcm", sort_vars = c("USUBJID"))

# -----------------------------------------------------------------------------
# Step 4: Select and order final variables
# -----------------------------------------------------------------------------
suppcm <- suppcm_temp %>%
  select(everything()) %>%
  arrange(USUBJID, SUPPCMSEQ)

log_step(sprintf("Created %d SUPPCM records", nrow(suppcm)))

# -----------------------------------------------------------------------------
# Step 5: Validation checks
# -----------------------------------------------------------------------------
# Check for required variables
suppcm_validation <- suppcm %>%
  assert(not_na, STUDYID, USUBJID, SUPPCMSEQ) %>%
  verify(n_distinct(USUBJID) > 0)

# Check for duplicates
dup_check <- suppcm %>%
  group_by(USUBJID, SUPPCMSEQ) %>%
  filter(n() > 1) %>%
  nrow()

if (dup_check > 0) {
  warning(sprintf("Found %d duplicate records by USUBJID + SUPPCMSEQ", dup_check))
}

# -----------------------------------------------------------------------------
# Step 6: Save output
# -----------------------------------------------------------------------------
# Save as CSV
write_csv(suppcm, file.path(sdtm_output_path, "suppcm.csv"))

# Save as SAS transport (XPT) if haven is available
tryCatch({
  write_xpt(suppcm, file.path(sdtm_output_path, "suppcm.xpt"))
  log_step("Saved SUPPCM as XPT format")
}, error = function(e) {
  log_step("Could not save XPT format", "WARNING")
})

log_step("SUPPCM Domain - Complete", "SUCCESS")

# Return dataset for pipeline
suppcm
