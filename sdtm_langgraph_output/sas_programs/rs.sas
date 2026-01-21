/*******************************************************************************
* Program:    rs.sas
* Purpose:    Create SDTM RS domain from source data
* Study:      MAXIS-08
* Source:     RESP.csv
* Created:    2026-01-21
* Author:     SDTM Pipeline (Auto-generated)
*
* Modification History:
* Date        Author      Description
* ----------  ----------  ---------------------------------------------------
* 2026-01-21  Pipeline    Initial creation
********************************************************************************/

%include "&programs/setup.sas";

%log_step(step=RS Domain - Start, status=RUNNING);

/*------------------------------------------------------------------------------
* Step 1: Read source data
------------------------------------------------------------------------------*/
data rs_raw;
    set raw.resp;
run;

%put NOTE: Source records read: %sysfunc(nobs(rs_raw));

/*------------------------------------------------------------------------------
* Step 2: Apply mappings and transformations
------------------------------------------------------------------------------*/
data rs_temp;
    length
        STUDYID $20
        DOMAIN $2
        USUBJID $40
        STUDYID $20
        SUBJID $20
        SITEID $10
        DOMAIN $2
        USUBJID $40
    ;

    set rs_raw;

    /* Standard variables */
    STUDYID = "&study";
    DOMAIN = "RS";

    /* Generate USUBJID */
    USUBJID = %gen_usubjid(study=STUDY, site=scan(INVSITE, -1, "_"), subj=PT);

    /* STUDYID from STUDY */
    STUDYID = STUDY;

    /* SUBJID from PT */
    SUBJID = PT;

    /* RSVISIT from VISIT */
    RSVISIT = VISIT;

    /* SITEID from INVSITE */
    SITEID = INVSITE;

    /* DOMAIN: Constant value */
    DOMAIN = 'RS';

    /* USUBJID: Derived unique subject identifier */
    USUBJID = STUDYID || '-' || SITEID || '-' || SUBJID;

    /* RSSEQ: Derived sequence number */
    /* Derivation: Row number within USUBJID */

run;

/*------------------------------------------------------------------------------
* Step 3: Generate sequence numbers
------------------------------------------------------------------------------*/
%gen_seq(domain=rs, sortvar=USUBJID);

/*------------------------------------------------------------------------------
* Step 4: Final dataset with variable ordering
------------------------------------------------------------------------------*/
data sdtm.rs (label="SDTM RS Domain");
    retain STUDYID DOMAIN USUBJID;
    set rs_temp;

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
    from sdtm.rs
    where missing(STUDYID);

    select count(*) into :missing_usubjid
    from sdtm.rs
    where missing(USUBJID);
quit;

%if &missing_studyid > 0 %then %do;
    %put ERROR: Found &missing_studyid records with missing STUDYID;
%end;

%if &missing_usubjid > 0 %then %do;
    %put ERROR: Found &missing_usubjid records with missing USUBJID;
%end;

/* Check for duplicates */
proc sort data=sdtm.rs out=_dup_check nodupkey dupout=_dups;
    by usubjid rsseq;
run;

%let dup_count = %sysfunc(nobs(_dups));
%if &dup_count > 0 %then %do;
    %put ERROR: Found &dup_count duplicate records by USUBJID + RSSEQ;
%end;


/*------------------------------------------------------------------------------
* Step 6: Generate documentation
------------------------------------------------------------------------------*/
proc contents data=sdtm.rs out=work.rs_contents noprint;
run;

proc print data=sdtm.rs(obs=10) label;
    title "Sample of SDTM RS Domain";
run;

%log_step(step=RS Domain - Complete, status=SUCCESS);
