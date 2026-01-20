#' ============================================================================
#' Program:    driver.R
#' Purpose:    Master driver for SDTM transformation pipeline
#' Study:      MAXIS-08
#' Created:    2026-01-20
#' Author:     SDTM Pipeline (Auto-generated)
#' ============================================================================

start_time <- Sys.time()
message("=" %>% rep(70) %>% paste(collapse = ""))
message("SDTM Transformation Pipeline - Started")
message(sprintf("Study: %s", "MAXIS-08"))
message(sprintf("Start Time: %s", start_time))
message("=" %>% rep(70) %>% paste(collapse = ""))

# Load setup
source("r_programs/setup.R")

# Execute domain transformations
source("r_programs/lb.R")
source("r_programs/lb.R")
source("r_programs/lb.R")
source("r_programs/pe.R")
source("r_programs/ae.R")
source("r_programs/lb.R")
source("r_programs/cm.R")
source("r_programs/suppae.R")
source("r_programs/suppcm.R")
source("r_programs/lb.R")
source("r_programs/vs.R")
source("r_programs/suppmh.R")
source("r_programs/cm.R")
source("r_programs/lb.R")
source("r_programs/suppcm.R")
source("r_programs/lb.R")
source("r_programs/co.R")
source("r_programs/suppmh.R")
source("r_programs/suppmh.R")
source("r_programs/mh.R")
source("r_programs/ie.R")
source("r_programs/lb.R")
source("r_programs/lb.R")
source("r_programs/tr.R")
source("r_programs/mh.R")
source("r_programs/tu.R")
source("r_programs/mh.R")
source("r_programs/qs.R")
source("r_programs/lb.R")
source("r_programs/qs.R")
source("r_programs/dm.R")
source("r_programs/eg.R")
source("r_programs/cm.R")
source("r_programs/rs.R")
source("r_programs/pe.R")
source("r_programs/ds.R")
source("r_programs/pc.R")
source("r_programs/dm.R")
source("r_programs/ta.R")
source("r_programs/ie.R")
source("r_programs/pc.R")
source("r_programs/lb.R")
source("r_programs/pc.R")
source("r_programs/ds.R")
source("r_programs/qs.R")
source("r_programs/lb.R")

# Generate summary report
end_time <- Sys.time()
duration <- difftime(end_time, start_time, units = "mins")

message("=" %>% rep(70) %>% paste(collapse = ""))
message("SDTM Transformation Pipeline - Complete")
message(sprintf("Duration: %.2f minutes", as.numeric(duration)))
message("=" %>% rep(70) %>% paste(collapse = ""))

# Summary of created datasets
sdtm_files <- list.files(sdtm_output_path, pattern = "\\.csv$", full.names = TRUE)
summary_df <- map_df(sdtm_files, function(f) {
  df <- read_csv(f, show_col_types = FALSE)
  tibble(
    Dataset = tools::file_path_sans_ext(basename(f)),
    Records = nrow(df),
    Variables = ncol(df)
  )
})

print(summary_df)
