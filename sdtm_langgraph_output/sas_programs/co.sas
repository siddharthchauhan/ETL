/*******************************************************************************
* Program:    co.sas
* Purpose:    Create SDTM CO domain from source data
* Study:      MAXIS-08
* Source:     COMGEN.csv
* Created:    2026-01-20
* Author:     SDTM Pipeline (Auto-generated)
*
* Modification History:
* Date        Author      Description
* ----------  ----------  ---------------------------------------------------
* 2026-01-20  Pipeline    Initial creation
********************************************************************************/

%include "&programs/setup.sas";

%log_step(step=CO Domain - Start, status=RUNNING);

/*------------------------------------------------------------------------------
* Step 1: Read source data
------------------------------------------------------------------------------*/
data co_raw;
    set raw.comgen;
run;

%put NOTE: Source records read: %sysfunc(nobs(co_raw));

/*------------------------------------------------------------------------------
* Step 2: Apply mappings and transformations
------------------------------------------------------------------------------*/
data co_temp;
    length
        STUDYID $20
        DOMAIN $2
        USUBJID $40
        STUDYID $20
        DOMAIN $2
        USUBJID $40
    ;

    set co_raw;

    /* Standard variables */
    STUDYID = "&study";
    DOMAIN = "CO";

    /* Generate USUBJID */
    USUBJID = %gen_usubjid(study=STUDY, site=scan(INVSITE, -1, "_"), subj=PT);

    /* STUDYID from STUDY */
    STUDYID = STUDY;

    /* DOMAIN: Domain constant for Comments */
    DOMAIN = Set to 'CO' for Comments domain;

    /* COSEQ from REPEATSN */
    COSEQ = REPEATSN;

    /* COVAL from GNCOM */
    COVAL = GNCOM;

    /* USUBJID from STUDY + PT */
    USUBJID = STUDY + PT;
    /* TODO: Apply transformation: Concatenate STUDY + '-' + PT */

    /* RDOMAIN from DCMNAME */
    RDOMAIN = DCMNAME;
    /* TODO: Apply transformation: Extract domain from form name */

    /* IDVAR from GNQS1 */
    IDVAR = GNQS1;
    /* TODO: Apply transformation: Map to appropriate ID variable name */

    /* IDVARVAL from GNQS1 */
    IDVARVAL = GNQS1;
    /* TODO: Apply transformation: Convert to character */

    /* CODTC from GNDT */
    %convert_to_iso(invar=GNDT, outvar=CODTC);

run;

/*------------------------------------------------------------------------------
* Step 3: Generate sequence numbers
------------------------------------------------------------------------------*/
%gen_seq(domain=co, sortvar=USUBJID);

/*------------------------------------------------------------------------------
* Step 4: Final dataset with variable ordering
------------------------------------------------------------------------------*/
data sdtm.co (label="SDTM CO Domain");
    retain STUDYID DOMAIN USUBJID;
    set co_temp;

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
    from sdtm.co
    where missing(STUDYID);

    select count(*) into :missing_usubjid
    from sdtm.co
    where missing(USUBJID);
quit;

%if &missing_studyid > 0 %then %do;
    %put ERROR: Found &missing_studyid records with missing STUDYID;
%end;

%if &missing_usubjid > 0 %then %do;
    %put ERROR: Found &missing_usubjid records with missing USUBJID;
%end;

/* Check for duplicates */
proc sort data=sdtm.co out=_dup_check nodupkey dupout=_dups;
    by usubjid coseq;
run;

%let dup_count = %sysfunc(nobs(_dups));
%if &dup_count > 0 %then %do;
    %put ERROR: Found &dup_count duplicate records by USUBJID + COSEQ;
%end;


/*------------------------------------------------------------------------------
* Step 6: Generate documentation
------------------------------------------------------------------------------*/
proc contents data=sdtm.co out=work.co_contents noprint;
run;

proc print data=sdtm.co(obs=10) label;
    title "Sample of SDTM CO Domain";
run;

%log_step(step=CO Domain - Complete, status=SUCCESS);
