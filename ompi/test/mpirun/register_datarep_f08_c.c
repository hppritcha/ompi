/*
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
 * C half of register_datarep_f08.f90; see there.
 *
 * This file defines PMPI_Register_datarep and PMPI_Register_datarep_c,
 * which take the place of the library's for this program, so they see
 * exactly what the mpi_f08 MPI_Register_datarep{_c} passes to them.
 * They record that, and let the Fortran program check it and call the
 * registered C callbacks the way the MPI-IO layer would.
 */

#include <mpi.h>
#include <string.h>

static char cap_datarep[MPI_MAX_DATAREP_STRING];
static MPI_Datarep_conversion_function *cap_read_fn, *cap_write_fn;
static MPI_Datarep_conversion_function_c *cap_read_fn_c, *cap_write_fn_c;
static MPI_Datarep_extent_function *cap_extent_fn;
static void *cap_extra_state;
static int cap_bigcount;

int PMPI_Register_datarep(const char *datarep,
                          MPI_Datarep_conversion_function *read_conversion_fn,
                          MPI_Datarep_conversion_function *write_conversion_fn,
                          MPI_Datarep_extent_function *dtype_file_extent_fn,
                          void *extra_state)
{
    strncpy(cap_datarep, datarep, sizeof(cap_datarep) - 1);
    cap_read_fn = read_conversion_fn;
    cap_write_fn = write_conversion_fn;
    cap_read_fn_c = cap_write_fn_c = NULL;
    cap_extent_fn = dtype_file_extent_fn;
    cap_extra_state = extra_state;
    cap_bigcount = 0;
    return MPI_SUCCESS;
}

int PMPI_Register_datarep_c(const char *datarep,
                            MPI_Datarep_conversion_function_c *read_conversion_fn,
                            MPI_Datarep_conversion_function_c *write_conversion_fn,
                            MPI_Datarep_extent_function *dtype_file_extent_fn,
                            void *extra_state)
{
    strncpy(cap_datarep, datarep, sizeof(cap_datarep) - 1);
    cap_read_fn = cap_write_fn = NULL;
    cap_read_fn_c = read_conversion_fn;
    cap_write_fn_c = write_conversion_fn;
    cap_extent_fn = dtype_file_extent_fn;
    cap_extra_state = extra_state;
    cap_bigcount = 1;
    return MPI_SUCCESS;
}

/* Was the last registration through PMPI_Register_datarep_c? */
int captured_bigcount(void);
int captured_bigcount(void)
{
    return cap_bigcount;
}

/* Is the captured datarep name the NUL-terminated expected one? */
int captured_datarep_is(const char *expected);
int captured_datarep_is(const char *expected)
{
    return 0 == strcmp(cap_datarep, expected);
}

/* Were the read / write conversion functions NULL (no conversion)? */
int captured_read_fn_is_null(void);
int captured_read_fn_is_null(void)
{
    return NULL == cap_read_fn && NULL == cap_read_fn_c;
}

int captured_write_fn_is_null(void);
int captured_write_fn_is_null(void)
{
    return NULL == cap_write_fn && NULL == cap_write_fn_c;
}

/* Call the captured extent function for MPI_DOUBLE_PRECISION */
int call_extent_fn(MPI_Aint *extent);
int call_extent_fn(MPI_Aint *extent)
{
    return cap_extent_fn(MPI_DOUBLE_PRECISION, extent, cap_extra_state);
}

/* Call the captured read (0) or write (1) conversion function for
   count MPI_INTEGERs */
int call_conversion_fn(int write, int *userbuf, int count, int *filebuf,
                       MPI_Offset position);
int call_conversion_fn(int write, int *userbuf, int count, int *filebuf,
                       MPI_Offset position)
{
    MPI_Datarep_conversion_function *fn = write ? cap_write_fn : cap_read_fn;
    return fn(userbuf, MPI_INTEGER, count, filebuf, position, cap_extra_state);
}

/* The same, for functions registered with PMPI_Register_datarep_c */
int call_conversion_fn_c(int write, int *userbuf, MPI_Count count,
                         int *filebuf, MPI_Offset position);
int call_conversion_fn_c(int write, int *userbuf, MPI_Count count,
                         int *filebuf, MPI_Offset position)
{
    MPI_Datarep_conversion_function_c *fn = write ? cap_write_fn_c : cap_read_fn_c;
    return fn(userbuf, MPI_INTEGER, count, filebuf, position, cap_extra_state);
}
