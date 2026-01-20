/*******************************************************************************
* Program:    lb.sas
* Purpose:    Create SDTM LB domain from source data
* Study:      MAXIS-08
* Source:     GENOLAB.csv
* Created:    2026-01-20
* Author:     SDTM Pipeline (Auto-generated)
*
* Modification History:
* Date        Author      Description
* ----------  ----------  ---------------------------------------------------
* 2026-01-20  Pipeline    Initial creation
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
        DOMAIN $2
        USUBJID $40
        LBSEQ 8
        LBTESTCD $8
        LBTEST $40
        LBORRES $20
    ;

    set lb_raw;

    /* Standard variables */
    STUDYID = "&study";
    DOMAIN = "LB";

    /* Generate USUBJID */
    USUBJID = %gen_usubjid(study=STUDY, site=scan(INVSITE, -1, "_"), subj=PT);

    /* STUDYID from STUDY */
    STUDYID = STUDY;

    /* DOMAIN: Domain abbreviation for Laboratory Test Results */
    DOMAIN = Set to 'LB' for all records;

    /* USUBJID from ['STUDY', 'PT'] */
    USUBJID = ['STUDY', 'PT'];
    /* TODO: Apply transformation: Concatenate STUDY + '-' + PT */

    /* LBSEQ from REPEATSN */
    LBSEQ = REPEATSN;

    /* LBTESTCD from LPARM */
    LBTESTCD = LPARM;

    /* LBTEST from LPARM */
    LBTEST = LPARM;
    /* TODO: Apply transformation: Expand to full test name */

    /* LBCAT from DCMNAME */
    LBCAT = DCMNAME;
    /* TODO: Apply transformation: Map 'LABS_GENOTYPING' to 'GENOTYPING' */

    /* LBORRES from LVALC */
    LBORRES = LVALC;

    /* LBSTRESC from LVALC */
    LBSTRESC = LVALC;

    /* LBBLFL from CPEVENT */
    LBBLFL = CPEVENT;
    /* TODO: Apply transformation: If CPEVENT = 'BASELINE' then 'Y' else null */

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
