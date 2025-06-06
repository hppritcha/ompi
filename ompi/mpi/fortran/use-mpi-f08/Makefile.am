# -*- makefile.am -*-
#
# Copyright (c) 2006-2019 Cisco Systems, Inc.  All rights reserved.
# Copyright (c) 2012-2013 The University of Tennessee and The University
#                         of Tennessee Research Foundation.  All rights
#                         reserved.
# Copyright (c) 2012-2013 Inria.  All rights reserved.
# Copyright (c) 2013-2018 Los Alamos National Security, LLC. All rights
#                         reserved.
# Copyright (c) 2015-2021 Research Organization for Information Science
#                         and Technology (RIST).  All rights reserved.
# Copyright (c) 2016      IBM Corporation.  All rights reserved.
# Copyright (c) 2017-2018 FUJITSU LIMITED.  All rights reserved.
# Copyright (c) 2019-2022 Triad National Security, LLC. All rights
#                         reserved.
# Copyright (c) 2020      Sandia National Laboratories. All rights reserved.
# Copyright (c) 2022      IBM Corporation.  All rights reserved.
# Copyright (c) 2025      Jeffrey M. Squyres.  All rights reserved.
#
# $COPYRIGHT$
#
# Additional copyrights may follow
#
# $HEADER$
#

include $(top_srcdir)/Makefile.ompi-rules

# Note that Automake's Fortran-buidling rules uses CPPFLAGS and
# AM_CPPFLAGS.  This can cause weirdness (e.g.,
# https://github.com/open-mpi/ompi/issues/7253).  Let's just zero
# those out and rely on AM_FCFLAGS.
CPPFLAGS =
AM_CPPFLAGS =

# This Makefile is only relevant if we're building the "use mpi_f08"
# MPI bindings.

# Profiling entry points are generated using a combination of the
# the mod/mpi-f08-rename.h file and the OMPI_BUILD_MPI_PROFILING
# define flag.  This approach is used both for the generated
# F08 entry points like MPI_SEND and ones that are still built
# using *.F90 files like COMM_SET_ERRHANDLER.
#
# When adding a new function, if it involves big count arguments and/or
# involves a user supplied buffer(s), and hence the need to generate
# either assumed rank or assumed shape arrays with possible async
# attributes, the *.c.in method needs to be used. Otherwise a *.F90
# file can be used.   In addition, the mod/mpi-f08-rename.h file
# will need to be updated to include a rename line for the new method.
#
if OMPI_BUILD_FORTRAN_USEMPIF08_BINDINGS

AM_FCFLAGS = -I$(top_srcdir)/ompi/mpi/fortran/use-mpi-f08/mod \
             -I$(top_builddir)/ompi/include \
             -I$(top_srcdir)/ompi/include \
             $(OMPI_FC_MODULE_FLAG)$(top_builddir)/ompi/mpi/fortran/use-mpi \
             $(OMPI_FC_MODULE_FLAG)$(top_builddir)/ompi/mpi/fortran/use-mpi-ignore-tkr \
             $(OMPI_FC_MODULE_FLAG)mod \
             $(OMPI_FC_MODULE_FLAG)bindings \
             -I$(top_srcdir) -I$(top_builddir) $(FCFLAGS_f90)

MOSTLYCLEANFILES = *.mod

CLEANFILES += *.i90

lib_LTLIBRARIES = lib@OMPI_LIBMPI_NAME@_usempif08.la
noinst_LTLIBRARIES = lib@OMPI_LIBMPI_NAME@_usempif08_profile.la

module_sentinel_files = \
        mod/libforce_usempif08_internal_modules_to_be_built.la \
        bindings/libforce_usempif08_internal_bindings_to_be_built.la

mpi-f08.lo: $(module_sentinel_files)
mpi-f08.lo: mpi-f08.F90
mpi-f08.lo: sizeof_f08.h

#
# *sizeof_f08.* are generated based on some results from
# configure tests.
#

sizeof_py=$(top_srcdir)/ompi/mpi/fortran/base/gen-mpi-sizeof.py

