#' ============================================================================
#' Program:    suppmh.R
#' Purpose:    Create SDTM SUPPMH domain from source data
#' Study:      MAXIS-08
#' Source:     SURGHXC.csv
#' Created:    2026-01-20
#' Author:     SDTM Pipeline (Auto-generated)
#' ============================================================================

source("r_programs/setup.R")

log_step("SUPPMH Domain - Starting transformation")

# -----------------------------------------------------------------------------
# Step 1: Read source data
# -----------------------------------------------------------------------------
surghxc_raw <- read_csv(
  file.path(raw_data_path, "SURGHXC.csv"),
  show_col_types = FALSE
) %>%
  clean_names(case = "all_caps")

log_step(sprintf("Read %d records from source", nrow(surghxc_raw)))

# -----------------------------------------------------------------------------
# Step 2: Apply mappings and transformations
# -----------------------------------------------------------------------------
suppmh_temp <- surghxc_raw %>%
  mutate(
    STUDYID = study_id,
    DOMAIN = "SUPPMH",
    USUBJID = pmap_chr(
      list(STUDY, INVSITE, PT),
      ~ gen_usubjid(..1, ..2, ..3)
    )
  ) %>%
  # No specific transformations defined

# -----------------------------------------------------------------------------
# Step 3: Generate sequence numbers
# -----------------------------------------------------------------------------
suppmh_temp <- suppmh_temp %>%
  add_seq("suppmh", sort_vars = c("USUBJID"))

# -----------------------------------------------------------------------------
# Step 4: Select and order final variables
# -----------------------------------------------------------------------------
suppmh <- suppmh_temp %>%
  select(everything()) %>%
  arrange(USUBJID, SUPPMHSEQ)

log_step(sprintf("Created %d SUPPMH records", nrow(suppmh)))

# -----------------------------------------------------------------------------
# Step 5: Validation checks
# -----------------------------------------------------------------------------
# Check for required variables
suppmh_validation <- suppmh %>%
  assert(not_na, STUDYID, USUBJID, SUPPMHSEQ) %>%
  verify(n_distinct(USUBJID) > 0)

# Check for duplicates
dup_check <- suppmh %>%
  group_by(USUBJID, SUPPMHSEQ) %>%
  filter(n() > 1) %>%
  nrow()

if (dup_check > 0) {
  warning(sprintf("Found %d duplicate records by USUBJID + SUPPMHSEQ", dup_check))
}

# -----------------------------------------------------------------------------
# Step 6: Save output
# -----------------------------------------------------------------------------
# Save as CSV
write_csv(suppmh, file.path(sdtm_output_path, "suppmh.csv"))

# Save as SAS transport (XPT) if haven is available
tryCatch({
  write_xpt(suppmh, file.path(sdtm_output_path, "suppmh.xpt"))
  log_step("Saved SUPPMH as XPT format")
}, error = function(e) {
  log_step("Could not save XPT format", "WARNING")
})

log_step("SUPPMH Domain - Complete", "SUCCESS")

# Return dataset for pipeline
suppmh
