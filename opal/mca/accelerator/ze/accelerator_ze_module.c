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

static int mca_accelerator_ze_get_device_pci_attr(int dev_id, opal_accelerator_pci_attr_t *pci_attr);

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
    .get_device_pci_attr = mca_accelerator_ze_get_device_pci_attr,
    .device_can_access_peer = mca_accelerator_ze_device_can_access_peer,

    .get_buffer_id = mca_accelerator_ze_get_buffer_id
};

static int accelerator_ze_dev_handle_to_dev_id(ze_device_handle_t hDevice)
{
    int i, ret = MCA_ACCELERATOR_NO_DEVICE_ID;

    for (i = 0; i < (int)opal_accelerator_ze_device_count; i++) {
        if (opal_accelerator_ze_devices_handle[i] == hDevice) {
            ret = i;
            break;
        }
    }

    return ret;
}

static int mca_accelerator_ze_check_addr (const void *addr, int *dev_id, uint64_t *flags)
{
    int ret = 0;
    ze_memory_allocation_properties_t attr;
    ze_device_handle_t hDevice;

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
                                  &hDevice);
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
            *dev_id = accelerator_ze_dev_handle_to_dev_id(hDevice);
            break;
        default:
            goto fn_fail;
    }

fn_fail:

    return ret;
}

static int mca_accelerator_ze_create_stream(int dev_id, opal_accelerator_stream_t **stream)
{
    int zret;
    ze_device_handle_t hDevice;
    opal_accelerator_ze_stream_t *ze_stream;

    ze_command_queue_desc_t cmdQueueDesc = {
            .stype = ZE_STRUCTURE_TYPE_COMMAND_QUEUE_DESC,
            .pNext = NULL,
            .index = 0,
            .flags = 0,
            .ordinal = 0,
            .mode = ZE_COMMAND_QUEUE_MODE_ASYNCHRONOUS,
            .priority = ZE_COMMAND_QUEUE_PRIORITY_NORMAL,
    };

    if (NULL == stream) {
        return OPAL_ERR_BAD_PARAM;
    }

    ze_stream = (opal_accelerator_ze_stream_t *)malloc(sizeof(opal_accelerator_ze_stream_t));
    if (NULL == ze_stream) {
        OBJ_RELEASE(*stream);
        return OPAL_ERR_OUT_OF_RESOURCE;
    }
   
#if 0
    (*stream)->stream = (opal_accelerator_ze_stream_t *)malloc(sizeof(opal_accelerator_ze_stream_t));
    if (NULL == (*stream)->stream) {
        OBJ_RELEASE(*stream);
        return OPAL_ERR_OUT_OF_RESOURCE;
    }
#endif

    if (MCA_ACCELERATOR_NO_DEVICE_ID == dev_id) {
        hDevice = opal_accelerator_ze_devices_handle[0];
    } else {
        hDevice = opal_accelerator_ze_devices_handle[dev_id];
    }
    ze_stream->dev_id = dev_id;

    zret = zeCommandQueueCreate(opal_accelerator_ze_context, 
                                hDevice,
                                &cmdQueueDesc, 
                                &ze_stream->hCommandQueue);
    assert(zret == ZE_RESULT_SUCCESS);

    /*
     * set up an event pool
     */

    ze_event_pool_desc_t eventPoolDesc = {
            .stype = ZE_STRUCTURE_TYPE_EVENT_POOL_DESC,
            .pNext = NULL,
            .flags = 0,
            .count = 1000,  /* TODO: fix this! */
    };

    zret = zeEventPoolCreate(opal_accelerator_ze_context,
                             &eventPoolDesc,
                             1,
                             opal_accelerator_ze_devices_handle,
                             &ze_stream->hEventPool);
    assert(zret == ZE_RESULT_SUCCESS);

    /*
     * create a command list
     */

    ze_command_list_desc_t commandListDesc = {
        .stype =  ZE_STRUCTURE_TYPE_COMMAND_LIST_DESC,
        .pNext = NULL,
        .commandQueueGroupOrdinal = 0,
        .flags = 0, 
    };

    zret = zeCommandListCreate(opal_accelerator_ze_context, 
                               opal_accelerator_ze_devices_handle[0], 
                               &commandListDesc, 
                               &ze_stream->hCommandList);
    assert(zret == ZE_RESULT_SUCCESS);
    (*stream)->stream = (void *)ze_stream;

    return OPAL_SUCCESS;
}

