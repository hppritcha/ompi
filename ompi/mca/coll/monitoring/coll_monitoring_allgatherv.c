/*
 * Copyright (c) 2016-2018 Inria. All rights reserved.
 * Copyright (c) 2019      Research Organization for Information Science
 *                         and Technology (RIST).  All rights reserved.
 * $COPYRIGHT$
 *
 * Additional copyrights may follow
 *
 * $HEADER$
 */

#include "ompi_config.h"
#include "ompi/request/request.h"
#include "ompi/datatype/ompi_datatype.h"
#include "ompi/communicator/communicator.h"
#include "coll_monitoring.h"

int mca_coll_monitoring_allgatherv(const void *sbuf, size_t scount,
                                   struct ompi_datatype_t *sdtype,
                                   void * rbuf, ompi_count_array *rcounts, ompi_disp_array *disps,
                                   struct ompi_datatype_t *rdtype,
                                   struct ompi_communicator_t *comm,
                                   mca_coll_base_module_t *module)
{
    mca_coll_monitoring_module_t*monitoring_module = (mca_coll_monitoring_module_t*) module;
    size_t type_size, data_size;
    const int comm_size = ompi_comm_size(comm);
    const int my_rank = ompi_comm_rank(comm);
    int i, rank;
    ompi_datatype_type_size(sdtype, &type_size);
    data_size = scount * type_size;
    mca_common_monitoring_coll_a2a(data_size * (comm_size - 1), monitoring_module->data);
    for( i = 0; i < comm_size; ++i ) {
        if( my_rank == i ) continue; /* No communication for self */
        /**
         * If this fails the destination is not part of my MPI_COM_WORLD
         * Lookup its name in the rank hashtable to get its MPI_COMM_WORLD rank
         */
        if( OPAL_SUCCESS == mca_common_monitoring_get_world_rank(i, comm->c_remote_group, &rank) ) {
            mca_common_monitoring_record_coll(rank, data_size);
        }
    }
    return monitoring_module->real.coll_allgatherv(sbuf, scount, sdtype, rbuf, rcounts, disps, rdtype, comm, monitoring_module->real.coll_allgatherv_module);
}

int mca_coll_monitoring_iallgatherv(const void *sbuf, size_t scount,
                                    struct ompi_datatype_t *sdtype,
                                    void * rbuf, ompi_count_array *rcounts, ompi_disp_array *disps,
                                    struct ompi_datatype_t *rdtype,
                                    struct ompi_communicator_t *comm,
                                    ompi_request_t ** request,
                                    mca_coll_base_module_t *module)
{
    mca_coll_monitoring_module_t*monitoring_module = (mca_coll_monitoring_module_t*) module;
    size_t type_size, data_size;
    const int comm_size = ompi_comm_size(comm);
    const int my_rank = ompi_comm_rank(comm);
    int i, rank;
    ompi_datatype_type_size(sdtype, &type_size);
    data_size = scount * type_size;
    mca_common_monitoring_coll_a2a(data_size * (comm_size - 1), monitoring_module->data);
    for( i = 0; i < comm_size; ++i ) {
        if( my_rank == i ) continue; /* No communication for self */
        /**
         * If this fails the destination is not part of my MPI_COM_WORLD
         * Lookup its name in the rank hashtable to get its MPI_COMM_WORLD rank
         */
        if( OPAL_SUCCESS == mca_common_monitoring_get_world_rank(i, comm->c_remote_group, &rank) ) {
            mca_common_monitoring_record_coll(rank, data_size);
        }
    }
    return monitoring_module->real.coll_iallgatherv(sbuf, scount, sdtype, rbuf, rcounts, disps, rdtype, comm, request, monitoring_module->real.coll_iallgatherv_module);
}
