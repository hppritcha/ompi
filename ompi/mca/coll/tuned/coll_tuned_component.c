/* -*- Mode: C; c-basic-offset:4 ; indent-tabs-mode:nil -*- */
/*
 * Copyright (c) 2004-2007 The Trustees of Indiana University and Indiana
 *                         University Research and Technology
 *                         Corporation.  All rights reserved.
 * Copyright (c) 2004-2015 The University of Tennessee and The University
 *                         of Tennessee Research Foundation.  All rights
 *                         reserved.
 * Copyright (c) 2004-2005 High Performance Computing Center Stuttgart,
 *                         University of Stuttgart.  All rights reserved.
 * Copyright (c) 2004-2005 The Regents of the University of California.
 *                         All rights reserved.
 * Copyright (c) 2008      Sun Microsystems, Inc.  All rights reserved.
 * Copyright (c) 2008      Cisco Systems, Inc.  All rights reserved.
 * Copyright (c) 2015      Los Alamos National Security, LLC. All rights
 *                         reserved.
 * Copyright (c) 2015-2018 Research Organization for Information Science
 *                         and Technology (RIST). All rights reserved.
 * Copyright (c) 2019      Mellanox Technologies. All rights reserved.
 * Copyright (c) 2024      NVIDIA Corporation.  All rights reserved.
 * Copyright (c) 2025      Amazon.com, Inc. or its affiliates.  All rights
 *                         reserved.
 * $COPYRIGHT$
 *
 * Additional copyrights may follow
 *
 * $HEADER$
 *
 * These symbols are in a file by themselves to provide nice linker
 * semantics.  Since linkers generally pull in symbols by object
 * files, keeping these symbols as the only symbols in this file
 * prevents utility programs such as "ompi_info" from having to import
 * entire components just to query their version and parameters.
 */

#include "ompi_config.h"
#include "opal/util/output.h"
#include "coll_tuned.h"

#include "mpi.h"
#include "ompi/mca/coll/coll.h"
#include "coll_tuned.h"
#include "coll_tuned_dynamic_file.h"

/*
 * Public string showing the coll ompi_tuned component version number
 */
const char *ompi_coll_tuned_component_version_string =
    "Open MPI tuned collective MCA component version " OMPI_VERSION;

/*
 * Global variable
 */
int   ompi_coll_tuned_stream = -1;
int   ompi_coll_tuned_priority = 30;
bool  ompi_coll_tuned_use_dynamic_rules = false;
char* ompi_coll_tuned_dynamic_rules_filename = (char*) NULL;
int   ompi_coll_tuned_init_tree_fanout = 4;
int   ompi_coll_tuned_init_chain_fanout = 4;
int   ompi_coll_tuned_init_max_requests = 128;
int   ompi_coll_tuned_verbose = 0;

/* Set it to the same value as intermediate msg by default, so it does not affect
 * default algorithm selection. Changing this value will force using linear with
 * sync algorithm on certain message sizes. */
int   ompi_coll_tuned_alltoall_max_requests  = 0; /* no limit for alltoall by default */

/* Disable by default */
int   ompi_coll_tuned_scatter_intermediate_msg = 0;
int   ompi_coll_tuned_scatter_large_msg = 0;
int   ompi_coll_tuned_scatter_min_procs = 0;
int   ompi_coll_tuned_scatter_blocking_send_ratio = 0;

/* forced algorithm variables */
/* indices for the MCA parameters */
coll_tuned_force_algorithm_mca_param_indices_t ompi_coll_tuned_forced_params[COLLCOUNT] = {{0}};
/* max algorithm values */
int ompi_coll_tuned_forced_max_algorithms[COLLCOUNT] = {0};

/* names of each algorithm for each collective */
mca_base_var_enum_t *coll_tuned_algorithm_enums[COLLCOUNT] = {0};


/*
 * Local function
 */
static int tuned_register(void);
static int tuned_open(void);
static int tuned_close(void);

/*
 * Instantiate the public struct with all of our public information
 * and pointers to our public functions in it
 */