sizeof_f08.h: $(top_builddir)/config.status
sizeof_f08.h: $(sizeof_py)
sizeof_f08.h:
	$(OMPI_V_GEN) $(PYTHON) $(sizeof_py) \
	    --header=$@ --ierror=optional \
	    --maxrank=$(OMPI_FORTRAN_MAX_ARRAY_RANK) \
	    --generate=$(OMPI_FORTRAN_BUILD_SIZEOF) \
	    --real2=$(OMPI_HAVE_FORTRAN_REAL2) \
	    --iso_real16=$(OMPI_FORTRAN_HAVE_ISO_FORTRAN_ENV_REAL16) \
	    --real16=$(OMPI_HAVE_FORTRAN_REAL16) \
	    --complex4=$(OMPI_HAVE_FORTRAN_COMPLEX4) \
	    --complex32=$(OMPI_HAVE_FORTRAN_COMPLEX32) \
	    --mpi_version=$(MPI_VERSION) \
	    --request_deprecate=$(OMPI_FORTRAN_HAVE_ATTR_DEPRECATED)

sizeof_f08.f90: $(top_builddir)/config.status
sizeof_f08.f90: $(sizeof_py)
sizeof_f08.f90:
	$(OMPI_V_GEN) $(PYTHON) $(sizeof_py) \
	    --impl=$@ --ierror=optional --mpi \
	    --maxrank=$(OMPI_FORTRAN_MAX_ARRAY_RANK) \
	    --generate=$(OMPI_FORTRAN_BUILD_SIZEOF) \
	    --real2=$(OMPI_HAVE_FORTRAN_REAL2) \
	    --iso_real16=$(OMPI_FORTRAN_HAVE_ISO_FORTRAN_ENV_REAL16) \
	    --real16=$(OMPI_HAVE_FORTRAN_REAL16) \
	    --complex4=$(OMPI_HAVE_FORTRAN_COMPLEX4) \
	    --complex32=$(OMPI_HAVE_FORTRAN_COMPLEX32)

psizeof_f08.f90: $(top_builddir)/config.status
psizeof_f08.f90: $(sizeof_py)
psizeof_f08.f90:
	$(OMPI_V_GEN) $(PYTHON) $(sizeof_py) \
	    --impl=$@ --ierror=optional --pmpi \
	    --maxrank=$(OMPI_FORTRAN_MAX_ARRAY_RANK) \
	    --generate=$(OMPI_FORTRAN_BUILD_SIZEOF) \
	    --real2=$(OMPI_HAVE_FORTRAN_REAL2) \
	    --iso_real16=$(OMPI_FORTRAN_HAVE_ISO_FORTRAN_ENV_REAL16) \
	    --real16=$(OMPI_HAVE_FORTRAN_REAL16) \
	    --complex4=$(OMPI_HAVE_FORTRAN_COMPLEX4) \
	    --complex32=$(OMPI_HAVE_FORTRAN_COMPLEX32)

CLEANFILES += sizeof_f08.h sizeof_f08.f90 psizeof_f08.f90

