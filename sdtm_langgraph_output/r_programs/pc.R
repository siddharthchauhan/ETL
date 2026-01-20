#' ============================================================================
#' Program:    pc.R
#' Purpose:    Create SDTM PC domain from source data
#' Study:      MAXIS-08
#' Source:     PKCRF.csv
#' Created:    2026-01-20
#' Author:     SDTM Pipeline (Auto-generated)
#' ============================================================================

source("r_programs/setup.R")

log_step("PC Domain - Starting transformation")

# -----------------------------------------------------------------------------
# Step 1: Read source data
# -----------------------------------------------------------------------------
pkcrf_raw <- read_csv(
  file.path(raw_data_path, "PKCRF.csv"),
  show_col_types = FALSE
) %>%
  clean_names(case = "all_caps")

log_step(sprintf("Read %d records from source", nrow(pkcrf_raw)))

# -----------------------------------------------------------------------------
# Step 2: Apply mappings and transformations
# -----------------------------------------------------------------------------
pc_temp <- pkcrf_raw %>%
  mutate(
    STUDYID = study_id,
    DOMAIN = "PC",
    USUBJID = pmap_chr(
      list(STUDY, INVSITE, PT),
      ~ gen_usubjid(..1, ..2, ..3)
    )
  ) %>%
  # No specific transformations defined

# -----------------------------------------------------------------------------
# Step 3: Generate sequence numbers
# -----------------------------------------------------------------------------
pc_temp <- pc_temp %>%
  add_seq("pc", sort_vars = c("USUBJID"))

# -----------------------------------------------------------------------------
# Step 4: Select and order final variables
# -----------------------------------------------------------------------------
pc <- pc_temp %>%
  select(everything()) %>%
  arrange(USUBJID, PCSEQ)

log_step(sprintf("Created %d PC records", nrow(pc)))

# -----------------------------------------------------------------------------
# Step 5: Validation checks
# -----------------------------------------------------------------------------
# Check for required variables
pc_validation <- pc %>%
  assert(not_na, STUDYID, USUBJID, PCSEQ) %>%
  verify(n_distinct(USUBJID) > 0)

# Check for duplicates
dup_check <- pc %>%
  group_by(USUBJID, PCSEQ) %>%
  filter(n() > 1) %>%
  nrow()

if (dup_check > 0) {
  warning(sprintf("Found %d duplicate records by USUBJID + PCSEQ", dup_check))
}

# -----------------------------------------------------------------------------
# Step 6: Save output
# -----------------------------------------------------------------------------
# Save as CSV
write_csv(pc, file.path(sdtm_output_path, "pc.csv"))

# Save as SAS transport (XPT) if haven is available
tryCatch({
  write_xpt(pc, file.path(sdtm_output_path, "pc.xpt"))
  log_step("Saved PC as XPT format")
}, error = function(e) {
  log_step("Could not save XPT format", "WARNING")
})

log_step("PC Domain - Complete", "SUCCESS")

# Return dataset for pipeline
pc