mca_coll_tuned_component_t mca_coll_tuned_component = {
    /* First, fill in the super */
    {
        /* First, the mca_component_t struct containing meta information
           about the component itself */
        .collm_version = {
            MCA_COLL_BASE_VERSION_3_0_0,

            /* Component name and version */
            .mca_component_name = "tuned",
            MCA_BASE_MAKE_VERSION(component, OMPI_MAJOR_VERSION, OMPI_MINOR_VERSION,
                                  OMPI_RELEASE_VERSION),

            /* Component open and close functions */
            .mca_open_component = tuned_open,
            .mca_close_component = tuned_close,
            .mca_register_component_params = tuned_register,
        },
        .collm_data = {
            /* The component is checkpoint ready */
            MCA_BASE_METADATA_PARAM_CHECKPOINT
        },

        /* Initialization / querying functions */

        .collm_init_query = ompi_coll_tuned_init_query,
        .collm_comm_query = ompi_coll_tuned_comm_query,
    },

    /* priority of the module */
    0,

    /* Tuned component specific information */
    NULL /* ompi_coll_alg_rule_t ptr */
};
MCA_BASE_COMPONENT_INIT(ompi, coll, tuned)

static int tuned_register(void)
{

    /* Use a low priority, but allow other components to be lower */
    ompi_coll_tuned_priority = 30;
    (void) mca_base_component_var_register(&mca_coll_tuned_component.super.collm_version,
                                           "priority", "Priority of the tuned coll component",
                                           MCA_BASE_VAR_TYPE_INT, NULL, 0, MCA_BASE_VAR_FLAG_SETTABLE,
                                           OPAL_INFO_LVL_6,
                                           MCA_BASE_VAR_SCOPE_ALL,
                                           &ompi_coll_tuned_priority);

    /* some initial guesses at topology parameters */
    ompi_coll_tuned_init_tree_fanout = 4;
    (void) mca_base_component_var_register(&mca_coll_tuned_component.super.collm_version,
                                           "init_tree_fanout",
                                           "Initial fanout used in the tree topologies for each communicator. This is only an initial guess, if a tuned collective needs a different fanout for an operation, it build it dynamically. This parameter is only for the first guess and might save a little time",
                                           MCA_BASE_VAR_TYPE_INT, NULL, 0, MCA_BASE_VAR_FLAG_SETTABLE,
                                           OPAL_INFO_LVL_6,
                                           MCA_BASE_VAR_SCOPE_ALL,
                                           &ompi_coll_tuned_init_tree_fanout);

    ompi_coll_tuned_init_chain_fanout = 4;
    (void) mca_base_component_var_register(&mca_coll_tuned_component.super.collm_version,
                                           "init_chain_fanout",
                                           "Initial fanout used in the chain (fanout followed by pipeline) topologies for each communicator. This is only an initial guess, if a tuned collective needs a different fanout for an operation, it build it dynamically. This parameter is only for the first guess and might save a little time",
                                           MCA_BASE_VAR_TYPE_INT, NULL, 0, MCA_BASE_VAR_FLAG_SETTABLE,
                                           OPAL_INFO_LVL_6,
                                           MCA_BASE_VAR_SCOPE_ALL,
                                           &ompi_coll_tuned_init_chain_fanout);

    int deprecated_mca_params = -1;
    (void) mca_base_component_var_register(&mca_coll_tuned_component.super.collm_version,
                                           "alltoall_small_msg",
                                           "threshold (if supported) to decide if small MSGs alltoall algorithm will be used",
                                           MCA_BASE_VAR_TYPE_INT, NULL, 0, MCA_BASE_VAR_FLAG_DEPRECATED,
                                           OPAL_INFO_LVL_6,
                                           MCA_BASE_VAR_SCOPE_READONLY,
                                           &deprecated_mca_params);

    (void) mca_base_component_var_register(&mca_coll_tuned_component.super.collm_version,
                                           "alltoall_intermediate_msg",
                                           "threshold (if supported) to decide if intermediate MSGs alltoall algorithm will be used",
                                           MCA_BASE_VAR_TYPE_INT, NULL, 0, MCA_BASE_VAR_FLAG_DEPRECATED,
                                           OPAL_INFO_LVL_6,
                                           MCA_BASE_VAR_SCOPE_READONLY,
                                           &deprecated_mca_params);

    (void) mca_base_component_var_register(&mca_coll_tuned_component.super.collm_version,
                                           "use_dynamic_rules",
                                           "Switch used to decide if we use static (compiled/if statements) or dynamic (built at runtime) decision function rules",
                                           MCA_BASE_VAR_TYPE_BOOL, NULL, 0, MCA_BASE_VAR_FLAG_SETTABLE,
                                           OPAL_INFO_LVL_6,
                                           MCA_BASE_VAR_SCOPE_ALL,
                                           &ompi_coll_tuned_use_dynamic_rules);

    ompi_coll_tuned_dynamic_rules_filename = NULL;
    (void) mca_base_component_var_register(&mca_coll_tuned_component.super.collm_version,
                                           "dynamic_rules_filename",
                                           "Filename of configuration file that contains the dynamic (@runtime) decision function rules",
                                           MCA_BASE_VAR_TYPE_STRING, NULL, 0, MCA_BASE_VAR_FLAG_SETTABLE,
                                           OPAL_INFO_LVL_6,
                                           MCA_BASE_VAR_SCOPE_ALL,
                                           &ompi_coll_tuned_dynamic_rules_filename);

    ompi_coll_tuned_verbose = 0;
    (void) mca_base_component_var_register(&mca_coll_tuned_component.super.collm_version,
                                           "verbose",
                                           "Verbosity of the tuned coll component",
                                           MCA_BASE_VAR_TYPE_INT, NULL, 0, MCA_BASE_VAR_FLAG_SETTABLE,
                                           OPAL_INFO_LVL_9,
                                           MCA_BASE_VAR_SCOPE_ALL,
                                           &ompi_coll_tuned_verbose);

    /* register forced params */
    ompi_coll_tuned_allreduce_intra_check_forced_init(&ompi_coll_tuned_forced_params[ALLREDUCE]);
    ompi_coll_tuned_alltoall_intra_check_forced_init(&ompi_coll_tuned_forced_params[ALLTOALL]);
    ompi_coll_tuned_allgather_intra_check_forced_init(&ompi_coll_tuned_forced_params[ALLGATHER]);
    ompi_coll_tuned_allgatherv_intra_check_forced_init(&ompi_coll_tuned_forced_params[ALLGATHERV]);
    ompi_coll_tuned_alltoallv_intra_check_forced_init(&ompi_coll_tuned_forced_params[ALLTOALLV]);
    ompi_coll_tuned_barrier_intra_check_forced_init(&ompi_coll_tuned_forced_params[BARRIER]);
    ompi_coll_tuned_bcast_intra_check_forced_init(&ompi_coll_tuned_forced_params[BCAST]);
    ompi_coll_tuned_reduce_intra_check_forced_init(&ompi_coll_tuned_forced_params[REDUCE]);
    ompi_coll_tuned_reduce_scatter_intra_check_forced_init(&ompi_coll_tuned_forced_params[REDUCESCATTER]);
    ompi_coll_tuned_reduce_scatter_block_intra_check_forced_init(&ompi_coll_tuned_forced_params[REDUCESCATTERBLOCK]);
    ompi_coll_tuned_gather_intra_check_forced_init(&ompi_coll_tuned_forced_params[GATHER]);
    ompi_coll_tuned_scatter_intra_check_forced_init(&ompi_coll_tuned_forced_params[SCATTER]);
    ompi_coll_tuned_exscan_intra_check_forced_init(&ompi_coll_tuned_forced_params[EXSCAN]);
    ompi_coll_tuned_scan_intra_check_forced_init(&ompi_coll_tuned_forced_params[SCAN]);

    return OMPI_SUCCESS;
}

