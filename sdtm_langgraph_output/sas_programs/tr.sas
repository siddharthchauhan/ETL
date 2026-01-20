/*******************************************************************************
* Program:    tr.sas
* Purpose:    Create SDTM TR domain from source data
* Study:      MAXIS-08
* Source:     TARTUMR.csv
* Created:    2026-01-20
* Author:     SDTM Pipeline (Auto-generated)
*
* Modification History:
* Date        Author      Description
* ----------  ----------  ---------------------------------------------------
* 2026-01-20  Pipeline    Initial creation
********************************************************************************/

%include "&programs/setup.sas";

%log_step(step=TR Domain - Start, status=RUNNING);

/*------------------------------------------------------------------------------
* Step 1: Read source data
------------------------------------------------------------------------------*/
data tr_raw;
    set raw.tartumr;
run;

%put NOTE: Source records read: %sysfunc(nobs(tr_raw));

/*------------------------------------------------------------------------------
* Step 2: Apply mappings and transformations
------------------------------------------------------------------------------*/
data tr_temp;
    length
        STUDYID $20
        DOMAIN $2
        USUBJID $40
        STUDYID $20
        DOMAIN $2
        USUBJID $40
    ;

    set tr_raw;

    /* Standard variables */
    STUDYID = "&study";
    DOMAIN = "TR";

    /* Generate USUBJID */
    USUBJID = %gen_usubjid(study=STUDY, site=scan(INVSITE, -1, "_"), subj=PT);

    /* STUDYID from STUDY */
    STUDYID = STUDY;

    /* DOMAIN: Hard-coded domain value for tumor results */
    DOMAIN = Set to 'TR';

    /* USUBJID from STUDY + INVSITE + PT */
    USUBJID = STUDY + INVSITE + PT;
    /* TODO: Apply transformation: Concatenate STUDY + '-' + INVSITE + '-' + PT */

    /* TRSEQ from REPEATSN */
    TRSEQ = REPEATSN;

    /* TRTESTCD from DCMNAME */
    TRTESTCD = DCMNAME;
    /* TODO: Apply transformation: Map 'TM_ASSESS_TAR' to appropriate test code */

    /* TRTEST from TMDESC */
    TRTEST = TMDESC;

    /* TRORRES from TMSUM */
    TRORRES = TMSUM;

    /* TRSTRESN from TMSIZE2 */
    TRSTRESN = TMSIZE2;

    /* TRLOC from TMLOCL */
    TRLOC = TMLOCL;

    /* TRLNKID from TMNO */
    TRLNKID = TMNO;

    /* TRDTC from TMDT */
    %convert_to_iso(invar=TMDT, outvar=TRDTC);

run;

/*------------------------------------------------------------------------------
* Step 3: Generate sequence numbers
------------------------------------------------------------------------------*/
%gen_seq(domain=tr, sortvar=USUBJID);

/*------------------------------------------------------------------------------
* Step 4: Final dataset with variable ordering
------------------------------------------------------------------------------*/
data sdtm.tr (label="SDTM TR Domain");
    retain STUDYID DOMAIN USUBJID;
    set tr_temp;

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
    from sdtm.tr
    where missing(STUDYID);

    select count(*) into :missing_usubjid
    from sdtm.tr
    where missing(USUBJID);
quit;

%if &missing_studyid > 0 %then %do;
    %put ERROR: Found &missing_studyid records with missing STUDYID;
%end;

%if &missing_usubjid > 0 %then %do;
    %put ERROR: Found &missing_usubjid records with missing USUBJID;
%end;

/* Check for duplicates */
proc sort data=sdtm.tr out=_dup_check nodupkey dupout=_dups;
    by usubjid trseq;
run;

%let dup_count = %sysfunc(nobs(_dups));
%if &dup_count > 0 %then %do;
    %put ERROR: Found &dup_count duplicate records by USUBJID + TRSEQ;
%end;


/*------------------------------------------------------------------------------
* Step 6: Generate documentation
------------------------------------------------------------------------------*/
proc contents data=sdtm.tr out=work.tr_contents noprint;
run;

proc print data=sdtm.tr(obs=10) label;
    title "Sample of SDTM TR Domain";
run;

%log_step(step=TR Domain - Complete, status=SUCCESS);
