/*
 * Copyright (c) 2022      Advanced Micro Devices, Inc. All Rights reserved.
 * $COPYRIGHT$
 *
 * Additional copyrights may follow
 *
 * $HEADER$
 */

#include "opal_config.h"

#include "accelerator_ze.h"
#include "opal/mca/accelerator/base/base.h"
#include "opal/constants.h"
#include "opal/util/output.h"

/* Accelerator API's */
static int mca_accelerator_ze_check_addr(const void *addr, int *dev_id, uint64_t *flags);
static int mca_accelerator_ze_create_stream(int dev_id, opal_accelerator_stream_t **stream);

static int mca_accelerator_ze_create_event(int dev_id, opal_accelerator_event_t **event);
static int mca_accelerator_ze_record_event(int dev_id, opal_accelerator_event_t *event, opal_accelerator_stream_t *stream);
static int mca_accelerator_ze_query_event(int dev_id, opal_accelerator_event_t *event);

static int mca_accelerator_ze_memcpy_async(int dest_dev_id, int src_dev_id, void *dest, const void *src, size_t size,
                                  opal_accelerator_stream_t *stream, opal_accelerator_transfer_type_t type);
static int mca_accelerator_ze_memcpy(int dest_dev_id, int src_dev_id, void *dest, const void *src,
                            size_t size, opal_accelerator_transfer_type_t type);
static int mca_accelerator_ze_memmove(int dest_dev_id, int src_dev_id, void *dest, const void *src, size_t size,
                                        opal_accelerator_transfer_type_t type);
static int mca_accelerator_ze_mem_alloc(int dev_id, void **ptr, size_t size);
static int mca_accelerator_ze_mem_release(int dev_id, void *ptr);
static int mca_accelerator_ze_get_address_range(int dev_id, const void *ptr, void **base,
                                                  size_t *size);

static int mca_accelerator_ze_host_register(int dev_id, void *ptr, size_t size);
static int mca_accelerator_ze_host_unregister(int dev_id, void *ptr);

static int mca_accelerator_ze_get_device(int *dev_id);
static int mca_accelerator_ze_device_can_access_peer( int *access, int dev1, int dev2);

static int mca_accelerator_ze_get_buffer_id(int dev_id, const void *addr, opal_accelerator_buffer_id_t *buf_id);

opal_accelerator_base_module_t opal_accelerator_ze_module =
{
    .check_addr = mca_accelerator_ze_check_addr,

    .create_stream = mca_accelerator_ze_create_stream,
    .create_event = mca_accelerator_ze_create_event,
    .record_event = mca_accelerator_ze_record_event,
    .query_event = mca_accelerator_ze_query_event,

    .mem_copy_async = mca_accelerator_ze_memcpy_async,
    .mem_copy = mca_accelerator_ze_memcpy,
    .mem_move = mca_accelerator_ze_memmove,

    .mem_alloc = mca_accelerator_ze_mem_alloc,
    .mem_release = mca_accelerator_ze_mem_release,
    .get_address_range = mca_accelerator_ze_get_address_range,

    .host_register = mca_accelerator_ze_host_register,
    .host_unregister = mca_accelerator_ze_host_unregister,

    .get_device= mca_accelerator_ze_get_device,
    .get_device_pci_attr = NULL,
    .device_can_access_peer = mca_accelerator_ze_device_can_access_peer,

    .get_buffer_id = mca_accelerator_ze_get_buffer_id
};


static int mca_accelerator_ze_check_addr (const void *addr, int *dev_id, uint64_t *flags)
{
    int ret = 0;
    ze_memory_allocation_properties_t attr;
    ze_device_handle_t phDevice;

    *dev_id = MCA_ACCELERATOR_NO_DEVICE_ID;
    *flags = 0;

    if (NULL == addr || NULL == flags) {
        return OPAL_ERR_BAD_PARAM;
    }

    ret = opal_accelerator_ze_lazy_init();
    if (OPAL_SUCCESS != ret) {
        return ret;
    }

    ret = zeMemGetAllocProperties(opal_accelerator_ze_context, 
                                  addr,
                                  &attr,
                                  &phDevice);
    ZE_ERR_CHECK(ret);
    switch (attr.type) {
        case ZE_MEMORY_TYPE_UNKNOWN:
        case ZE_MEMORY_TYPE_HOST:
            break;
        case ZE_MEMORY_TYPE_DEVICE:
        /*
         *  Assume that although shared is accessible from host, access may be slow so
         *  like device memory for now.
         */
        case ZE_MEMORY_TYPE_SHARED:
           *flags |= MCA_ACCELERATOR_FLAGS_UNIFIED_MEMORY;
            ret = 1;
            break;
        default:
            goto fn_fail;
    }

fn_fail:

    return ret;
}

static int mca_accelerator_ze_create_stream(int dev_id, opal_accelerator_stream_t **stream)
{
    /*
     *  maps to hipStreamCreate - zeCommandQueueCreate
     */
    return OPAL_SUCCESS;
}

static void mca_accelerator_ze_stream_destruct(opal_accelerator_ze_stream_t *stream)
{
    /*
     *  maps to hipStreamDestroy
     */
}

OBJ_CLASS_INSTANCE(
    opal_accelerator_ze_stream_t,
    opal_accelerator_stream_t,
    NULL,
    mca_accelerator_ze_stream_destruct);

