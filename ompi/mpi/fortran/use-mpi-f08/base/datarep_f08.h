/*
 * Copyright (c) 2004-2007 The Trustees of Indiana University and Indiana
 *                         University Research and Technology
 *                         Corporation.  All rights reserved.
 * Copyright (c) 2004-2005 The University of Tennessee and The University
 *                         of Tennessee Research Foundation.  All rights
 *                         reserved.
 * Copyright (c) 2004-2005 High Performance Computing Center Stuttgart,
 *                         University of Stuttgart.  All rights reserved.
 * Copyright (c) 2004-2005 The Regents of the University of California.
 *                         All rights reserved.
 * Copyright (c) 2007-2012 Cisco Systems, Inc.  All rights reserved.
 * Copyright (c) 2015-2017 Research Organization for Information Science
 *                         and Technology (RIST). All rights reserved.
 * Copyright (c) 2017      IBM Corporation. All rights reserved.
 * Copyright (c) 2026      Triad National Security, LLC. All rights
 *                         reserved.
 * $COPYRIGHT$
 *
 * Additional copyrights may follow
 *
 * $HEADER$
 * SPDX-License-Identifier: BSD-3-Clause-Open-MPI
 */

/*
 * Support for MPI_Register_datarep in the mpi_f08 bindings.
 *
 * The C MPI_Register_datarep needs C callbacks, but the ones passed to
 * the Fortran binding are Fortran procedures, which expect Fortran
 * argument passing conventions.  So, as in the mpif-h binding, the
 * generated wrapper registers C intercept functions, with an intercept
 * object as their extra_state; when the datarep is used, the intercepts
 * translate the arguments and call the Fortran procedures.
 */

#ifndef OMPI_FORTRAN_USE_MPI_F08_BASE_DATAREP_F08_H
#define OMPI_FORTRAN_USE_MPI_F08_BASE_DATAREP_F08_H

#include "ompi_config.h"

#include "mpi.h"
#include "opal/class/opal_list.h"

BEGIN_C_DECLS

/* The mpi_f08 MPI_Datarep_conversion_function, as called from C */
typedef void (ompi_f08_datarep_conversion_fn_t)
    (void *userbuf, MPI_Fint *datatype, MPI_Fint *count, void *filebuf,
     MPI_Offset *position, MPI_Aint *extra_state, MPI_Fint *ierror);

/* The mpi_f08 MPI_Datarep_conversion_function_c, as called from C */
typedef void (ompi_f08_datarep_conversion_c_fn_t)
    (void *userbuf, MPI_Fint *datatype, MPI_Count *count, void *filebuf,
     MPI_Offset *position, MPI_Aint *extra_state, MPI_Fint *ierror);

/* The mpi_f08 MPI_Datarep_extent_function, as called from C */
typedef void (ompi_f08_datarep_extent_fn_t)
    (MPI_Fint *datatype, MPI_Aint *extent, MPI_Aint *extra_state,
     MPI_Fint *ierror);

/* The extra_state of the intercepts.  It is an opal_list_item_t so that
   it can be kept on ompi_registered_datareps and freed during
   MPI_FINALIZE.  read_fn and write_fn are set by MPI_Register_datarep,
   read_fn_c and write_fn_c by MPI_Register_datarep_c.  extra_state is a
   copy of the user's value: the Fortran callbacks take it by reference,
   and the user's variable need not outlive the registration call. */
typedef struct ompi_f08_datarep_intercept_t {
    opal_list_item_t base;
    ompi_f08_datarep_conversion_fn_t *read_fn;
    ompi_f08_datarep_conversion_fn_t *write_fn;
    ompi_f08_datarep_conversion_c_fn_t *read_fn_c;
    ompi_f08_datarep_conversion_c_fn_t *write_fn_c;
    ompi_f08_datarep_extent_fn_t *extent_fn;
    MPI_Aint extra_state;
} ompi_f08_datarep_intercept_t;

OBJ_CLASS_DECLARATION(ompi_f08_datarep_intercept_t);

/* Create an intercept object and put it on ompi_registered_datareps.
   Returns NULL if out of memory. */
ompi_f08_datarep_intercept_t *ompi_f08_datarep_intercept_create(void);

/* The C intercepts, registered with PMPI_Register_datarep */
int ompi_f08_datarep_read_intercept(void *userbuf, MPI_Datatype type,
                                    int count, void *filebuf,
                                    MPI_Offset position, void *extra_state);
int ompi_f08_datarep_write_intercept(void *userbuf, MPI_Datatype type,
                                     int count, void *filebuf,
                                     MPI_Offset position, void *extra_state);
int ompi_f08_datarep_read_intercept_c(void *userbuf, MPI_Datatype type,
                                      MPI_Count count, void *filebuf,
                                      MPI_Offset position, void *extra_state);
int ompi_f08_datarep_write_intercept_c(void *userbuf, MPI_Datatype type,
                                       MPI_Count count, void *filebuf,
                                       MPI_Offset position, void *extra_state);
int ompi_f08_datarep_extent_intercept(MPI_Datatype type, MPI_Aint *file_extent,
                                      void *extra_state);

END_C_DECLS

#endif /* OMPI_FORTRAN_USE_MPI_F08_BASE_DATAREP_F08_H */
