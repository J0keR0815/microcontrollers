"""
This module provides functions which can be used by the cli
via serial-connection
"""

# Import from libraries

import machine
import sys
import uos

# Local imports

from boot import functor

"""
Octal values for mode-flags of stat-buffer
"""
S_IFBLK = 0o60000
S_IFCHR = 0o20000
S_IFDIR = 0o40000
S_IFIFO = 0o10000
S_IFLNK = 0o120000
S_IFREG = 0o100000
S_IFSOCK = 0o140000
S_IFMT = 0o170000

"""
Header for result output
"""
BEG_RES = "##### BEGIN RESULTS #####\n"

"""
Footer for result output
"""
END_RES = "##### END RESULTS #####\n"

"""
Error codes for exit, which are not provided by errno
"""
EXIT_SUCCESS = 0
EXIT_FAILURE = 255


@functor
class sysinfo:
    """
    This Class is responsible for the extraction of important
    system information of the serial-device.
    """

    """
    Indices of uos.uname()
    """
    UN_SYSNAME = 0
    UN_NODENAME = 1  # Hostname
    UN_RELEASE = 2  # hardware release
    UN_VERSION = 3  # micropython firmware version
    UN_MACHINE = 4

    """
    Indices of uos.statvfs(path)
    """
    F_BSIZE = 0
    F_FRSIZE = 1
    F_BLOCKS = 2
    F_BFREE = 3
    F_BAVAIL = 4
    F_FILES = 5
    F_FFREE = 6
    F_FAVAIL = 7
    F_FLAG = 8
    F_NAMEMAX = 9

    """
    List of possible queries
    """
    QUERIES_MEM = [
        "avail",
        "bsize",
        "free",
        "frsize",
        "size"
    ]
    QUERIES_SYS = [
        "fwver",
        "hostname",
        "hwrelease",
        "machine",
        "sysname",
    ]

    def __init__(self):
        """
        The constructor creates the sysinfo instance which is used as
        a Functor.
        """

        self.queries = [
            "all",
            "all_mem",
            "all_sys"
        ]
        self.queries.extend(self.QUERIES_MEM)
        self.queries.extend(self.QUERIES_SYS)

    def __call__(self, query=None):
        """
        This function allows objects to be called as functions.
        """

        serial_print(self.__query(q=query))

    def __meminfo(self, q=None):
        """
        Resolves queries about memory information.
        """

        results = ""
        stvfs = uos.statvfs("/")

        if q is None:
            results += self.__meminfo("avail")
            results += self.__meminfo("bsize")
            results += self.__meminfo("free")
            results += self.__meminfo("frsize")
            results += self.__meminfo("size")

        if q == "avail":
            val = stvfs[self.F_BAVAIL] * stvfs[self.F_BSIZE]
            results += "available userspace: {}\n".format(val)
        if q == "bsize":
            val = stvfs[self.F_BSIZE]
            results += "blocksize: {}\n".format(val)
        if q == "free":
            val = stvfs[self.F_BFREE] * stvfs[self.F_BSIZE]
            results += "free space: {}\n".format(val)
        if q == "frsize":
            val = stvfs[self.F_FRSIZE]
            results += "fragment size: {}\n".format(val)
        if q == "size":
            val = stvfs[self.F_BLOCKS] * stvfs[self.F_FRSIZE]
            results += "total memory space: {}\n".format(val)

        return results

    def __query(self, q=None):
        """
        This function processes the requested query.

        @return Result string
        """

        if q is None:
            return self.__query(q="all")

        try:
            if q not in self.queries:
                raise ValueError("Unknown query")
        except ValueError as err:
            usage(err)

        results = ""
        if q == "all":
            results += self.__sysinfo()
            results += self.__meminfo()
        elif q == "all_mem":
            results += self.__meminfo()
        elif q == "all_sys":
            results += self.__sysinfo()
        else:
            if q in self.QUERIES_MEM:
                results += self.__meminfo(q=q)
            if q in self.QUERIES_SYS:
                results += self.__sysinfo(q=q)

        return results

    def __sysinfo(self, q=None):
        """
        Resolves queries about system information.
        """

        un = uos.uname()
        results = ""

        if q is None:
            results += self.__sysinfo("fwver")
            results += self.__sysinfo("hostname")
            results += self.__sysinfo("hwrelease")
            results += self.__sysinfo("machine")
            results += self.__sysinfo("sysname")

        if q == "fwver":
            results += "firmware version: {}\n" \
                .format(un[self.UN_VERSION])
        if q == "hostname":
            results += "hostname: {}\n" \
                .format(un[self.UN_NODENAME])
        if q == "hwrelease":
            results += "hardware release: {}\n" \
                .format(un[self.UN_RELEASE])
        if q == "machine":
            results += "machine: {}\n" \
                .format(un[self.UN_MACHINE])
        if q == "sysname":
            results += "system name: {}\n" \
                .format(un[self.UN_SYSNAME])

        return results


