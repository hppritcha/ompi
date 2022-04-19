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
 * Copyright (c) 2009-2012 Cisco Systems, Inc.  All rights reserved.
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

static const char FUNC_NAME[] = "MPI_Reduce_local";

void ompi_reduce_local_ts(CFI_cdesc_t *x1, CFI_cdesc_t *x2, MPI_Fint *count,
                          MPI_Fint *datatype, MPI_Fint *op, MPI_Fint *ierr)
{
    int c_ierr;
    MPI_Datatype c_type;
    MPI_Op c_op;
    char *inbuf = x1->base_addr, *inoutbuf = x2->base_addr;

    OMPI_CFI_CHECK_CONTIGUOUS(x1, c_ierr);
    if (MPI_SUCCESS != c_ierr) {
        if (NULL != ierr) *ierr = OMPI_INT_2_FINT(c_ierr);
        OMPI_ERRHANDLER_INVOKE(MPI_COMM_SELF, c_ierr, FUNC_NAME)
        return;
    }
    OMPI_CFI_CHECK_CONTIGUOUS(x2, c_ierr);
    if (MPI_SUCCESS != c_ierr) {
        if (NULL != ierr) *ierr = OMPI_INT_2_FINT(c_ierr);
        OMPI_ERRHANDLER_INVOKE(MPI_COMM_SELF, c_ierr, FUNC_NAME)
        return;
    }

    c_type = PMPI_Type_f2c(*datatype);
    c_op = PMPI_Op_f2c(*op);

    inbuf = (char *) OMPI_F2C_BOTTOM(inbuf);
    inoutbuf = (char *) OMPI_F2C_BOTTOM(inoutbuf);

    c_ierr = PMPI_Reduce_local(inbuf, inoutbuf,
                              OMPI_FINT_2_INT(*count),
                              c_type, c_op);
   if (NULL != ierr) *ierr = OMPI_INT_2_FINT(c_ierr);
}