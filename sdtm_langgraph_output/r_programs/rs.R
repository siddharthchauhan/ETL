#' ============================================================================
#' Program:    rs.R
#' Purpose:    Create SDTM RS domain from source data
#' Study:      MAXIS-08
#' Source:     RESP.csv
#' Created:    2026-01-21
#' Author:     SDTM Pipeline (Auto-generated)
#' ============================================================================

source("r_programs/setup.R")

log_step("RS Domain - Starting transformation")

# -----------------------------------------------------------------------------
# Step 1: Read source data
# -----------------------------------------------------------------------------
resp_raw <- read_csv(
  file.path(raw_data_path, "RESP.csv"),
  show_col_types = FALSE
) %>%
  clean_names(case = "all_caps")

log_step(sprintf("Read %d records from source", nrow(resp_raw)))

# -----------------------------------------------------------------------------
# Step 2: Apply mappings and transformations
# -----------------------------------------------------------------------------
rs_temp <- resp_raw %>%
  mutate(
    STUDYID = study_id,
    DOMAIN = "RS",
    USUBJID = pmap_chr(
      list(STUDY, INVSITE, PT),
      ~ gen_usubjid(..1, ..2, ..3)
    )
  ) %>%
  # No specific transformations defined

# -----------------------------------------------------------------------------
# Step 3: Generate sequence numbers
# -----------------------------------------------------------------------------
rs_temp <- rs_temp %>%
  add_seq("rs", sort_vars = c("USUBJID"))

# -----------------------------------------------------------------------------
# Step 4: Select and order final variables
# -----------------------------------------------------------------------------
rs <- rs_temp %>%
  select(everything()) %>%
  arrange(USUBJID, RSSEQ)

log_step(sprintf("Created %d RS records", nrow(rs)))

# -----------------------------------------------------------------------------
# Step 5: Validation checks
# -----------------------------------------------------------------------------
# Check for required variables
rs_validation <- rs %>%
  assert(not_na, STUDYID, USUBJID, RSSEQ) %>%
  verify(n_distinct(USUBJID) > 0)

# Check for duplicates
dup_check <- rs %>%
  group_by(USUBJID, RSSEQ) %>%
  filter(n() > 1) %>%
  nrow()

if (dup_check > 0) {
  warning(sprintf("Found %d duplicate records by USUBJID + RSSEQ", dup_check))
}

# -----------------------------------------------------------------------------
# Step 6: Save output
# -----------------------------------------------------------------------------
# Save as CSV
write_csv(rs, file.path(sdtm_output_path, "rs.csv"))

# Save as SAS transport (XPT) if haven is available
tryCatch({
  write_xpt(rs, file.path(sdtm_output_path, "rs.xpt"))
  log_step("Saved RS as XPT format")
}, error = function(e) {
  log_step("Could not save XPT format", "WARNING")
})

log_step("RS Domain - Complete", "SUCCESS")

# Return dataset for pipeline
rs
