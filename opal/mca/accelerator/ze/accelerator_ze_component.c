/*
 * Copyright (c) 2014      Intel, Inc.  All rights reserved.
 * Copyright (c) 2014      Research Organization for Information Science
 *                         and Technology (RIST). All rights reserved.
 * Copyright (c) 2015      Los Alamos National Security, LLC. All rights
 *                         reserved.
 * Copyright (c) 2017-2022 Amazon.com, Inc. or its affiliates.
 *                         All Rights reserved.
 * Copyright (c) 2022      Advanced Micro Devices, Inc. All Rights reserved.
 * $COPYRIGHT$
 *
 * Additional copyrights may follow
 *
 * $HEADER$
 */

#include "opal_config.h"

#include <stdio.h>
#include <dlfcn.h>

#include "opal/mca/dl/base/base.h"
#include "opal/runtime/opal_params.h"
#include "accelerator_ze.h"

int opal_accelerator_ze_memcpy_async = 1;
int opal_accelerator_ze_verbose = 0;
uint32_t opal_accelerator_ze_device_count;
ze_device_handle_t *opal_accelerator_ze_devices_handle = NULL;
ze_driver_handle_t opal_accelerator_ze_driver_handle;
ze_context_handle_t opal_accelerator_ze_context;
ze_event_pool_handle_t opal_accelerator_ze_event_pool;
ze_command_list_handle_t opal_accelerator_ze_commandlist;
ze_command_queue_handle_t opal_accelerator_ze_MemcpyStream = NULL;

size_t opal_accelerator_ze_memcpyD2H_limit=1024;
size_t opal_accelerator_ze_memcpyH2D_limit=1048576;

/* Initialization lock for lazy ze initialization */
static opal_mutex_t accelerator_ze_init_lock;
static bool accelerator_ze_init_complete = false;

#define ZE_ERR_CHECK(ret) \
    do { \
        if ((ret) != ZE_RESULT_SUCCESS) \
            goto fn_fail; \
    } while (0)


/*
 * Public string showing the accelerator ze component version number
 */
const char *opal_accelerator_ze_component_version_string
    = "OPAL ze accelerator MCA component version " OPAL_VERSION;


/*
 * Local function
 */
static int accelerator_ze_open(void);
static int accelerator_ze_close(void);
static int accelerator_ze_component_register(void);
static opal_accelerator_base_module_t* accelerator_ze_init(void);
static void accelerator_ze_finalize(opal_accelerator_base_module_t* module);

/*
 * Instantiate the public struct with all of our public information
 * and pointers to our public functions in it
 */

opal_accelerator_ze_component_t mca_accelerator_ze_component = {{

    /* First, the mca_component_t struct containing meta information
     * about the component itself */

    .base_version =
        {
            /* Indicate that we are a accelerator v1.1.0 component (which also
             * implies a specific MCA version) */

            OPAL_ACCELERATOR_BASE_VERSION_1_0_0,

            /* Component name and version */

            .mca_component_name = "ze",
            MCA_BASE_MAKE_VERSION(component, OPAL_MAJOR_VERSION, OPAL_MINOR_VERSION,
                                  OPAL_RELEASE_VERSION),

            /* Component open and close functions */

            .mca_open_component = accelerator_ze_open,
            .mca_close_component = accelerator_ze_close,
            .mca_register_component_params = accelerator_ze_component_register,

        },
    /* Next the MCA v1.0.0 component meta data */
    .base_data =
        { /* The component is checkpoint ready */
         MCA_BASE_METADATA_PARAM_CHECKPOINT},
    .accelerator_init = accelerator_ze_init,
    .accelerator_finalize = accelerator_ze_finalize,
}};

static int accelerator_ze_open(void)
{
    /* construct the component fields */

    return OPAL_SUCCESS;
}

static int accelerator_ze_close(void)
{
    return OPAL_SUCCESS;
}

