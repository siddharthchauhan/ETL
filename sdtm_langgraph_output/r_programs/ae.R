#' ============================================================================
#' Program:    ae.R
#' Purpose:    Create SDTM AE domain from source data
#' Study:      MAXIS-08
#' Source:     AEVENT.csv
#' Created:    2026-01-21
#' Author:     SDTM Pipeline (Auto-generated)
#' ============================================================================

source("r_programs/setup.R")

log_step("AE Domain - Starting transformation")

# -----------------------------------------------------------------------------
# Step 1: Read source data
# -----------------------------------------------------------------------------
aevent_raw <- read_csv(
  file.path(raw_data_path, "AEVENT.csv"),
  show_col_types = FALSE
) %>%
  clean_names(case = "all_caps")

log_step(sprintf("Read %d records from source", nrow(aevent_raw)))

# -----------------------------------------------------------------------------
# Step 2: Apply mappings and transformations
# -----------------------------------------------------------------------------
ae_temp <- aevent_raw %>%
  mutate(
    STUDYID = study_id,
    DOMAIN = "AE",
    USUBJID = pmap_chr(
      list(STUDY, INVSITE, PT),
      ~ gen_usubjid(..1, ..2, ..3)
    )
  ) %>%
  mutate(
    AETERM = as.character(coalesce(AETERM, AEDESC, AENAME)),
    AEDECOD = AETERM,  # Would use MedDRA coding in production
    AESTDTC = map_chr(coalesce(AESTDT, STDT), convert_to_iso),
    AEENDTC = map_chr(coalesce(AEENDT, ENDT), convert_to_iso),
    AESEV = toupper(as.character(AESEV)),
    AESER = if_else(toupper(as.character(AESER)) %in% c("Y", "YES", "1", "TRUE"), "Y", "N"),
    AEREL = toupper(as.character(AEREL)),
    AEOUT = as.character(AEOUT)
  )

# -----------------------------------------------------------------------------
# Step 3: Generate sequence numbers
# -----------------------------------------------------------------------------
ae_temp <- ae_temp %>%
  add_seq("ae", sort_vars = c("AESTDTC"))

# -----------------------------------------------------------------------------
# Step 4: Select and order final variables
# -----------------------------------------------------------------------------
ae <- ae_temp %>%
  select(STUDYID, DOMAIN, USUBJID, AESEQ, AETERM, AEDECOD, AESTDTC, AEENDTC, AESEV, AESER, AEREL, AEOUT) %>%
  arrange(USUBJID, AESEQ)

log_step(sprintf("Created %d AE records", nrow(ae)))

# -----------------------------------------------------------------------------
# Step 5: Validation checks
# -----------------------------------------------------------------------------
# Check for required variables
ae_validation <- ae %>%
  assert(not_na, STUDYID, USUBJID, AESEQ) %>%
  verify(n_distinct(USUBJID) > 0)

# Check for duplicates
dup_check <- ae %>%
  group_by(USUBJID, AESEQ) %>%
  filter(n() > 1) %>%
  nrow()

if (dup_check > 0) {
  warning(sprintf("Found %d duplicate records by USUBJID + AESEQ", dup_check))
}

# -----------------------------------------------------------------------------
# Step 6: Save output
# -----------------------------------------------------------------------------
# Save as CSV
write_csv(ae, file.path(sdtm_output_path, "ae.csv"))

# Save as SAS transport (XPT) if haven is available
tryCatch({
  write_xpt(ae, file.path(sdtm_output_path, "ae.xpt"))
  log_step("Saved AE as XPT format")
}, error = function(e) {
  log_step("Could not save XPT format", "WARNING")
})

log_step("AE Domain - Complete", "SUCCESS")

# Return dataset for pipeline
ae