def cat(*argv):
    """
    This function displays one or more files on STDOUT.
    """

    try:
        if len(argv) == 0:
            raise ValueError("No file too display")
    except ValueError as err:
        usage(err)

    for fn in argv:
        serial_fprint(fn)


def cp(*argv, dest=".", rec=False):
    pass


def du(*argv, max_depth=-1, human_readable=False):
    """
    This function displays the usage of filesystem memory for the
    provided file pathes.
    """

    pass


def err_msg(err):
    """
    This function creates an error message for an error.
    """

    return "{}\n".format(
        err.message if hasattr(err, "message") else err
    )


def error(err):
    """
    This function raises an error after catching an exception.
    If term is True the program terminates.
    """

    serial_print(err_msg(err))
    if hasattr(err, "errno"):
        sys.exit(err.errno)
    else:
        sys.exit(EXIT_FAILURE)


def human_readable(n):
    """
    Prints n bytes in human readable format
    """

    try:
        n = int(n)
        if n < 0:
            raise ValueError(
                "Number of bytes must be non-negative integer"
            )
    except Exception as err:
        usage(err)

    units = ["K", "M", "G", "T"]
    i = 0
    unit = ""
    while n >= 1024:
        if n % 1024 == 0:
            n //= 1024
        else:
            n /= 1024
        i += 1

    if i > 0:
        unit = units[i - 1]

    result = "{:.1f}{}".format(n, unit)
    if n == int(n):
        result = "{}{}".format(n, unit)

    return result


def is_dir(path):
    """
    This fucntion checks, if path is a directory.
    """

    try:
        if path.strip() == "":
            raise ValueError("No path given")
        sb = uos.stat(path)
        if sb[0] & S_IFMT == S_IFDIR:
            serial_print("TRUE\n")
        else:
            serial_print("FALSE\n")
    except Exception as err:
        serial_print(err_msg("{}: {}".format(path, err)))


def ls(*argv, human_readable=False, list_format=False, rec=False):
    """
    This function lists files or the content of directories.
    """

    if len(argv) == 0:
        argv = (".", )

    output = ""
    for arg in argv:
        try:
            sb = uos.stat(arg)
            entries = arg
            if sb[0] & S_IFMT == S_IFDIR:
                entries = uos.listdir(arg)
            if list_format is False:
                output += "{}\n".format(entries)
        except Exception as err:
            output += err_msg("{}: {}".format(arg, err))

    serial_print(output)


def serial_fprint(file):
    """
    Prints a file for host connected to the serial-device.
    """

    print(BEG_RES, end="")

    try:
        sb = uos.stat(file)
        if sb[0] & S_IFMT == S_IFREG:
            fd = open(file, "r")
            for line in fd:
                print(line, end="")
        else:
            raise ValueError("{} is not a regular file".format(file))
    except Exception as err:
        print(err_msg("{}: {}".format(file, err)), end="")

    print(END_RES, end="")


def serial_print(msg):
    """
    Prints a message for host connected to the serial-device.
    """

    output = "{}{}{}".format(BEG_RES, msg, END_RES)
    print(output)


def restore():
    """
    This function deletes the module for the cli and resets the
    serial-device.
    """

    uos.remove("cli_module.py")
    machine.reset()


def usage(err, is_err=True):
    """
    This function raises a usage-error, when this programm
    is executed incorrect via commandline.
    """

    serial_print("Usage: {}\n".format(err))
    if is_err is True:
        sys.exit(EXIT_FAILURE)
    else:
        sys.exit(uos.EXIT_SUCCESS)
