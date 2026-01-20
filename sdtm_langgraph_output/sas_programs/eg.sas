/*******************************************************************************
* Program:    eg.sas
* Purpose:    Create SDTM EG domain from source data
* Study:      MAXIS-08
* Source:     ECG.csv
* Created:    2026-01-20
* Author:     SDTM Pipeline (Auto-generated)
*
* Modification History:
* Date        Author      Description
* ----------  ----------  ---------------------------------------------------
* 2026-01-20  Pipeline    Initial creation
********************************************************************************/

%include "&programs/setup.sas";

%log_step(step=EG Domain - Start, status=RUNNING);

/*------------------------------------------------------------------------------
* Step 1: Read source data
------------------------------------------------------------------------------*/
data eg_raw;
    set raw.ecg;
run;

%put NOTE: Source records read: %sysfunc(nobs(eg_raw));

/*------------------------------------------------------------------------------
* Step 2: Apply mappings and transformations
------------------------------------------------------------------------------*/
data eg_temp;
    length
        STUDYID $20
        DOMAIN $2
        USUBJID $40
        STUDYID $20
        DOMAIN $2
        USUBJID $40
    ;

    set eg_raw;

    /* Standard variables */
    STUDYID = "&study";
    DOMAIN = "EG";

    /* Generate USUBJID */
    USUBJID = %gen_usubjid(study=STUDY, site=scan(INVSITE, -1, "_"), subj=PT);

    /* STUDYID from STUDY */
    STUDYID = STUDY;

    /* DOMAIN: Domain constant for EG domain */
    DOMAIN = Set to 'EG' for all records;

    /* USUBJID from STUDY + PT */
    USUBJID = STUDY + PT;
    /* TODO: Apply transformation: concatenate with '-' */

    /* EGSEQ: Sequential numbering of EG records per subject */
    /* Derivation: Row number per USUBJID */

    /* EGTESTCD from DCMNAME */
    EGTESTCD = DCMNAME;
    /* TODO: Apply transformation: standardize to test code */

    /* EGTEST from DCMNAME */
    EGTEST = DCMNAME;
    /* TODO: Apply transformation: expand to full test name */

    /* EGORRES from ECGANY */
    EGORRES = ECGANY;

    /* EGSTRESC from ECGANY */
    EGSTRESC = ECGANY;

    /* EGDTC from ECGDT */
    %convert_to_iso(invar=ECGDT, outvar=EGDTC);

    /* VISIT from CPEVENT */
    VISIT = CPEVENT;

    /* VISITNUM from VISIT */
    VISITNUM = VISIT;

run;

/*------------------------------------------------------------------------------
* Step 3: Generate sequence numbers
------------------------------------------------------------------------------*/
%gen_seq(domain=eg, sortvar=USUBJID);

/*------------------------------------------------------------------------------
* Step 4: Final dataset with variable ordering
------------------------------------------------------------------------------*/
data sdtm.eg (label="SDTM EG Domain");
    retain STUDYID DOMAIN USUBJID;
    set eg_temp;

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
    from sdtm.eg
    where missing(STUDYID);

    select count(*) into :missing_usubjid
    from sdtm.eg
    where missing(USUBJID);
quit;

%if &missing_studyid > 0 %then %do;
    %put ERROR: Found &missing_studyid records with missing STUDYID;
%end;

%if &missing_usubjid > 0 %then %do;
    %put ERROR: Found &missing_usubjid records with missing USUBJID;
%end;

/* Check for duplicates */
proc sort data=sdtm.eg out=_dup_check nodupkey dupout=_dups;
    by usubjid egseq;
run;

%let dup_count = %sysfunc(nobs(_dups));
%if &dup_count > 0 %then %do;
    %put ERROR: Found &dup_count duplicate records by USUBJID + EGSEQ;
%end;


/*------------------------------------------------------------------------------
* Step 6: Generate documentation
------------------------------------------------------------------------------*/
proc contents data=sdtm.eg out=work.eg_contents noprint;
run;

proc print data=sdtm.eg(obs=10) label;
    title "Sample of SDTM EG Domain";
run;

%log_step(step=EG Domain - Complete, status=SUCCESS);
