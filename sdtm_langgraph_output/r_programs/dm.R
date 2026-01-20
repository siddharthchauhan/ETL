#' ============================================================================
#' Program:    dm.R
#' Purpose:    Create SDTM DM domain from source data
#' Study:      MAXIS-08
#' Source:     DEMO.csv
#' Created:    2026-01-20
#' Author:     SDTM Pipeline (Auto-generated)
#' ============================================================================

source("r_programs/setup.R")

log_step("DM Domain - Starting transformation")

# -----------------------------------------------------------------------------
# Step 1: Read source data
# -----------------------------------------------------------------------------
demo_raw <- read_csv(
  file.path(raw_data_path, "DEMO.csv"),
  show_col_types = FALSE
) %>%
  clean_names(case = "all_caps")

log_step(sprintf("Read %d records from source", nrow(demo_raw)))

# -----------------------------------------------------------------------------
# Step 2: Apply mappings and transformations
# -----------------------------------------------------------------------------
dm_temp <- demo_raw %>%
  mutate(
    STUDYID = study_id,
    DOMAIN = "DM",
    USUBJID = pmap_chr(
      list(STUDY, INVSITE, PT),
      ~ gen_usubjid(..1, ..2, ..3)
    )
  ) %>%
  mutate(
    SUBJID = as.character(PT),
    SITEID = str_extract(INVSITE, "\\d+$"),
    BRTHDTC = map_chr(DOB, convert_to_iso),
    SEX = map_chr(coalesce(GENDER, GENDRL), ~ map_ct(.x, ct_sex)),
    RACE = map_chr(RCE, ~ map_ct(.x, ct_race)),
    ETHNIC = if_else(
      grepl("HISPANIC", toupper(RCE)),
      "HISPANIC OR LATINO",
      "NOT HISPANIC OR LATINO"
    ),
    AGE = as.integer(
      difftime(Sys.Date(), as.Date(BRTHDTC), units = "days") / 365.25
    ),
    AGEU = "YEARS"
  )

# -----------------------------------------------------------------------------
# Step 3: Generate sequence numbers
# -----------------------------------------------------------------------------
dm_temp <- dm_temp %>%
  add_seq("dm", sort_vars = c("BRTHDTC"))

# -----------------------------------------------------------------------------
# Step 4: Select and order final variables
# -----------------------------------------------------------------------------
dm <- dm_temp %>%
  select(STUDYID, DOMAIN, USUBJID, SUBJID, SITEID, BRTHDTC, AGE, AGEU, SEX, RACE, ETHNIC) %>%
  arrange(USUBJID, DMSEQ)

log_step(sprintf("Created %d DM records", nrow(dm)))

# -----------------------------------------------------------------------------
# Step 5: Validation checks
# -----------------------------------------------------------------------------
# Check for required variables
dm_validation <- dm %>%
  assert(not_na, STUDYID, USUBJID, DMSEQ) %>%
  verify(n_distinct(USUBJID) > 0)

# Check for duplicates
dup_check <- dm %>%
  group_by(USUBJID, DMSEQ) %>%
  filter(n() > 1) %>%
  nrow()

if (dup_check > 0) {
  warning(sprintf("Found %d duplicate records by USUBJID + DMSEQ", dup_check))
}

# -----------------------------------------------------------------------------
# Step 6: Save output
# -----------------------------------------------------------------------------
# Save as CSV
write_csv(dm, file.path(sdtm_output_path, "dm.csv"))

# Save as SAS transport (XPT) if haven is available
tryCatch({
  write_xpt(dm, file.path(sdtm_output_path, "dm.xpt"))
  log_step("Saved DM as XPT format")
}, error = function(e) {
  log_step("Could not save XPT format", "WARNING")
})

log_step("DM Domain - Complete", "SUCCESS")

# Return dataset for pipeline
dm
