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
    return OPAL_SUCCESS;
}

static int mca_accelerator_ze_create_stream(int dev_id, opal_accelerator_stream_t **stream)
{
    return OPAL_SUCCESS;
}

static void mca_accelerator_ze_stream_destruct(opal_accelerator_ze_stream_t *stream)
{

}

OBJ_CLASS_INSTANCE(
    opal_accelerator_ze_stream_t,
    opal_accelerator_stream_t,
    NULL,
    mca_accelerator_ze_stream_destruct);

static int mca_accelerator_ze_create_event(int dev_id, opal_accelerator_event_t **event)
{
    return OPAL_SUCCESS;
}

static void mca_accelerator_ze_event_destruct(opal_accelerator_ze_event_t *event)
{
}

OBJ_CLASS_INSTANCE(
    opal_accelerator_ze_event_t,
    opal_accelerator_event_t,
    NULL,
    mca_accelerator_ze_event_destruct);

static int mca_accelerator_ze_record_event(int dev_id, opal_accelerator_event_t *event,
                                             opal_accelerator_stream_t *stream)
{
    return OPAL_SUCCESS;
}

static int mca_accelerator_ze_query_event(int dev_id, opal_accelerator_event_t *event)
{
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