static int tuned_open(void)
{
    int rc;

    if (ompi_coll_tuned_verbose) {
        ompi_coll_tuned_stream = opal_output_open(NULL);
        opal_output_set_verbosity(ompi_coll_tuned_stream, ompi_coll_tuned_verbose);
    }

    /* now check that the user hasn't overrode any of the decision functions if dynamic rules are enabled */
    /* the user can redo this before every comm dup/create if they like */
    /* this is useful for benchmarking and user knows best tuning */
    /* as this is the component we only lookup the indices of the mca params */
    /* the actual values are looked up during comm create via module init */

    /* intra functions first */
    /* if dynamic rules allowed then look up dynamic rules config filename, else we leave it an empty filename (NULL) */
    /* by default DISABLE dynamic rules and instead use fixed [if based] rules */
    if (ompi_coll_tuned_use_dynamic_rules) {
        if( ompi_coll_tuned_dynamic_rules_filename ) {
            OPAL_OUTPUT_VERBOSE((COLL_TUNED_TRACING_VERBOSE, ompi_coll_tuned_stream,
                "coll:tuned:component_open Reading collective rules file [%s]",
                ompi_coll_tuned_dynamic_rules_filename));
            rc = ompi_coll_tuned_read_rules_config_file( ompi_coll_tuned_dynamic_rules_filename,
                                                         &(mca_coll_tuned_component.all_base_rules));
            if( rc == OPAL_SUCCESS ) {
                OPAL_OUTPUT_VERBOSE((COLL_TUNED_TRACING_VERBOSE, ompi_coll_tuned_stream,
                    "coll:tuned:module_open Read a valid rules file"));
            } else {
                OPAL_OUTPUT_VERBOSE((COLL_TUNED_TRACING_VERBOSE, ompi_coll_tuned_stream,
                    "coll:tuned:module_open Reading collective rules file failed\n"));
                mca_coll_tuned_component.all_base_rules = NULL;
            }
        }
    }

    OPAL_OUTPUT_VERBOSE((COLL_TUNED_TRACING_VERBOSE, ompi_coll_tuned_stream,
        "coll:tuned:component_open: done!"));

    return OMPI_SUCCESS;
}

