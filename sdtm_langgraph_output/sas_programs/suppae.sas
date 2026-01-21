/*******************************************************************************
* Program:    suppae.sas
* Purpose:    Create SDTM SUPPAE domain from source data
* Study:      MAXIS-08
* Source:     AEVENTC.csv
* Created:    2026-01-21
* Author:     SDTM Pipeline (Auto-generated)
*
* Modification History:
* Date        Author      Description
* ----------  ----------  ---------------------------------------------------
* 2026-01-21  Pipeline    Initial creation
********************************************************************************/

%include "&programs/setup.sas";

%log_step(step=SUPPAE Domain - Start, status=RUNNING);

/*------------------------------------------------------------------------------
* Step 1: Read source data
------------------------------------------------------------------------------*/
data suppae_raw;
    set raw.aeventc;
run;

%put NOTE: Source records read: %sysfunc(nobs(suppae_raw));

/*------------------------------------------------------------------------------
* Step 2: Apply mappings and transformations
------------------------------------------------------------------------------*/
data suppae_temp;
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

    set suppae_raw;

    /* Standard variables */
    STUDYID = "&study";
    DOMAIN = "SUPPAE";

    /* Generate USUBJID */
    USUBJID = %gen_usubjid(study=STUDY, site=scan(INVSITE, -1, "_"), subj=PT);

    /* SUBJID from PT */
    SUBJID = PT;

    /* STUDYID from STUDY */
    STUDYID = STUDY;

    /* SUPPAEVISIT from VISIT */
    SUPPAEVISIT = VISIT;

    /* SITEID from INVSITE */
    SITEID = INVSITE;

    /* DOMAIN: Constant value */
    DOMAIN = 'SUPPAE';

    /* USUBJID: Derived unique subject identifier */
    USUBJID = STUDYID || '-' || SITEID || '-' || SUBJID;

    /* SUPPAESEQ: Derived sequence number */
    /* Derivation: Row number within USUBJID */

run;

/*------------------------------------------------------------------------------
* Step 3: Generate sequence numbers
------------------------------------------------------------------------------*/
%gen_seq(domain=suppae, sortvar=USUBJID);

/*------------------------------------------------------------------------------
* Step 4: Final dataset with variable ordering
------------------------------------------------------------------------------*/
data sdtm.suppae (label="SDTM SUPPAE Domain");
    retain STUDYID DOMAIN USUBJID;
    set suppae_temp;

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
    from sdtm.suppae
    where missing(STUDYID);

    select count(*) into :missing_usubjid
    from sdtm.suppae
    where missing(USUBJID);
quit;

%if &missing_studyid > 0 %then %do;
    %put ERROR: Found &missing_studyid records with missing STUDYID;
%end;

%if &missing_usubjid > 0 %then %do;
    %put ERROR: Found &missing_usubjid records with missing USUBJID;
%end;

/* Check for duplicates */
proc sort data=sdtm.suppae out=_dup_check nodupkey dupout=_dups;
    by usubjid suppaeseq;
run;

%let dup_count = %sysfunc(nobs(_dups));
%if &dup_count > 0 %then %do;
    %put ERROR: Found &dup_count duplicate records by USUBJID + SUPPAESEQ;
%end;


/*------------------------------------------------------------------------------
* Step 6: Generate documentation
------------------------------------------------------------------------------*/
proc contents data=sdtm.suppae out=work.suppae_contents noprint;
run;

proc print data=sdtm.suppae(obs=10) label;
    title "Sample of SDTM SUPPAE Domain";
run;

%log_step(step=SUPPAE Domain - Complete, status=SUCCESS);
