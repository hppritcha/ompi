/* -*- Mode: C; c-basic-offset:4 ; indent-tabs-mode:nil -*- */
/*
 * Copyright (c) 2004-2007 The Trustees of Indiana University and Indiana
 *                         University Research and Technology
 *                         Corporation.  All rights reserved.
 * Copyright (c) 2004-2022 The University of Tennessee and The University
 *                         of Tennessee Research Foundation.  All rights
 *                         reserved.
 * Copyright (c) 2004-2008 High Performance Computing Center Stuttgart,
 *                         University of Stuttgart.  All rights reserved.
 * Copyright (c) 2004-2005 The Regents of the University of California.
 *                         All rights reserved.
 * Copyright (c) 2007      Cisco Systems, Inc.  All rights reserved.
 * Copyright (c) 2012-2017 Los Alamos National Security, LLC.  All rights
 *                         reserved.
 * Copyright (c) 2014-2023 Research Organization for Information Science
 *                         and Technology (RIST).  All rights reserved.
 * Copyright (c) 2017      IBM Corporation.  All rights reserved.
 * $COPYRIGHT$
 *
 * Additional copyrights may follow
 *
 * $HEADER$
 */

#include "ompi_config.h"
#include <stdio.h>

#include "ompi/mpi/c/bindings.h"
#include "ompi/runtime/params.h"
#include "ompi/communicator/communicator.h"
#include "ompi/errhandler/errhandler.h"
#include "ompi/datatype/ompi_datatype.h"
#include "ompi/mca/coll/base/coll_base_util.h"
#include "ompi/memchecker.h"
#include "ompi/mca/topo/topo.h"
#include "ompi/mca/topo/base/base.h"
#include "ompi/runtime/ompi_spc.h"

#if OMPI_BUILD_MPI_PROFILING
#if OPAL_HAVE_WEAK_SYMBOLS
#pragma weak MPI_Neighbor_alltoallw_init = PMPI_Neighbor_alltoallw_init
#endif
#define MPI_Neighbor_alltoallw_init PMPI_Neighbor_alltoallw_init
#endif

static const char FUNC_NAME[] = "MPI_Neighbor_alltoallw_init";


