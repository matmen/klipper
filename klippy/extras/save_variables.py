# Save arbitrary variables so that values can be kept across restarts.
#
# Copyright (C) 2020 Dushyant Ahuja <dusht.ahuja@gmail.com>
# Copyright (C) 2016-2020  Kevin O'Connor <kevin@koconnor.net>
#
# This file may be distributed under the terms of the GNU GPLv3 license.
import os, logging, ast, configparser

class SaveVariables:
    def __init__(self, config):
        self.printer = config.get_printer()
        self.filename = os.path.expanduser(config.get('filename'))
        self.allSections = {}
        self.printer.register_event_handler('klippy:connect', self.handle_connect)
        gcode = self.printer.lookup_object('gcode')
        gcode.register_command('SAVE_VARIABLE', self.cmd_SAVE_VARIABLE,
                               desc=self.cmd_SAVE_VARIABLE_help)
    def handle_connect(self):
        try:
            if not os.path.exists(self.filename):
                open(self.filename, "w").close()
            self.loadVariables()
        except self.printer.command_error as e:
            raise self.printer.config_error(str(e))
    def loadVariables(self):
        allsections = {}
        varfile = configparser.ConfigParser()
        try:
            varfile.read(self.filename)
            for sname in varfile.sections():
                for vname, val in varfile.items(sname):
                    if sname not in allsections:
                        allsections[sname] = {}
                    allsections[sname][vname] = ast.literal_eval(val)

            for mname, macro in self.printer.lookup_objects('gcode_macro'):
                if hasattr(macro, 'variables'):
                    if mname in allsections:
                        vars = dict(macro.variables)
                        for vname, val in allsections[mname].items():
                            vars[vname] = val
                        macro.variables = vars
        except:
            msg = "Unable to parse existing variable file"
            logging.exception(msg)
            raise self.printer.command_error(msg)
        self.allSections = allsections
    cmd_SAVE_VARIABLE_help = "Save arbitrary variables to disk"
    def cmd_SAVE_VARIABLE(self, gcmd):
        varname = gcmd.get('VARIABLE')
        value = gcmd.get('VALUE')
        macroname = gcmd.get('MACRO', None)
        macro_section = None
        try:
            value = ast.literal_eval(value)
        except ValueError as e:
            raise gcmd.error("Unable to parse '%s' as a literal" % (value,))

        if macroname is not None:
            macros = self.printer.lookup_objects('gcode_macro')
            for mname, macro in macros:
                if hasattr(macro, 'alias') and macro.alias == macroname:
                    if not hasattr(macro, 'variables') or not varname in macro.variables:
                        raise gcmd.error("Unknwon gcode_macro variable '%s'" % (varname,))
                    vars = dict(macro.variables)
                    vars[varname] = value
                    macro.variables = vars
                    macro_section = mname
                    break
            if macro_section is None:
                raise gcmd.error("Unknown gcode_macro '%s'" % (macroname,))

        section = macro_section if macro_section is not None else 'Variables'
        newsections = dict(self.allSections)
        if not section in newsections:
            newsections[section] = {}
        newsections[section][varname] = value
        # Write file
        varfile = configparser.ConfigParser()
        varfile.add_section('Variables')
        for sname in sorted(newsections.keys()):
            if not varfile.has_section(sname):
                varfile.add_section(sname)
            for vname, val in sorted(newsections[sname].items()):
                varfile.set(sname, vname, repr(val))
        try:
            f = open(self.filename, "w")
            varfile.write(f)
            f.close()
        except:
            msg = "Unable to save variable"
            logging.exception(msg)
            raise gcmd.error(msg)
        self.loadVariables()
    def get_status(self, eventtime):
        status = {'variables': {}}
        for sname, val in self.allSections.items():
            if sname == 'Variables':
                sname = 'variables'
            else:
                if not sname in status:
                    status[sname] = {}
                status[sname] = val
        return status

def load_config(config):
    return SaveVariables(config)
