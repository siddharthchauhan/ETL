#' ============================================================================
#' Program:    vs.R
#' Purpose:    Create SDTM VS domain from source data
#' Study:      MAXIS-08
#' Source:     VITALS.csv
#' Created:    2026-01-20
#' Author:     SDTM Pipeline (Auto-generated)
#' ============================================================================

source("r_programs/setup.R")

log_step("VS Domain - Starting transformation")

# -----------------------------------------------------------------------------
# Step 1: Read source data
# -----------------------------------------------------------------------------
vitals_raw <- read_csv(
  file.path(raw_data_path, "VITALS.csv"),
  show_col_types = FALSE
) %>%
  clean_names(case = "all_caps")

log_step(sprintf("Read %d records from source", nrow(vitals_raw)))

# -----------------------------------------------------------------------------
# Step 2: Apply mappings and transformations
# -----------------------------------------------------------------------------
vs_temp <- vitals_raw %>%
  mutate(
    STUDYID = study_id,
    DOMAIN = "VS",
    USUBJID = pmap_chr(
      list(STUDY, INVSITE, PT),
      ~ gen_usubjid(..1, ..2, ..3)
    )
  ) %>%
  # Reshape vital signs from wide to long format
  pivot_longer(
    cols = any_of(c("SYSBP", "DIABP", "PULSE", "RESP", "TEMP", "WEIGHT", "HEIGHT")),
    names_to = "VSTESTCD",
    values_to = "VSORRES",
    values_drop_na = TRUE
  ) %>%
  mutate(
    VSTEST = case_when(
      VSTESTCD == "SYSBP" ~ "Systolic Blood Pressure",
      VSTESTCD == "DIABP" ~ "Diastolic Blood Pressure",
      VSTESTCD == "PULSE" ~ "Pulse Rate",
      VSTESTCD == "RESP" ~ "Respiratory Rate",
      VSTESTCD == "TEMP" ~ "Temperature",
      VSTESTCD == "WEIGHT" ~ "Weight",
      VSTESTCD == "HEIGHT" ~ "Height",
      TRUE ~ VSTESTCD
    ),
    VSORRESU = case_when(
      VSTESTCD == "SYSBP" ~ "mmHg",
      VSTESTCD == "DIABP" ~ "mmHg",
      VSTESTCD == "PULSE" ~ "beats/min",
      VSTESTCD == "RESP" ~ "breaths/min",
      VSTESTCD == "TEMP" ~ "C",
      VSTESTCD == "WEIGHT" ~ "kg",
      VSTESTCD == "HEIGHT" ~ "cm",
      TRUE ~ ""
    ),
    VSSTRESN = as.numeric(VSORRES),
    VSSTRESC = as.character(VSORRES),
    VSSTRESU = VSORRESU,
    VSDTC = map_chr(coalesce(VSDT, DATE, VISITDT), convert_to_iso)
  )

# -----------------------------------------------------------------------------
# Step 3: Generate sequence numbers
# -----------------------------------------------------------------------------
vs_temp <- vs_temp %>%
  add_seq("vs", sort_vars = c("VSDTC", "VSTESTCD"))

# -----------------------------------------------------------------------------
# Step 4: Select and order final variables
# -----------------------------------------------------------------------------
vs <- vs_temp %>%
  select(STUDYID, DOMAIN, USUBJID, VSSEQ, VSTESTCD, VSTEST, VSORRES, VSORRESU, VSSTRESC, VSSTRESN, VSSTRESU, VSDTC) %>%
  arrange(USUBJID, VSSEQ)

log_step(sprintf("Created %d VS records", nrow(vs)))

# -----------------------------------------------------------------------------
# Step 5: Validation checks
# -----------------------------------------------------------------------------
# Check for required variables
vs_validation <- vs %>%
  assert(not_na, STUDYID, USUBJID, VSSEQ) %>%
  verify(n_distinct(USUBJID) > 0)

# Check for duplicates
dup_check <- vs %>%
  group_by(USUBJID, VSSEQ) %>%
  filter(n() > 1) %>%
  nrow()

if (dup_check > 0) {
  warning(sprintf("Found %d duplicate records by USUBJID + VSSEQ", dup_check))
}

# -----------------------------------------------------------------------------
# Step 6: Save output
# -----------------------------------------------------------------------------
# Save as CSV
write_csv(vs, file.path(sdtm_output_path, "vs.csv"))

# Save as SAS transport (XPT) if haven is available
tryCatch({
  write_xpt(vs, file.path(sdtm_output_path, "vs.xpt"))
  log_step("Saved VS as XPT format")
}, error = function(e) {
  log_step("Could not save XPT format", "WARNING")
})

log_step("VS Domain - Complete", "SUCCESS")

# Return dataset for pipeline
vs