static void mca_accelerator_ze_stream_destruct(opal_accelerator_ze_stream_t *stream)
{
    int zret;
    opal_accelerator_ze_stream_t *ze_stream;

    if (NULL != stream->base.stream) {
        ze_stream = (opal_accelerator_ze_stream_t  *)stream->base.stream;
        zret = zeCommandQueueDestroy(ze_stream->hCommandQueue);
        if (ZE_RESULT_SUCCESS != zret) {
            opal_output_verbose(10, opal_accelerator_base_framework.framework_output,
                                "error while destroying the zeCommandQueue\n");
        }
        zret = zeEventPoolDestroy(ze_stream->hEventPool);
        if (ZE_RESULT_SUCCESS != zret) {
            opal_output_verbose(10, opal_accelerator_base_framework.framework_output,
                                "error while destroying the zeEventPool\n");
        }
        free(stream->base.stream);
    }
}

OBJ_CLASS_INSTANCE(
    opal_accelerator_ze_stream_t,
    opal_accelerator_stream_t,
    NULL,
    mca_accelerator_ze_stream_destruct);

static int mca_accelerator_ze_create_event(int dev_id, opal_accelerator_event_t **event)
{
    int zret;

    ze_event_desc_t eventDesc = {
       .stype = ZE_STRUCTURE_TYPE_EVENT_DESC,
       .pNext = NULL,
       .index = 0,
       .signal = ZE_EVENT_SCOPE_FLAG_HOST,
       .wait = ZE_EVENT_SCOPE_FLAG_HOST,
    };

    if (NULL == event) {
        return OPAL_ERR_BAD_PARAM;
    }

    *event = (opal_accelerator_event_t*)OBJ_NEW(opal_accelerator_ze_event_t);
    if (NULL == *event) {
        return OPAL_ERR_OUT_OF_RESOURCE;
    }

    (*event)->event = malloc(sizeof(ze_event_handle_t));
    if (NULL == (*event)->event) {
        OBJ_RELEASE(*event);
        return OPAL_ERR_OUT_OF_RESOURCE;
    }

    zret = zeEventCreate(opal_accelerator_ze_event_pool, &eventDesc, (ze_event_handle_t *)(*event)->event);
    if (ZE_RESULT_SUCCESS != zret) {
        opal_output_verbose(10, opal_accelerator_base_framework.framework_output,
                            "error creating event\n");
        free((*event)->event);
        OBJ_RELEASE(*event);
        return OPAL_ERROR;
    }

    return OPAL_SUCCESS;

}

static void mca_accelerator_ze_event_destruct(opal_accelerator_ze_event_t *event)
{
    int zret;
    if (NULL != event->base.event) {
        zret = zeEventDestroy(*(ze_event_handle_t *)event->base.event);
        if (ZE_RESULT_SUCCESS != zret) {
            opal_output_verbose(10, opal_accelerator_base_framework.framework_output,
                                "error destroying event\n");
        }
        free(event->base.event);
    }
}

OBJ_CLASS_INSTANCE(
    opal_accelerator_ze_event_t,
    opal_accelerator_event_t,
    NULL,
    mca_accelerator_ze_event_destruct);

