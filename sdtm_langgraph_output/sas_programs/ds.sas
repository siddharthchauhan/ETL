/*******************************************************************************
* Program:    ds.sas
* Purpose:    Create SDTM DS domain from source data
* Study:      MAXIS-08
* Source:     DEATHGEN.csv
* Created:    2026-01-20
* Author:     SDTM Pipeline (Auto-generated)
*
* Modification History:
* Date        Author      Description
* ----------  ----------  ---------------------------------------------------
* 2026-01-20  Pipeline    Initial creation
********************************************************************************/

%include "&programs/setup.sas";

%log_step(step=DS Domain - Start, status=RUNNING);

/*------------------------------------------------------------------------------
* Step 1: Read source data
------------------------------------------------------------------------------*/
data ds_raw;
    set raw.deathgen;
run;

%put NOTE: Source records read: %sysfunc(nobs(ds_raw));

/*------------------------------------------------------------------------------
* Step 2: Apply mappings and transformations
------------------------------------------------------------------------------*/
data ds_temp;
    length
        STUDYID $20
        DOMAIN $2
        USUBJID $40
        STUDYID $20
        DOMAIN $2
        USUBJID $40
    ;

    set ds_raw;

    /* Standard variables */
    STUDYID = "&study";
    DOMAIN = "DS";

    /* Generate USUBJID */
    USUBJID = %gen_usubjid(study=STUDY, site=scan(INVSITE, -1, "_"), subj=PT);

    /* STUDYID from STUDY */
    STUDYID = STUDY;

    /* DOMAIN: Domain abbreviation for Disposition domain */
    DOMAIN = Set to 'DS';

    /* USUBJID from STUDY,INVSITE,PT */
    USUBJID = STUDY,INVSITE,PT;
    /* TODO: Apply transformation: Concatenate with hyphens */

    /* DSSEQ from REPEATSN */
    DSSEQ = REPEATSN;

    /* DSTERM from CPEVENT */
    DSTERM = CPEVENT;

    /* DSDECOD from CPEVENT */
    DSDECOD = CPEVENT;

    /* DSCAT from DCMNAME */
    DSCAT = DCMNAME;
    /* TODO: Apply transformation: Extract category from form name */

    /* DSSTDTC from GNDT */
    %convert_to_iso(invar=GNDT, outvar=DSSTDTC);

run;

/*------------------------------------------------------------------------------
* Step 3: Generate sequence numbers
------------------------------------------------------------------------------*/
%gen_seq(domain=ds, sortvar=USUBJID);

/*------------------------------------------------------------------------------
* Step 4: Final dataset with variable ordering
------------------------------------------------------------------------------*/
data sdtm.ds (label="SDTM DS Domain");
    retain STUDYID DOMAIN USUBJID;
    set ds_temp;

    /* Apply formats */
    format _numeric_ best12.;
    format _character_ $varying.;

    /* Keep only SDTM variables */
    keep STUDYID DOMAIN USUBJID;
run;

/*------------------------------------------------------------------------------
* Step 5: Validation checks
------------------------------------------------------------------------------*/

/* Check for required variables */
proc sql noprint;
    select count(*) into :missing_studyid
    from sdtm.ds
    where missing(STUDYID);

    select count(*) into :missing_usubjid
    from sdtm.ds
    where missing(USUBJID);
quit;

%if &missing_studyid > 0 %then %do;
    %put ERROR: Found &missing_studyid records with missing STUDYID;
%end;

%if &missing_usubjid > 0 %then %do;
    %put ERROR: Found &missing_usubjid records with missing USUBJID;
%end;

/* Check for duplicates */
proc sort data=sdtm.ds out=_dup_check nodupkey dupout=_dups;
    by usubjid dsseq;
run;

%let dup_count = %sysfunc(nobs(_dups));
%if &dup_count > 0 %then %do;
    %put ERROR: Found &dup_count duplicate records by USUBJID + DSSEQ;
%end;


/*------------------------------------------------------------------------------
* Step 6: Generate documentation
------------------------------------------------------------------------------*/
proc contents data=sdtm.ds out=work.ds_contents noprint;
run;

proc print data=sdtm.ds(obs=10) label;
    title "Sample of SDTM DS Domain";
run;

%log_step(step=DS Domain - Complete, status=SUCCESS);
