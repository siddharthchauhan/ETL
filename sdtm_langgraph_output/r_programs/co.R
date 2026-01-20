#' ============================================================================
#' Program:    co.R
#' Purpose:    Create SDTM CO domain from source data
#' Study:      MAXIS-08
#' Source:     COMGEN.csv
#' Created:    2026-01-20
#' Author:     SDTM Pipeline (Auto-generated)
#' ============================================================================

source("r_programs/setup.R")

log_step("CO Domain - Starting transformation")

# -----------------------------------------------------------------------------
# Step 1: Read source data
# -----------------------------------------------------------------------------
comgen_raw <- read_csv(
  file.path(raw_data_path, "COMGEN.csv"),
  show_col_types = FALSE
) %>%
  clean_names(case = "all_caps")

log_step(sprintf("Read %d records from source", nrow(comgen_raw)))

# -----------------------------------------------------------------------------
# Step 2: Apply mappings and transformations
# -----------------------------------------------------------------------------
co_temp <- comgen_raw %>%
  mutate(
    STUDYID = study_id,
    DOMAIN = "CO",
    USUBJID = pmap_chr(
      list(STUDY, INVSITE, PT),
      ~ gen_usubjid(..1, ..2, ..3)
    )
  ) %>%
  # No specific transformations defined

# -----------------------------------------------------------------------------
# Step 3: Generate sequence numbers
# -----------------------------------------------------------------------------
co_temp <- co_temp %>%
  add_seq("co", sort_vars = c("USUBJID"))

# -----------------------------------------------------------------------------
# Step 4: Select and order final variables
# -----------------------------------------------------------------------------
co <- co_temp %>%
  select(everything()) %>%
  arrange(USUBJID, COSEQ)

log_step(sprintf("Created %d CO records", nrow(co)))

# -----------------------------------------------------------------------------
# Step 5: Validation checks
# -----------------------------------------------------------------------------
# Check for required variables
co_validation <- co %>%
  assert(not_na, STUDYID, USUBJID, COSEQ) %>%
  verify(n_distinct(USUBJID) > 0)

# Check for duplicates
dup_check <- co %>%
  group_by(USUBJID, COSEQ) %>%
  filter(n() > 1) %>%
  nrow()

if (dup_check > 0) {
  warning(sprintf("Found %d duplicate records by USUBJID + COSEQ", dup_check))
}

# -----------------------------------------------------------------------------
# Step 6: Save output
# -----------------------------------------------------------------------------
# Save as CSV
write_csv(co, file.path(sdtm_output_path, "co.csv"))

# Save as SAS transport (XPT) if haven is available
tryCatch({
  write_xpt(co, file.path(sdtm_output_path, "co.xpt"))
  log_step("Saved CO as XPT format")
}, error = function(e) {
  log_step("Could not save XPT format", "WARNING")
})

log_step("CO Domain - Complete", "SUCCESS")

# Return dataset for pipeline
co