static int mca_accelerator_ze_record_event(int dev_id, opal_accelerator_event_t *event,
                                             opal_accelerator_stream_t *stream)
{
    int zret = ZE_RESULT_SUCCESS;
    opal_accelerator_ze_stream_t *ze_stream;

    if (NULL == event || NULL == event->event){
        return OPAL_ERR_BAD_PARAM;
    }
    if (NULL == stream || NULL == stream->stream){
        return OPAL_ERR_BAD_PARAM;
    }

    ze_stream = (opal_accelerator_ze_stream_t  *)stream->stream;

    zret = zeCommandListAppendSignalEvent(ze_stream->hCommandList,
                                          *(ze_event_handle_t *)event->event);
    if (ZE_RESULT_SUCCESS != zret) {
        opal_output_verbose(10, opal_accelerator_base_framework.framework_output,
                            "error recording event\n");
        return OPAL_ERROR;
    }

    /*
     * okay now close the command list and submit
     */

    zret = zeCommandListClose(ze_stream->hCommandList);
    if (ZE_RESULT_SUCCESS != zret) {
        opal_output_verbose(10, opal_accelerator_base_framework.framework_output,
                            "zeCommandListClose returned %d", zret);
        return OPAL_ERROR;
    }
    
    zret = zeCommandQueueExecuteCommandLists(ze_stream->hCommandQueue,
                                             1,
                                             &ze_stream->hCommandList,
                                             NULL);
    if (ZE_RESULT_SUCCESS != zret) {
        opal_output_verbose(10, opal_accelerator_base_framework.framework_output,
                            "zeCommandQueueExecuteCommandList returned %d", zret);
        return OPAL_ERROR;
    }

    return OPAL_SUCCESS;
}

static int mca_accelerator_ze_query_event(int dev_id, opal_accelerator_event_t *event)
{
    int zret;

    if (NULL == event || NULL == event->event) {
        return OPAL_ERR_BAD_PARAM;
    }

    zret = zeEventQueryStatus(*((ze_event_handle_t *)event->event));
    switch (zret) {
        case ZE_RESULT_SUCCESS:
            return OPAL_SUCCESS;
            break;
        case ZE_RESULT_NOT_READY:
            return OPAL_ERR_RESOURCE_BUSY;
            break;
        default:
            opal_output_verbose(10, opal_accelerator_base_framework.framework_output,
                                "error while querying event\n");
            return OPAL_ERROR;
    }

    return OPAL_SUCCESS;
}

static int mca_accelerator_ze_memcpy_async(int dest_dev_id, int src_dev_id, void *dest, const void *src,
                                             size_t size, opal_accelerator_stream_t *stream,
                                             opal_accelerator_transfer_type_t type)
{
   int zret;
   opal_accelerator_ze_stream_t *ze_stream = NULL;

   if (NULL == stream || NULL == src ||
        NULL == dest   || size <= 0) {
        return OPAL_ERR_BAD_PARAM;
    }

    ze_stream = (opal_accelerator_ze_stream_t  *)stream->stream;
    assert(NULL != ze_stream);

    zret = zeCommandListAppendMemoryCopy(ze_stream->hCommandList,
                                         dest,
                                         src,
                                         size,
                                         NULL,
                                         0,
                                         NULL);
    if (ZE_RESULT_SUCCESS != zret) {
        opal_output_verbose(10, opal_accelerator_base_framework.framework_output,
                            "zeCommandListAppendMemoryCopy returned %d", zret);
        return OPAL_ERROR;
    }

    return OPAL_SUCCESS;
}

