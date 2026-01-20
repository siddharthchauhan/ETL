/*******************************************************************************
* Program:    ae.sas
* Purpose:    Create SDTM AE domain from source data
* Study:      MAXIS-08
* Source:     AEVENT.csv
* Created:    2026-01-20
* Author:     SDTM Pipeline (Auto-generated)
*
* Modification History:
* Date        Author      Description
* ----------  ----------  ---------------------------------------------------
* 2026-01-20  Pipeline    Initial creation
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
        STUDYID $20
        DOMAIN $2
        USUBJID $40
        AESEQ 8
        AETERM $200
        AEDECOD $200
        AESTDTC $20
        AEENDTC $20
        AESEV $10
    ;

    set ae_raw;

    /* Standard variables */
    STUDYID = "&study";
    DOMAIN = "AE";

    /* Generate USUBJID */
    USUBJID = %gen_usubjid(study=STUDY, site=scan(INVSITE, -1, "_"), subj=PT);

    /* STUDYID from STUDY */
    STUDYID = STUDY;

    /* DOMAIN: Domain abbreviation for Adverse Events */
    DOMAIN = Set to constant 'AE';

    /* USUBJID from INVSITE */
    USUBJID = INVSITE;
    /* TODO: Apply transformation: STUDY + '-' + INVSITE + '-' + subject_id */

    /* AESEQ from AESEQ */
    AESEQ = AESEQ;

    /* AETERM from AECOD */
    AETERM = AECOD;

    /* AEDECOD from AECOD */
    AEDECOD = AECOD;

    /* AEBODSYS from AEHTT */
    AEBODSYS = AEHTT;

    /* AESTDTC from AESTDT */
    %convert_to_iso(invar=AESTDT, outvar=AESTDTC);

    /* AEENDTC from AEENDT */
    %convert_to_iso(invar=AEENDT, outvar=AEENDTC);

    /* AESER from AESER */
    AESER = AESER;

    /* AESEV from AESEV */
    AESEV = AESEV;

    /* AEREL from AEREL */
    AEREL = AEREL;

    /* AEACN from AEACT */
    AEACN = AEACT;

    /* AEOUT from AEOUTC */
    AEOUT = AEOUTC;

    /* AESCONG: Congenital anomaly or birth defect - not available in source */
    /* Derivation: Derive from available serious event criteria if present */

    /* AESDISAB: Persistent or significant disability/incapacity - not available in source */
    /* Derivation: Derive from available serious event criteria if present */

    /* AESDTH: Results in death - not available in source */
    /* Derivation: Derive from available serious event criteria if present */

    /* AESHOSP: Requires or prolongs hospitalization - not available in source */
    /* Derivation: Derive from available serious event criteria if present */

    /* AESLIFE: Life threatening - not available in source */
    /* Derivation: Derive from available serious event criteria if present */

    /* AESMIE: Other medically important serious event - not available in source */
    /* Derivation: Derive from available serious event criteria if present */

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
