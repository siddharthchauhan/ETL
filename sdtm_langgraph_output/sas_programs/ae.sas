/*******************************************************************************
* Program:    ae.sas
* Purpose:    Create SDTM AE domain from source data
* Study:      MAXIS-08
* Source:     AEVENT.csv
* Created:    2026-01-21
* Author:     SDTM Pipeline (Auto-generated)
*
* Modification History:
* Date        Author      Description
* ----------  ----------  ---------------------------------------------------
* 2026-01-21  Pipeline    Initial creation
********************************************************************************/

%include "&programs/setup.sas";

%log_step(step=AE Domain - Start, status=RUNNING);

/*------------------------------------------------------------------------------
* Step 1: Read source data
------------------------------------------------------------------------------*/
data ae_raw;
    set raw.aevent;
run;

%put NOTE: Source records read: %sysfunc(nobs(ae_raw));

/*------------------------------------------------------------------------------
* Step 2: Apply mappings and transformations
------------------------------------------------------------------------------*/
data ae_temp;
    length
        STUDYID $20
        DOMAIN $2
        USUBJID $40
        SUBJID $20
        AEENDTC $20
        AESTDTC $20
        STUDYID $20
        AESEV $10
        SITEID $10
        DOMAIN $2
        USUBJID $40
        AESEQ 8
    ;

    set ae_raw;

    /* Standard variables */
    STUDYID = "&study";
    DOMAIN = "AE";

    /* Generate USUBJID */
    USUBJID = %gen_usubjid(study=STUDY, site=scan(INVSITE, -1, "_"), subj=PT);

    /* SUBJID from PT */
    SUBJID = PT;

    /* AEENDTC from AEENDT */
    %convert_to_iso(invar=AEENDT, outvar=AEENDTC);

    /* AESTDTC from AESTDT */
    %convert_to_iso(invar=AESTDT, outvar=AESTDTC);

    /* STUDYID from STUDY */
    STUDYID = STUDY;

    /* AESEV from AESEV */
    AESEV = AESEV;

    /* AEREL from AEREL */
    AEREL = AEREL;

    /* AEVISIT from VISIT */
    AEVISIT = VISIT;

    /* SITEID from INVSITE */
    SITEID = INVSITE;

    /* DOMAIN: Constant value */
    DOMAIN = 'AE';

    /* USUBJID: Derived unique subject identifier */
    USUBJID = STUDYID || '-' || SITEID || '-' || SUBJID;

    /* AESEQ: Derived sequence number */
    /* Derivation: Row number within USUBJID */

run;

/*------------------------------------------------------------------------------
* Step 3: Generate sequence numbers
------------------------------------------------------------------------------*/
%gen_seq(domain=ae, sortvar=AESTDTC);

/*------------------------------------------------------------------------------
* Step 4: Final dataset with variable ordering
------------------------------------------------------------------------------*/
data sdtm.ae (label="SDTM AE Domain");
    retain STUDYID DOMAIN USUBJID AESEQ AETERM AEDECOD AESTDTC AEENDTC AESEV AESER AEREL;
    set ae_temp;

    /* Apply formats */
    format _numeric_ best12.;
    format _character_ $varying.;

    /* Keep only SDTM variables */
    keep STUDYID DOMAIN USUBJID AESEQ AETERM AEDECOD AESTDTC AEENDTC AESEV AESER AEREL;
run;

/*------------------------------------------------------------------------------
* Step 5: Validation checks
------------------------------------------------------------------------------*/

/* Check for required variables */
proc sql noprint;
    select count(*) into :missing_studyid
    from sdtm.ae
    where missing(STUDYID);

    select count(*) into :missing_usubjid
    from sdtm.ae
    where missing(USUBJID);
quit;

%if &missing_studyid > 0 %then %do;
    %put ERROR: Found &missing_studyid records with missing STUDYID;
%end;

%if &missing_usubjid > 0 %then %do;
    %put ERROR: Found &missing_usubjid records with missing USUBJID;
%end;

/* Check for duplicates */
proc sort data=sdtm.ae out=_dup_check nodupkey dupout=_dups;
    by usubjid aeseq;
run;

%let dup_count = %sysfunc(nobs(_dups));
%if &dup_count > 0 %then %do;
    %put ERROR: Found &dup_count duplicate records by USUBJID + AESEQ;
%end;


/*------------------------------------------------------------------------------
* Step 6: Generate documentation
------------------------------------------------------------------------------*/
proc contents data=sdtm.ae out=work.ae_contents noprint;
run;

proc print data=sdtm.ae(obs=10) label;
    title "Sample of SDTM AE Domain";
run;

%log_step(step=AE Domain - Complete, status=SUCCESS);
