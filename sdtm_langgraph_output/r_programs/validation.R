#' ============================================================================
#' Program:    validation.R
#' Purpose:    Validate SDTM datasets against CDISC standards
#' Study:      MAXIS-08
#' Created:    2026-01-20
#' ============================================================================

source("r_programs/setup.R")

log_step("Starting SDTM Validation")

# Load all SDTM datasets
sdtm_files <- list.files(sdtm_output_path, pattern = "\\.csv$", full.names = TRUE)
sdtm_data <- map(setNames(sdtm_files, tools::file_path_sans_ext(basename(sdtm_files))),
                 read_csv, show_col_types = FALSE)

# Validation results
validation_results <- list()

#' Validate a single domain
validate_domain <- function(df, domain) {
  issues <- list()

  # Check required variables
  required_vars <- c("STUDYID", "DOMAIN", "USUBJID")
  seq_var <- paste0(domain, "SEQ")
  if (seq_var %in% names(df)) {
    required_vars <- c(required_vars, seq_var)
  }

  for (var in required_vars) {
    if (!var %in% names(df)) {
      issues <- c(issues, list(list(
        domain = domain,
        variable = var,
        severity = "ERROR",
        message = sprintf("Required variable %s is missing", var)
      )))
    } else if (all(is.na(df[[var]]))) {
      issues <- c(issues, list(list(
        domain = domain,
        variable = var,
        severity = "ERROR",
        message = sprintf("Required variable %s is completely empty", var)
      )))
    }
  }

  # Check DOMAIN value
  if ("DOMAIN" %in% names(df)) {
    wrong_domain <- sum(df$DOMAIN != domain, na.rm = TRUE)
    if (wrong_domain > 0) {
      issues <- c(issues, list(list(
        domain = domain,
        variable = "DOMAIN",
        severity = "ERROR",
        message = sprintf("%d records have incorrect DOMAIN value", wrong_domain)
      )))
    }
  }

  # Check for duplicates
  if (seq_var %in% names(df) && "USUBJID" %in% names(df)) {
    dups <- df %>%
      group_by(USUBJID, .data[[seq_var]]) %>%
      filter(n() > 1) %>%
      nrow()

    if (dups > 0) {
      issues <- c(issues, list(list(
        domain = domain,
        variable = seq_var,
        severity = "ERROR",
        message = sprintf("%d duplicate records by USUBJID + %s", dups, seq_var)
      )))
    }
  }

  # Check date formats (ISO 8601)
  date_vars <- names(df)[grepl("DTC$", names(df))]
  iso_pattern <- "^\\d{4}(-\\d{2}(-\\d{2})?)?$"

  for (dvar in date_vars) {
    invalid_dates <- sum(!grepl(iso_pattern, df[[dvar]]) & !is.na(df[[dvar]]))
    if (invalid_dates > 0) {
      issues <- c(issues, list(list(
        domain = domain,
        variable = dvar,
        severity = "ERROR",
        message = sprintf("%d records have non-ISO 8601 dates", invalid_dates)
      )))
    }
  }

  list(
    domain = domain,
    records = nrow(df),
    issues = issues,
    is_valid = length(Filter(function(x) x$severity == "ERROR", issues)) == 0
  )
}

# Validate each domain
for (domain_name in names(sdtm_data)) {
  domain_code <- toupper(domain_name)
  log_step(sprintf("Validating %s domain", domain_code))

  result <- validate_domain(sdtm_data[[domain_name]], domain_code)
  validation_results[[domain_code]] <- result

  if (!result$is_valid) {
    log_step(sprintf("%s has validation errors", domain_code), "WARNING")
  }
}

# Generate validation report
report <- map_df(validation_results, function(r) {
  tibble(
    Domain = r$domain,
    Records = r$records,
    Valid = r$is_valid,
    Errors = length(Filter(function(x) x$severity == "ERROR", r$issues)),
    Warnings = length(Filter(function(x) x$severity == "WARNING", r$issues))
  )
})

cat("\n")
cat("=" %>% rep(70) %>% paste(collapse = ""), "\n")
cat("SDTM Validation Report\n")
cat("=" %>% rep(70) %>% paste(collapse = ""), "\n")
print(report)
cat("\n")

# Overall status
all_valid <- all(report$Valid)
if (all_valid) {
  log_step("All domains passed validation", "SUCCESS")
} else {
  log_step("Some domains have validation issues", "WARNING")
}

# Save detailed report
all_issues <- map_df(validation_results, function(r) {
  if (length(r$issues) > 0) {
    map_df(r$issues, as_tibble)
  } else {
    tibble()
  }
})

if (nrow(all_issues) > 0) {
  write_csv(all_issues, file.path(sdtm_output_path, "validation_issues.csv"))
  log_step("Validation issues saved to validation_issues.csv")
}

# Return results
list(
  summary = report,
  details = validation_results,
  submission_ready = all_valid
)
