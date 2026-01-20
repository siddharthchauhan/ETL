#' ============================================================================
#' Program:    lb.R
#' Purpose:    Create SDTM LB domain from source data
#' Study:      MAXIS-08
#' Source:     GENOLAB.csv
#' Created:    2026-01-20
#' Author:     SDTM Pipeline (Auto-generated)
#' ============================================================================

source("r_programs/setup.R")

log_step("LB Domain - Starting transformation")

# -----------------------------------------------------------------------------
# Step 1: Read source data
# -----------------------------------------------------------------------------
genolab_raw <- read_csv(
  file.path(raw_data_path, "GENOLAB.csv"),
  show_col_types = FALSE
) %>%
  clean_names(case = "all_caps")

log_step(sprintf("Read %d records from source", nrow(genolab_raw)))

# -----------------------------------------------------------------------------
# Step 2: Apply mappings and transformations
# -----------------------------------------------------------------------------
lb_temp <- genolab_raw %>%
  mutate(
    STUDYID = study_id,
    DOMAIN = "LB",
    USUBJID = pmap_chr(
      list(STUDY, INVSITE, PT),
      ~ gen_usubjid(..1, ..2, ..3)
    )
  ) %>%
  mutate(
    LBTESTCD = as.character(coalesce(LBTESTCD, TESTCD, TEST)),
    LBTEST = as.character(coalesce(LBTEST, TESTNAME, TEST)),
    LBCAT = as.character(coalesce(LBCAT, CAT, CATEGORY)),
    LBORRES = as.character(coalesce(LBORRES, RESULT, VALUE)),
    LBORRESU = as.character(coalesce(LBORRESU, UNIT, UNITS)),
    LBSTRESN = as.numeric(LBORRES),
    LBSTRESC = LBORRES,
    LBSTRESU = LBORRESU,
    LBORNRLO = as.character(coalesce(LBORNRLO, NRLO, LOLIMIT)),
    LBORNRHI = as.character(coalesce(LBORNRHI, NRHI, HILIMIT)),
    LBSTNRLO = as.numeric(LBORNRLO),
    LBSTNRHI = as.numeric(LBORNRHI),
    LBNRIND = case_when(
      !is.na(LBSTRESN) & !is.na(LBSTNRLO) & LBSTRESN < LBSTNRLO ~ "LOW",
      !is.na(LBSTRESN) & !is.na(LBSTNRHI) & LBSTRESN > LBSTNRHI ~ "HIGH",
      !is.na(LBSTRESN) ~ "NORMAL",
      TRUE ~ NA_character_
    ),
    LBDTC = map_chr(coalesce(LBDT, DATE, VISITDT), convert_to_iso)
  )

# -----------------------------------------------------------------------------
# Step 3: Generate sequence numbers
# -----------------------------------------------------------------------------
lb_temp <- lb_temp %>%
  add_seq("lb", sort_vars = c("LBDTC", "LBTESTCD"))

# -----------------------------------------------------------------------------
# Step 4: Select and order final variables
# -----------------------------------------------------------------------------
lb <- lb_temp %>%
  select(STUDYID, DOMAIN, USUBJID, LBSEQ, LBTESTCD, LBTEST, LBCAT, LBORRES, LBORRESU, LBSTRESC, LBSTRESN, LBSTRESU, LBNRIND, LBDTC) %>%
  arrange(USUBJID, LBSEQ)

log_step(sprintf("Created %d LB records", nrow(lb)))

# -----------------------------------------------------------------------------
# Step 5: Validation checks
# -----------------------------------------------------------------------------
# Check for required variables
lb_validation <- lb %>%
  assert(not_na, STUDYID, USUBJID, LBSEQ) %>%
  verify(n_distinct(USUBJID) > 0)

# Check for duplicates
dup_check <- lb %>%
  group_by(USUBJID, LBSEQ) %>%
  filter(n() > 1) %>%
  nrow()

if (dup_check > 0) {
  warning(sprintf("Found %d duplicate records by USUBJID + LBSEQ", dup_check))
}

# -----------------------------------------------------------------------------
# Step 6: Save output
# -----------------------------------------------------------------------------
# Save as CSV
write_csv(lb, file.path(sdtm_output_path, "lb.csv"))

# Save as SAS transport (XPT) if haven is available
tryCatch({
  write_xpt(lb, file.path(sdtm_output_path, "lb.xpt"))
  log_step("Saved LB as XPT format")
}, error = function(e) {
  log_step("Could not save XPT format", "WARNING")
})

log_step("LB Domain - Complete", "SUCCESS")

# Return dataset for pipeline
lb
