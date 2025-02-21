from seedemu.core.Emulator import Emulator
from seedemu.core import Registry
from enum import IntFlag
from os import mkdir, chdir, getcwd, path
from shutil import rmtree
from sys import stderr, exit


class OptionHandling(IntFlag):
    """! different ways a compiler can deal with Options
    ( and ENV variables for containers )"""

    # only hardcoding of option values in node config files (OptionMode.BUILD_TIME)
    # any changes of Options thus require image re-compile (except config files are mounted as shared volume)
    UNSUPPORTED = 0
    # options are mapped to container ENV variables (OptionMode.RUN_TIME)
    #  ('environment:' section of each service in docker-compose.yml contains KEY: VALUE pairs)
    DIRECT_DOCKER_COMPOSE = 1
    # options are mapped to container ENV variables (OptionMode.RUN_TIME)
    #  ('environment:' section of each service in docker-compose.yml contains KEY: SNDARY_KEY pairs
    # and the SNDARY_KEY: ACTUAL_VALUE pairs are placed in a separate '.env' file alongside docker-compose.yml )
    # This is simply more overseeable.
    CREATE_SEPARATE_ENV_FILE = 2


class Compiler:
    """!
    @brief The Compiler base class.

    Compiler takes the rendered result and compiles them to working emulators.
    """

    def optionHandlingCapabilities(self) -> OptionHandling:
        """!@brief returns the capabilities of this compiler
           regarding (DynamicConfigurable-) Option handling"""
        return OptionHandling.UNSUPPORTED

    def _doCompile(self, emulator: Emulator):
        """!
        @brief Compiler driver implementation.

        This method should be implemented by the compiler driver. The driver
        class can assume that the current working directory is the output
        folder.

        @param emulator emulator object.
        """
        raise NotImplementedError('_doCompile not implemented.')

    def getName(self) -> str:
        """!
        @brief Get the name of compiler driver.

        @returns name of the driver.
        """
        raise NotImplementedError('getName not implemented.')

    def compile(self, emulator: Emulator, output: str, override: bool = False): # add OptionHandling parameter here ?!
        """!
        @brief Compile the simulation.

        @param emulator emulator object.
        @param output output directory path.
        @param override (optional) override the output folder if it already
        exist. False by default.
        """
        assert emulator.rendered(), 'Simulation needs to be rendered before compile.'

        cur = getcwd()
        if path.exists(output):
            if override:
                self._log('output folder "{}" already exist, overriding.'.format(output))
                rmtree(output)
            else:
                self._log('output folder "{}" already exist. Set "override = True" when calling compile() to override.'.format(output))
                exit(1)
        mkdir(output)
        chdir(output)
        self._doCompile(emulator)
        chdir(cur)

    def _log(self, message: str) -> None:
        """!
        @brief Log to stderr.

        @param message message.
        """
        print("== {}Compiler: {}".format(self.getName(), message), file=stderr)