int MPI_Neighbor_alltoallw_init(const void *sendbuf, const int sendcounts[], const MPI_Aint sdispls[],
                                const MPI_Datatype sendtypes[], void *recvbuf, const int recvcounts[],
                                const MPI_Aint rdispls[], const MPI_Datatype recvtypes[], MPI_Comm comm,
                                MPI_Info info, MPI_Request *request)
{
    int i, err;
    int indegree, outdegree;
    OMPI_TEMP_ARRAYS_DECL(sendcounts, sdispls);
    OMPI_TEMP_ARRAYS_DECL(recvcounts, rdispls);

    SPC_RECORD(OMPI_SPC_NEIGHBOR_ALLTOALLW_INIT, 1);

    mca_topo_base_neighbor_count (comm, &indegree, &outdegree);
    MEMCHECKER(
        ptrdiff_t recv_ext;
        ptrdiff_t send_ext;

        memchecker_comm(comm);

        if (MPI_IN_PLACE != sendbuf) {
            for ( i = 0; i < outdegree; i++ ) {
                memchecker_datatype(sendtypes[i]);

                ompi_datatype_type_extent(sendtypes[i], &send_ext);

                memchecker_call(&opal_memchecker_base_isdefined,
                                (char *)(sendbuf)+sdispls[i]*send_ext,
                                sendcounts[i], sendtypes[i]);
            }
        }
        for ( i = 0; i < indegree; i++ ) {
            memchecker_datatype(recvtypes[i]);

            ompi_datatype_type_extent(recvtypes[i], &recv_ext);

            memchecker_call(&opal_memchecker_base_isaddressable,
                            (char *)(recvbuf)+sdispls[i]*recv_ext,
                            recvcounts[i], recvtypes[i]);
        }
    );

    if (MPI_PARAM_CHECK) {

        /* Unrooted operation -- same checks for all ranks */

        err = MPI_SUCCESS;
        OMPI_ERR_INIT_FINALIZE(FUNC_NAME);
        if (ompi_comm_invalid(comm) || OMPI_COMM_IS_INTER(comm)) {
            return OMPI_ERRHANDLER_NOHANDLE_INVOKE(MPI_ERR_COMM,
                                          FUNC_NAME);
        } else if (! OMPI_COMM_IS_TOPO(comm)) {
            return OMPI_ERRHANDLER_NOHANDLE_INVOKE(MPI_ERR_TOPOLOGY,
                                          FUNC_NAME);
        }

        err = mca_topo_base_neighbor_count (comm, &indegree, &outdegree);
        OMPI_ERRHANDLER_CHECK(err, comm, err, FUNC_NAME);
        if (((0 < outdegree) && ((NULL == sendcounts) || (NULL == sdispls) || (NULL == sendtypes))) ||
            ((0 < indegree) && ((NULL == recvcounts) || (NULL == rdispls) || (NULL == recvtypes))) ||
            MPI_IN_PLACE == sendbuf || MPI_IN_PLACE == recvbuf) {
            return OMPI_ERRHANDLER_INVOKE(comm, MPI_ERR_ARG, FUNC_NAME);
        }
        for (i = 0; i < outdegree; ++i) {
            OMPI_CHECK_DATATYPE_FOR_SEND(err, sendtypes[i], sendcounts[i]);
            OMPI_ERRHANDLER_CHECK(err, comm, err, FUNC_NAME);
        }
        for (i = 0; i < indegree; ++i) {
            OMPI_CHECK_DATATYPE_FOR_RECV(err, recvtypes[i], recvcounts[i]);
            OMPI_ERRHANDLER_CHECK(err, comm, err, FUNC_NAME);
        }

        if( OMPI_COMM_IS_CART(comm) ) {
            const mca_topo_base_comm_cart_2_2_0_t *cart = comm->c_topo->mtc.cart;
            if( 0 > cart->ndims ) {
                return OMPI_ERRHANDLER_INVOKE(comm, MPI_ERR_ARG, FUNC_NAME);
            }
        }
        else if( OMPI_COMM_IS_GRAPH(comm) ) {
            int degree;
            mca_topo_base_graph_neighbors_count(comm, ompi_comm_rank(comm), &degree);
            if( 0 > degree ) {
                return OMPI_ERRHANDLER_INVOKE(comm, MPI_ERR_ARG, FUNC_NAME);
            }
        }
        else if( OMPI_COMM_IS_DIST_GRAPH(comm) ) {
            const mca_topo_base_comm_dist_graph_2_2_0_t *dist_graph = comm->c_topo->mtc.dist_graph;
            indegree  = dist_graph->indegree;
            outdegree = dist_graph->outdegree;
            if( indegree <  0 || outdegree <  0 ) {
                return OMPI_ERRHANDLER_INVOKE(comm, MPI_ERR_ARG, FUNC_NAME);
            }
        }
    }

    OMPI_TEMP_ARRAYS_PREPARE(sendcounts, sdispls, i, outdegree);
    OMPI_TEMP_ARRAYS_PREPARE(recvcounts, rdispls, i, indegree);
    /* Invoke the coll component to perform the back-end operation */
    err = comm->c_coll->coll_neighbor_alltoallw_init(sendbuf, OMPI_TEMP_ARRAY_NAME_CONVERT(sendcounts),
                                                     OMPI_TEMP_ARRAY_NAME_CONVERT(sdispls), sendtypes,
                                                     recvbuf, OMPI_TEMP_ARRAY_NAME_CONVERT(recvcounts),
                                                     OMPI_TEMP_ARRAY_NAME_CONVERT(rdispls), recvtypes,
                                                     comm, info, request,
                                                     comm->c_coll->coll_neighbor_alltoallw_init_module);
    OMPI_TEMP_ARRAYS_CLEANUP(sendcounts, sdispls);
    OMPI_TEMP_ARRAYS_CLEANUP(recvcounts, rdispls);
    if (OPAL_LIKELY(OMPI_SUCCESS == err)) {
        ompi_coll_base_retain_datatypes_w(*request, sendtypes, recvtypes, true);
    }
    OMPI_ERRHANDLER_RETURN(err, comm, err, FUNC_NAME);
}

