/* -*- Mode: C; c-basic-offset:4 ; indent-tabs-mode:nil -*- */
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
 * Copyright (c) 2007-2016 Los Alamos National Security, LLC.  All rights
 *                         reserved.
 * Copyright (c) 2015      Research Organization for Information Science
 *                         and Technology (RIST). All rights reserved.
 * Copyright (c) 2019      Sandia National Laboratories.  All rights reserved.
 *
 * $COPYRIGHT$
 *
 * Additional copyrights may follow
 *
 * $HEADER$
 */

#include "opal_config.h"

#include "opal/mca/threads/mutex.h"

/*
 * Wait and see if some upper layer wants to use threads, if support
 * exists.
 */
bool opal_uses_threads = false;

static void opal_mutex_construct(opal_mutex_t *m)
{
}

static void opal_mutex_destruct(opal_mutex_t *m)
{
}

OBJ_CLASS_INSTANCE(opal_mutex_t,
                   opal_object_t,
                   opal_mutex_construct,
                   opal_mutex_destruct);

static void opal_recursive_mutex_construct(opal_recursive_mutex_t *m)
{
}

OBJ_CLASS_INSTANCE(opal_recursive_mutex_t,
                   opal_object_t,
                   opal_recursive_mutex_construct,
                   opal_mutex_destruct);
