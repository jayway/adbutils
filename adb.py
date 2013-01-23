import  subprocess

__author__    = 'Andreas Nilsson'
__email__     = 'andreas.nilsson@jayway.com'
__copyright__ = "Copyright 2013, Jayway"
__license__   = 'Apache 2.0'

def run_instrument(package, instrument_runner='android.test.InstrumentationTestRunner', class_name=None):
    '''
    Return the output from ADB when running the defined instrument in a shell.

    Keyword arguments:
    package -- The package whom the TestRunner belongs to.
    instrument_runner -- Your Custom testrunner (default android.test.InstrumentationTestRunner)
    class_name -- The test class to execute. (default None)
    '''
    class_str  = "-e class %s/%s" % (package, class_name) if class_name else ''

    cmd = r'adb shell "am instrument -w %(clazz)s %(package)s/%(test_runner)s"' %\
          {'package': package,'test_runner': instrument_runner, 'clazz': class_str, }
    #        print cmd
    return subprocess.check_output(cmd, shell=True)
