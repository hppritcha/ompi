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
 * Copyright (c) 2012      Oracle and/or its affiliates.  All rights reserved.
 * Copyright (c) 2015      Research Organization for Information Science
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
#include "ompi/mpi/fortran/mpif-h/status-conversion.h"
#include "ompi/mpi/fortran/base/constants.h"

static const char FUNC_NAME[] = "MPI_Recv";

void ompi_recv_ts(CFI_cdesc_t *x, MPI_Fint *count, MPI_Fint *datatype,
                  MPI_Fint *source, MPI_Fint *tag, MPI_Fint *comm,
                  MPI_Fint *status, MPI_Fint *ierr)
{
    OMPI_FORTRAN_STATUS_DECLARATION(c_status,c_status2)
    MPI_Comm c_comm = PMPI_Comm_f2c(*comm);
    MPI_Datatype c_datatype, c_type = PMPI_Type_f2c(*datatype);
    int c_ierr;
    void *buf = x->base_addr;
    int c_count = OMPI_FINT_2_INT(*count);

    OMPI_CFI_2_C(x, c_count, c_type, c_datatype, c_ierr);
    if (MPI_SUCCESS != c_ierr) {
        if (NULL != ierr) *ierr = OMPI_INT_2_FINT(c_ierr);
        OMPI_ERRHANDLER_INVOKE(c_comm, c_ierr, FUNC_NAME);
        return;
    }

    OMPI_FORTRAN_STATUS_SET_POINTER(c_status,c_status2,status)

    /* Call the C function */
    c_ierr = PMPI_Recv(OMPI_F2C_BOTTOM(buf), c_count,
                      c_datatype, OMPI_FINT_2_INT(*source),
                      OMPI_FINT_2_INT(*tag), c_comm,
                      c_status);

    if (c_datatype != c_type) {
        ompi_datatype_destroy(&c_datatype);
    }
    if (NULL != ierr) *ierr = OMPI_INT_2_FINT(c_ierr);

    OMPI_FORTRAN_STATUS_RETURN(c_status,c_status2,status,c_ierr)
}