"""
R Code Generator
================
Generates R code for SDTM transformations using pharmaverse packages.
"""

from typing import List, Dict, Any, Optional
from datetime import datetime
import os

from ..models.sdtm_models import MappingSpecification, ColumnMapping


class RCodeGenerator:
    """
    Generates R programs for SDTM transformations.

    Uses pharmaverse ecosystem:
    - admiral: ADaM dataset derivation
    - sdtm.oak: SDTM transformation
    - metacore: Metadata management
    - metatools: Metadata-driven tools
    """

    def __init__(self, study_id: str, output_dir: str = "./r_programs"):
        self.study_id = study_id
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)

    def generate_all(self, mappings: List[MappingSpecification]) -> Dict[str, str]:
        """
        Generate all R scripts for given mappings.

        Args:
            mappings: List of mapping specifications

        Returns:
            Dictionary of script names to file paths
        """
        generated_files = {}

        # Generate setup script
        setup_path = self.generate_setup_script()
        generated_files["setup"] = setup_path

        # Generate domain scripts
        for spec in mappings:
            domain_path = self.generate_domain_script(spec)
            generated_files[spec.target_domain] = domain_path

        # Generate master driver
        driver_path = self.generate_driver_script(mappings)
        generated_files["driver"] = driver_path

        # Generate validation script
        validation_path = self.generate_validation_script()
        generated_files["validation"] = validation_path

        return generated_files

    def generate_setup_script(self) -> str:
        """Generate setup/initialization R script."""
        code = f'''#' ============================================================================
#' Program:    setup.R
#' Purpose:    Initialize environment for SDTM transformations
#' Study:      {self.study_id}
#' Created:    {datetime.now().strftime("%Y-%m-%d")}
#' Author:     SDTM Pipeline (Auto-generated)
#' ============================================================================

# Load required packages
library(tidyverse)
library(lubridate)
library(haven)
library(readr)
library(janitor)
library(assertr)

# Pharmaverse packages (if available)
tryCatch({{
  library(admiral)
  library(metacore)
  library(metatools)
  message("Pharmaverse packages loaded successfully")
}}, error = function(e) {{
  message("Note: Pharmaverse packages not installed. Using base tidyverse.")
}})

# Configuration
study_id <- "{self.study_id}"
raw_data_path <- "rawdata"
sdtm_output_path <- "sdtm"

# Create output directories
dir.create(sdtm_output_path, showWarnings = FALSE, recursive = TRUE)
dir.create("logs", showWarnings = FALSE, recursive = TRUE)

# Logging function
log_step <- function(step, status = "INFO") {{
  timestamp <- format(Sys.time(), "%Y-%m-%d %H:%M:%S")
  message(sprintf("[%s] %s: %s", timestamp, status, step))
}}

#' Convert date to ISO 8601 format
#' @param x Date value (numeric YYYYMMDD or character)
#' @return ISO 8601 formatted date string
convert_to_iso <- function(x) {{
  if (is.na(x) || x == "") return(NA_character_)

  # Handle numeric YYYYMMDD
  if (is.numeric(x)) {{
    x <- as.character(as.integer(x))
  }}

  x <- as.character(x)

  if (nchar(x) == 8 && grepl("^\\\\d{{8}}$", x)) {{
    # YYYYMMDD format
    formatted <- tryCatch({{
      date <- as.Date(x, format = "%Y%m%d")
      format(date, "%Y-%m-%d")
    }}, error = function(e) NA_character_)
    return(formatted)
  }}

  return(x)
}}

#' Generate USUBJID
#' @param study Study identifier
#' @param site Site identifier
#' @param subj Subject identifier
#' @return USUBJID string
gen_usubjid <- function(study, site, subj) {{
  # Extract site number if formatted like C008_408
  site_clean <- if (grepl("_", site)) {{
    strsplit(as.character(site), "_")[[1]][2]
  }} else {{
    as.character(site)
  }}

  paste(study, site_clean, subj, sep = "-")
}}

#' Generate sequence number within subject
#' @param data Data frame
#' @param domain Domain code
#' @param sort_vars Variables to sort by
#' @return Data frame with sequence variable added
add_seq <- function(data, domain, sort_vars = NULL) {{
  seq_var <- paste0(toupper(domain), "SEQ")

  data %>%
    arrange(USUBJID, across(all_of(sort_vars))) %>%
    group_by(USUBJID) %>%
    mutate(!!seq_var := row_number()) %>%
    ungroup()
}}

#' Map values to controlled terminology
#' @param x Input value
#' @param mapping Named vector of mappings
#' @return Mapped value
map_ct <- function(x, mapping) {{
  if (is.na(x)) return(NA_character_)
  x_upper <- toupper(trimws(as.character(x)))
  if (x_upper %in% names(mapping)) {{
    return(mapping[x_upper])
  }}
  return(x_upper)
}}

# Controlled terminology mappings
ct_sex <- c(
  "M" = "M", "MALE" = "M",
  "F" = "F", "FEMALE" = "F",
  "U" = "U", "UNKNOWN" = "U"
)

ct_race <- c(
  "WHITE" = "WHITE",
  "BLACK" = "BLACK OR AFRICAN AMERICAN",
  "AFRICAN AMERICAN" = "BLACK OR AFRICAN AMERICAN",
  "ASIAN" = "ASIAN",
  "HISPANIC" = "WHITE",
  "NATIVE" = "AMERICAN INDIAN OR ALASKA NATIVE",
  "PACIFIC" = "NATIVE HAWAIIAN OR OTHER PACIFIC ISLANDER",
  "OTHER" = "OTHER",
  "UNKNOWN" = "UNKNOWN"
)

log_step("Setup complete", "SUCCESS")
'''
        output_path = os.path.join(self.output_dir, "setup.R")
        with open(output_path, 'w') as f:
            f.write(code)
        return output_path

    def generate_domain_script(self, spec: MappingSpecification) -> str:
        """Generate R script for a specific domain transformation."""
        domain = spec.target_domain
        source = spec.source_domain.replace(".csv", "").lower()

        # Build domain-specific transformation code
        transform_code = self._generate_transform_code(spec)

        code = f'''#' ============================================================================
#' Program:    {domain.lower()}.R
#' Purpose:    Create SDTM {domain} domain from source data
#' Study:      {spec.study_id}
#' Source:     {spec.source_domain}
#' Created:    {datetime.now().strftime("%Y-%m-%d")}
#' Author:     SDTM Pipeline (Auto-generated)
#' ============================================================================

source("r_programs/setup.R")

log_step("{domain} Domain - Starting transformation")

# -----------------------------------------------------------------------------
# Step 1: Read source data
# -----------------------------------------------------------------------------
{source}_raw <- read_csv(
  file.path(raw_data_path, "{spec.source_domain}"),
  show_col_types = FALSE
) %>%
  clean_names(case = "all_caps")

log_step(sprintf("Read %d records from source", nrow({source}_raw)))

# -----------------------------------------------------------------------------
# Step 2: Apply mappings and transformations
# -----------------------------------------------------------------------------
{domain.lower()}_temp <- {source}_raw %>%
  mutate(
    STUDYID = study_id,
    DOMAIN = "{domain}",
    USUBJID = pmap_chr(
      list(STUDY, INVSITE, PT),
      ~ gen_usubjid(..1, ..2, ..3)
    )
  ) %>%
{transform_code}

# -----------------------------------------------------------------------------
# Step 3: Generate sequence numbers
# -----------------------------------------------------------------------------
{domain.lower()}_temp <- {domain.lower()}_temp %>%
  add_seq("{domain.lower()}", sort_vars = {self._get_sort_vars_r(domain)})

# -----------------------------------------------------------------------------
# Step 4: Select and order final variables
# -----------------------------------------------------------------------------
{domain.lower()} <- {domain.lower()}_temp %>%
  select({self._get_select_vars_r(domain)}) %>%
  arrange(USUBJID, {domain}SEQ)

log_step(sprintf("Created %d {domain} records", nrow({domain.lower()})))

# -----------------------------------------------------------------------------
# Step 5: Validation checks
# -----------------------------------------------------------------------------
# Check for required variables
{domain.lower()}_validation <- {domain.lower()} %>%
  assert(not_na, STUDYID, USUBJID, {domain}SEQ) %>%
  verify(n_distinct(USUBJID) > 0)

# Check for duplicates
dup_check <- {domain.lower()} %>%
  group_by(USUBJID, {domain}SEQ) %>%
  filter(n() > 1) %>%
  nrow()

if (dup_check > 0) {{
  warning(sprintf("Found %d duplicate records by USUBJID + {domain}SEQ", dup_check))
}}

# -----------------------------------------------------------------------------
# Step 6: Save output
# -----------------------------------------------------------------------------
# Save as CSV
write_csv({domain.lower()}, file.path(sdtm_output_path, "{domain.lower()}.csv"))

# Save as SAS transport (XPT) if haven is available
tryCatch({{
  write_xpt({domain.lower()}, file.path(sdtm_output_path, "{domain.lower()}.xpt"))
  log_step("Saved {domain} as XPT format")
}}, error = function(e) {{
  log_step("Could not save XPT format", "WARNING")
}})

log_step("{domain} Domain - Complete", "SUCCESS")

# Return dataset for pipeline
{domain.lower()}
'''
        output_path = os.path.join(self.output_dir, f"{domain.lower()}.R")
        with open(output_path, 'w') as f:
            f.write(code)
        return output_path

    def _generate_transform_code(self, spec: MappingSpecification) -> str:
        """Generate R transformation code from mappings."""
        domain = spec.target_domain

        if domain == "DM":
            return '''  mutate(
    SUBJID = as.character(PT),
    SITEID = str_extract(INVSITE, "\\\\d+$"),
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
  )'''

        elif domain == "AE":
            return '''  mutate(
    AETERM = as.character(coalesce(AETERM, AEDESC, AENAME)),
    AEDECOD = AETERM,  # Would use MedDRA coding in production
    AESTDTC = map_chr(coalesce(AESTDT, STDT), convert_to_iso),
    AEENDTC = map_chr(coalesce(AEENDT, ENDT), convert_to_iso),
    AESEV = toupper(as.character(AESEV)),
    AESER = if_else(toupper(as.character(AESER)) %in% c("Y", "YES", "1", "TRUE"), "Y", "N"),
    AEREL = toupper(as.character(AEREL)),
    AEOUT = as.character(AEOUT)
  )'''

        elif domain == "VS":
            return '''  # Reshape vital signs from wide to long format
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
  )'''

        elif domain == "LB":
            return '''  mutate(
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
  )'''

        elif domain == "CM":
            return '''  mutate(
    CMTRT = as.character(coalesce(CMTRT, MEDNAME, MEDICATION, DRUG)),
    CMDECOD = CMTRT,  # Would use WHODrug coding in production
    CMDOSE = as.numeric(coalesce(CMDOSE, DOSE)),
    CMDOSU = as.character(coalesce(CMDOSU, DOSEUNIT, UNIT)),
    CMROUTE = toupper(as.character(coalesce(CMROUTE, ROUTE))),
    CMDOSFRQ = toupper(as.character(coalesce(CMDOSFRQ, FREQ, FREQUENCY))),
    CMSTDTC = map_chr(coalesce(CMSTDT, STDT), convert_to_iso),
    CMENDTC = map_chr(coalesce(CMENDT, ENDT), convert_to_iso),
    CMINDC = as.character(coalesce(CMINDC, INDICATION))
  )'''

        return "  # No specific transformations defined"

    def _get_sort_vars_r(self, domain: str) -> str:
        """Get sort variables for R."""
        sort_vars = {
            "DM": 'c("BRTHDTC")',
            "AE": 'c("AESTDTC")',
            "VS": 'c("VSDTC", "VSTESTCD")',
            "LB": 'c("LBDTC", "LBTESTCD")',
            "CM": 'c("CMSTDTC")',
        }
        return sort_vars.get(domain, 'c("USUBJID")')

    def _get_select_vars_r(self, domain: str) -> str:
        """Get select variables for R."""
        selects = {
            "DM": "STUDYID, DOMAIN, USUBJID, SUBJID, SITEID, BRTHDTC, AGE, AGEU, SEX, RACE, ETHNIC",
            "AE": "STUDYID, DOMAIN, USUBJID, AESEQ, AETERM, AEDECOD, AESTDTC, AEENDTC, AESEV, AESER, AEREL, AEOUT",
            "VS": "STUDYID, DOMAIN, USUBJID, VSSEQ, VSTESTCD, VSTEST, VSORRES, VSORRESU, VSSTRESC, VSSTRESN, VSSTRESU, VSDTC",
            "LB": "STUDYID, DOMAIN, USUBJID, LBSEQ, LBTESTCD, LBTEST, LBCAT, LBORRES, LBORRESU, LBSTRESC, LBSTRESN, LBSTRESU, LBNRIND, LBDTC",
            "CM": "STUDYID, DOMAIN, USUBJID, CMSEQ, CMTRT, CMDECOD, CMDOSE, CMDOSU, CMROUTE, CMDOSFRQ, CMSTDTC, CMENDTC, CMINDC",
        }
        return selects.get(domain, "everything()")

    def generate_driver_script(self, mappings: List[MappingSpecification]) -> str:
        """Generate master driver R script."""
        domain_sources = "\n".join([
            f'source("r_programs/{spec.target_domain.lower()}.R")'
            for spec in mappings
        ])

        code = f'''#' ============================================================================
#' Program:    driver.R
#' Purpose:    Master driver for SDTM transformation pipeline
#' Study:      {self.study_id}
#' Created:    {datetime.now().strftime("%Y-%m-%d")}
#' Author:     SDTM Pipeline (Auto-generated)
#' ============================================================================

start_time <- Sys.time()
message("=" %>% rep(70) %>% paste(collapse = ""))
message("SDTM Transformation Pipeline - Started")
message(sprintf("Study: %s", "{self.study_id}"))
message(sprintf("Start Time: %s", start_time))
message("=" %>% rep(70) %>% paste(collapse = ""))

# Load setup
source("r_programs/setup.R")

# Execute domain transformations
{domain_sources}

# Generate summary report
end_time <- Sys.time()
duration <- difftime(end_time, start_time, units = "mins")

message("=" %>% rep(70) %>% paste(collapse = ""))
message("SDTM Transformation Pipeline - Complete")
message(sprintf("Duration: %.2f minutes", as.numeric(duration)))
message("=" %>% rep(70) %>% paste(collapse = ""))

# Summary of created datasets
sdtm_files <- list.files(sdtm_output_path, pattern = "\\\\.csv$", full.names = TRUE)
summary_df <- map_df(sdtm_files, function(f) {{
  df <- read_csv(f, show_col_types = FALSE)
  tibble(
    Dataset = tools::file_path_sans_ext(basename(f)),
    Records = nrow(df),
    Variables = ncol(df)
  )
}})

print(summary_df)
'''
        output_path = os.path.join(self.output_dir, "driver.R")
        with open(output_path, 'w') as f:
            f.write(code)
        return output_path

    def generate_validation_script(self) -> str:
        """Generate validation R script."""
        code = f'''#' ============================================================================
#' Program:    validation.R
#' Purpose:    Validate SDTM datasets against CDISC standards
#' Study:      {self.study_id}
#' Created:    {datetime.now().strftime("%Y-%m-%d")}
#' ============================================================================

source("r_programs/setup.R")

log_step("Starting SDTM Validation")

# Load all SDTM datasets
sdtm_files <- list.files(sdtm_output_path, pattern = "\\\\.csv$", full.names = TRUE)
sdtm_data <- map(setNames(sdtm_files, tools::file_path_sans_ext(basename(sdtm_files))),
                 read_csv, show_col_types = FALSE)

# Validation results
validation_results <- list()

#' Validate a single domain
validate_domain <- function(df, domain) {{
  issues <- list()

  # Check required variables
  required_vars <- c("STUDYID", "DOMAIN", "USUBJID")
  seq_var <- paste0(domain, "SEQ")
  if (seq_var %in% names(df)) {{
    required_vars <- c(required_vars, seq_var)
  }}

  for (var in required_vars) {{
    if (!var %in% names(df)) {{
      issues <- c(issues, list(list(
        domain = domain,
        variable = var,
        severity = "ERROR",
        message = sprintf("Required variable %s is missing", var)
      )))
    }} else if (all(is.na(df[[var]]))) {{
      issues <- c(issues, list(list(
        domain = domain,
        variable = var,
        severity = "ERROR",
        message = sprintf("Required variable %s is completely empty", var)
      )))
    }}
  }}

  # Check DOMAIN value
  if ("DOMAIN" %in% names(df)) {{
    wrong_domain <- sum(df$DOMAIN != domain, na.rm = TRUE)
    if (wrong_domain > 0) {{
      issues <- c(issues, list(list(
        domain = domain,
        variable = "DOMAIN",
        severity = "ERROR",
        message = sprintf("%d records have incorrect DOMAIN value", wrong_domain)
      )))
    }}
  }}

  # Check for duplicates
  if (seq_var %in% names(df) && "USUBJID" %in% names(df)) {{
    dups <- df %>%
      group_by(USUBJID, .data[[seq_var]]) %>%
      filter(n() > 1) %>%
      nrow()

    if (dups > 0) {{
      issues <- c(issues, list(list(
        domain = domain,
        variable = seq_var,
        severity = "ERROR",
        message = sprintf("%d duplicate records by USUBJID + %s", dups, seq_var)
      )))
    }}
  }}

  # Check date formats (ISO 8601)
  date_vars <- names(df)[grepl("DTC$", names(df))]
  iso_pattern <- "^\\\\d{{4}}(-\\\\d{{2}}(-\\\\d{{2}})?)?$"

  for (dvar in date_vars) {{
    invalid_dates <- sum(!grepl(iso_pattern, df[[dvar]]) & !is.na(df[[dvar]]))
    if (invalid_dates > 0) {{
      issues <- c(issues, list(list(
        domain = domain,
        variable = dvar,
        severity = "ERROR",
        message = sprintf("%d records have non-ISO 8601 dates", invalid_dates)
      )))
    }}
  }}

  list(
    domain = domain,
    records = nrow(df),
    issues = issues,
    is_valid = length(Filter(function(x) x$severity == "ERROR", issues)) == 0
  )
}}

# Validate each domain
for (domain_name in names(sdtm_data)) {{
  domain_code <- toupper(domain_name)
  log_step(sprintf("Validating %s domain", domain_code))

  result <- validate_domain(sdtm_data[[domain_name]], domain_code)
  validation_results[[domain_code]] <- result

  if (!result$is_valid) {{
    log_step(sprintf("%s has validation errors", domain_code), "WARNING")
  }}
}}

# Generate validation report
report <- map_df(validation_results, function(r) {{
  tibble(
    Domain = r$domain,
    Records = r$records,
    Valid = r$is_valid,
    Errors = length(Filter(function(x) x$severity == "ERROR", r$issues)),
    Warnings = length(Filter(function(x) x$severity == "WARNING", r$issues))
  )
}})

cat("\\n")
cat("=" %>% rep(70) %>% paste(collapse = ""), "\\n")
cat("SDTM Validation Report\\n")
cat("=" %>% rep(70) %>% paste(collapse = ""), "\\n")
print(report)
cat("\\n")

# Overall status
all_valid <- all(report$Valid)
if (all_valid) {{
  log_step("All domains passed validation", "SUCCESS")
}} else {{
  log_step("Some domains have validation issues", "WARNING")
}}

# Save detailed report
all_issues <- map_df(validation_results, function(r) {{
  if (length(r$issues) > 0) {{
    map_df(r$issues, as_tibble)
  }} else {{
    tibble()
  }}
}})

if (nrow(all_issues) > 0) {{
  write_csv(all_issues, file.path(sdtm_output_path, "validation_issues.csv"))
  log_step("Validation issues saved to validation_issues.csv")
}}

# Return results
list(
  summary = report,
  details = validation_results,
  submission_ready = all_valid
)
'''
        output_path = os.path.join(self.output_dir, "validation.R")
        with open(output_path, 'w') as f:
            f.write(code)
        return output_path
