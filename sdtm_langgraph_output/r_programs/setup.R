#' ============================================================================
#' Program:    setup.R
#' Purpose:    Initialize environment for SDTM transformations
#' Study:      MAXIS-08
#' Created:    2026-01-21
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
tryCatch({
  library(admiral)
  library(metacore)
  library(metatools)
  message("Pharmaverse packages loaded successfully")
}, error = function(e) {
  message("Note: Pharmaverse packages not installed. Using base tidyverse.")
})

# Configuration
study_id <- "MAXIS-08"
raw_data_path <- "rawdata"
sdtm_output_path <- "sdtm"

# Create output directories
dir.create(sdtm_output_path, showWarnings = FALSE, recursive = TRUE)
dir.create("logs", showWarnings = FALSE, recursive = TRUE)

# Logging function
log_step <- function(step, status = "INFO") {
  timestamp <- format(Sys.time(), "%Y-%m-%d %H:%M:%S")
  message(sprintf("[%s] %s: %s", timestamp, status, step))
}

#' Convert date to ISO 8601 format
#' @param x Date value (numeric YYYYMMDD or character)
#' @return ISO 8601 formatted date string
convert_to_iso <- function(x) {
  if (is.na(x) || x == "") return(NA_character_)

  # Handle numeric YYYYMMDD
  if (is.numeric(x)) {
    x <- as.character(as.integer(x))
  }

  x <- as.character(x)

  if (nchar(x) == 8 && grepl("^\\d{8}$", x)) {
    # YYYYMMDD format
    formatted <- tryCatch({
      date <- as.Date(x, format = "%Y%m%d")
      format(date, "%Y-%m-%d")
    }, error = function(e) NA_character_)
    return(formatted)
  }

  return(x)
}

#' Generate USUBJID
#' @param study Study identifier
#' @param site Site identifier
#' @param subj Subject identifier
#' @return USUBJID string
gen_usubjid <- function(study, site, subj) {
  # Extract site number if formatted like C008_408
  site_clean <- if (grepl("_", site)) {
    strsplit(as.character(site), "_")[[1]][2]
  } else {
    as.character(site)
  }

  paste(study, site_clean, subj, sep = "-")
}

#' Generate sequence number within subject
#' @param data Data frame
#' @param domain Domain code
#' @param sort_vars Variables to sort by
#' @return Data frame with sequence variable added
add_seq <- function(data, domain, sort_vars = NULL) {
  seq_var <- paste0(toupper(domain), "SEQ")

  data %>%
    arrange(USUBJID, across(all_of(sort_vars))) %>%
    group_by(USUBJID) %>%
    mutate(!!seq_var := row_number()) %>%
    ungroup()
}

#' Map values to controlled terminology
#' @param x Input value
#' @param mapping Named vector of mappings
#' @return Mapped value
map_ct <- function(x, mapping) {
  if (is.na(x)) return(NA_character_)
  x_upper <- toupper(trimws(as.character(x)))
  if (x_upper %in% names(mapping)) {
    return(mapping[x_upper])
  }
  return(x_upper)
}

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
