/*******************************************************************************
* Program:    dm.sas
* Purpose:    Create SDTM DM domain from source data
* Study:      MAXIS-08
* Source:     DEMO.csv
* Created:    2026-01-20
* Author:     SDTM Pipeline (Auto-generated)
*
* Modification History:
* Date        Author      Description
* ----------  ----------  ---------------------------------------------------
* 2026-01-20  Pipeline    Initial creation
********************************************************************************/

%include "&programs/setup.sas";

%log_step(step=DM Domain - Start, status=RUNNING);

/*------------------------------------------------------------------------------
* Step 1: Read source data
------------------------------------------------------------------------------*/
data dm_raw;
    set raw.demo;
run;

%put NOTE: Source records read: %sysfunc(nobs(dm_raw));

/*------------------------------------------------------------------------------
* Step 2: Apply mappings and transformations
------------------------------------------------------------------------------*/
data dm_temp;
    length
        STUDYID $20
        DOMAIN $2
        USUBJID $40
        STUDYID $20
        DOMAIN $2
        USUBJID $40
        SUBJID $20
        SITEID $10
        BRTHDTC $20
        SEX $2
        RACE $50
        AGE 8
    ;

    set dm_raw;

    /* Standard variables */
    STUDYID = "&study";
    DOMAIN = "DM";

    /* Generate USUBJID */
    USUBJID = %gen_usubjid(study=STUDY, site=scan(INVSITE, -1, "_"), subj=PT);

    /* STUDYID from STUDY */
    STUDYID = STUDY;

    /* DOMAIN: Domain abbreviation for Demographics */
    DOMAIN = Constant value 'DM';

    /* USUBJID from PT */
    USUBJID = PT;
    /* TODO: Apply transformation: STUDY + '-' + INVSITE + '-' + PT */

    /* SUBJID from PT */
    SUBJID = PT;

    /* SITEID from INVSITE */
    SITEID = INVSITE;

    /* BRTHDTC from DOB */
    BRTHDTC = DOB;
    /* TODO: Apply transformation: Convert YYYYMMDD integer to YYYY-MM-DD format */

    /* SEX from GENDER */
    SEX = GENDER;

    /* RACE from RCE */
    RACE = upcase(strip(RCE));
    /* Apply controlled terminology mapping */

    /* AGE: Age derived from birth date - requires reference date */
    /* Derivation: Calculate age in years from birth date to study reference date */

    /* AGEU: Age unit set to years */
    AGEU = Constant value 'YEARS';

run;

/*------------------------------------------------------------------------------
* Step 3: Generate sequence numbers
------------------------------------------------------------------------------*/
%gen_seq(domain=dm, sortvar=BRTHDTC);

/*------------------------------------------------------------------------------
* Step 4: Final dataset with variable ordering
------------------------------------------------------------------------------*/
data sdtm.dm (label="SDTM DM Domain");
    retain STUDYID DOMAIN USUBJID SUBJID SITEID BRTHDTC AGE AGEU SEX RACE ETHNIC;
    set dm_temp;

    /* Apply formats */
    format _numeric_ best12.;
    format _character_ $varying.;

    /* Keep only SDTM variables */
    keep STUDYID DOMAIN USUBJID SUBJID SITEID BRTHDTC AGE AGEU SEX RACE ETHNIC;
run;

/*------------------------------------------------------------------------------
* Step 5: Validation checks
------------------------------------------------------------------------------*/

/* Check for required variables */
proc sql noprint;
    select count(*) into :missing_studyid
    from sdtm.dm
    where missing(STUDYID);

    select count(*) into :missing_usubjid
    from sdtm.dm
    where missing(USUBJID);
quit;

%if &missing_studyid > 0 %then %do;
    %put ERROR: Found &missing_studyid records with missing STUDYID;
%end;

%if &missing_usubjid > 0 %then %do;
    %put ERROR: Found &missing_usubjid records with missing USUBJID;
%end;

/* Check for duplicates */
proc sort data=sdtm.dm out=_dup_check nodupkey dupout=_dups;
    by usubjid dmseq;
run;

%let dup_count = %sysfunc(nobs(_dups));
%if &dup_count > 0 %then %do;
    %put ERROR: Found &dup_count duplicate records by USUBJID + DMSEQ;
%end;


/*------------------------------------------------------------------------------
* Step 6: Generate documentation
------------------------------------------------------------------------------*/
proc contents data=sdtm.dm out=work.dm_contents noprint;
run;

proc print data=sdtm.dm(obs=10) label;
    title "Sample of SDTM DM Domain";
run;

%log_step(step=DM Domain - Complete, status=SUCCESS);
