#' ============================================================================
#' Program:    ta.R
#' Purpose:    Create SDTM TA domain from source data
#' Study:      MAXIS-08
#' Source:     INV.csv
#' Created:    2026-01-20
#' Author:     SDTM Pipeline (Auto-generated)
#' ============================================================================

source("r_programs/setup.R")

log_step("TA Domain - Starting transformation")

# -----------------------------------------------------------------------------
# Step 1: Read source data
# -----------------------------------------------------------------------------
inv_raw <- read_csv(
  file.path(raw_data_path, "INV.csv"),
  show_col_types = FALSE
) %>%
  clean_names(case = "all_caps")

log_step(sprintf("Read %d records from source", nrow(inv_raw)))

# -----------------------------------------------------------------------------
# Step 2: Apply mappings and transformations
# -----------------------------------------------------------------------------
ta_temp <- inv_raw %>%
  mutate(
    STUDYID = study_id,
    DOMAIN = "TA",
    USUBJID = pmap_chr(
      list(STUDY, INVSITE, PT),
      ~ gen_usubjid(..1, ..2, ..3)
    )
  ) %>%
  # No specific transformations defined

# -----------------------------------------------------------------------------
# Step 3: Generate sequence numbers
# -----------------------------------------------------------------------------
ta_temp <- ta_temp %>%
  add_seq("ta", sort_vars = c("USUBJID"))

# -----------------------------------------------------------------------------
# Step 4: Select and order final variables
# -----------------------------------------------------------------------------
ta <- ta_temp %>%
  select(everything()) %>%
  arrange(USUBJID, TASEQ)

log_step(sprintf("Created %d TA records", nrow(ta)))

# -----------------------------------------------------------------------------
# Step 5: Validation checks
# -----------------------------------------------------------------------------
# Check for required variables
ta_validation <- ta %>%
  assert(not_na, STUDYID, USUBJID, TASEQ) %>%
  verify(n_distinct(USUBJID) > 0)

# Check for duplicates
dup_check <- ta %>%
  group_by(USUBJID, TASEQ) %>%
  filter(n() > 1) %>%
  nrow()

if (dup_check > 0) {
  warning(sprintf("Found %d duplicate records by USUBJID + TASEQ", dup_check))
}

# -----------------------------------------------------------------------------
# Step 6: Save output
# -----------------------------------------------------------------------------
# Save as CSV
write_csv(ta, file.path(sdtm_output_path, "ta.csv"))

# Save as SAS transport (XPT) if haven is available
tryCatch({
  write_xpt(ta, file.path(sdtm_output_path, "ta.xpt"))
  log_step("Saved TA as XPT format")
}, error = function(e) {
  log_step("Could not save XPT format", "WARNING")
})

log_step("TA Domain - Complete", "SUCCESS")

# Return dataset for pipeline
ta