static int mca_accelerator_ze_memcpy(int dest_dev_id, int src_dev_id, void *dest,
				       const void *src, size_t size,
                                       opal_accelerator_transfer_type_t type)
{
    int zret;

    if (NULL == src || NULL == dest || size <=0) {
        return OPAL_ERR_BAD_PARAM;
    }                           
            
    zret = zeCommandListAppendMemoryCopy(opal_accelerator_ze_commandlist,
                                         dest,
                                         src,
                                         size,
                                         NULL,
                                         0,
                                         NULL);
    if (ZE_RESULT_SUCCESS != zret) {
        opal_output_verbose(10, opal_accelerator_base_framework.framework_output,
                            "zeCommandListAppendMemoryCopy returned %d", zret);
        return OPAL_ERROR;
    }

    zret = zeCommandListClose(opal_accelerator_ze_commandlist);
    if (ZE_RESULT_SUCCESS != zret) {
        opal_output_verbose(10, opal_accelerator_base_framework.framework_output,
                            "zeCommandListClose returned %d", zret);
        return OPAL_ERROR;
    }

    zret = zeCommandQueueExecuteCommandLists(opal_accelerator_ze_MemcpyStream, 
                                             1, 
                                             &opal_accelerator_ze_commandlist, 
                                             NULL);
    if (ZE_RESULT_SUCCESS != zret) {
        opal_output_verbose(10, opal_accelerator_base_framework.framework_output,
                            "zeCommandQueueExecuteCommandList returned %d", zret);
        return OPAL_ERROR;
    }

    zret = zeCommandQueueSynchronize(opal_accelerator_ze_MemcpyStream, 
                                     UINT32_MAX);
    if (ZE_RESULT_SUCCESS != zret) {
        opal_output_verbose(10, opal_accelerator_base_framework.framework_output,
                            "zeCommandQueueSynchronize returned %d", zret);
        return OPAL_ERROR;
    }

    zret = zeCommandListReset(opal_accelerator_ze_commandlist);
    if (ZE_RESULT_SUCCESS != zret) {
        opal_output_verbose(10, opal_accelerator_base_framework.framework_output,
                            "zeCommandListReset returned %d", zret);
        return OPAL_ERROR;
    }


    return OPAL_SUCCESS;
}

static int mca_accelerator_ze_memmove(int dest_dev_id, int src_dev_id, void *dest,
					const void *src, size_t size,
                                        opal_accelerator_transfer_type_t type)
{
    /*
     * TODO
     */
    return OPAL_ERR_NOT_IMPLEMENTED;
}

static int mca_accelerator_ze_mem_alloc(int dev_id, void **ptr, size_t size)
{
   int zret;
   size_t mem_alignment;
   ze_device_handle_t hDevice;
   
   ze_device_mem_alloc_desc_t device_desc = {
        .stype = ZE_STRUCTURE_TYPE_DEVICE_MEM_ALLOC_DESC,
        .pNext = NULL,
        .flags = 0,
        .ordinal = 0,   /* We currently support a single memory type */
    };

    if (MCA_ACCELERATOR_NO_DEVICE_ID == dev_id) {
        hDevice = opal_accelerator_ze_devices_handle[0];
    } else {
        hDevice = opal_accelerator_ze_devices_handle[dev_id];
    }

    /* Currently ZE ignores this argument and uses an internal alignment
     * value. However, this behavior can change in the future. */
    mem_alignment = 1;
    zret = zeMemAllocDevice(opal_accelerator_ze_context, 
                           &device_desc, 
                           size, 
                           mem_alignment, 
                           hDevice,
                           ptr);
    ZE_ERR_CHECK(zret);

    return OPAL_SUCCESS;
  fn_fail:
    return OPAL_ERROR;
}

static int mca_accelerator_ze_mem_release(int dev_id, void *ptr)
{
    int zerr;

    zerr = zeMemFree(opal_accelerator_ze_context, ptr);
    ZE_ERR_CHECK(zerr);

    return OPAL_SUCCESS;
  fn_fail:
    return OPAL_ERROR;
}

