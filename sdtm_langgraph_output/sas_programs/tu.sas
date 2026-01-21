/*******************************************************************************
* Program:    tu.sas
* Purpose:    Create SDTM TU domain from source data
* Study:      MAXIS-08
* Source:     NONTUMR.csv
* Created:    2026-01-21
* Author:     SDTM Pipeline (Auto-generated)
*
* Modification History:
* Date        Author      Description
* ----------  ----------  ---------------------------------------------------
* 2026-01-21  Pipeline    Initial creation
********************************************************************************/

%include "&programs/setup.sas";

%log_step(step=TU Domain - Start, status=RUNNING);

/*------------------------------------------------------------------------------
* Step 1: Read source data
------------------------------------------------------------------------------*/
data tu_raw;
    set raw.nontumr;
run;

%put NOTE: Source records read: %sysfunc(nobs(tu_raw));

/*------------------------------------------------------------------------------
* Step 2: Apply mappings and transformations
------------------------------------------------------------------------------*/
data tu_temp;
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

    set tu_raw;

    /* Standard variables */
    STUDYID = "&study";
    DOMAIN = "TU";

    /* Generate USUBJID */
    USUBJID = %gen_usubjid(study=STUDY, site=scan(INVSITE, -1, "_"), subj=PT);

    /* SUBJID from PT */
    SUBJID = PT;

    /* STUDYID from STUDY */
    STUDYID = STUDY;

    /* TUVISIT from VISIT */
    TUVISIT = VISIT;

    /* SITEID from INVSITE */
    SITEID = INVSITE;

    /* DOMAIN: Constant value */
    DOMAIN = 'TU';

    /* USUBJID: Derived unique subject identifier */
    USUBJID = STUDYID || '-' || SITEID || '-' || SUBJID;

    /* TUSEQ: Derived sequence number */
    /* Derivation: Row number within USUBJID */

run;

/*------------------------------------------------------------------------------
* Step 3: Generate sequence numbers
------------------------------------------------------------------------------*/
%gen_seq(domain=tu, sortvar=USUBJID);

/*------------------------------------------------------------------------------
* Step 4: Final dataset with variable ordering
------------------------------------------------------------------------------*/
data sdtm.tu (label="SDTM TU Domain");
    retain STUDYID DOMAIN USUBJID;
    set tu_temp;

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
    from sdtm.tu
    where missing(STUDYID);

    select count(*) into :missing_usubjid
    from sdtm.tu
    where missing(USUBJID);
quit;

%if &missing_studyid > 0 %then %do;
    %put ERROR: Found &missing_studyid records with missing STUDYID;
%end;

%if &missing_usubjid > 0 %then %do;
    %put ERROR: Found &missing_usubjid records with missing USUBJID;
%end;

/* Check for duplicates */
proc sort data=sdtm.tu out=_dup_check nodupkey dupout=_dups;
    by usubjid tuseq;
run;

%let dup_count = %sysfunc(nobs(_dups));
%if &dup_count > 0 %then %do;
    %put ERROR: Found &dup_count duplicate records by USUBJID + TUSEQ;
%end;


/*------------------------------------------------------------------------------
* Step 6: Generate documentation
------------------------------------------------------------------------------*/
proc contents data=sdtm.tu out=work.tu_contents noprint;
run;

proc print data=sdtm.tu(obs=10) label;
    title "Sample of SDTM TU Domain";
run;

%log_step(step=TU Domain - Complete, status=SUCCESS);
