/*******************************************************************************
* Program:    ie.sas
* Purpose:    Create SDTM IE domain from source data
* Study:      MAXIS-08
* Source:     ELIG.csv
* Created:    2026-01-20
* Author:     SDTM Pipeline (Auto-generated)
*
* Modification History:
* Date        Author      Description
* ----------  ----------  ---------------------------------------------------
* 2026-01-20  Pipeline    Initial creation
********************************************************************************/

%include "&programs/setup.sas";

%log_step(step=IE Domain - Start, status=RUNNING);

/*------------------------------------------------------------------------------
* Step 1: Read source data
------------------------------------------------------------------------------*/
data ie_raw;
    set raw.elig;
run;

%put NOTE: Source records read: %sysfunc(nobs(ie_raw));

/*------------------------------------------------------------------------------
* Step 2: Apply mappings and transformations
------------------------------------------------------------------------------*/
data ie_temp;
    length
        STUDYID $20
        DOMAIN $2
        USUBJID $40
        STUDYID $20
        DOMAIN $2
        USUBJID $40
    ;

    set ie_raw;

    /* Standard variables */
    STUDYID = "&study";
    DOMAIN = "IE";

    /* Generate USUBJID */
    USUBJID = %gen_usubjid(study=STUDY, site=scan(INVSITE, -1, "_"), subj=PT);

    /* STUDYID from STUDY */
    STUDYID = STUDY;

    /* DOMAIN: Domain constant for Inclusion/Exclusion Events */
    DOMAIN = Set to constant 'IE';

    /* USUBJID from PT */
    USUBJID = PT;
    /* TODO: Apply transformation: STUDY + '-' + PT */

    /* IESEQ from REPEATSN */
    IESEQ = REPEATSN;

    /* IETEST from ELQSN */
    IETEST = ELQSN;
    /* TODO: Apply transformation: Map ELQSN values to full test descriptions */

    /* IETESTCD from ELQSN */
    IETESTCD = ELQSN;

    /* IECAT from DCMNAME */
    IECAT = DCMNAME;

    /* IEORRES from ELQSN */
    IEORRES = ELQSN;

    /* IESTRESC from ELQSN */
    IESTRESC = ELQSN;

run;

/*------------------------------------------------------------------------------
* Step 3: Generate sequence numbers
------------------------------------------------------------------------------*/
%gen_seq(domain=ie, sortvar=USUBJID);

/*------------------------------------------------------------------------------
* Step 4: Final dataset with variable ordering
------------------------------------------------------------------------------*/
data sdtm.ie (label="SDTM IE Domain");
    retain STUDYID DOMAIN USUBJID;
    set ie_temp;

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
    from sdtm.ie
    where missing(STUDYID);

    select count(*) into :missing_usubjid
    from sdtm.ie
    where missing(USUBJID);
quit;

%if &missing_studyid > 0 %then %do;
    %put ERROR: Found &missing_studyid records with missing STUDYID;
%end;

%if &missing_usubjid > 0 %then %do;
    %put ERROR: Found &missing_usubjid records with missing USUBJID;
%end;

/* Check for duplicates */
proc sort data=sdtm.ie out=_dup_check nodupkey dupout=_dups;
    by usubjid ieseq;
run;

%let dup_count = %sysfunc(nobs(_dups));
%if &dup_count > 0 %then %do;
    %put ERROR: Found &dup_count duplicate records by USUBJID + IESEQ;
%end;


/*------------------------------------------------------------------------------
* Step 6: Generate documentation
------------------------------------------------------------------------------*/
proc contents data=sdtm.ie out=work.ie_contents noprint;
run;

proc print data=sdtm.ie(obs=10) label;
    title "Sample of SDTM IE Domain";
run;

%log_step(step=IE Domain - Complete, status=SUCCESS);
