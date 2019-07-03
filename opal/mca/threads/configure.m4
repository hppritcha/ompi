dnl -*- shell-script -*-
dnl
dnl Copyright (c) 2004-2005 The Trustees of Indiana University and Indiana
dnl                         University Research and Technology
dnl                         Corporation.  All rights reserved.
dnl Copyright (c) 2004-2005 The University of Tennessee and The University
dnl                         of Tennessee Research Foundation.  All rights
dnl                         reserved.
dnl Copyright (c) 2004-2005 High Performance Computing Center Stuttgart,
dnl                         University of Stuttgart.  All rights reserved.
dnl Copyright (c) 2004-2005 The Regents of the University of California.
dnl                         All rights reserved.
dnl Copyright (c) 2010      Cisco Systems, Inc.  All rights reserved.
dnl Copyright (c) 2019      Sandia National Laboratories.  All rights reserved.
dnl $COPYRIGHT$
dnl
dnl Additional copyrights may follow
dnl
dnl $HEADER$
dnl


AC_DEFUN([OPAL_CONFIG_THREADS],[
#
# Arguments: none
#
# Dependencies: None
#
# Modifies:
#  none - see called tests
#
# configure threads
#

#
# First see what kind of threads we are going to use
#

AC_ARG_WITH([threads],
            [AC_HELP_STRING([--with-threads=TYPE],
                        [Specify thread TYPE to use. default:pthreads. Other options are qthreads and argobots.])])

#
# Check we for the thread package requested, or posix
#

thread_type_found=

#
# check for posix threads
#
AS_IF([test -z "$with_threads" || test "$with_threads" = "pthreads" || test "$with_threads" = "yes"],
      [OPAL_CONFIG_POSIX_THREADS(HAVE_THREAD_PKG=1, HAVE_THREAD_PKG=0)
       AC_MSG_CHECKING([for working POSIX threads package])
       AS_IF([test "$HAVE_THREAD_PKG" = "1"],
             [AC_MSG_RESULT([yes])
              thread_type_found="pthreads"],
             [AC_MSG_RESULT([no])])],
      [])

#
# see if argobots is called for
#
AS_IF([test -z "$thread_type_found" && test "$with_threads" = "argobots"],
      [OPAL_CONFIG_ARGOBOTS_THREADS(HAVE_THREAD_PKG=1, HAVE_THREAD_PKG=0)
       AC_MSG_CHECKING([for working ARGOBOTS threads package])
       AS_IF([test "$HAVE_THREAD_PKG" = "1"],
             [AC_MSG_RESULT([yes])
              thread_type_found="argobots"],
             [AC_MSG_RESULT([no])])],
      [])

AS_IF([test -z "$thread_type_found" && test "$with_threads" = "qthreads"],
      [OPAL_CONFIG_QTHREADS(HAVE_THREAD_PKG=1, HAVE_THREAD_PKG=0)
       AC_MSG_CHECKING([for working Qthreads package])
       AS_IF([test "$HAVE_THREAD_PKG" = "1"],
             [AC_MSG_RESULT([yes])
              thread_type_found="qthreads"],
             [AC_MSG_RESULT([no])])],
      [])

#
# Bail if we didn't find any thread package
#

AS_IF([test -z "$thread_type_found"],
      [AC_MSG_WARN([*** no thread package $with_threads])
       AC_MSG_WARN([*** available on your system])
       AC_MSG_ERROR([*** Can not continue])])

THREAD_CFLAGS="$TPKG_CFLAGS"
THREAD_FCFLAGS="$TPKG_FCFLAGS"
THREAD_CXXFLAGS="$TPKG_CXXFLAGS"
THREAD_CPPFLAGS="$TPKG_CPPFLAGS"
THREAD_CXXCPPFLAGS="$TPKG_CXXCPPFLAGS"
THREAD_LDFLAGS="$TPKG_LDFLAGS"
THREAD_LIBS="$TPKG_LIBS"
HAVE_THREAD_PKG_TYPE="$thread_type_found"
export HAVE_THREAD_PKG_TYPE

AS_IF([test "$thread_type_found" = "pthreads"],
      [OPAL_CHECK_PTHREAD_PIDS],[])

OPAL_SUMMARY_ADD([[Miscellaneous]],[[Threading Package]],[opal_threads], [$thread_type_found])
])dnl

dnl we only want one :)
m4_define(MCA_opal_threads_CONFIGURE_MODE, STOP_AT_FIRST)

AC_DEFINE_UNQUOTED([OPAL_ENABLE_MULTI_THREADS], [1],
	[Whether we should enable thread support within the OPAL code base])
AC_DEFUN([MCA_opal_threads_CONFIG],[
        thread_type=$HAVE_THREAD_PKG_TYPE
        threads_base_include=
        mutex_base_include=

        # first, compile all the components
        MCA_CONFIGURE_FRAMEWORK($1, $2, 1)

        threads_base_include="${thread_type}/threads_${thread_type}_threads.h"
        mutex_base_include="${thread_type}/threads_${thread_type}_mutex.h"
        tsd_base_include="${thread_type}/threads_${thread_type}_tsd.h"
        wait_sync_base_include="${thread_type}/threads_${thread_type}_wait_sync.h"

        AC_DEFINE_UNQUOTED([MCA_threads_base_include_HEADER],
                           ["opal/mca/threads/$threads_base_include"],
                           [Header to include for threads implementation])

        AC_DEFINE_UNQUOTED([MCA_threads_mutex_base_include_HEADER],
                           ["opal/mca/threads/$mutex_base_include"],
                           [Header to include for mutex implementation])

        AC_DEFINE_UNQUOTED([MCA_threads_tsd_base_include_HEADER],
                           ["opal/mca/threads/$tsd_base_include"],
                           [Header to include for tsd implementation])

        AC_DEFINE_UNQUOTED([MCA_threads_wait_sync_base_include_HEADER],
                           ["opal/mca/threads/$wait_sync_base_include"],
                           [Header to include for wait_sync implementation])
])
