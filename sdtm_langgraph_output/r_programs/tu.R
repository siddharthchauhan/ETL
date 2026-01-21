#' ============================================================================
#' Program:    tu.R
#' Purpose:    Create SDTM TU domain from source data
#' Study:      MAXIS-08
#' Source:     NONTUMR.csv
#' Created:    2026-01-21
#' Author:     SDTM Pipeline (Auto-generated)
#' ============================================================================

source("r_programs/setup.R")

log_step("TU Domain - Starting transformation")

# -----------------------------------------------------------------------------
# Step 1: Read source data
# -----------------------------------------------------------------------------
nontumr_raw <- read_csv(
  file.path(raw_data_path, "NONTUMR.csv"),
  show_col_types = FALSE
) %>%
  clean_names(case = "all_caps")

log_step(sprintf("Read %d records from source", nrow(nontumr_raw)))

# -----------------------------------------------------------------------------
# Step 2: Apply mappings and transformations
# -----------------------------------------------------------------------------
tu_temp <- nontumr_raw %>%
  mutate(
    STUDYID = study_id,
    DOMAIN = "TU",
    USUBJID = pmap_chr(
      list(STUDY, INVSITE, PT),
      ~ gen_usubjid(..1, ..2, ..3)
    )
  ) %>%
  # No specific transformations defined

# -----------------------------------------------------------------------------
# Step 3: Generate sequence numbers
# -----------------------------------------------------------------------------
tu_temp <- tu_temp %>%
  add_seq("tu", sort_vars = c("USUBJID"))

# -----------------------------------------------------------------------------
# Step 4: Select and order final variables
# -----------------------------------------------------------------------------
tu <- tu_temp %>%
  select(everything()) %>%
  arrange(USUBJID, TUSEQ)

log_step(sprintf("Created %d TU records", nrow(tu)))

# -----------------------------------------------------------------------------
# Step 5: Validation checks
# -----------------------------------------------------------------------------
# Check for required variables
tu_validation <- tu %>%
  assert(not_na, STUDYID, USUBJID, TUSEQ) %>%
  verify(n_distinct(USUBJID) > 0)

# Check for duplicates
dup_check <- tu %>%
  group_by(USUBJID, TUSEQ) %>%
  filter(n() > 1) %>%
  nrow()

if (dup_check > 0) {
  warning(sprintf("Found %d duplicate records by USUBJID + TUSEQ", dup_check))
}

# -----------------------------------------------------------------------------
# Step 6: Save output
# -----------------------------------------------------------------------------
# Save as CSV
write_csv(tu, file.path(sdtm_output_path, "tu.csv"))

# Save as SAS transport (XPT) if haven is available
tryCatch({
  write_xpt(tu, file.path(sdtm_output_path, "tu.xpt"))
  log_step("Saved TU as XPT format")
}, error = function(e) {
  log_step("Could not save XPT format", "WARNING")
})

log_step("TU Domain - Complete", "SUCCESS")

# Return dataset for pipeline
tu
