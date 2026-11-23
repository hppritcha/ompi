# -*- makefile.am -*-
#
# Copyright (c) 2006-2019 Cisco Systems, Inc.  All rights reserved.
# Copyright (c) 2012-2013 The University of Tennessee and The University
#                         of Tennessee Research Foundation.  All rights
#                         reserved.
# Copyright (c) 2012-2013 Inria.  All rights reserved.
# Copyright (c) 2013-2018 Los Alamos National Security, LLC. All rights
#                         reserved.
# Copyright (c) 2015-2024 Research Organization for Information Science
#                         and Technology (RIST).  All rights reserved.
# Copyright (c) 2016      IBM Corporation.  All rights reserved.
# Copyright (c) 2017-2018 FUJITSU LIMITED.  All rights reserved.
# Copyright (c) 2019-2026 Triad National Security, LLC. All rights
#                         reserved.
# Copyright (c) 2020      Sandia National Laboratories. All rights reserved.
# Copyright (c) 2022      IBM Corporation.  All rights reserved.
# Copyright (c) 2025-2026 Jeffrey M. Squyres.  All rights reserved.
#
# $COPYRIGHT$
#
# Additional copyrights may follow
#
# $HEADER$
# SPDX-License-Identifier: BSD-3-Clause-Open-MPI
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

# All the MPI procedures are generated from the *.c.in templates
# listed in Makefile.prototype_files (see
# docs/developers/bindings.rst).  Profiling entry points are generated
# using a combination of the rename macros at the top of the generated
# files and the OMPI_BUILD_MPI_PROFILING define flag.
#
if OMPI_BUILD_FORTRAN_USEMPIF08_BINDINGS

AM_FCFLAGS = -I$(top_srcdir)/ompi/mpi/fortran/use-mpi-f08/mod \
             -I$(top_builddir)/ompi/include \
             -I$(top_srcdir)/ompi/include \
             $(OMPI_FC_MODULE_FLAG)$(top_builddir)/ompi/mpi/fortran/use-mpi \
             $(OMPI_FC_MODULE_FLAG)$(top_builddir)/ompi/mpi/fortran/use-mpi-ignore-tkr \
             $(OMPI_FC_MODULE_FLAG)mod \
             -I$(top_srcdir) -I$(top_builddir) $(FCFLAGS_f90)

MOSTLYCLEANFILES = *.mod

CLEANFILES += *.i90

lib_LTLIBRARIES = lib@OMPI_LIBMPI_NAME@_usempif08.la
noinst_LTLIBRARIES = lib@OMPI_LIBMPI_NAME@_usempif08_profile.la

module_sentinel_files = \
        mod/libforce_usempif08_internal_modules_to_be_built.la

# Because the libraries have their own FCFLAGS, Automake prefixes their
# object files with the library name; dependencies must use those names.
mpi_f08_lo_file = lib@OMPI_LIBMPI_NAME@_usempif08_la-mpi-f08.lo

$(mpi_f08_lo_file): $(module_sentinel_files)
$(mpi_f08_lo_file): mpi-f08.F90
$(mpi_f08_lo_file): sizeof_f08.h

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
        api_f08_generated.F90

lib@OMPI_LIBMPI_NAME@_usempif08_la_SOURCES = \
        $(mpi_api_files) \
        mpi-f08.F90

SIZEOF_H = sizeof_f08.h
nodist_lib@OMPI_LIBMPI_NAME@_usempif08_la_SOURCES = \
        sizeof_f08.h \
        sizeof_f08.f90 \
        psizeof_f08.f90

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

mpi_api_lo_files = \
        $(mpi_api_files:%.F90=lib@OMPI_LIBMPI_NAME@_usempif08_la-%.lo) \
        $(mpi_api_files:%.F90=lib@OMPI_LIBMPI_NAME@_usempif08_profile_la-%.lo)

$(mpi_api_lo_files): $(module_sentinel_files)

$(mpi_f08_lo_file): $(module_sentinel_files) $(SIZEOF_H)
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

api_f08_generated.F90: $(template_files) $(OMPI_BINDINGS_GENERATOR)
	$(OMPI_V_GEN) $(PYTHON) $(top_srcdir)/ompi/mpi/bindings/bindings.py \
	    --builddir $(abs_top_builddir) \
	    --srcdir $(abs_top_srcdir) \
	    --output $(abs_builddir)/$@ \
	    fortran \
	    $(gen_ts) \
	    --pympistd-dir $(abs_top_srcdir)/3rd-party/pympistandard \
	    code \
	    --lang fortran \
	    --prototype-files $(template_files)

EXTRA_DIST = $(prototype_files)

# Delete generated file on maintainer-clean
MAINTAINERCLEANFILES = api_f08_generated.F90
if OPAL_DEVEL_BUILD
CLEANFILES += api_f08_generated.F90
endif

###########################################################################

# Validate that the mpi_f08 interfaces -- both the generated
# (api_f08_generated.F90) and the hand-written (*_f08.F90) ones -- use the
# parameter names, types, and intents mandated by the MPI standard, as
# provided by the pympistandard submodule.  Run during "make check"; fails
# if any mpi_f08 interface drifts from the standard.  The hand-written
# sources live in $(srcdir); api_f08_generated.F90 is in the build directory
# (built by "all", on which "check" depends).
f08_name_check_handwritten = $(filter-out api_f08_generated.F90,$(mpi_api_files))

check-local:
	@$(PYTHON) $(top_srcdir)/ompi/mpi/bindings/check_fortran_param_names.py \
	    --label "mpi_f08 bindings (generated + hand-written)" \
	    --lang f08 \
	    --pympistd-dir $(abs_top_srcdir)/3rd-party/pympistandard \
	    api_f08_generated.F90 $(f08_name_check_handwritten:%=$(srcdir)/%)

###########################################################################

# Install the generated .mod files.  Unfortunately, each F90 compiler
# may generate different filenames, so we have to use a glob.  :-(

install-exec-hook:
	@ $(INSTALL) -d $(DESTDIR)$(OMPI_FORTRAN_MODULEDIR)
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
