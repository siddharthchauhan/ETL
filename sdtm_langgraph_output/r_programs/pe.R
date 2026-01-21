#' ============================================================================
#' Program:    pe.R
#' Purpose:    Create SDTM PE domain from source data
#' Study:      MAXIS-08
#' Source:     XRAYSAMP.csv
#' Created:    2026-01-21
#' Author:     SDTM Pipeline (Auto-generated)
#' ============================================================================

source("r_programs/setup.R")

log_step("PE Domain - Starting transformation")

# -----------------------------------------------------------------------------
# Step 1: Read source data
# -----------------------------------------------------------------------------
xraysamp_raw <- read_csv(
  file.path(raw_data_path, "XRAYSAMP.csv"),
  show_col_types = FALSE
) %>%
  clean_names(case = "all_caps")

log_step(sprintf("Read %d records from source", nrow(xraysamp_raw)))

# -----------------------------------------------------------------------------
# Step 2: Apply mappings and transformations
# -----------------------------------------------------------------------------
pe_temp <- xraysamp_raw %>%
  mutate(
    STUDYID = study_id,
    DOMAIN = "PE",
    USUBJID = pmap_chr(
      list(STUDY, INVSITE, PT),
      ~ gen_usubjid(..1, ..2, ..3)
    )
  ) %>%
  # No specific transformations defined

# -----------------------------------------------------------------------------
# Step 3: Generate sequence numbers
# -----------------------------------------------------------------------------
pe_temp <- pe_temp %>%
  add_seq("pe", sort_vars = c("USUBJID"))

# -----------------------------------------------------------------------------
# Step 4: Select and order final variables
# -----------------------------------------------------------------------------
pe <- pe_temp %>%
  select(everything()) %>%
  arrange(USUBJID, PESEQ)

log_step(sprintf("Created %d PE records", nrow(pe)))

# -----------------------------------------------------------------------------
# Step 5: Validation checks
# -----------------------------------------------------------------------------
# Check for required variables
pe_validation <- pe %>%
  assert(not_na, STUDYID, USUBJID, PESEQ) %>%
  verify(n_distinct(USUBJID) > 0)

# Check for duplicates
dup_check <- pe %>%
  group_by(USUBJID, PESEQ) %>%
  filter(n() > 1) %>%
  nrow()

if (dup_check > 0) {
  warning(sprintf("Found %d duplicate records by USUBJID + PESEQ", dup_check))
}

# -----------------------------------------------------------------------------
# Step 6: Save output
# -----------------------------------------------------------------------------
# Save as CSV
write_csv(pe, file.path(sdtm_output_path, "pe.csv"))

# Save as SAS transport (XPT) if haven is available
tryCatch({
  write_xpt(pe, file.path(sdtm_output_path, "pe.xpt"))
  log_step("Saved PE as XPT format")
}, error = function(e) {
  log_step("Could not save XPT format", "WARNING")
})

log_step("PE Domain - Complete", "SUCCESS")

# Return dataset for pipeline
pe
