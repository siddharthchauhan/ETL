/*******************************************************************************
* Program:    setup.sas
* Purpose:    Initialize environment for SDTM transformations
* Study:      MAXIS-08
* Created:    2026-01-21
* Author:     SDTM Pipeline (Auto-generated)
********************************************************************************/

%let study = MAXIS-08;
%let root = /clinical/&study;
%let rawdata = &root/rawdata;
%let sdtm = &root/sdtm;
%let programs = &root/programs;
%let logs = &root/logs;

/* Create library references */
libname raw "&rawdata" access=readonly;
libname sdtm "&sdtm";

/* Setup output options */
options mprint mlogic symbolgen;
options validvarname=upcase;
options nofmterr;

/* Macro for logging */
%macro log_step(step=, status=);
    %put NOTE: ================================================================;
    %put NOTE: Step: &step;
    %put NOTE: Status: &status;
    %put NOTE: Timestamp: %sysfunc(datetime(), datetime20.);
    %put NOTE: ================================================================;
%mend log_step;

/* Macro for date conversion to ISO 8601 */
%macro convert_to_iso(invar=, outvar=);
    length &outvar $20;
    if not missing(&invar) then do;
        if length(strip(put(&invar, best.))) = 8 then do;
            &outvar = put(input(put(&invar, 8.), yymmdd8.), e8601da.);
        end;
        else do;
            &outvar = put(&invar, e8601da.);
        end;
    end;
%mend convert_to_iso;

/* Macro for generating USUBJID */
%macro gen_usubjid(study=, site=, subj=);
    catx("-", &study, &site, &subj)
%mend gen_usubjid;

/* Macro for sequence number generation */
%macro gen_seq(domain=, sortvar=);
    proc sort data=&domain._temp;
        by usubjid &sortvar;
    run;

    data &domain._temp;
        set &domain._temp;
        by usubjid;
        if first.usubjid then &domain.seq = 0;
        &domain.seq + 1;
    run;
%mend gen_seq;

%log_step(step=Setup Complete, status=SUCCESS);
