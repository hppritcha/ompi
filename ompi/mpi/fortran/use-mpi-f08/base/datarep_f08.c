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

#include "ompi_config.h"

#include "ompi/mpi/fortran/base/fint_2_int.h"
#include "ompi/mpi/fortran/use-mpi-f08/base/datarep_f08.h"
#include "ompi/runtime/mpiruntime.h"

static void intercept_constructor(ompi_f08_datarep_intercept_t *obj)
{
    obj->read_fn = NULL;
    obj->write_fn = NULL;
    obj->read_fn_c = NULL;
    obj->write_fn_c = NULL;
    obj->extent_fn = NULL;
    obj->extra_state = 0;
}

OBJ_CLASS_INSTANCE(ompi_f08_datarep_intercept_t,
                   opal_list_item_t,
                   intercept_constructor, NULL);

ompi_f08_datarep_intercept_t *ompi_f08_datarep_intercept_create(void)
{
    ompi_f08_datarep_intercept_t *intercept;

    intercept = OBJ_NEW(ompi_f08_datarep_intercept_t);
    if (NULL != intercept) {
        /* There is no way to deregister a datarep, so the intercept is
           never freed by the user's actions.  Keep it on a global list
           so that it is freed during MPI_FINALIZE (and memory-tracking
           debuggers do not report it as a leak). */
        opal_list_append(&ompi_registered_datareps, &intercept->base);
    }
    return intercept;
}

/*
 * C->Fortran intercept for the read conversion.
 */
int ompi_f08_datarep_read_intercept(void *userbuf, MPI_Datatype type,
                                    int count, void *filebuf,
                                    MPI_Offset position, void *extra_state)
{
    ompi_f08_datarep_intercept_t *intercept =
        (ompi_f08_datarep_intercept_t *) extra_state;
    MPI_Fint ierr, f_type = PMPI_Type_c2f(type);
    MPI_Fint f_count = OMPI_INT_2_FINT(count);

    intercept->read_fn(userbuf, &f_type, &f_count, filebuf, &position,
                       &intercept->extra_state, &ierr);
    return OMPI_FINT_2_INT(ierr);
}

/*
 * C->Fortran intercept for the write conversion.
 */
int ompi_f08_datarep_write_intercept(void *userbuf, MPI_Datatype type,
                                     int count, void *filebuf,
                                     MPI_Offset position, void *extra_state)
{
    ompi_f08_datarep_intercept_t *intercept =
        (ompi_f08_datarep_intercept_t *) extra_state;
    MPI_Fint ierr, f_type = PMPI_Type_c2f(type);
    MPI_Fint f_count = OMPI_INT_2_FINT(count);

    intercept->write_fn(userbuf, &f_type, &f_count, filebuf, &position,
                        &intercept->extra_state, &ierr);
    return OMPI_FINT_2_INT(ierr);
}

/*
 * C->Fortran intercept for the read conversion of MPI_Register_datarep_c.
 */
int ompi_f08_datarep_read_intercept_c(void *userbuf, MPI_Datatype type,
                                      MPI_Count count, void *filebuf,
                                      MPI_Offset position, void *extra_state)
{
    ompi_f08_datarep_intercept_t *intercept =
        (ompi_f08_datarep_intercept_t *) extra_state;
    MPI_Fint ierr, f_type = PMPI_Type_c2f(type);

    intercept->read_fn_c(userbuf, &f_type, &count, filebuf, &position,
                         &intercept->extra_state, &ierr);
    return OMPI_FINT_2_INT(ierr);
}

/*
 * C->Fortran intercept for the write conversion of MPI_Register_datarep_c.
 */
int ompi_f08_datarep_write_intercept_c(void *userbuf, MPI_Datatype type,
                                       MPI_Count count, void *filebuf,
                                       MPI_Offset position, void *extra_state)
{
    ompi_f08_datarep_intercept_t *intercept =
        (ompi_f08_datarep_intercept_t *) extra_state;
    MPI_Fint ierr, f_type = PMPI_Type_c2f(type);

    intercept->write_fn_c(userbuf, &f_type, &count, filebuf, &position,
                          &intercept->extra_state, &ierr);
    return OMPI_FINT_2_INT(ierr);
}

/*
 * C->Fortran intercept for the extent calculation.
 */
int ompi_f08_datarep_extent_intercept(MPI_Datatype type, MPI_Aint *file_extent,
                                      void *extra_state)
{
    ompi_f08_datarep_intercept_t *intercept =
        (ompi_f08_datarep_intercept_t *) extra_state;
    MPI_Fint ierr, f_type = PMPI_Type_c2f(type);

    intercept->extent_fn(&f_type, file_extent, &intercept->extra_state, &ierr);
    return OMPI_FINT_2_INT(ierr);
}
