/*
 * $HEADER$
 */
/**
 * @file
 */
#ifndef MCA_PML_BASE_SEND_REQUEST_H
#define MCA_PML_BASE_SEND_REQUEST_H

#include "ompi_config.h"
#include "datatype/datatype.h"
#include "mca/pml/base/pml_base_request.h"

extern ompi_class_t mca_pml_base_send_request_t_class;


/**
 * Base type for send requests 
 */
struct mca_pml_base_send_request_t {
    mca_pml_base_request_t req_base;         /** base request type - common data structure for use by wait/test */
    size_t req_offset;                       /**< number of bytes that have already been assigned to a fragment */
    size_t req_bytes_packed;                 /**< packed size of a message given the datatype and count */
    size_t req_bytes_sent;                   /**< number of bytes that have been sent */
    mca_pml_base_send_mode_t req_send_mode;  /**< type of send */
    struct mca_ptl_base_module_t* req_ptl;   /**< PTL that is selected for first fragment */
    struct mca_ptl_base_peer_t* req_peer;    /**< PTL peer instance that will be used for first fragment */
    ompi_ptr_t req_peer_match;               /**< matched receive at peer */
    ompi_ptr_t req_peer_addr;                /**< peers remote buffer address */
    size_t req_peer_size;                    /**< size of peers remote buffer */
    ompi_convertor_t req_convertor;          /**< convertor that describes this datatype */
};
typedef struct mca_pml_base_send_request_t mca_pml_base_send_request_t;



/**
 * Initialize a send request with call parameters.
 *
 * @param request (IN)     Send request
 * @param addr (IN)        User buffer
 * @param count (IN)       Number of elements of indicated datatype.
 * @param datatype (IN)    User defined datatype
 * @param peer (IN)        Destination rank
 * @param tag (IN)         User defined tag
 * @param comm (IN)        Communicator
 * @param mode (IN)        Send mode (STANDARD,BUFFERED,SYNCHRONOUS,READY)
 * @param persistent (IN)  Is request persistent.
 */
#define MCA_PML_BASE_SEND_REQUEST_INIT(                                             \
    request,                                                                        \
    addr,                                                                           \
    count,                                                                          \
    datatype,                                                                       \
    peer,                                                                           \
    tag,                                                                            \
    comm,                                                                           \
    mode,                                                                           \
    persistent)                                                                     \
{                                                                                   \
    /* increment reference count on communicator */                                 \
    OBJ_RETAIN(comm);                                                               \
                                                                                    \
    OMPI_REQUEST_INIT(&(request)->req_base.req_ompi);                               \
    request->req_offset = 0;                                                        \
    request->req_bytes_sent = 0;                                                    \
    request->req_send_mode = mode;                                                  \
    request->req_peer_match.lval = 0;                                               \
    request->req_peer_addr.lval = 0;                                                \
    request->req_peer_size = 0;                                                     \
    request->req_base.req_addr = addr;                                              \
    request->req_base.req_count = count;                                            \
    request->req_base.req_datatype = datatype;                                      \
    request->req_base.req_peer = peer;                                              \
    request->req_base.req_tag = tag;                                                \
    request->req_base.req_comm = comm;                                              \
    request->req_base.req_proc = ompi_comm_peer_lookup(comm,peer);                  \
    request->req_base.req_persistent = persistent;                                  \
    request->req_base.req_mpi_done = false;                                         \
    request->req_base.req_pml_done = false;                                         \
    request->req_base.req_free_called = false;                                      \
                                                                                    \
    /* initialize datatype convertor for this request */                            \
    if(count > 0) {                                                                 \
        int packed_size;                                                            \
        ompi_convertor_copy(                                                        \
            request->req_base.req_proc->proc_convertor,                             \
            &request->req_convertor);                                               \
        ompi_convertor_init_for_send(                                               \
            &request->req_convertor,                                                \
            0,                                                                      \
            request->req_base.req_datatype,                                         \
            request->req_base.req_count,                                            \
            request->req_base.req_addr,                                             \
            0);                                                                     \
        ompi_convertor_get_packed_size(&request->req_convertor, &packed_size);      \
        request->req_bytes_packed = packed_size;                                    \
    } else {                                                                        \
        request->req_bytes_packed = 0;                                              \
    }                                                                               \
}


/**
 * Test to check if an acknowledgment has been received, with the match.
 *
 * @param  request (IN)  Send request.
 * return                TRUE if an ack/match has been received from peer.
 */
static inline bool mca_pml_base_send_request_matched(
    mca_pml_base_send_request_t* request)
{
    return (NULL != request->req_peer_match.pval);
}

#endif

