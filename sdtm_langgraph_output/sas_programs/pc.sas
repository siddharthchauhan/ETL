/*******************************************************************************
* Program:    pc.sas
* Purpose:    Create SDTM PC domain from source data
* Study:      MAXIS-08
* Source:     PKCRF.csv
* Created:    2026-01-21
* Author:     SDTM Pipeline (Auto-generated)
*
* Modification History:
* Date        Author      Description
* ----------  ----------  ---------------------------------------------------
* 2026-01-21  Pipeline    Initial creation
********************************************************************************/

%include "&programs/setup.sas";

%log_step(step=PC Domain - Start, status=RUNNING);

/*------------------------------------------------------------------------------
* Step 1: Read source data
------------------------------------------------------------------------------*/
data pc_raw;
    set raw.pkcrf;
run;

%put NOTE: Source records read: %sysfunc(nobs(pc_raw));

/*------------------------------------------------------------------------------
* Step 2: Apply mappings and transformations
------------------------------------------------------------------------------*/
data pc_temp;
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

    set pc_raw;

    /* Standard variables */
    STUDYID = "&study";
    DOMAIN = "PC";

    /* Generate USUBJID */
    USUBJID = %gen_usubjid(study=STUDY, site=scan(INVSITE, -1, "_"), subj=PT);

    /* STUDYID from STUDY */
    STUDYID = STUDY;

    /* SUBJID from PT */
    SUBJID = PT;

    /* PCVISIT from VISIT */
    PCVISIT = VISIT;

    /* SITEID from INVSITE */
    SITEID = INVSITE;

    /* DOMAIN: Constant value */
    DOMAIN = 'PC';

    /* USUBJID: Derived unique subject identifier */
    USUBJID = STUDYID || '-' || SITEID || '-' || SUBJID;

    /* PCSEQ: Derived sequence number */
    /* Derivation: Row number within USUBJID */

run;

/*------------------------------------------------------------------------------
* Step 3: Generate sequence numbers
------------------------------------------------------------------------------*/
%gen_seq(domain=pc, sortvar=USUBJID);

/*------------------------------------------------------------------------------
* Step 4: Final dataset with variable ordering
------------------------------------------------------------------------------*/
data sdtm.pc (label="SDTM PC Domain");
    retain STUDYID DOMAIN USUBJID;
    set pc_temp;

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
    from sdtm.pc
    where missing(STUDYID);

    select count(*) into :missing_usubjid
    from sdtm.pc
    where missing(USUBJID);
quit;

%if &missing_studyid > 0 %then %do;
    %put ERROR: Found &missing_studyid records with missing STUDYID;
%end;

%if &missing_usubjid > 0 %then %do;
    %put ERROR: Found &missing_usubjid records with missing USUBJID;
%end;

/* Check for duplicates */
proc sort data=sdtm.pc out=_dup_check nodupkey dupout=_dups;
    by usubjid pcseq;
run;

%let dup_count = %sysfunc(nobs(_dups));
%if &dup_count > 0 %then %do;
    %put ERROR: Found &dup_count duplicate records by USUBJID + PCSEQ;
%end;


/*------------------------------------------------------------------------------
* Step 6: Generate documentation
------------------------------------------------------------------------------*/
proc contents data=sdtm.pc out=work.pc_contents noprint;
run;

proc print data=sdtm.pc(obs=10) label;
    title "Sample of SDTM PC Domain";
run;

%log_step(step=PC Domain - Complete, status=SUCCESS);