mpi_api_files = \
        abort_f08.F90 \
        add_error_class_f08.F90 \
        add_error_code_f08.F90 \
        add_error_string_f08.F90 \
        aint_add_f08.F90 \
        aint_diff_f08.F90 \
        alloc_mem_f08.F90 \
        barrier_f08.F90 \
        barrier_init_f08.F90 \
        cancel_f08.F90 \
        cart_coords_f08.F90 \
        cart_create_f08.F90 \
        cartdim_get_f08.F90 \
        cart_get_f08.F90 \
        cart_map_f08.F90 \
        cart_rank_f08.F90 \
        cart_shift_f08.F90 \
        cart_sub_f08.F90 \
        close_port_f08.F90 \
        comm_accept_f08.F90 \
        comm_call_errhandler_f08.F90 \
        comm_compare_f08.F90 \
        comm_connect_f08.F90 \
        comm_create_errhandler_f08.F90 \
        comm_create_f08.F90 \
        comm_create_from_group_f08.F90 \
        comm_create_group_f08.F90 \
        comm_create_keyval_f08.F90 \
        comm_delete_attr_f08.F90 \
        comm_disconnect_f08.F90 \
        comm_dup_f08.F90 \
        comm_dup_with_info_f08.F90 \
        comm_idup_f08.F90 \
        comm_idup_with_info_f08.F90 \
        comm_free_f08.F90 \
        comm_free_keyval_f08.F90 \
        comm_get_attr_f08.F90 \
        comm_get_errhandler_f08.F90 \
        comm_get_info_f08.F90 \
        comm_get_name_f08.F90 \
        comm_get_parent_f08.F90 \
        comm_group_f08.F90 \
        comm_join_f08.F90 \
        comm_rank_f08.F90 \
        comm_remote_group_f08.F90 \
        comm_remote_size_f08.F90 \
        comm_set_attr_f08.F90 \
        comm_set_errhandler_f08.F90 \
        comm_set_info_f08.F90 \
        comm_set_name_f08.F90 \
        comm_size_f08.F90 \
        comm_spawn_f08.F90 \
        comm_spawn_multiple_f08.F90 \
        comm_split_f08.F90 \
        comm_split_type_f08.F90 \
        comm_test_inter_f08.F90 \
        dist_graph_create_adjacent_f08.F90 \
        dist_graph_create_f08.F90 \
        dist_graph_neighbors_count_f08.F90 \
        dist_graph_neighbors_f08.F90 \
        dims_create_f08.F90 \
        errhandler_free_f08.F90 \
        error_class_f08.F90 \
        error_string_f08.F90 \
        file_call_errhandler_f08.F90 \
        file_close_f08.F90 \
        file_create_errhandler_f08.F90 \
        file_delete_f08.F90 \
        file_get_amode_f08.F90 \
        file_get_atomicity_f08.F90 \
        file_get_byte_offset_f08.F90 \
        file_get_errhandler_f08.F90 \
        file_get_group_f08.F90 \
        file_get_info_f08.F90 \
        file_get_position_f08.F90 \
        file_get_position_shared_f08.F90 \
        file_get_size_f08.F90 \
        file_get_type_extent_f08.F90 \
        file_get_view_f08.F90 \
        file_open_f08.F90 \
        file_preallocate_f08.F90 \
        file_seek_f08.F90 \
        file_seek_shared_f08.F90 \
        file_set_atomicity_f08.F90 \
        file_set_errhandler_f08.F90 \
        file_set_info_f08.F90 \
        file_set_size_f08.F90 \
        file_set_view_f08.F90 \
        file_sync_f08.F90 \
        finalized_f08.F90 \
        finalize_f08.F90 \
        get_elements_x_f08.F90 \
        get_library_version_f08.F90 \
        get_processor_name_f08.F90 \
        get_version_f08.F90 \
        graph_create_f08.F90 \
        graphdims_get_f08.F90 \
        graph_get_f08.F90 \
        graph_map_f08.F90 \
        graph_neighbors_count_f08.F90 \
        graph_neighbors_f08.F90 \
        grequest_complete_f08.F90 \
        grequest_start_f08.F90 \
        group_compare_f08.F90 \
        group_difference_f08.F90 \
        group_excl_f08.F90 \
        group_free_f08.F90 \
        group_from_session_pset_f08.F90 \
        group_incl_f08.F90 \
        group_intersection_f08.F90 \
        group_range_excl_f08.F90 \
        group_range_incl_f08.F90 \
        group_rank_f08.F90 \
        group_size_f08.F90 \
        group_translate_ranks_f08.F90 \
        group_union_f08.F90 \
        ibarrier_f08.F90 \
        improbe_f08.F90 \
        info_create_f08.F90 \
        info_create_env_f08.F90 \
        info_delete_f08.F90 \
        info_dup_f08.F90 \
        info_free_f08.F90 \
        info_get_f08.F90 \
        info_get_nkeys_f08.F90 \
        info_get_nthkey_f08.F90 \
        info_get_valuelen_f08.F90 \
        info_get_string_f08.F90 \
        info_set_f08.F90 \
        init_f08.F90 \
        initialized_f08.F90 \
        init_thread_f08.F90 \
        intercomm_create_f08.F90 \
        intercomm_create_from_groups_f08.F90 \
        intercomm_merge_f08.F90 \
        iprobe_f08.F90 \
        is_thread_main_f08.F90 \
        lookup_name_f08.F90 \
        mprobe_f08.F90 \
        op_commutative_f08.F90 \
        op_create_f08.F90 \
        open_port_f08.F90 \
        op_free_f08.F90 \
        parrived_f08.F90 \
        pcontrol_f08.F90 \
        pready_f08.F90 \
        pready_range_f08.F90 \
        pready_list_f08.F90 \
        probe_f08.F90 \
        publish_name_f08.F90 \
        query_thread_f08.F90 \
        register_datarep_f08.F90 \
        request_free_f08.F90 \
        request_get_status_f08.F90 \
        session_call_errhandler_f08.F90\
        session_create_errhandler_f08.F90\
        session_get_errhandler_f08.F90\
	session_get_info_f08.F90 \
	session_get_nth_pset_f08.F90 \
	session_get_num_psets_f08.F90 \
	session_get_pset_info_f08.F90 \
	session_init_f08.F90 \
	session_finalize_f08.F90 \
        session_set_errhandler_f08.F90\
        startall_f08.F90 \
        start_f08.F90 \
        status_f082f_f08.F90 \
        status_f2f08_f08.F90 \
        status_set_cancelled_f08.F90 \
        status_set_elements_x_f08.F90 \
        testall_f08.F90 \
        test_cancelled_f08.F90 \
        test_f08.F90 \
        testsome_f08.F90 \
        topo_test_f08.F90 \
        type_commit_f08.F90 \
        type_create_f90_complex_f08.F90 \
        type_create_f90_integer_f08.F90 \
        type_create_f90_real_f08.F90 \
        type_create_keyval_f08.F90 \
        type_create_resized_f08.F90 \
        type_delete_attr_f08.F90 \
        type_dup_f08.F90 \
        type_free_f08.F90 \
        type_free_keyval_f08.F90 \
        type_get_attr_f08.F90 \
        type_get_contents_f08.F90 \
        type_get_contents_f08_c.F90 \
        type_get_extent_f08.F90 \
        type_get_extent_x_f08.F90 \
        type_get_name_f08.F90 \
        type_get_true_extent_x_f08.F90 \
        type_get_envelope_f08.F90 \
        type_get_envelope_f08_c.F90 \
        type_match_size_f08.F90 \
        type_set_attr_f08.F90 \
        type_set_name_f08.F90 \
        type_size_x_f08.F90 \
        unpublish_name_f08.F90 \
        waitany_f08.F90 \
        wait_f08.F90 \
        waitsome_f08.F90 \
        win_call_errhandler_f08.F90 \
        win_complete_f08.F90 \
        win_create_dynamic_f08.F90 \
        win_create_errhandler_f08.F90 \
        win_create_keyval_f08.F90 \
        win_delete_attr_f08.F90 \
        win_fence_f08.F90 \
        win_flush_f08.F90 \
        win_flush_all_f08.F90 \
        win_flush_local_f08.F90 \
        win_flush_local_all_f08.F90 \
        win_free_f08.F90 \
        win_free_keyval_f08.F90 \
        win_get_attr_f08.F90 \
        win_get_errhandler_f08.F90 \
        win_get_group_f08.F90 \
        win_get_info_f08.F90 \
        win_get_name_f08.F90 \
        win_lock_f08.F90 \
        win_lock_all_f08.F90 \
        win_post_f08.F90 \
        win_set_attr_f08.F90 \
        win_set_errhandler_f08.F90 \
        win_set_info_f08.F90 \
        win_set_name_f08.F90 \
        win_start_f08.F90 \
        win_sync_f08.F90 \
        win_test_f08.F90 \
        win_unlock_f08.F90 \
        win_unlock_all_f08.F90 \
        win_wait_f08.F90 \
        api_f08_generated.F90

