/*
 * Copyright (c) 2004-2005 The Trustees of Indiana University and Indiana
 *                         University Research and Technology
 *                         Corporation.  All rights reserved.
 * Copyright (c) 2004-2005 The University of Tennessee and The University
 *                         of Tennessee Research Foundation.  All rights
 *                         reserved.
 * Copyright (c) 2004-2005 High Performance Computing Center Stuttgart,
 *                         University of Stuttgart.  All rights reserved.
 * Copyright (c) 2004-2005 The Regents of the University of California.
 *                         All rights reserved.
 * Copyright (c) 2011-2012 Cisco Systems, Inc.  All rights reserved.
 * Copyright (c) 2015-2019 Research Organization for Information Science
 *                         and Technology (RIST). All rights reserved.
 * $COPYRIGHT$
 *
 * Additional copyrights may follow
 *
 * $HEADER$
 */

#include "ompi_config.h"

#include "ompi/communicator/communicator.h"
#include "ompi/errhandler/errhandler.h"
#include "ompi/mpi/fortran/use-mpi-f08/ts/bindings.h"
#include "ompi/mpi/fortran/base/constants.h"

static const char FUNC_NAME[] = "MPI_Isendrecv_replace";

void ompi_isendrecv_replace_ts(CFI_cdesc_t* x, MPI_Fint *count, MPI_Fint *datatype,
                               MPI_Fint *dest, MPI_Fint *sendtag,
                               MPI_Fint *source, MPI_Fint *recvtag,
                               MPI_Fint *comm, MPI_Fint *request, MPI_Fint *ierr)
{
    int c_ierr;
    MPI_Request c_req;
    MPI_Datatype c_datatype, c_type = PMPI_Type_f2c(*datatype);
    MPI_Comm c_comm = PMPI_Comm_f2c (*comm);

    MPI_Status c_status;
    void *buf = x->base_addr;
    int c_count =  OMPI_FINT_2_INT(*count);

    OMPI_CFI_2_C(x, c_count, c_type, c_datatype, c_ierr);
    if (MPI_SUCCESS != c_ierr) {
        if (NULL != ierr) *ierr = OMPI_INT_2_FINT(c_ierr);
        OMPI_ERRHANDLER_INVOKE(c_comm, c_ierr, FUNC_NAME);
        return;
    }

    c_ierr = PMPI_Isendrecv_replace(OMPI_F2C_BOTTOM(buf),
                                    OMPI_FINT_2_INT(*count),
                                    c_datatype,
                                    OMPI_FINT_2_INT(*dest),
                                    OMPI_FINT_2_INT(*sendtag),
                                    OMPI_FINT_2_INT(*source),
                                    OMPI_FINT_2_INT(*recvtag),
                                   c_comm, &c_req);
    if (c_datatype != c_type) {
        ompi_datatype_destroy(&c_datatype);
    }
    if (NULL != ierr) *ierr = OMPI_INT_2_FINT(c_ierr);

    if (MPI_SUCCESS == c_ierr) {
       *request = PMPI_Request_c2f(c_req);
    }
}
