/*******************************************************************************
* Program:    suppcm.sas
* Purpose:    Create SDTM SUPPCM domain from source data
* Study:      MAXIS-08
* Source:     CAMED19C.csv
* Created:    2026-01-20
* Author:     SDTM Pipeline (Auto-generated)
*
* Modification History:
* Date        Author      Description
* ----------  ----------  ---------------------------------------------------
* 2026-01-20  Pipeline    Initial creation
********************************************************************************/

%include "&programs/setup.sas";

%log_step(step=SUPPCM Domain - Start, status=RUNNING);

/*------------------------------------------------------------------------------
* Step 1: Read source data
------------------------------------------------------------------------------*/
data suppcm_raw;
    set raw.camed19c;
run;

%put NOTE: Source records read: %sysfunc(nobs(suppcm_raw));

/*------------------------------------------------------------------------------
* Step 2: Apply mappings and transformations
------------------------------------------------------------------------------*/
data suppcm_temp;
    length
        STUDYID $20
        DOMAIN $2
        USUBJID $40
        STUDYID $20
        USUBJID $40
    ;

    set suppcm_raw;

    /* Standard variables */
    STUDYID = "&study";
    DOMAIN = "SUPPCM";

    /* Generate USUBJID */
    USUBJID = %gen_usubjid(study=STUDY, site=scan(INVSITE, -1, "_"), subj=PT);

    /* STUDYID from STUDY */
    STUDYID = STUDY;

    /* RDOMAIN from STUDY */
    RDOMAIN = STUDY;
    /* TODO: Apply transformation: Set to 'CM' */

    /* USUBJID from PT */
    USUBJID = PT;
    /* TODO: Apply transformation: STUDY + '-' + INVSITE + '-' + PT */

    /* IDVAR from REPEATSN */
    IDVAR = REPEATSN;
    /* TODO: Apply transformation: Set to 'CMSEQ' */

    /* IDVARVAL from REPEATSN */
    IDVARVAL = REPEATSN;
    /* TODO: Apply transformation: Convert to character */

    /* QNAM from ATCCODE */
    QNAM = ATCCODE;
    /* TODO: Apply transformation: Set to 'ATCCODE' */

    /* QLABEL from ATCCODE */
    QLABEL = ATCCODE;
    /* TODO: Apply transformation: Set to 'ATC Code' */

    /* QVAL from ATCCODE */
    QVAL = ATCCODE;

    /* QNAM from ATCCLASS */
    QNAM = ATCCLASS;
    /* TODO: Apply transformation: Set to 'ATCCLASS' */

    /* QLABEL from ATCCLASS */
    QLABEL = ATCCLASS;
    /* TODO: Apply transformation: Set to 'ATC Class' */

    /* QVAL from ATCCLASS */
    QVAL = ATCCLASS;

    /* QNAM from MDINDL */
    QNAM = MDINDL;
    /* TODO: Apply transformation: Set to 'MDINDL' */

    /* QLABEL from MDINDL */
    QLABEL = MDINDL;
    /* TODO: Apply transformation: Set to 'Medical Indication' */

    /* QVAL from MDINDL */
    QVAL = MDINDL;

run;

/*------------------------------------------------------------------------------
* Step 3: Generate sequence numbers
------------------------------------------------------------------------------*/
%gen_seq(domain=suppcm, sortvar=USUBJID);

/*------------------------------------------------------------------------------
* Step 4: Final dataset with variable ordering
------------------------------------------------------------------------------*/
data sdtm.suppcm (label="SDTM SUPPCM Domain");
    retain STUDYID DOMAIN USUBJID;
    set suppcm_temp;

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
    from sdtm.suppcm
    where missing(STUDYID);

    select count(*) into :missing_usubjid
    from sdtm.suppcm
    where missing(USUBJID);
quit;

%if &missing_studyid > 0 %then %do;
    %put ERROR: Found &missing_studyid records with missing STUDYID;
%end;

%if &missing_usubjid > 0 %then %do;
    %put ERROR: Found &missing_usubjid records with missing USUBJID;
%end;

/* Check for duplicates */
proc sort data=sdtm.suppcm out=_dup_check nodupkey dupout=_dups;
    by usubjid suppcmseq;
run;

%let dup_count = %sysfunc(nobs(_dups));
%if &dup_count > 0 %then %do;
    %put ERROR: Found &dup_count duplicate records by USUBJID + SUPPCMSEQ;
%end;


/*------------------------------------------------------------------------------
* Step 6: Generate documentation
------------------------------------------------------------------------------*/
proc contents data=sdtm.suppcm out=work.suppcm_contents noprint;
run;

proc print data=sdtm.suppcm(obs=10) label;
    title "Sample of SDTM SUPPCM Domain";
run;

%log_step(step=SUPPCM Domain - Complete, status=SUCCESS);
