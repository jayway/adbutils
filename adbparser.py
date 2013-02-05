#!/usr/bin/env python
'''A Python module containing functionality for parsing and creating junit reports form adb test runners output.
'''
import xml.etree.ElementTree as ET
import xml.dom.minidom
import os
import logging

__author__    = 'Andreas Nilsson'
__email__     = 'andreas.nilsson@jayway.com'
__copyright__ = "Copyright 2013, Jayway"
__license__   = 'Apache 2.0'

#Constants
_COLON_CHAR  = ':'
_EQUALS_CHAR = '='
_DOT_CHAR    = '.'

#Logger
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

#Formatter
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

#Setup Console logging
ch = logging.StreamHandler()
ch.setLevel(logging.DEBUG)
ch.setFormatter(formatter)

#Add logger handlers
logger.addHandler(ch)


_process_error_words = ['INSTRUMENTATION_RESULT', 'INSTRUMENTATION_CODE']

class TestObject(object):
    '''The parsed representation from the adb output of running an instrument.'''
    class_name = ''

    # Dict format: {method : (type, details)}
    erroneous_methods = dict()
    _last_failed_method = None

    def __init__(self, class_name=''):
        self.class_name = class_name
        self.erroneous_methods = dict()
        self._last_failed_method = 'Unknown Method'

    def __str__(self):
        str = 'class:\n%s\n' % self.class_name
        str += 'failed methods:\n'
        for key in self.erroneous_methods:
            str += key + '\n'
            type, details = self.erroneous_methods[key]
            str += 'type: %s\n' % type
            str += 'details: %s\n' % details

        return str


    def add_failed_method(self, method_name):
        self._last_failed_method = method_name
        self.erroneous_methods[method_name] = (None, None)


    def has_failures(self):
        return True if self.erroneous_methods else False


    def add_error(self, error_type, error_details):
        '''
        Adds an error for the last registered method.
        Limitation: There could be only one error per method
        '''
        if self._last_failed_method:
            self.erroneous_methods[self._last_failed_method] = (error_type, error_details)


    def get_error(self, method_name):
        '''
        Returns the error for a specific method name.
        '''
        if self.erroneous_methods[method_name]:
            return self.erroneous_methods[method_name]
        else:
            return None


def _is_line_process_crash(line):
    return any(word in line for word in _process_error_words)


def _parse_test_object_from_line(line):
    test_obj = None
    split = line.split(_COLON_CHAR)

    if len(split) > 1:
        class_line = split[0]
        # checks that there is at least two dots thus giving us confidence
        # That it is probably a class name on that line.
        if class_line.count(_DOT_CHAR) > 2:
            test_obj = TestObject(class_line)


    if not test_obj:
        logger.error('Could not parse object from line: %s', line)
    return test_obj


def _parse_process_crash_error(line, next_line):
    error_type = None
    error_details = None
    split = line.split(_COLON_CHAR)
    if len(split) > 1 and 'shortMsg' in line:
        if len(line.split(_EQUALS_CHAR)) > 1:
            error_type = line.split(_EQUALS_CHAR)[1]

            #next line has full msg
            if next_line and 'longMsg' in next_line:
                error_details = next_line.split(_EQUALS_CHAR)[1]

    return error_type, error_details


def parse_adb_output(output):
    try:
        logger.debug("ADB Output: %s", output)
        lines = output.splitlines()
        all_objects = []
        test_obj = None

        for i, line in enumerate(lines):
            line = line.strip('\t').strip()

            if not line:
                continue

            is_failure = line.startswith('Failure')
            is_stacktrace = line.startswith('at')
            is_type_of_fail_line = line.startswith('junit')
            is_last_parse_line = 'Test results for' in line

            if is_last_parse_line:
                break
            elif is_failure:
                if 'in' in line:
                    failed_method = line.split('in')[1].strip(" :")
                    if failed_method and test_obj:
                        test_obj.add_failed_method(failed_method)
            elif is_type_of_fail_line:
                split = line.split(_COLON_CHAR)
                if len(split) > 1:
                    error_type = split[0]
                    error_details = line

                    if error_type:
                        test_obj.add_error(error_type, error_details)
            elif is_stacktrace:
                pass
            else:
                new_test_obj = _parse_test_object_from_line(line)

                if new_test_obj:
                    test_obj = new_test_obj
                    all_objects.append(test_obj)
                else:
                    logger.debug('Failed to parse object from line "%s', line)

            if _is_line_process_crash(line):
                next_line = None

                try:
                    next_line = lines[i + 1]
                except IndexError:
                    pass

                error_type, error_details = _parse_process_crash_error(line, next_line)

                if error_type:
                    test_obj.add_error(error_type, error_details)

        logger.info("Created %d test objects" % len(all_objects))
        logger.info("Objects failed: %d" % get_no_failed_objects(all_objects))
        return all_objects
    except Exception as e:
        logger.error(e.message)
        logger.error('Failed to parse adb output properly')
        return []



def parse_and_generate_xml(adb_output):
    return generate_junit_xml_report(parse_adb_output(adb_output))


def generate_junit_xml_report(test_objects, success_message='Successful'):
    test_suite = ET.Element('testsuite')

    for obj in test_objects:
        if obj.has_failures():
            for method_name in obj.erroneous_methods:
                type, details = obj.get_error(method_name)

                test_case = ET.SubElement(test_suite, 'testcase', {'classname': obj.class_name, 'name': method_name})

                failure = ET.SubElement(test_case, 'failure', {'type': type})
                failure.text = details

        else:
            ET.SubElement(test_suite, 'testcase', {'classname': obj.class_name, 'name': success_message})

    x = xml.dom.minidom.parseString(ET.tostring(test_suite))
    return x.toprettyxml()


def get_no_failed_objects(test_objects):
    return sum(obj.has_failures() for obj in test_objects)


def write_to_file(filename, report, use_relative_path=True):
    if filename:
        full_filename = os.getcwd() + os.sep + filename if use_relative_path else filename

        out_file = open(full_filename, 'w')

        #noinspection PyCompatibility
        try:
            out_file.write(report)
        except IOError:
            logger.error('failed to write file to disk: ' + str(IOError.message))
        finally:
            logger.info('Wrote report to file: %s', full_filename)
            out_file.close()
    else:
        logger.error('A proper filename not provided')

