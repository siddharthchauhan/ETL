/*******************************************************************************
* Program:    co.sas
* Purpose:    Create SDTM CO domain from source data
* Study:      MAXIS-08
* Source:     COMGEN.csv
* Created:    2026-01-21
* Author:     SDTM Pipeline (Auto-generated)
*
* Modification History:
* Date        Author      Description
* ----------  ----------  ---------------------------------------------------
* 2026-01-21  Pipeline    Initial creation
********************************************************************************/

%include "&programs/setup.sas";

%log_step(step=CO Domain - Start, status=RUNNING);

/*------------------------------------------------------------------------------
* Step 1: Read source data
------------------------------------------------------------------------------*/
data co_raw;
    set raw.comgen;
run;

%put NOTE: Source records read: %sysfunc(nobs(co_raw));

/*------------------------------------------------------------------------------
* Step 2: Apply mappings and transformations
------------------------------------------------------------------------------*/
data co_temp;
    length
        STUDYID $20
        DOMAIN $2
        USUBJID $40
        SUBJID $20
        STUDYID $20
        SITEID $10
        DOMAIN $2
        USUBJID $40
    ;

    set co_raw;

    /* Standard variables */
    STUDYID = "&study";
    DOMAIN = "CO";

    /* Generate USUBJID */
    USUBJID = %gen_usubjid(study=STUDY, site=scan(INVSITE, -1, "_"), subj=PT);

    /* SUBJID from PT */
    SUBJID = PT;

    /* STUDYID from STUDY */
    STUDYID = STUDY;

    /* COVISIT from VISIT */
    COVISIT = VISIT;

    /* SITEID from INVSITE */
    SITEID = INVSITE;

    /* DOMAIN: Constant value */
    DOMAIN = 'CO';

    /* USUBJID: Derived unique subject identifier */
    USUBJID = STUDYID || '-' || SITEID || '-' || SUBJID;

    /* COSEQ: Derived sequence number */
    /* Derivation: Row number within USUBJID */

run;

/*------------------------------------------------------------------------------
* Step 3: Generate sequence numbers
------------------------------------------------------------------------------*/
%gen_seq(domain=co, sortvar=USUBJID);

/*------------------------------------------------------------------------------
* Step 4: Final dataset with variable ordering
------------------------------------------------------------------------------*/
data sdtm.co (label="SDTM CO Domain");
    retain STUDYID DOMAIN USUBJID;
    set co_temp;

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
    from sdtm.co
    where missing(STUDYID);

    select count(*) into :missing_usubjid
    from sdtm.co
    where missing(USUBJID);
quit;

%if &missing_studyid > 0 %then %do;
    %put ERROR: Found &missing_studyid records with missing STUDYID;
%end;

%if &missing_usubjid > 0 %then %do;
    %put ERROR: Found &missing_usubjid records with missing USUBJID;
%end;

/* Check for duplicates */
proc sort data=sdtm.co out=_dup_check nodupkey dupout=_dups;
    by usubjid coseq;
run;

%let dup_count = %sysfunc(nobs(_dups));
%if &dup_count > 0 %then %do;
    %put ERROR: Found &dup_count duplicate records by USUBJID + COSEQ;
%end;


/*------------------------------------------------------------------------------
* Step 6: Generate documentation
------------------------------------------------------------------------------*/
proc contents data=sdtm.co out=work.co_contents noprint;
run;

proc print data=sdtm.co(obs=10) label;
    title "Sample of SDTM CO Domain";
run;

%log_step(step=CO Domain - Complete, status=SUCCESS);
