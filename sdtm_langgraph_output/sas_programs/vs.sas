/*******************************************************************************
* Program:    vs.sas
* Purpose:    Create SDTM VS domain from source data
* Study:      MAXIS-08
* Source:     VITALS.csv
* Created:    2026-01-21
* Author:     SDTM Pipeline (Auto-generated)
*
* Modification History:
* Date        Author      Description
* ----------  ----------  ---------------------------------------------------
* 2026-01-21  Pipeline    Initial creation
********************************************************************************/

%include "&programs/setup.sas";

%log_step(step=VS Domain - Start, status=RUNNING);

/*------------------------------------------------------------------------------
* Step 1: Read source data
------------------------------------------------------------------------------*/
data vs_raw;
    set raw.vitals;
run;

%put NOTE: Source records read: %sysfunc(nobs(vs_raw));

/*------------------------------------------------------------------------------
* Step 2: Apply mappings and transformations
------------------------------------------------------------------------------*/
data vs_temp;
    length
        STUDYID $20
        DOMAIN $2
        USUBJID $40
        SUBJID $20
        STUDYID $20
        SITEID $10
        DOMAIN $2
        USUBJID $40
        VSSEQ 8
    ;

    set vs_raw;

    /* Standard variables */
    STUDYID = "&study";
    DOMAIN = "VS";

    /* Generate USUBJID */
    USUBJID = %gen_usubjid(study=STUDY, site=scan(INVSITE, -1, "_"), subj=PT);

    /* SUBJID from PT */
    SUBJID = PT;

    /* STUDYID from STUDY */
    STUDYID = STUDY;

    /* VSVISIT from VISIT */
    VSVISIT = VISIT;

    /* SITEID from INVSITE */
    SITEID = INVSITE;

    /* DOMAIN: Constant value */
    DOMAIN = 'VS';

    /* USUBJID: Derived unique subject identifier */
    USUBJID = STUDYID || '-' || SITEID || '-' || SUBJID;

    /* VSSEQ: Derived sequence number */
    /* Derivation: Row number within USUBJID */

run;

/*------------------------------------------------------------------------------
* Step 3: Generate sequence numbers
------------------------------------------------------------------------------*/
%gen_seq(domain=vs, sortvar=VSDTC VSTESTCD);

/*------------------------------------------------------------------------------
* Step 4: Final dataset with variable ordering
------------------------------------------------------------------------------*/
data sdtm.vs (label="SDTM VS Domain");
    retain STUDYID DOMAIN USUBJID VSSEQ VSTESTCD VSTEST VSORRES VSORRESU VSSTRESC VSSTRESN VSSTRESU VSDTC;
    set vs_temp;

    /* Apply formats */
    format _numeric_ best12.;
    format _character_ $varying.;

    /* Keep only SDTM variables */
    keep STUDYID DOMAIN USUBJID VSSEQ VSTESTCD VSTEST VSORRES VSORRESU VSSTRESC VSSTRESN VSSTRESU VSDTC;
run;

/*------------------------------------------------------------------------------
* Step 5: Validation checks
------------------------------------------------------------------------------*/

/* Check for required variables */
proc sql noprint;
    select count(*) into :missing_studyid
    from sdtm.vs
    where missing(STUDYID);

    select count(*) into :missing_usubjid
    from sdtm.vs
    where missing(USUBJID);
quit;

%if &missing_studyid > 0 %then %do;
    %put ERROR: Found &missing_studyid records with missing STUDYID;
%end;

%if &missing_usubjid > 0 %then %do;
    %put ERROR: Found &missing_usubjid records with missing USUBJID;
%end;

/* Check for duplicates */
proc sort data=sdtm.vs out=_dup_check nodupkey dupout=_dups;
    by usubjid vsseq;
run;

%let dup_count = %sysfunc(nobs(_dups));
%if &dup_count > 0 %then %do;
    %put ERROR: Found &dup_count duplicate records by USUBJID + VSSEQ;
%end;


/*------------------------------------------------------------------------------
* Step 6: Generate documentation
------------------------------------------------------------------------------*/
proc contents data=sdtm.vs out=work.vs_contents noprint;
run;

proc print data=sdtm.vs(obs=10) label;
    title "Sample of SDTM VS Domain";
run;

%log_step(step=VS Domain - Complete, status=SUCCESS);