lib@OMPI_LIBMPI_NAME@_usempif08_la_SOURCES = \
        $(mpi_api_files) \
        mpi-f08.F90

if BUILD_FORTRAN_SIZEOF
SIZEOF_H = sizeof_f08.h
nodist_lib@OMPI_LIBMPI_NAME@_usempif08_la_SOURCES = \
        sizeof_f08.h \
        sizeof_f08.f90 \
        psizeof_f08.f90
endif

lib@OMPI_LIBMPI_NAME@_usempif08_la_FCFLAGS = \
        $(AM_FCFLAGS) \
        -DOMPI_BUILD_MPI_PROFILING=0

#
# Include the mpi_f08-based MPI extensions in libmpi_usempif08, too.
#
# Also include the one .c file that we need in this library -- because
# we zero out CPPFLAGS and AM_CPPFLAGS in this Makefile.am, we have to
# compile that .c file in a separate directory / Makefile.
#

lib@OMPI_LIBMPI_NAME@_usempif08_la_LIBADD = \
        lib@OMPI_LIBMPI_NAME@_usempif08_profile.la \
        $(OMPI_MPIEXT_USEMPIF08_LIBS) \
        $(top_builddir)/ompi/mpi/fortran/mpif-h/lib@OMPI_LIBMPI_NAME@_mpifh.la \
        $(top_builddir)/ompi/lib@OMPI_LIBMPI_NAME@.la \
        mod/libusempif08_internal_modules.la \
        base/libusempif08_ccode.la