static int mca_accelerator_ze_create_event(int dev_id, opal_accelerator_event_t **event)
{
    if (NULL == event) {
        return OPAL_ERR_BAD_PARAM;
    }

#if 0
    *event = (opal_accelerator_event_t*)OBJ_NEW(opal_accelerator_rocm_event_t);
    if (NULL == *event) {
        return OPAL_ERR_OUT_OF_RESOURCE;
    }

    (*event)->event = malloc(sizeof(hipEvent_t));
    if (NULL == (*event)->event) {
        OBJ_RELEASE(*event);
        return OPAL_ERR_OUT_OF_RESOURCE;
    }
    hipError_t err = hipEventCreateWithFlags((hipEvent_t*)(*event)->event,
                                                       hipEventDisableTiming);
    if (hipSuccess != err) {
        opal_output_verbose(10, opal_accelerator_base_framework.framework_output,
                            "error creating event\n");
        free((*event)->event);
        OBJ_RELEASE(*event);
        return OPAL_ERROR;
    }
#endif

    return OPAL_SUCCESS;

}

static void mca_accelerator_ze_event_destruct(opal_accelerator_ze_event_t *event)
{
#if 0
    if (NULL != event->base.event) {
        hipError_t err = hipEventDestroy(*(hipEvent_t*)event->base.event);
        if (hipSuccess != err) {
            opal_output_verbose(10, opal_accelerator_base_framework.framework_output,
                                "error destroying event\n");
        }
        free(event->base.event);
    }
#endif
}

OBJ_CLASS_INSTANCE(
    opal_accelerator_ze_event_t,
    opal_accelerator_event_t,
    NULL,
    mca_accelerator_ze_event_destruct);

static int mca_accelerator_ze_record_event(int dev_id, opal_accelerator_event_t *event,
                                             opal_accelerator_stream_t *stream)
{
    if (NULL == event || NULL == event->event){
        return OPAL_ERR_BAD_PARAM;
    }
    if (NULL == stream || NULL == stream->stream){
        return OPAL_ERR_BAD_PARAM;
    }

#if 0
    hipError_t err = hipEventRecord(*((hipEvent_t *)event->event),
                                              *((hipStream_t *)stream->stream));
    if (hipSuccess != err) {
        opal_output_verbose(10, opal_accelerator_base_framework.framework_output,
                            "error recording event\n");
        return OPAL_ERROR;
    }
#endif

    return OPAL_SUCCESS;
}

static int mca_accelerator_ze_query_event(int dev_id, opal_accelerator_event_t *event)
{
    if (NULL == event || NULL == event->event) {
        return OPAL_ERR_BAD_PARAM;
    }

#if 0
    hipError_t err = hipEventQuery(*((hipEvent_t *)event->event));
    switch (err) {
        case hipSuccess:
            return OPAL_SUCCESS;
            break;
        case hipErrorNotReady:
            return OPAL_ERR_RESOURCE_BUSY;
            break;
        default:
            opal_output_verbose(10, opal_accelerator_base_framework.framework_output,
                                "error while querying event\n");
            return OPAL_ERROR;
    }
#endif

    return OPAL_SUCCESS;
}

static int mca_accelerator_ze_memcpy_async(int dest_dev_id, int src_dev_id, void *dest, const void *src,
                                             size_t size, opal_accelerator_stream_t *stream,
                                             opal_accelerator_transfer_type_t type)
{
    return OPAL_SUCCESS;
}

static int mca_accelerator_ze_memcpy(int dest_dev_id, int src_dev_id, void *dest,
				       const void *src, size_t size,
                                       opal_accelerator_transfer_type_t type)
{
    return OPAL_SUCCESS;
}

static int mca_accelerator_ze_memmove(int dest_dev_id, int src_dev_id, void *dest,
					const void *src, size_t size,
                                        opal_accelerator_transfer_type_t type)
{
    return OPAL_SUCCESS;
}

static int mca_accelerator_ze_mem_alloc(int dev_id, void **ptr, size_t size)
{
#if 0
   int mpl_err = MPL_SUCCESS;
    int ret;
    size_t mem_alignment;
    ze_device_mem_alloc_desc_t device_desc = {
        .stype = ZE_STRUCTURE_TYPE_DEVICE_MEM_ALLOC_DESC,
        .pNext = NULL,
        .flags = 0,
        .ordinal = 0,   /* We currently support a single memory type */
    };
    /* Currently ZE ignores this argument and uses an internal alignment
     * value. However, this behavior can change in the future. */
    mem_alignment = 1;
    ret = zeMemAllocDevice(global_ze_context, &device_desc, size, mem_alignment, h_device, ptr);

    ZE_ERR_CHECK(ret);

  fn_exit:
    return mpl_err;
  fn_fail:
    mpl_err = MPL_ERR_GPU_INTERNAL;
    goto fn_exit;

#endif
    return OPAL_SUCCESS;
}

static int mca_accelerator_ze_mem_release(int dev_id, void *ptr)
{
    return OPAL_SUCCESS;
}

static int mca_accelerator_ze_get_address_range(int dev_id, const void *ptr, void **base,
						  size_t *size)
{
    return OPAL_SUCCESS;
}

/*
 * ZE doesn't have explicit host memory registration functions
 */

static int mca_accelerator_ze_host_register(int dev_id, void *ptr, size_t size)
{
    return OPAL_SUCCESS;
}

static int mca_accelerator_ze_host_unregister(int dev_id, void *ptr)
{
    return OPAL_SUCCESS;
}

static int mca_accelerator_ze_get_device(int *dev_id)
{
    return OPAL_SUCCESS;
}

static int mca_accelerator_ze_device_can_access_peer(int *access, int dev1, int dev2)
{
    return OPAL_SUCCESS;
}

static int mca_accelerator_ze_get_buffer_id(int dev_id, const void *addr, opal_accelerator_buffer_id_t *buf_id)
{
    return OPAL_SUCCESS;
}
