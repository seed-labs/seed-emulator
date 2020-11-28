from os import mkdir, chdir
from sys import stderr

class Compiler:
    """!
    @brief The Compiler base class.

    Compiler takes the rendered result and compiles them to working simulators.
    """

    def _doCompile(self):
        """!
        @brief Compiler driver implementation.

        This method should be implemented by the compiler driver. The driver
        class can assume that the current working directory is the output
        folder.

        @param registry rendered simulation.
        """
        raise NotImplementedError('_doCompile not implemented.')

    def getName(self) -> str:
        """!
        @brief Get the name of compiler driver.

        @returns name of the driver.
        """
        raise NotImplementedError('getName not implemented.')

    def compile(self, output: str):
        """!
        @brief Compile the simulation.

        @param output output directory path.
        """
        mkdir(output)
        chdir(output)
        self._doCompile()
        chdir('..')

    def _log(self, message: str) -> None:
        """!
        @brief Log to stderr.
        """
        print("== {}Compiler: {}".format(self.getName(), message), file=stderr)