static int accelerator_ze_component_register(void)
{
    /* Set verbosity in the ze related code. */
    opal_accelerator_ze_verbose = 0;
    (void) mca_base_var_register("ompi", "mpi", "accelerator_ze", "verbose",
                                 "Set level of ze verbosity", MCA_BASE_VAR_TYPE_INT, NULL,
                                 0, 0, OPAL_INFO_LVL_9, MCA_BASE_VAR_SCOPE_READONLY,
                                 &opal_accelerator_ze_verbose);

#if 0
    /* Switching point between using memcpy and hipMemcpy* functions. */
    opal_accelerator_ze_memcpyD2H_limit = 1024;
    (void) mca_base_var_register("ompi", "mpi", "accelerator_ze", "memcpyD2H_limit",
                                 "Max. msg. length to use memcpy instead of hip functions "
                                 "for device-to-host copy operations",
                                 MCA_BASE_VAR_TYPE_INT, NULL, 0, 0,
                                 OPAL_INFO_LVL_9, MCA_BASE_VAR_SCOPE_READONLY,
                                 &opal_accelerator_ze_memcpyD2H_limit);

    /* Switching point between using memcpy and hipMemcpy* functions. */
    opal_accelerator_ze_memcpyH2D_limit = 1048576;
    (void) mca_base_var_register("ompi", "mpi", "accelerator_ze", "memcpyH2D_limit",
                                 "Max. msg. length to use memcpy instead of hip functions "
                                 "for host-to-device copy operations",
                                 MCA_BASE_VAR_TYPE_INT, NULL, 0, 0,
                                 OPAL_INFO_LVL_9, MCA_BASE_VAR_SCOPE_READONLY,
                                 &opal_accelerator_ze_memcpyH2D_limit);

    /* Use this flag to test async vs sync copies */
    opal_accelerator_ze_memcpy_async = 1;
    (void) mca_base_var_register("ompi", "mpi", "accelerator_ze", "memcpy_async",
                                 "Set to 0 to force using hipMemcpy instead of hipMemcpyAsync",
                                 MCA_BASE_VAR_TYPE_INT, NULL, 0, 0, OPAL_INFO_LVL_9,
                                 MCA_BASE_VAR_SCOPE_READONLY, &opal_accelerator_ze_memcpy_async);
#endif
    return OPAL_SUCCESS;
}

/*
 * If this method is invoked it means we already
 * initialized ZE in the accelerator_ze_init method below
 */

int opal_accelerator_ze_lazy_init(void)
{
    uint32_t i,d;
    int err = OPAL_SUCCESS;
    ze_result_t zret;
    uint32_t driver_count = 0;
    ze_driver_handle_t *all_drivers = NULL;

    /* Double checked locking to avoid having to
     * grab locks post lazy-initialization.  */

    opal_atomic_rmb();
    if (true == accelerator_ze_init_complete) {
        return OPAL_SUCCESS;
    }
    OPAL_THREAD_LOCK(&accelerator_ze_init_lock);

    /* If already initialized, just exit */
    if (true == accelerator_ze_init_complete) {
        goto out;
    }

    zret = zeDriverGet(&driver_count, NULL);
    if (ZE_RESULT_SUCCESS != zret) {
        err =  OPAL_ERR_NOT_INITIALIZED;
        goto out;
    }

    /*
     * driver count should not be zero as to get here ZE component
     * was successfully init'd.
     */
    if (0 == driver_count) {
        err = OPAL_ERR_NOT_FOUND;
    }

    all_drivers = (ze_driver_handle_t *)malloc(driver_count * sizeof(ze_driver_handle_t));
    if (all_drivers == NULL) {
        err = OPAL_ERR_OUT_OF_RESOURCE;
        goto out;
    }

    zret = zeDriverGet(&driver_count, all_drivers);
    if (ZE_RESULT_SUCCESS != zret) {
        err = OPAL_ERR_NOT_FOUND;
        goto out;
    }

    /*
     * Current design of ZE component assumes we find the first driver with a GPU device.
     * we'll create a single ZE context if we do find such a device.  This may need to
     * be revisited at some point but would impact areas of code outside of the 
     * accelerator framework.
     */

    for (i = 0; i < driver_count; ++i) {
        opal_accelerator_ze_device_count = 0;
        zret = zeDeviceGet(all_drivers[i], &opal_accelerator_ze_device_count, NULL);
        ZE_ERR_CHECK(zret);
        opal_accelerator_ze_devices_handle =
            malloc(opal_accelerator_ze_device_count * sizeof(ze_device_handle_t));
        if (NULL == opal_accelerator_ze_devices_handle) {
            err = OPAL_ERR_OUT_OF_RESOURCE;
            goto out;
        }
        zret = zeDeviceGet(all_drivers[i], &opal_accelerator_ze_device_count, opal_accelerator_ze_devices_handle);
        ZE_ERR_CHECK(zret);
        /* Check if the driver supports a gpu */
        for (d = 0; d < opal_accelerator_ze_device_count; ++d) {
            ze_device_properties_t device_properties;
            zret = zeDeviceGetProperties(opal_accelerator_ze_devices_handle[d], &device_properties);
            ZE_ERR_CHECK(zret);

            if (ZE_DEVICE_TYPE_GPU == device_properties.type) {
                opal_accelerator_ze_driver_handle = all_drivers[i];
                break;
            }
        }

        if (NULL != opal_accelerator_ze_driver_handle) {
            break;
        } else {
            free(opal_accelerator_ze_devices_handle);
            opal_accelerator_ze_devices_handle = NULL;
        }
    }

    ze_context_desc_t contextDesc = {
        .stype = ZE_STRUCTURE_TYPE_CONTEXT_DESC,
        .pNext = NULL,
        .flags = 0,
    };
    zret = zeContextCreate(opal_accelerator_ze_driver_handle, 
                          &contextDesc, 
                          &opal_accelerator_ze_context);
    ZE_ERR_CHECK(zret);

    /*
     * create command queue for synchronize memcopies
     */

   ze_command_queue_desc_t cmdQueueDesc = {
            .stype = ZE_STRUCTURE_TYPE_COMMAND_QUEUE_DESC,
            .pNext = NULL,
            .index = 0,
            .flags = 0,
            .ordinal = 0,
            .mode = ZE_COMMAND_QUEUE_MODE_ASYNCHRONOUS,
            .priority = ZE_COMMAND_QUEUE_PRIORITY_NORMAL,
    };  
    
    zret = zeCommandQueueCreate(opal_accelerator_ze_context,
                                opal_accelerator_ze_devices_handle[0], 
                                &cmdQueueDesc,
                                &opal_accelerator_ze_MemcpyStream);
    assert(zret == ZE_RESULT_SUCCESS);
        

    opal_atomic_wmb();
    accelerator_ze_init_complete = true;

out:
fn_fail:
    if (NULL != all_drivers) {
        free(all_drivers);
    }

    if (OPAL_SUCCESS != err)  {
        free(opal_accelerator_ze_devices_handle);
        opal_accelerator_ze_devices_handle = NULL;
    }
      
    OPAL_THREAD_UNLOCK(&accelerator_ze_init_lock);
    return err;
}

