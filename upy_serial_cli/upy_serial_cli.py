#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
This module contains a shell for mycro-python via a
serial-connection, which provides basic filesystem
commands.
"""

import getopt
import inspect
import os
from serial import Serial, serialutil
import sys
import time

"""
Error codes for exit, which are not provided by errno
"""
EXIT_SUCCESS = 0
EXIT_FAILURE = 255


def error(err):
    """
    This function raises an error after catching an exception.
    The program is terminated using the error code as exit code
    """

    msg = "{}\n".format(
        err.message if hasattr(err, "message") else err
    )
    print(msg, file=sys.stderr)
    if hasattr(err, "errno"):
        sys.exit(err.errno)
    else:
        sys.exit(EXIT_FAILURE)


def usage(is_err=True):
    """
    This function raises a usage-error, when this programm
    is executed incorrect via commandline.
    """

    print(
        "Usage: {} [OPTIONS] [COMMAND]\n\n"
        "OPTIONS:\n\n"
        "-b <baudrate>: "
        "Baudrate for serial-connection, requires option \"-p\" "
        "(Default: 9600)\n\n"
        "-i: Interactive mode, requires option \"-p\", "
        "on default, non-interactive mode is used and a "
        "COMMAND is expected\n\n"
        "-h: Show help\n\n"
        "-p <serial_port>: "
        "Serial port / device required to setup"
        "serial-connection\n\n"
        "COMMAND:\n\n"
        "Run command help to see commands."
        .format(sys.argv[0]),
        file=sys.stderr
    )

    if is_err is True:
        sys.exit(EXIT_FAILURE)
    else:
        sys.exit(EXIT_SUCCESS)


class upy_serial_cli:
    """
    This class is responsible to provide a commandline-interface
    to execute commands on micro-python via a serial-connection.
    """

    """
    Default value for baudrate of a serial-connection
    """
    DEFAULT_BAUDRATE = 9600

    """
    Default value for waiting after writing to serial-buffer.
    """
    DEFAULT_WAIT = 0.1

    """
    Defaul value for timeout in seconds, which is used for
    read via serial-connection
    """
    DEFAULT_TIMEOUT = 1

    """
    Default value for size of write-buffer via serial-connection.
    """
    DEFAULT_SER_WRBUF_SIZE = 256

    """
    Default value for size of read-buffer via serial-connection.
    """
    DEFAULT_SER_RDBUF_SIZE = 1000

    """
    List of commands, that can be used via the serial-shell.
    """
    COMMANDS = [
        "cat",
        "cp",
        "du",
        "exit",
        "free",
        "help",
        "ls",
        "mkdir",
        "mv",
        "restore",
        "rm",
        "sysinfo"
    ]

    """
    Default path for this program.
    """
    DEFAULT_PATH = "{}".format(os.getcwd())

    """
    Filename of cli-module
    """
    CLI_MOD = "cli_module.py"

    """
    dictionary of characters, which are replaced
    when transferring source-code via serial-connection.
    """
    SUBSTITUTES = {
        "\\": "\\\\",
        "\n": "\\n",
        "\r": "\\r",
        "\t": " " * 4,
        "\'": "\\'",
    }

    """
    Header for result output
    """
    BEG_RES = "##### BEGIN RESULTS #####"

    """
    Footer for result output
    """
    END_RES = "##### END RESULTS #####"

    def __init__(self, port, baudrate):
        """
        Constructor: Checks, if a connection to the specified
        serial-device can be established.
        """

        try:
            # Set tty-port for serial-connection
            self.port = port

            # Set specific baudrate for serial-device
            if baudrate is None:
                self.baudrate = upy_serial_cli.DEFAULT_BAUDRATE
            else:
                self.baudrate = int(baudrate)
                if self.baudrate <= 0:
                    raise ValueError()

            # Create instance for serial-conncection
            self.ser_conn = Serial(
                port=self.port,
                baudrate=self.baudrate,
                timeout=upy_serial_cli.DEFAULT_TIMEOUT
            )

            # Check, if module for cli is already on the serial-device
            # If this is not the case transfer module and reboot
            self.serial_write(
                "try: sb = uos.stat(\"{}\")\r\n"
                "except Exception as err: "
                "print(\"### {{}} ###\".format(err))\r\n\r\n"
                .format(upy_serial_cli.CLI_MOD)
            )
            output = self.serial_read()
            self.ser_conn.close()

            if len(output) > 0:
                output = output.split("\r\n")

            if (
                len(output) == 0 or
                "### [Errno 2] ENOENT ###" in output
            ):
                print("Transferring cli-module ...")
                self.cp(
                    "{}/{}".format(
                        upy_serial_cli.DEFAULT_PATH,
                        upy_serial_cli.CLI_MOD
                    ),
                    upy_serial_cli.CLI_MOD
                )
                print("... Done!\nRebooting device ...")
                sys.exit(EXIT_SUCCESS)
        except ValueError:
            usage()
        except serialutil.SerialException as e:
            error(e)

    def __del__(self):
        """
        Destructor: Restarts serial-device
        """

        self.ser_conn.open()
        self.serial_write(
            "import machine\r\n"
            "machine.reset()\r\n"
        )
        self.ser_conn.close()

    def argv_to_str(self, argv):
        """
        Transforms an argument list to string format matching:
        "arg_1", "arg_2", ... , "arg_n"
        """

        result = ""

        for i in range(len(argv)):
            result += "\"{}\"{}".format(
                argv[i], ", " if i != len(argv) - 1 else ""
            )

        return result

    def cat(self, *argv):
        """
        This function displays one or more files from the
        serial-device.
        """

        if len(argv) == 0 or "-h" in argv:
            # If help option is specified or no file is given as an
            # argument the helpmessage is displayed.
            strout = \
                "USAGE:\n\n" \
                "cat [OPTIONS] <file_1> [file_2 ... file_n]\n\n" \
                "DESCRIPTION:\n\n" \
                "{}\n\n" \
                "OPTIONS:\n\n" \
                "-h: Print help about this command" \
                .format(self.func_descr())
            self.helpmsg(strout)
        else:
            # Display content of specified files
            args = self.argv_to_str(argv)
            self.ser_conn.open()
            self.serial_write(
                "cat({})\r\n".format(args)
            )
            results = self.serial_read()
            self.ser_conn.close()
            print(self.extract_results(results))

    def cp(self, *argv):
        """
        This function copies files or directories
        to / from / on the serial-device.
        """

        if "-h" in argv:
            # If help option is specified helpmessage is displayed.
            strout = \
                "USAGE:\n\n" \
                "cp [OPTIONS] <src_1> [src_2 ... src_n]> <target>\n\n" \
                "DESCRIPTION:\n\n" \
                "{}\n\n" \
                "On default sources are interpreted as local " \
                "files / directories, whereas the destination " \
                "is interpreted as a path on the " \
                "serial-device.\n\n" \
                "Copying files from local source to local " \
                "destination is not permitted. Use the actual " \
                "\"cp\"-program (man 1 cp) for that " \
                "operation\n\n" \
                "OPTIONS:\n\n" \
                "-h: Print help about this command\n\n" \
                "-r: Copy directories recursively\n\n" \
                "-s <serial|local>: Copy sources from the " \
                "serial- / local device\n\n" \
                "-d <serial|local>: Copy to destination on the " \
                "serial- / local device" \
                .format(self.func_descr())
            self.helpmsg(strout)
        else:
            # Resolve arguments
            opts = None
            args = None
            try:
                opts, args = getopt.getopt(argv, "rs:d:")
            except getopt.GetoptError:
                self.cp("-h")
                return -1

            # There must be at least one source and one target
            if len(args) < 2:
                self.cp("-h")
                return -1

            # Disassemble sources and target
            srcs = args[:-1:]
            dest = args[-1]

            # Check options
            # Default:
            # - No recursion
            # - sources from local device,
            # - destination on serial-device
            s = "local"
            d = "serial"
            rec = False
            for opt in opts:
                if opt[0] == "-s":
                    if not (
                        opt[1] == "serial" or
                        opt[1] == "local"
                    ):
                        self.cp("-h")
                        return -1
                    else:
                        s = opt[1]

                if opt[0] == "-d":
                    if not (
                        opt[1] == "serial" or
                        opt[1] == "local"
                    ):
                        self.cp("-h")
                        return -1
                    else:
                        d = opt[1]
                if opt[0] == "-r":
                    rec = True

            # Run cp() for the specified location of sources
            # and destination
            if s == "local" and d == "local":
                """
                Copy from local source to local destination is
                not permitted. Use program "cp" for this operation.
                """
                self.cp("-h")
                return -1

            if s == "local" and d == "serial":
                """
                Copy local sources to destination on serial-device.
                """

                # If cli-module is initiated, transfer it directly
                if (
                    len(srcs) == 1 and
                    srcs[0] == "{}/{}".format(
                        upy_serial_cli.DEFAULT_PATH,
                        upy_serial_cli.CLI_MOD
                    ) and
                    dest == upy_serial_cli.CLI_MOD
                ):
                    self.ser_conn.open()
                    self.serial_fwrite(srcs[0], dest)
                    self.ser_conn.close()
                else:
                    try:
                        # Check dest: Cannot be empty
                        if dest.strip() == "":
                            raise ValueError(
                                "Destination path cannot be empty"
                            )

                        # Check if dest is a directory
                        self.ser_conn.open()
                        self.serial_write(
                            "is_dir(\"{}\")\r\n".format(dest)
                        )
                        results = self.serial_read()
                        results = self.extract_results(results)
                        results = results.strip()

                        # Deduplicate list of sources:
                        # Each source must be unique
                        srcs = self.dedup(*srcs)

                        if results == "TRUE":
                            # Copy into directory
                            for src in srcs:
                                self.serial_fwrite(
                                    src, "{}/{}".format(
                                        dest, os.path.basename(src)
                                    )
                                )
                        elif results == "FALSE":
                            if len(srcs) == 1:
                                # File exists and only one source:
                                # Copy into file
                                self.serial_fwrite(srcs[0], dest)
                            else:
                                # dest is not a directory:
                                # Cannot copy multiple files
                                raise ValueError(
                                    "{} is not a directory: Cannot "
                                    "copy files"
                                    .format(dest)
                                )
                        else:
                            # dest does not exist
                            if len(srcs) == 1:
                                # File dest does not exist and only
                                # one source: Copy into new file dest
                                self.serial_fwrite(srcs[0], dest)
                            else:
                                # Directory dest needs to be created
                                # before copying multiple sources into
                                # it
                                raise ValueError(
                                    "Directory {} does not exist: "
                                    "Cannot copy files"
                                    .format(dest)
                                )

                    except Exception as err:
                        error(err)
                    finally:
                        self.ser_conn.close()

            if s == "serial" and d == "local":
                """
                Copy sources from serial-device to local
                destination.
                """
                pass

            if s == "serial" and d == "serial":
                """
                Copy sources from serial-device to destination
                on serial-device.
                """
                pass

    def dedup(self, *pathes):
        """
        This function deduplicates pathes of the local host
        the serial-device is connected to.

        @return deduplicated list of pathes on success, None on error
        """

        result = []

        for p in pathes:
            p = os.path.realpath(p)
            if p not in result:
                result.append(p)

        return result

    def du(self, *argv):
        """
        This function displays the usage of filesystem memory for the
        provided pathes on the serial-device.
        """

        if "-h" in argv:
            # If help option is specified the helpmessage is displayed.
            strout = \
                "USAGE:\n\n" \
                "du [OPTIONS] [file_1 file_2 ... file_n]\n\n" \
                "DESCRIPTION:\n\n" \
                "{}\n\n" \
                "OPTIONS:\n\n" \
                "-d n: Maximal depth of n, n = 0, 1, 2, ...\n\n" \
                "-f: Human readable memory output format\n\n" \
                "-h: Print help about this command" \
                .format(self.func_descr())
            self.helpmsg(strout)
        else:
            # Resolve arguments
            opts = None
            args = None
            try:
                opts, args = getopt.getopt(argv, "d:hf")
            except getopt.GetoptError:
                self.cp("-h")
                return -1

            # Check options:
            # Default:
            # max_depth = -1: Traverse full depth
            # human_readable = False: Display memory output in bytes
            max_depth = -1
            human_readable = False
            for opt in opts:
                if opt[0] == "-d":
                    max_depth = int(opt[1])
                    if max_depth <= 0:
                        ValueError()
                if opt[0] == "-f":
                    human_readable = True

            # If no path is given "." is set
            if len(args) == 0:
                args = (".", )

            # Run du() for the specified pathes on serial-device
            self.ser_conn.open()
            args = self.argv_to_str(args)
            self.serial_write(
                "du({}, max_depth={}, human_readable={})\r\n"
                .format(args, max_depth, human_readable)
            )
            results = self.serial_read()
            self.ser_conn.close()
            print(self.extract_results(results))

    def exit(self, *argv):
        """
        This function exits the serial-shell from the host-side.
        """

        if "-h" in argv:
            # If help option is specified helpmessage is displayed.
            strout = \
                "USAGE:\n\n" \
                "exit [OPTIONS]\n\n" \
                "DESCRIPTION:\n\n" \
                "{}\n\n" \
                "OPTIONS:\n\n" \
                "-h: Print help about this command" \
                .format(self.func_descr())
            self.helpmsg(strout)
        else:
            # Exit shell
            sys.exit(EXIT_SUCCESS)

    def extract_results(self, res_str):
        """
        This function extracts the results from the string
        res_str. Each result is marked by BEG_RES and END_RES.
        """

        results = None
        try:
            results = res_str.split("\r\n")
            results = "\n".join(results)
            results = results.split(upy_serial_cli.BEG_RES)
            if len(results) == 1:
                raise ValueError("No results found")
            results = "".join(results[1::])
            results = results.split(upy_serial_cli.END_RES)
            if len(results) == 1:
                raise ValueError("Result incomplete")
            results = "".join(results[:-1:])
        except ValueError as err:
            error(err)

        return results

    def free(self, *argv):
        """
        This function calculates the free memory on the serial-device
        """

        if "-h" in argv:
            # If help option is specified helpmessage is displayed.
            strout = \
                "USAGE:\n\n" \
                "free [OPTIONS]\n\n" \
                "DESCRIPTION:\n\n" \
                "{}\n\n" \
                "OPTIONS:\n\n" \
                "-h: Print help about this command" \
                .format(self.func_descr())
            self.helpmsg(strout)
        else:
            self.sysinfo("-q", "free")

    def func_descr(self, fn=None):
        """
        This function returns the description of the specified function.
        If fn is None the description of the function, which is
        the previous on stack (calling function), is returned.
        """

        func = None
        if fn is None:
            func = getattr(self, inspect.stack()[1].function)
        else:
            func = getattr(self, fn)

        return " ".join(func.__doc__.lstrip().split())

    def help(self, *argv):
        """
        This function provides help for the several commands.
        """

        if (
            len(argv) == 0 or
            (
                "-h" not in argv and
                argv[0] not in upy_serial_cli.COMMANDS
            )
        ):
            # If no argument is given or help is not specified and
            # the specified command is unknown the helpmessage contains
            # short descriptions of all known commands.
            strout = "##### COMMANDS: #####\n\n"
            for command in upy_serial_cli.COMMANDS:
                strout += "##### {}: #####\n\n{}\n\n".format(
                    command,
                    self.func_descr(command)
                )
            strout += \
                "####################################\n\n" \
                "For information about a COMMAND use:\n\n" \
                "help COMMAND\n" \
                "COMMAND -h\n"
            self.helpmsg(strout)
        elif (
            "-h" in argv or
            argv[0] == "help"
        ):
            # Help option is specified for help command:
            # Print helpmessage for command help
            strout = \
                "USAGE:\n\n" \
                "help [OPTIONS] COMMAND\n\n" \
                "DESCRIPTION:\n\n" \
                "{}\n\n" \
                "OPTIONS:\n\n" \
                "-h: Print help about this command\n\n" \
                "COMMAND: Print help about command COMMAND" \
                .format(self.func_descr())
            self.helpmsg(strout)
        else:
            # Help option is specified for a known command but help:
            # Helpmessage for specified command is printed
            m = getattr(self, argv[0])
            m("-h")

    def ls(self, *argv):
        """
        This function lists files or the content of directories
        on the serial-device. On default the content of
        the current directory is listed.
        """

        if "-h" in argv:
            # If help option is specified helpmessage is displayed.
            strout = \
                "USAGE:\n\n" \
                "ls [OPTIONS] [file_1 ... file_n]\n\n" \
                "DESCRIPTION:\n\n" \
                "{}\n\n" \
                "OPTIONS:\n\n" \
                "-f: Human readable memory output format\n\n" \
                "-h: Print help about this command\n\n" \
                "-l: Print detailed list of " \
                "file information\n\n" \
                "-r: Traverse directories recursively" \
                .format(self.func_descr())
            self.helpmsg(strout)
        else:
            # Resolve arguments
            opts = None
            args = None
            try:
                opts, args = getopt.getopt(argv, "flr")
            except getopt.GetoptError:
                self.ls("-h")
                return -1

            # Check options:
            # Default:
            # - human_readable = False: Display memory output in bytes
            # - list_format = False: Display only list of filenames
            # - No recursion: Display only filenames directly below
            #   the specified path
            human_readable = False
            list_format = False
            rec = False
            for opt in opts:
                if opt[0] == "-f":
                    human_readable = True
                if opt[0] == "-l":
                    list_format = True
                if opt[0] == "-r":
                    rec = True

            # If no path is given "." is set
            if len(args) == 0:
                args = (".", )

            # Run ls() on the serial-device
            args = self.argv_to_str(args)
            self.ser_conn.open()
            self.serial_write(
                "ls({}, human_readable={}, list_format={}, rec={})\r\n"
                .format(args, human_readable, list_format, rec)
            )
            results = self.serial_read()
            self.ser_conn.close()
            print(self.extract_results(results))

    def mkdir(self, *argv):
        """
        This function creates directories on a serial-device.
        """

        if len(argv) == 0 or "-h" in argv[0]:
            # If help option is specified helpmessage is displayed.
            strout = \
                "USAGE:\n\n" \
                "mkdir [OPTIONS] <dir_1> [dir_2 ... dir_n]\n\n" \
                "DESCRIPTION:\n\n" \
                "{}\n\n" \
                "OPTIONS:\n\n" \
                "-h: Print help about this commandi\n\n" \
                "-p: Create parent directories if not existent" \
                .format(self.func_descr())
            self.helpmsg(strout)
        else:
            pass

    def mv(self, *argv):
        """
        This function renames / moves files or directories
        to / from / on the serial-device.
        """

        if "-h" in argv:
            # If help option is specified helpmessage is displayed.
            strout = \
                "USAGE:\n\n" \
                "mv [OPTIONS] <src_1> [src_2 ... src_n]> <target>\n\n" \
                "DESCRIPTION:\n\n" \
                "{}\n\n" \
                "On default sources are interpreted as local " \
                "files / directories, whereas the destination " \
                "is interpreted as a path on the " \
                "serial-device.\n\n" \
                "Moving files from local source to local " \
                "destination is not permitted. Use the actual " \
                "\"mv\"-command (man 1 mv) for that " \
                "operation\n\n" \
                "OPTIONS:\n\n" \
                "-h: Print help about this command\n\n" \
                "-s <serial|local>: Copy sources from the " \
                "serial- / local device\n\n" \
                "-d <serial|local>: Copy to destination on the " \
                "serial- / local device" \
                .format(self.func_descr())
            self.helpmsg(strout)
        else:
            pass

    def helpmsg(self, msg):
        """
        This function prints a help message to STDERR.
        """

        print(msg, file=sys.stderr)

    def restore(self, *argv):
        """
        This function resets the serial-device by deleting the
        cli_module and rebooting the device.
        """

        if "-h" in argv:
            # If help option is specified helpmessage is displayed.
            strout = \
                "USAGE:\n\n" \
                "restore [OPTIONS]\n\n" \
                "DESCRIPTION:\n\n" \
                "{}\n\n" \
                "OPTIONS:\n\n" \
                "-h: Print help about this command" \
                .format(self.func_descr())
            self.helpmsg(strout)
        else:
            # Run restore on serial device
            self.ser_conn.open()
            self.serial_write("restore()\r\n")
            self.ser_conn.close()

    def rm(self, *argv):
        """
        This function removes files / directories from the
        serial-device.
        """

        if len(argv) == 0 or "-h" in argv:
            # If help option is specified or no path is given
            # helpmessage is displayed.
            strout = \
                "USAGE:\n\n" \
                "rm [OPTIONS] <file_1> [file_2 ... file_n]\n\n" \
                "DESCRIPTION:\n\n" \
                "{}\n\n" \
                "OPTIONS:\n\n" \
                "-h: Print help about this command\n\n" \
                "-r: Removes a directory recursively" \
                .format(self.func_descr())
            self.helpmsg(strout)
        else:
            pass

    def run(self, *argv):
        """
        This function runs a command to communicate with
        the serial-device in non-interactive mode.
        """

        if len(argv) == 0:
            usage()

        command = argv[0]
        args = argv[1::]
        if command in upy_serial_cli.COMMANDS:
            m = getattr(self, command)
            m(*args)
        else:
            self.help()

    def serial_fwrite(self, src, dest):
        """
        This function writes the file content over the serial-connection
        into a file on the serial-device.
        """

        fd = open(src, "r")
        self.serial_write(
            "fd = open(\"{}\", \"w\")\r\n"
            .format(dest)
        )
        for line in fd:
            for key in upy_serial_cli.SUBSTITUTES:
                line = line.replace(
                    key,
                    upy_serial_cli.SUBSTITUTES[key]
                )
            self.serial_write(
                "fd.write(\'{}\'.encode(\"utf-8\"))\r\n"
                .format(line),
            )
        self.serial_write("fd.close()\r\n")

    def serial_read(self):
        """
        This function reads via serial-connection.
        """

        result = b""
        read_bytes = upy_serial_cli.DEFAULT_SER_RDBUF_SIZE
        while (
            read_bytes ==
                upy_serial_cli.DEFAULT_SER_RDBUF_SIZE
        ):
            buf = self.ser_conn.read(
                upy_serial_cli.DEFAULT_SER_RDBUF_SIZE
            )
            read_bytes = len(buf)
            result += buf
            self.ser_conn.flush()
        return result.decode("utf-8")

    def serial_write(self, buf, t_wait=None):
        """
        This function writes buffer-content via serial-connection.
        """

        if t_wait is None:
            t_wait = upy_serial_cli.DEFAULT_WAIT

        written_bytes = upy_serial_cli.DEFAULT_SER_WRBUF_SIZE
        offset = 0
        end = upy_serial_cli.DEFAULT_SER_WRBUF_SIZE
        while (
            written_bytes ==
                upy_serial_cli.DEFAULT_SER_WRBUF_SIZE
        ):
            written_bytes = self.ser_conn.write(
                buf[offset:end:].encode("utf-8")
            )
            if t_wait > 0:
                time.sleep(t_wait)
            offset += written_bytes
            end = offset + upy_serial_cli.DEFAULT_SER_WRBUF_SIZE

    def start(self, prompt="upy_serial_cli> "):
        """
        This function starts the cli, to interact with the
        serial-device.
        """

        print(prompt, end="", flush=True)
        while True:
            command = sys.stdin.readline()
            command = command.split()
            if (
                len(command) > 0 and
                command[0] in upy_serial_cli.COMMANDS
            ):
                m = getattr(self, command[0])
                m(*command[1::])
            else:
                self.help()
            print(prompt, end="", flush=True)

    def sysinfo(self, *argv):
        """
        This function extracts a summary of important system information
        of the serial-device.
        """

        if "-h" in argv:
            # If help option is specified helpmessage is displayed.
            strout = \
                "USAGE:\n\n" \
                "sysinfo [OPTIONS]\n\n" \
                "DESCRIPTION:\n\n" \
                "{}\n\n" \
                "OPTIONS:\n\n" \
                "-h: Print help about this command\n\n" \
                "-q QUERY: Specifies the query which information are " \
                "required\n\n" \
                "QUERIES:\n\n" \
                "all: All MEMORY QUERIES and SYSTEM QUERIES (default)\n" \
                "all_mem: All MEMORY QUERIES\n" \
                "all_sys: All SYSTEM QUERIES\n\n" \
                "MEMORY QUERIES:\n\n" \
                "avail: Available memory space for users\n" \
                "bsize: Blocksize\n" \
                "free: Free memory space on serial-device\n" \
                "frsize: Fragment size\n" \
                "size: Total memory space of serial-device\n\n" \
                "SYSTEM QUERIES:\n\n" \
                "fwver: Micropython firmware version\n" \
                "hostname: Hostname of the serial-device\n" \
                "hwrelease: Hardware release of the device\n" \
                "machine: Machine label of serial-device\n" \
                "sysname: System name of serial-device" \
                .format(self.func_descr())
            self.helpmsg(strout)
        else:
            # Resolve arguments
            opts = None
            args = None
            try:
                opts, args = getopt.getopt(argv, "q:")
            except getopt.GetoptError:
                self.ls("-h")
                return -1

            # Check options:
            # Default:
            # - query = "all"
            query = "all"
            for opt in opts:
                if opt[0] == "-q":
                    query = opt[1]

            # Run sysinfo(query)
            self.ser_conn.open()
            self.serial_write("sysinfo(query=\"{}\")\r\n".format(query))
            results = self.serial_read()
            self.ser_conn.close()
            print(self.extract_results(results))


if __name__ == "__main__":
    opts = None
    args = None
    try:
        opts, args = getopt.getopt(sys.argv[1::], "b:hp:i")
    except getopt.GetoptError:
        usage()

    if len(opts) == 0:
        usage()
    if ("-h", "") in opts:
        usage(is_err=False)

    port = None
    baudrate = None
    interactive = False
    for opt in opts:
        if opt[0] == "-p":
            port = opt[1]
        if opt[0] == "-b":
            baudrate = opt[1]
        if opt[0] == "-i":
            interactive = True

    if port is None:
        usage()

    cli = upy_serial_cli(port, baudrate)
    if interactive is True:
        cli.start()
    else:
        cli.run(*args)
