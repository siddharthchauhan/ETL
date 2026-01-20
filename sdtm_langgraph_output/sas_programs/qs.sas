/*******************************************************************************
* Program:    qs.sas
* Purpose:    Create SDTM QS domain from source data
* Study:      MAXIS-08
* Source:     QS.csv
* Created:    2026-01-20
* Author:     SDTM Pipeline (Auto-generated)
*
* Modification History:
* Date        Author      Description
* ----------  ----------  ---------------------------------------------------
* 2026-01-20  Pipeline    Initial creation
********************************************************************************/

%include "&programs/setup.sas";

%log_step(step=QS Domain - Start, status=RUNNING);

/*------------------------------------------------------------------------------
* Step 1: Read source data
------------------------------------------------------------------------------*/
data qs_raw;
    set raw.qs;
run;

%put NOTE: Source records read: %sysfunc(nobs(qs_raw));

/*------------------------------------------------------------------------------
* Step 2: Apply mappings and transformations
------------------------------------------------------------------------------*/
data qs_temp;
    length
        STUDYID $20
        DOMAIN $2
        USUBJID $40
        STUDYID $20
        DOMAIN $2
        USUBJID $40
    ;

    set qs_raw;

    /* Standard variables */
    STUDYID = "&study";
    DOMAIN = "QS";

    /* Generate USUBJID */
    USUBJID = %gen_usubjid(study=STUDY, site=scan(INVSITE, -1, "_"), subj=PT);

    /* STUDYID from STUDY */
    STUDYID = STUDY;

    /* DOMAIN: Domain abbreviation for Questionnaires domain */
    DOMAIN = Constant value 'QS';

    /* USUBJID from STUDY, INVSITE, PT */
    USUBJID = STUDY, INVSITE, PT;
    /* TODO: Apply transformation: Concatenate with hyphens */

    /* QSSEQ: Sequence number for questionnaire records per subject */
    /* Derivation: Row number per USUBJID */

    /* QSCAT from DCMNAME */
    QSCAT = DCMNAME;
    /* TODO: Apply transformation: Remove 'QS_' prefix */

    /* VISITNUM from VISIT */
    VISITNUM = VISIT;

    /* QSDTC from VISDT */
    %convert_to_iso(invar=VISDT, outvar=QSDTC);

    /* QSSEQ from SUBEVE */
    QSSEQ = SUBEVE;
    /* TODO: Apply transformation: Use as part of sequence logic */

run;

/*------------------------------------------------------------------------------
* Step 3: Generate sequence numbers
------------------------------------------------------------------------------*/
%gen_seq(domain=qs, sortvar=USUBJID);

/*------------------------------------------------------------------------------
* Step 4: Final dataset with variable ordering
------------------------------------------------------------------------------*/
data sdtm.qs (label="SDTM QS Domain");
    retain STUDYID DOMAIN USUBJID;
    set qs_temp;

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
    from sdtm.qs
    where missing(STUDYID);

    select count(*) into :missing_usubjid
    from sdtm.qs
    where missing(USUBJID);
quit;

%if &missing_studyid > 0 %then %do;
    %put ERROR: Found &missing_studyid records with missing STUDYID;
%end;

%if &missing_usubjid > 0 %then %do;
    %put ERROR: Found &missing_usubjid records with missing USUBJID;
%end;

/* Check for duplicates */
proc sort data=sdtm.qs out=_dup_check nodupkey dupout=_dups;
    by usubjid qsseq;
run;

%let dup_count = %sysfunc(nobs(_dups));
%if &dup_count > 0 %then %do;
    %put ERROR: Found &dup_count duplicate records by USUBJID + QSSEQ;
%end;


/*------------------------------------------------------------------------------
* Step 6: Generate documentation
------------------------------------------------------------------------------*/
proc contents data=sdtm.qs out=work.qs_contents noprint;
run;

proc print data=sdtm.qs(obs=10) label;
    title "Sample of SDTM QS Domain";
run;

%log_step(step=QS Domain - Complete, status=SUCCESS);