static int mca_accelerator_ze_get_address_range(int dev_id, const void *ptr, void **base,
						  size_t *size)
{
    int zret;
    void *pBase;
    size_t pSize;

    if (NULL == ptr || NULL == base || NULL == size) {
        return OPAL_ERR_BAD_PARAM;
    }

    zret = zeMemGetAddressRange(opal_accelerator_ze_context,
                                ptr,                             
                                &pBase,
                                &pSize);
    if (ZE_RESULT_SUCCESS != zret) {
        opal_output_verbose(10, opal_accelerator_base_framework.framework_output,
                            "couldn't get address range for pointer %p/%lu", ptr, *size);
        return OPAL_ERROR;
    }

    *size = pSize;
    *base = (char *) pBase;

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
    /*
     * this method does not map to the Zero Level API, just return 0.  
     * This may just work if the runtime is use the ZE_AFFINITY_MASK
     * environment variable to control the visible PV(s) for a given process.
     */

    if (NULL == dev_id) {
        return OPAL_ERR_BAD_PARAM;
    }

    *dev_id = 0;

    return OPAL_SUCCESS;
}

static int mca_accelerator_ze_get_device_pci_attr(int dev_id, opal_accelerator_pci_attr_t *pci_attr)
{                                       
    int zret;
    ze_device_handle_t hDevice;
    ze_pci_ext_properties_t pPciProperties;
    
    if (NULL == pci_attr) {
        return OPAL_ERR_BAD_PARAM;
    }
    
    if (MCA_ACCELERATOR_NO_DEVICE_ID == dev_id) {
        hDevice = opal_accelerator_ze_devices_handle[0];
    } else {
        hDevice = opal_accelerator_ze_devices_handle[dev_id];
    }

    zret = zeDevicePciGetPropertiesExt(hDevice, &pPciProperties);
    if(ZE_RESULT_SUCCESS != zret) {
        opal_output_verbose(10, opal_accelerator_base_framework.framework_output,
                            "error retrieving device PCI attributes");
        return OPAL_ERROR;
    }
    
    pci_attr->domain_id = (uint16_t)pPciProperties.address.domain;
    pci_attr->bus_id = (uint8_t) pPciProperties.address.bus;
    pci_attr->device_id = (uint8_t)pPciProperties.address.device;
    pci_attr->function_id = (uint8_t)pPciProperties.address.function;

    return OPAL_SUCCESS;
}       
            

/*
 * could zeDeviceGetP2PProperties be used instead here?
 */
static int mca_accelerator_ze_device_can_access_peer(int *access, int dev1, int dev2)
{
    int zret;
    ze_bool_t value;
    ze_device_handle_t hDevice;
    ze_device_handle_t hPeerDevice;

    if (NULL == access || dev1 < 0 || dev2 < 0){
        return OPAL_ERR_BAD_PARAM;
    }

    hDevice = opal_accelerator_ze_devices_handle[dev1];
    hPeerDevice = opal_accelerator_ze_devices_handle[dev2];
    
    zret = zeDeviceCanAccessPeer(hDevice,
                                 hPeerDevice,
                                 &value);
    if (ZE_RESULT_SUCCESS != zret) {
        return OPAL_ERROR;
    }

    *access = (value == 1) ? 1 : 0;

    return OPAL_SUCCESS;
}

static int mca_accelerator_ze_get_buffer_id(int dev_id, const void *addr, opal_accelerator_buffer_id_t *buf_id)
{
    int zret;
    ze_memory_allocation_properties_t pMemAllocProperties;
    ze_device_handle_t hDevice;

    if (NULL == buf_id) {
        return OPAL_ERR_BAD_PARAM;
    }

    if (MCA_ACCELERATOR_NO_DEVICE_ID == dev_id) { 
        hDevice = opal_accelerator_ze_devices_handle[0];
    } else {
        hDevice = opal_accelerator_ze_devices_handle[dev_id];
    }

    zret = zeMemGetAllocProperties(opal_accelerator_ze_context,
                                   addr,
                                   &pMemAllocProperties,
                                   &hDevice);
    if (ZE_RESULT_SUCCESS != zret) {
        return OPAL_ERROR;
    }

    *buf_id = pMemAllocProperties.id;
                                   
    return OPAL_SUCCESS;
}
