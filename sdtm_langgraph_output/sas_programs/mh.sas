/*******************************************************************************
* Program:    mh.sas
* Purpose:    Create SDTM MH domain from source data
* Study:      MAXIS-08
* Source:     SURGHX.csv
* Created:    2026-01-20
* Author:     SDTM Pipeline (Auto-generated)
*
* Modification History:
* Date        Author      Description
* ----------  ----------  ---------------------------------------------------
* 2026-01-20  Pipeline    Initial creation
********************************************************************************/

%include "&programs/setup.sas";

%log_step(step=MH Domain - Start, status=RUNNING);

/*------------------------------------------------------------------------------
* Step 1: Read source data
------------------------------------------------------------------------------*/
data mh_raw;
    set raw.surghx;
run;

%put NOTE: Source records read: %sysfunc(nobs(mh_raw));

/*------------------------------------------------------------------------------
* Step 2: Apply mappings and transformations
------------------------------------------------------------------------------*/
data mh_temp;
    length
        STUDYID $20
        DOMAIN $2
        USUBJID $40
        STUDYID $20
        DOMAIN $2
        USUBJID $40
    ;

    set mh_raw;

    /* Standard variables */
    STUDYID = "&study";
    DOMAIN = "MH";

    /* Generate USUBJID */
    USUBJID = %gen_usubjid(study=STUDY, site=scan(INVSITE, -1, "_"), subj=PT);

    /* STUDYID from STUDY */
    STUDYID = STUDY;

    /* DOMAIN: Domain abbreviation is a constant for MH domain */
    DOMAIN = Set to 'MH' for Medical History domain;

    /* USUBJID from PT */
    USUBJID = PT;
    /* TODO: Apply transformation: Concatenate STUDY + '-' + PT */

    /* MHSEQ from REPEATSN */
    MHSEQ = REPEATSN;

    /* MHTERM from MHFDG */
    MHTERM = MHFDG;

    /* MHDECOD from MHQSN */
    MHDECOD = MHQSN;

    /* MHCAT from DCMNAME */
    MHCAT = DCMNAME;
    /* TODO: Apply transformation: Extract category from 'MH_SURGICAL_HX' */

    /* MHSTDTC from MHDT */
    %convert_to_iso(invar=MHDT, outvar=MHSTDTC);

run;

/*------------------------------------------------------------------------------
* Step 3: Generate sequence numbers
------------------------------------------------------------------------------*/
%gen_seq(domain=mh, sortvar=USUBJID);

/*------------------------------------------------------------------------------
* Step 4: Final dataset with variable ordering
------------------------------------------------------------------------------*/
data sdtm.mh (label="SDTM MH Domain");
    retain STUDYID DOMAIN USUBJID;
    set mh_temp;

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
    from sdtm.mh
    where missing(STUDYID);

    select count(*) into :missing_usubjid
    from sdtm.mh
    where missing(USUBJID);
quit;

%if &missing_studyid > 0 %then %do;
    %put ERROR: Found &missing_studyid records with missing STUDYID;
%end;

%if &missing_usubjid > 0 %then %do;
    %put ERROR: Found &missing_usubjid records with missing USUBJID;
%end;

/* Check for duplicates */
proc sort data=sdtm.mh out=_dup_check nodupkey dupout=_dups;
    by usubjid mhseq;
run;

%let dup_count = %sysfunc(nobs(_dups));
%if &dup_count > 0 %then %do;
    %put ERROR: Found &dup_count duplicate records by USUBJID + MHSEQ;
%end;


/*------------------------------------------------------------------------------
* Step 6: Generate documentation
------------------------------------------------------------------------------*/
proc contents data=sdtm.mh out=work.mh_contents noprint;
run;

proc print data=sdtm.mh(obs=10) label;
    title "Sample of SDTM MH Domain";
run;

%log_step(step=MH Domain - Complete, status=SUCCESS);
