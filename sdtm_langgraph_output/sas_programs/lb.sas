/*******************************************************************************
* Program:    lb.sas
* Purpose:    Create SDTM LB domain from source data
* Study:      MAXIS-08
* Source:     GENOLAB.csv
* Created:    2026-01-21
* Author:     SDTM Pipeline (Auto-generated)
*
* Modification History:
* Date        Author      Description
* ----------  ----------  ---------------------------------------------------
* 2026-01-21  Pipeline    Initial creation
********************************************************************************/

%include "&programs/setup.sas";

%log_step(step=LB Domain - Start, status=RUNNING);

/*------------------------------------------------------------------------------
* Step 1: Read source data
------------------------------------------------------------------------------*/
data lb_raw;
    set raw.genolab;
run;

%put NOTE: Source records read: %sysfunc(nobs(lb_raw));

/*------------------------------------------------------------------------------
* Step 2: Apply mappings and transformations
------------------------------------------------------------------------------*/
data lb_temp;
    length
        STUDYID $20
        DOMAIN $2
        USUBJID $40
        STUDYID $20
        SUBJID $20
        SITEID $10
        DOMAIN $2
        USUBJID $40
        LBSEQ 8
    ;

    set lb_raw;

    /* Standard variables */
    STUDYID = "&study";
    DOMAIN = "LB";

    /* Generate USUBJID */
    USUBJID = %gen_usubjid(study=STUDY, site=scan(INVSITE, -1, "_"), subj=PT);

    /* STUDYID from STUDY */
    STUDYID = STUDY;

    /* SUBJID from PT */
    SUBJID = PT;

    /* LBVISIT from VISIT */
    LBVISIT = VISIT;

    /* SITEID from INVSITE */
    SITEID = INVSITE;

    /* DOMAIN: Constant value */
    DOMAIN = 'LB';

    /* USUBJID: Derived unique subject identifier */
    USUBJID = STUDYID || '-' || SITEID || '-' || SUBJID;

    /* LBSEQ: Derived sequence number */
    /* Derivation: Row number within USUBJID */

run;

/*------------------------------------------------------------------------------
* Step 3: Generate sequence numbers
------------------------------------------------------------------------------*/
%gen_seq(domain=lb, sortvar=LBDTC LBTESTCD);

/*------------------------------------------------------------------------------
* Step 4: Final dataset with variable ordering
------------------------------------------------------------------------------*/
data sdtm.lb (label="SDTM LB Domain");
    retain STUDYID DOMAIN USUBJID LBSEQ LBTESTCD LBTEST LBORRES LBORRESU LBSTRESC LBSTRESN LBSTRESU LBDTC;
    set lb_temp;

    /* Apply formats */
    format _numeric_ best12.;
    format _character_ $varying.;

    /* Keep only SDTM variables */
    keep STUDYID DOMAIN USUBJID LBSEQ LBTESTCD LBTEST LBORRES LBORRESU LBSTRESC LBSTRESN LBSTRESU LBDTC;
run;

/*------------------------------------------------------------------------------
* Step 5: Validation checks
------------------------------------------------------------------------------*/

/* Check for required variables */
proc sql noprint;
    select count(*) into :missing_studyid
    from sdtm.lb
    where missing(STUDYID);

    select count(*) into :missing_usubjid
    from sdtm.lb
    where missing(USUBJID);
quit;

%if &missing_studyid > 0 %then %do;
    %put ERROR: Found &missing_studyid records with missing STUDYID;
%end;

%if &missing_usubjid > 0 %then %do;
    %put ERROR: Found &missing_usubjid records with missing USUBJID;
%end;

/* Check for duplicates */
proc sort data=sdtm.lb out=_dup_check nodupkey dupout=_dups;
    by usubjid lbseq;
run;

%let dup_count = %sysfunc(nobs(_dups));
%if &dup_count > 0 %then %do;
    %put ERROR: Found &dup_count duplicate records by USUBJID + LBSEQ;
%end;


/*------------------------------------------------------------------------------
* Step 6: Generate documentation
------------------------------------------------------------------------------*/
proc contents data=sdtm.lb out=work.lb_contents noprint;
run;

proc print data=sdtm.lb(obs=10) label;
    title "Sample of SDTM LB Domain";
run;

%log_step(step=LB Domain - Complete, status=SUCCESS);
