/*******************************************************************************
* Program:    driver.sas
* Purpose:    Master driver for SDTM transformation pipeline
* Study:      MAXIS-08
* Created:    2026-01-21
* Author:     SDTM Pipeline (Auto-generated)
********************************************************************************/

%let start_time = %sysfunc(datetime());
%put NOTE: ================================================================;
%put NOTE: SDTM Transformation Pipeline - Started;
%put NOTE: Study: MAXIS-08;
%put NOTE: Start Time: %sysfunc(datetime(), datetime20.);
%put NOTE: ================================================================;

/* Run setup */
%include "&programs/setup.sas";

/* Execute domain transformations */
%include "&programs/lb.sas";
%include "&programs/lb.sas";
%include "&programs/lb.sas";
%include "&programs/pe.sas";
%include "&programs/ae.sas";
%include "&programs/lb.sas";
%include "&programs/cm.sas";
%include "&programs/suppae.sas";
%include "&programs/suppcm.sas";
%include "&programs/lb.sas";
%include "&programs/vs.sas";
%include "&programs/suppmh.sas";
%include "&programs/cm.sas";
%include "&programs/ex.sas";
%include "&programs/lb.sas";
%include "&programs/suppcm.sas";
%include "&programs/lb.sas";
%include "&programs/co.sas";
%include "&programs/suppmh.sas";
%include "&programs/suppmh.sas";
%include "&programs/mh.sas";
%include "&programs/ie.sas";
%include "&programs/lb.sas";
%include "&programs/lb.sas";
%include "&programs/tr.sas";
%include "&programs/mh.sas";
%include "&programs/tu.sas";
%include "&programs/mh.sas";
%include "&programs/qs.sas";
%include "&programs/lb.sas";
%include "&programs/pc.sas";
%include "&programs/qs.sas";
%include "&programs/dm.sas";
%include "&programs/eg.sas";
%include "&programs/cm.sas";
%include "&programs/rs.sas";
%include "&programs/pe.sas";
%include "&programs/ds.sas";
%include "&programs/pc.sas";
%include "&programs/dm.sas";
%include "&programs/ta.sas";
%include "&programs/ie.sas";
%include "&programs/pc.sas";
%include "&programs/lb.sas";
%include "&programs/pc.sas";
%include "&programs/ds.sas";
%include "&programs/qs.sas";
%include "&programs/lb.sas";

/* Generate final report */
%let end_time = %sysfunc(datetime());
%let duration = %sysevalf(&end_time - &start_time);

%put NOTE: ================================================================;
%put NOTE: SDTM Transformation Pipeline - Complete;
%put NOTE: Duration: %sysfunc(putn(&duration, time8.));
%put NOTE: ================================================================;

/* Summary of created datasets */
proc sql;
    title "SDTM Datasets Created";
    select memname as Dataset,
           nobs as Records,
           nvar as Variables
    from dictionary.tables
    where libname = "SDTM"
    order by memname;
quit;
