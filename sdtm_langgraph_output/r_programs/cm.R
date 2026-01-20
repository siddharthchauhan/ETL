#' ============================================================================
#' Program:    cm.R
#' Purpose:    Create SDTM CM domain from source data
#' Study:      MAXIS-08
#' Source:     RADMEDS.csv
#' Created:    2026-01-20
#' Author:     SDTM Pipeline (Auto-generated)
#' ============================================================================

source("r_programs/setup.R")

log_step("CM Domain - Starting transformation")

# -----------------------------------------------------------------------------
# Step 1: Read source data
# -----------------------------------------------------------------------------
radmeds_raw <- read_csv(
  file.path(raw_data_path, "RADMEDS.csv"),
  show_col_types = FALSE
) %>%
  clean_names(case = "all_caps")

log_step(sprintf("Read %d records from source", nrow(radmeds_raw)))

# -----------------------------------------------------------------------------
# Step 2: Apply mappings and transformations
# -----------------------------------------------------------------------------
cm_temp <- radmeds_raw %>%
  mutate(
    STUDYID = study_id,
    DOMAIN = "CM",
    USUBJID = pmap_chr(
      list(STUDY, INVSITE, PT),
      ~ gen_usubjid(..1, ..2, ..3)
    )
  ) %>%
  mutate(
    CMTRT = as.character(coalesce(CMTRT, MEDNAME, MEDICATION, DRUG)),
    CMDECOD = CMTRT,  # Would use WHODrug coding in production
    CMDOSE = as.numeric(coalesce(CMDOSE, DOSE)),
    CMDOSU = as.character(coalesce(CMDOSU, DOSEUNIT, UNIT)),
    CMROUTE = toupper(as.character(coalesce(CMROUTE, ROUTE))),
    CMDOSFRQ = toupper(as.character(coalesce(CMDOSFRQ, FREQ, FREQUENCY))),
    CMSTDTC = map_chr(coalesce(CMSTDT, STDT), convert_to_iso),
    CMENDTC = map_chr(coalesce(CMENDT, ENDT), convert_to_iso),
    CMINDC = as.character(coalesce(CMINDC, INDICATION))
  )

# -----------------------------------------------------------------------------
# Step 3: Generate sequence numbers
# -----------------------------------------------------------------------------
cm_temp <- cm_temp %>%
  add_seq("cm", sort_vars = c("CMSTDTC"))

# -----------------------------------------------------------------------------
# Step 4: Select and order final variables
# -----------------------------------------------------------------------------
cm <- cm_temp %>%
  select(STUDYID, DOMAIN, USUBJID, CMSEQ, CMTRT, CMDECOD, CMDOSE, CMDOSU, CMROUTE, CMDOSFRQ, CMSTDTC, CMENDTC, CMINDC) %>%
  arrange(USUBJID, CMSEQ)

log_step(sprintf("Created %d CM records", nrow(cm)))

# -----------------------------------------------------------------------------
# Step 5: Validation checks
# -----------------------------------------------------------------------------
# Check for required variables
cm_validation <- cm %>%
  assert(not_na, STUDYID, USUBJID, CMSEQ) %>%
  verify(n_distinct(USUBJID) > 0)

# Check for duplicates
dup_check <- cm %>%
  group_by(USUBJID, CMSEQ) %>%
  filter(n() > 1) %>%
  nrow()

if (dup_check > 0) {
  warning(sprintf("Found %d duplicate records by USUBJID + CMSEQ", dup_check))
}

# -----------------------------------------------------------------------------
# Step 6: Save output
# -----------------------------------------------------------------------------
# Save as CSV
write_csv(cm, file.path(sdtm_output_path, "cm.csv"))

# Save as SAS transport (XPT) if haven is available
tryCatch({
  write_xpt(cm, file.path(sdtm_output_path, "cm.xpt"))
  log_step("Saved CM as XPT format")
}, error = function(e) {
  log_step("Could not save XPT format", "WARNING")
})

log_step("CM Domain - Complete", "SUCCESS")

# Return dataset for pipeline
cm
