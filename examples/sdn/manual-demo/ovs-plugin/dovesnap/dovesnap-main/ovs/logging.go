package ovs

import (
	"io"
	"io/ioutil"
	"log"
	"os"
)

var (
	Debug   *log.Logger
	Info    *log.Logger
	Warning *log.Logger
	Error   *log.Logger
	debugF  bool
)

const (
	standardLogFlags = log.Ldate | log.Ltime | log.Lmicroseconds
)

func InitLogging(debugHandle io.Writer,
	infoHandle io.Writer,
	warningHandle io.Writer,
	errorHandle io.Writer) {
	Debug = log.New(debugHandle, "DEBUG: ", standardLogFlags)
	Info = log.New(infoHandle, "INFO: ", standardLogFlags)
	Warning = log.New(warningHandle, "WARNING: ", standardLogFlags)
	Error = log.New(errorHandle, "ERROR: ", standardLogFlags)
}

func InitDefaultLogging(debug bool) {
	if debug == debugF {
		return
	}
	debugF = debug
	debugOut := ioutil.Discard
	if debug {
		debugOut = os.Stderr
	}
	InitLogging(debugOut, os.Stdout, os.Stdout, os.Stderr)
}