/* here we should clean up state stored on the component */
/* i.e. alg table and dynamic changeable rules if allocated etc */
static int tuned_close(void)
{
    OPAL_OUTPUT_VERBOSE((COLL_TUNED_TRACING_VERBOSE, ompi_coll_tuned_stream,
        "coll:tuned:component_close: called"));

    /* dealloc alg table if allocated */
    /* dealloc dynamic changeable rules if allocated */

    OPAL_OUTPUT_VERBOSE((COLL_TUNED_TRACING_VERBOSE, ompi_coll_tuned_stream,
        "coll:tuned:component_close: done!"));

    if( NULL != mca_coll_tuned_component.all_base_rules ) {
        ompi_coll_tuned_free_all_rules(mca_coll_tuned_component.all_base_rules);
        mca_coll_tuned_component.all_base_rules = NULL;
    }

    for (int i=0; i<COLLCOUNT; i++) {
        if (coll_tuned_algorithm_enums[i] != NULL) {
            OBJ_RELEASE(coll_tuned_algorithm_enums[i]);
        }
    }

    return OMPI_SUCCESS;
}

static void
mca_coll_tuned_module_construct(mca_coll_tuned_module_t *module)
{
    mca_coll_tuned_module_t *tuned_module = (mca_coll_tuned_module_t*) module;

    for( int i = 0; i < COLLCOUNT; i++ ) {
        tuned_module->user_forced[i].algorithm = 0;
        tuned_module->com_rules[i] = NULL;
    }
}

int coll_tuned_alg_from_str(int collective_id, const char *alg_name, int *alg_value) {
    int rc;
    if (collective_id >= COLLCOUNT || collective_id < 0) { return OPAL_ERROR; };
    rc = coll_tuned_algorithm_enums[collective_id]->value_from_string(
        coll_tuned_algorithm_enums[collective_id],
        alg_name, alg_value );
    return rc;
}

/* return the enum's value and string.  caller's responsibility to free alg_string if NULL was not provided. */
int coll_tuned_alg_to_str(int collective_id, int alg_value, char **alg_string) {
    int rc;
    if (collective_id >= COLLCOUNT || collective_id < 0) { return OPAL_ERROR; };
    rc = coll_tuned_algorithm_enums[collective_id]->string_from_value(
        coll_tuned_algorithm_enums[collective_id],
        alg_value, alg_string );
    return rc;
}


int coll_tuned_alg_register_options(int collective_id, mca_base_var_enum_t *options) {
    /* use the same enum used for mca parameters to allow tuning files to use
    algorithm names rather than just numbers.*/
    if (!options) { return OPAL_ERROR; }
    if (collective_id >= COLLCOUNT || collective_id < 0) {
        return OPAL_ERROR;
    }

    /* retain the enum until tuned_close() */
    OBJ_RETAIN(options);
    coll_tuned_algorithm_enums[collective_id] = options;
    return OPAL_SUCCESS;
}


OBJ_CLASS_INSTANCE(mca_coll_tuned_module_t, mca_coll_base_module_t,
                   mca_coll_tuned_module_construct, NULL);