#
# Make sure to build the profile library before this library, since adding it
# to LIBADD doesn't enforce any ordering
#
lib@OMPI_LIBMPI_NAME@_usempif08_la_DEPENDENCIES = \
        $(module_sentinel_files) \
        lib@OMPI_LIBMPI_NAME@_usempif08_profile.la
lib@OMPI_LIBMPI_NAME@_usempif08_la_LDFLAGS = -version-info $(libmpi_usempif08_so_version)

#
# Automake doesn't do Fortran dependency analysis, so must list them
# manually here.  Bummer!
#

mpi_api_lo_files = $(mpi_api_files:.F90=.lo)

$(mpi_api_lo_files): bindings/libforce_usempif08_internal_bindings_to_be_built.la

mpi-f08.lo: $(module_sentinel_files) $(SIZEOF_H)
mpi-f08.F90: $(SIZEOF_H)

#
# Profiling interface
#

lib@OMPI_LIBMPI_NAME@_usempif08_profile_la_SOURCES = \
        $(mpi_api_files)

lib@OMPI_LIBMPI_NAME@_usempif08_profile_la_FCFLAGS = \
        $(AM_FCFLAGS) \
        -DOMPI_BUILD_MPI_PROFILING=1


#
# Generate the Fortran bindings and C wrapper functions for bindings with a
# *.in template.
#

include Makefile.prototype_files
template_files =${prototype_files:%=$(abs_top_srcdir)/ompi/mpi/fortran/use-mpi-f08/%}

if OMPI_FORTRAN_HAVE_TS
gen_ts = --generate-ts-suffix
endif

api_f08_generated.F90: $(template_files)
	$(OMPI_V_GEN) $(PYTHON) $(top_srcdir)/ompi/mpi/bindings/bindings.py \
	    --builddir $(abs_top_builddir) \
	    --srcdir $(abs_top_srcdir) \
	    --output $(abs_builddir)/$@ \
	    fortran \
	    $(gen_ts) \
	    code \
	    --lang fortran \
	    --prototype-files $(template_files)

EXTRA_DIST = $(prototype_files)

# Delete generated file on maintainer-clean
MAINTAINERCLEANFILES = api_f08_generated.F90

###########################################################################

# Install the generated .mod files.  Unfortunately, each F90 compiler
# may generate different filenames, so we have to use a glob.  :-(

install-exec-hook:
	@ for file in `ls *.mod`; do \
	  echo $(INSTALL) $$file $(DESTDIR)$(OMPI_FORTRAN_MODULEDIR); \
	  $(INSTALL) $$file $(DESTDIR)$(OMPI_FORTRAN_MODULEDIR); \
	done

uninstall-local:
	@ for file in `ls *.mod`; do \
	  echo rm -f $(DESTDIR)$(OMPI_FORTRAN_MODULEDIR)/$$file; \
	  rm -f $(DESTDIR)$(OMPI_FORTRAN_MODULEDIR)/$$file; \
	done

endif
