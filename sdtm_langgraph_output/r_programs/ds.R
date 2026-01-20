#' ============================================================================
#' Program:    ds.R
#' Purpose:    Create SDTM DS domain from source data
#' Study:      MAXIS-08
#' Source:     DEATHGEN.csv
#' Created:    2026-01-20
#' Author:     SDTM Pipeline (Auto-generated)
#' ============================================================================

source("r_programs/setup.R")

log_step("DS Domain - Starting transformation")

# -----------------------------------------------------------------------------
# Step 1: Read source data
# -----------------------------------------------------------------------------
deathgen_raw <- read_csv(
  file.path(raw_data_path, "DEATHGEN.csv"),
  show_col_types = FALSE
) %>%
  clean_names(case = "all_caps")

log_step(sprintf("Read %d records from source", nrow(deathgen_raw)))

# -----------------------------------------------------------------------------
# Step 2: Apply mappings and transformations
# -----------------------------------------------------------------------------
ds_temp <- deathgen_raw %>%
  mutate(
    STUDYID = study_id,
    DOMAIN = "DS",
    USUBJID = pmap_chr(
      list(STUDY, INVSITE, PT),
      ~ gen_usubjid(..1, ..2, ..3)
    )
  ) %>%
  # No specific transformations defined

# -----------------------------------------------------------------------------
# Step 3: Generate sequence numbers
# -----------------------------------------------------------------------------
ds_temp <- ds_temp %>%
  add_seq("ds", sort_vars = c("USUBJID"))

# -----------------------------------------------------------------------------
# Step 4: Select and order final variables
# -----------------------------------------------------------------------------
ds <- ds_temp %>%
  select(everything()) %>%
  arrange(USUBJID, DSSEQ)

log_step(sprintf("Created %d DS records", nrow(ds)))

# -----------------------------------------------------------------------------
# Step 5: Validation checks
# -----------------------------------------------------------------------------
# Check for required variables
ds_validation <- ds %>%
  assert(not_na, STUDYID, USUBJID, DSSEQ) %>%
  verify(n_distinct(USUBJID) > 0)

# Check for duplicates
dup_check <- ds %>%
  group_by(USUBJID, DSSEQ) %>%
  filter(n() > 1) %>%
  nrow()

if (dup_check > 0) {
  warning(sprintf("Found %d duplicate records by USUBJID + DSSEQ", dup_check))
}

# -----------------------------------------------------------------------------
# Step 6: Save output
# -----------------------------------------------------------------------------
# Save as CSV
write_csv(ds, file.path(sdtm_output_path, "ds.csv"))

# Save as SAS transport (XPT) if haven is available
tryCatch({
  write_xpt(ds, file.path(sdtm_output_path, "ds.xpt"))
  log_step("Saved DS as XPT format")
}, error = function(e) {
  log_step("Could not save XPT format", "WARNING")
})

log_step("DS Domain - Complete", "SUCCESS")

# Return dataset for pipeline
ds
