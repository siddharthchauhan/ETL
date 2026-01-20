/*******************************************************************************
* Program:    cm.sas
* Purpose:    Create SDTM CM domain from source data
* Study:      MAXIS-08
* Source:     RADMEDS.csv
* Created:    2026-01-20
* Author:     SDTM Pipeline (Auto-generated)
*
* Modification History:
* Date        Author      Description
* ----------  ----------  ---------------------------------------------------
* 2026-01-20  Pipeline    Initial creation
********************************************************************************/

%include "&programs/setup.sas";

%log_step(step=CM Domain - Start, status=RUNNING);

/*------------------------------------------------------------------------------
* Step 1: Read source data
------------------------------------------------------------------------------*/
data cm_raw;
    set raw.radmeds;
run;

%put NOTE: Source records read: %sysfunc(nobs(cm_raw));

/*------------------------------------------------------------------------------
* Step 2: Apply mappings and transformations
------------------------------------------------------------------------------*/
data cm_temp;
    length
        STUDYID $20
        DOMAIN $2
        USUBJID $40
        STUDYID $20
        DOMAIN $2
        USUBJID $40
        CMSEQ 8
        CMTRT $200
        CMDECOD $200
        CMSTDTC $20
        CMENDTC $20
    ;

    set cm_raw;

    /* Standard variables */
    STUDYID = "&study";
    DOMAIN = "CM";

    /* Generate USUBJID */
    USUBJID = %gen_usubjid(study=STUDY, site=scan(INVSITE, -1, "_"), subj=PT);

    /* STUDYID from STUDY */
    STUDYID = STUDY;

    /* DOMAIN: Standard domain code for concomitant medications */
    DOMAIN = Set to 'CM';

    /* USUBJID from PT */
    USUBJID = PT;
    /* TODO: Apply transformation: STUDY + '-' + PT */

    /* CMSEQ from REPEATSN */
    CMSEQ = REPEATSN;

    /* CMTRT from MDANYL */
    CMTRT = MDANYL;

    /* CMDECOD from MDANYL */
    CMDECOD = MDANYL;

    /* CMCAT from DCMNAME */
    CMCAT = DCMNAME;
    /* TODO: Apply transformation: Remove 'MD_' prefix and replace underscores with spaces */

    /* CMOCCUR from MDANYL */
    CMOCCUR = MDANYL;
    /* TODO: Apply transformation: If MDANYL contains 'NO' then 'N', else 'Y' */

    /* CMSTDTC from MDSTDT */
    %convert_to_iso(invar=MDSTDT, outvar=CMSTDTC);

    /* CMENDTC from MDEDDT */
    %convert_to_iso(invar=MDEDDT, outvar=CMENDTC);

    /* CMINDC from MDIND */
    CMINDC = MDIND;

    /* CMDOSU from MDUNIT */
    CMDOSU = MDUNIT;

    /* VISITNUM from VISIT */
    VISITNUM = VISIT;

run;

/*------------------------------------------------------------------------------
* Step 3: Generate sequence numbers
------------------------------------------------------------------------------*/
%gen_seq(domain=cm, sortvar=CMSTDTC);

/*------------------------------------------------------------------------------
* Step 4: Final dataset with variable ordering
------------------------------------------------------------------------------*/
data sdtm.cm (label="SDTM CM Domain");
    retain STUDYID DOMAIN USUBJID CMSEQ CMTRT CMDECOD CMDOSE CMDOSU CMROUTE CMSTDTC CMENDTC;
    set cm_temp;

    /* Apply formats */
    format _numeric_ best12.;
    format _character_ $varying.;

    /* Keep only SDTM variables */
    keep STUDYID DOMAIN USUBJID CMSEQ CMTRT CMDECOD CMDOSE CMDOSU CMROUTE CMSTDTC CMENDTC;
run;

/*------------------------------------------------------------------------------
* Step 5: Validation checks
------------------------------------------------------------------------------*/

/* Check for required variables */
proc sql noprint;
    select count(*) into :missing_studyid
    from sdtm.cm
    where missing(STUDYID);

    select count(*) into :missing_usubjid
    from sdtm.cm
    where missing(USUBJID);
quit;

%if &missing_studyid > 0 %then %do;
    %put ERROR: Found &missing_studyid records with missing STUDYID;
%end;

%if &missing_usubjid > 0 %then %do;
    %put ERROR: Found &missing_usubjid records with missing USUBJID;
%end;

/* Check for duplicates */
proc sort data=sdtm.cm out=_dup_check nodupkey dupout=_dups;
    by usubjid cmseq;
run;

%let dup_count = %sysfunc(nobs(_dups));
%if &dup_count > 0 %then %do;
    %put ERROR: Found &dup_count duplicate records by USUBJID + CMSEQ;
%end;


/*------------------------------------------------------------------------------
* Step 6: Generate documentation
------------------------------------------------------------------------------*/
proc contents data=sdtm.cm out=work.cm_contents noprint;
run;

proc print data=sdtm.cm(obs=10) label;
    title "Sample of SDTM CM Domain";
run;

%log_step(step=CM Domain - Complete, status=SUCCESS);
