#' ============================================================================
#' Program:    suppae.R
#' Purpose:    Create SDTM SUPPAE domain from source data
#' Study:      MAXIS-08
#' Source:     AEVENTC.csv
#' Created:    2026-01-21
#' Author:     SDTM Pipeline (Auto-generated)
#' ============================================================================

source("r_programs/setup.R")

log_step("SUPPAE Domain - Starting transformation")

# -----------------------------------------------------------------------------
# Step 1: Read source data
# -----------------------------------------------------------------------------
aeventc_raw <- read_csv(
  file.path(raw_data_path, "AEVENTC.csv"),
  show_col_types = FALSE
) %>%
  clean_names(case = "all_caps")

log_step(sprintf("Read %d records from source", nrow(aeventc_raw)))

# -----------------------------------------------------------------------------
# Step 2: Apply mappings and transformations
# -----------------------------------------------------------------------------
suppae_temp <- aeventc_raw %>%
  mutate(
    STUDYID = study_id,
    DOMAIN = "SUPPAE",
    USUBJID = pmap_chr(
      list(STUDY, INVSITE, PT),
      ~ gen_usubjid(..1, ..2, ..3)
    )
  ) %>%
  # No specific transformations defined

# -----------------------------------------------------------------------------
# Step 3: Generate sequence numbers
# -----------------------------------------------------------------------------
suppae_temp <- suppae_temp %>%
  add_seq("suppae", sort_vars = c("USUBJID"))

# -----------------------------------------------------------------------------
# Step 4: Select and order final variables
# -----------------------------------------------------------------------------
suppae <- suppae_temp %>%
  select(everything()) %>%
  arrange(USUBJID, SUPPAESEQ)

log_step(sprintf("Created %d SUPPAE records", nrow(suppae)))

# -----------------------------------------------------------------------------
# Step 5: Validation checks
# -----------------------------------------------------------------------------
# Check for required variables
suppae_validation <- suppae %>%
  assert(not_na, STUDYID, USUBJID, SUPPAESEQ) %>%
  verify(n_distinct(USUBJID) > 0)

# Check for duplicates
dup_check <- suppae %>%
  group_by(USUBJID, SUPPAESEQ) %>%
  filter(n() > 1) %>%
  nrow()

if (dup_check > 0) {
  warning(sprintf("Found %d duplicate records by USUBJID + SUPPAESEQ", dup_check))
}

# -----------------------------------------------------------------------------
# Step 6: Save output
# -----------------------------------------------------------------------------
# Save as CSV
write_csv(suppae, file.path(sdtm_output_path, "suppae.csv"))

# Save as SAS transport (XPT) if haven is available
tryCatch({
  write_xpt(suppae, file.path(sdtm_output_path, "suppae.xpt"))
  log_step("Saved SUPPAE as XPT format")
}, error = function(e) {
  log_step("Could not save XPT format", "WARNING")
})

log_step("SUPPAE Domain - Complete", "SUCCESS")

# Return dataset for pipeline
suppae