static opal_accelerator_base_module_t* accelerator_ze_init(void)
{
    uint32_t driver_count=0;
    ze_result_t zret;
    ze_init_flag_t flags = ZE_INIT_FLAG_GPU_ONLY;

    OBJ_CONSTRUCT(&accelerator_ze_init_lock, opal_mutex_t);

    if (opal_ze_runtime_initialized) {
        return NULL;
    }

    /* 
     * Initialize ze, this function can be called multiple times
     */

    zret = zeInit(flags);
    if (ZE_RESULT_SUCCESS != zret) {
        return NULL;
    }

    /*
     * zeDriverGet can return:
     * ZE_RESULT_SUCCESS
     * ZE_RESULT_ERROR_UNINITIALIZED
     * ZE_RESULT_ERROR_DEVICE_LOST
     * ZE_RESULT_ERROR_OUT_OF_HOST_MEMORY
     * ZE_RESULT_ERROR_OUT_OF_DEVICE_MEMORY
     */
    zret = zeDriverGet(&driver_count, NULL);
    if (ZE_RESULT_SUCCESS != zret || 0 == driver_count) {
        opal_output(0, "No ZE capabale device found. Disabling component.\n");
        return NULL;
    }

    opal_atomic_mb();
    opal_ze_runtime_initialized = true;

    return &opal_accelerator_ze_module;
    return NULL;
}

static void accelerator_ze_finalize(opal_accelerator_base_module_t* module)
{
    if (NULL != (void *)opal_accelerator_ze_context) {
        zeContextDestroy(opal_accelerator_ze_context);
    }
#if 0
    if (NULL != (void*)opal_accelerator_ze_MemcpyStream) {
        hipError_t err = hipStreamDestroy(opal_accelerator_ze_MemcpyStream);
        if (hipSuccess != err) {
            opal_output_verbose(10, 0, "hip_dl_finalize: error while destroying the hipStream\n");
        }
        opal_accelerator_ze_MemcpyStream = NULL;
    }
#endif

    OBJ_DESTRUCT(&accelerator_ze_init_lock);
    return;
}
