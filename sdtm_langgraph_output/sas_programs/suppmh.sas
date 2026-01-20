/*******************************************************************************
* Program:    suppmh.sas
* Purpose:    Create SDTM SUPPMH domain from source data
* Study:      MAXIS-08
* Source:     SURGHXC.csv
* Created:    2026-01-20
* Author:     SDTM Pipeline (Auto-generated)
*
* Modification History:
* Date        Author      Description
* ----------  ----------  ---------------------------------------------------
* 2026-01-20  Pipeline    Initial creation
********************************************************************************/

%include "&programs/setup.sas";

%log_step(step=SUPPMH Domain - Start, status=RUNNING);

/*------------------------------------------------------------------------------
* Step 1: Read source data
------------------------------------------------------------------------------*/
data suppmh_raw;
    set raw.surghxc;
run;

%put NOTE: Source records read: %sysfunc(nobs(suppmh_raw));

/*------------------------------------------------------------------------------
* Step 2: Apply mappings and transformations
------------------------------------------------------------------------------*/
data suppmh_temp;
    length
        STUDYID $20
        DOMAIN $2
        USUBJID $40
        STUDYID $20
        USUBJID $40
    ;

    set suppmh_raw;

    /* Standard variables */
    STUDYID = "&study";
    DOMAIN = "SUPPMH";

    /* Generate USUBJID */
    USUBJID = %gen_usubjid(study=STUDY, site=scan(INVSITE, -1, "_"), subj=PT);

    /* STUDYID from STUDY */
    STUDYID = STUDY;

    /* RDOMAIN from STUDY */
    RDOMAIN = STUDY;
    /* TODO: Apply transformation: Set to 'MH' */

    /* USUBJID from PT */
    USUBJID = PT;
    /* TODO: Apply transformation: STUDY + '-' + INVSITE + '-' + PT */

    /* IDVAR from REPEATSN */
    IDVAR = REPEATSN;
    /* TODO: Apply transformation: Set to 'MHSEQ' */

    /* IDVARVAL from REPEATSN */
    IDVARVAL = REPEATSN;
    /* TODO: Apply transformation: Convert to character */

    /* QNAM from HLGTTERM */
    QNAM = HLGTTERM;
    /* TODO: Apply transformation: Set to 'HLGTTERM' */

    /* QVAL from HLGTTERM */
    QVAL = HLGTTERM;

    /* QNAM from HLGTCODE */
    QNAM = HLGTCODE;
    /* TODO: Apply transformation: Set to 'HLGTCODE' */

    /* QVAL from HLGTCODE */
    QVAL = HLGTCODE;
    /* TODO: Apply transformation: Convert to character */

    /* QNAM from HLTTERM */
    QNAM = HLTTERM;
    /* TODO: Apply transformation: Set to 'HLTTERM' */

    /* QVAL from HLTTERM */
    QVAL = HLTTERM;

    /* QNAM from HLTCODE */
    QNAM = HLTCODE;
    /* TODO: Apply transformation: Set to 'HLTCODE' */

    /* QVAL from HLTCODE */
    QVAL = HLTCODE;
    /* TODO: Apply transformation: Convert to character */

    /* QNAM from LLTTERM */
    QNAM = LLTTERM;
    /* TODO: Apply transformation: Set to 'LLTTERM' */

    /* QVAL from LLTTERM */
    QVAL = LLTTERM;

    /* QNAM from LLTCODE */
    QNAM = LLTCODE;
    /* TODO: Apply transformation: Set to 'LLTCODE' */

    /* QVAL from LLTCODE */
    QVAL = LLTCODE;
    /* TODO: Apply transformation: Convert to character */

    /* QNAM from SOCTERM */
    QNAM = SOCTERM;
    /* TODO: Apply transformation: Set to 'SOCTERM' */

    /* QVAL from SOCTERM */
    QVAL = SOCTERM;

    /* QNAM from SOCCODE */
    QNAM = SOCCODE;
    /* TODO: Apply transformation: Set to 'SOCCODE' */

    /* QVAL from SOCCODE */
    QVAL = SOCCODE;
    /* TODO: Apply transformation: Convert to character */

run;

/*------------------------------------------------------------------------------
* Step 3: Generate sequence numbers
------------------------------------------------------------------------------*/
%gen_seq(domain=suppmh, sortvar=USUBJID);

/*------------------------------------------------------------------------------
* Step 4: Final dataset with variable ordering
------------------------------------------------------------------------------*/
data sdtm.suppmh (label="SDTM SUPPMH Domain");
    retain STUDYID DOMAIN USUBJID;
    set suppmh_temp;

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
    from sdtm.suppmh
    where missing(STUDYID);

    select count(*) into :missing_usubjid
    from sdtm.suppmh
    where missing(USUBJID);
quit;

%if &missing_studyid > 0 %then %do;
    %put ERROR: Found &missing_studyid records with missing STUDYID;
%end;

%if &missing_usubjid > 0 %then %do;
    %put ERROR: Found &missing_usubjid records with missing USUBJID;
%end;

/* Check for duplicates */
proc sort data=sdtm.suppmh out=_dup_check nodupkey dupout=_dups;
    by usubjid suppmhseq;
run;

%let dup_count = %sysfunc(nobs(_dups));
%if &dup_count > 0 %then %do;
    %put ERROR: Found &dup_count duplicate records by USUBJID + SUPPMHSEQ;
%end;


/*------------------------------------------------------------------------------
* Step 6: Generate documentation
------------------------------------------------------------------------------*/
proc contents data=sdtm.suppmh out=work.suppmh_contents noprint;
run;

proc print data=sdtm.suppmh(obs=10) label;
    title "Sample of SDTM SUPPMH Domain";
run;

%log_step(step=SUPPMH Domain - Complete, status=SUCCESS);
