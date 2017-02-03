#!/usr/bin/python3 -i
#
# Copyright (c) 2015-2017 The Khronos Group Inc.
# Copyright (c) 2015-2017 Valve Corporation
# Copyright (c) 2015-2017 LunarG, Inc.
# Copyright (c) 2015-2017 Google Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
# Author: Mark Young <marky@lunarg.com>

import os,re,sys
import xml.etree.ElementTree as etree
import loader_constants
from generator import *
from collections import namedtuple

#
# IcdDispatchTableOutputGeneratorOptions - subclass of GeneratorOptions.
class IcdDispatchTableOutputGeneratorOptions(GeneratorOptions):
    def __init__(self,
                 filename = None,
                 directory = '.',
                 apiname = None,
                 profile = None,
                 versions = '.*',
                 emitversions = '.*',
                 defaultExtensions = None,
                 addExtensions = None,
                 removeExtensions = None,
                 sortProcedure = regSortFeatures,
                 prefixText = "",
                 genFuncPointers = True,
                 protectFile = True,
                 protectFeature = True,
                 protectProto = None,
                 protectProtoStr = None,
                 apicall = '',
                 apientry = '',
                 apientryp = '',
                 currentExtension = '',
                 extensionOfInterest = 0,
                 alignFuncParam = 0):
        GeneratorOptions.__init__(self, filename, directory, apiname, profile,
                                  versions, emitversions, defaultExtensions,
                                  addExtensions, removeExtensions, sortProcedure)
        self.filename        = filename
        self.prefixText      = prefixText
        self.genFuncPointers = genFuncPointers
        self.prefixText      = None
        self.protectFile     = protectFile
        self.protectFeature  = protectFeature
        self.protectProto    = protectProto
        self.protectProtoStr = protectProtoStr
        self.apicall         = apicall
        self.apientry        = apientry
        self.apientryp       = apientryp
        self.alignFuncParam  = alignFuncParam
#
# IcdDispatchTableOutputGenerator - subclass of OutputGenerator.
# Generates dispatch table helper header files for LVL
class IcdDispatchTableOutputGenerator(OutputGenerator):
    """Generate dispatch table helper header based on XML element attributes"""
    def __init__(self,
                 errFile = sys.stderr,
                 warnFile = sys.stderr,
                 diagFile = sys.stdout):
        OutputGenerator.__init__(self, errFile, warnFile, diagFile)
        # Internal state - accumulators for different inner block text
        self.dispatch_list = []      # List of entries for icd dispatch list
        self.inst_ext_list = []      # List of instance extensions that we need flags for
    #
    # Called once at the beginning of each run
    def beginFile(self, genOpts):
        preamble = ''

        OutputGenerator.beginFile(self, genOpts)
        # User-supplied prefix text, if any (list of strings)
        if (genOpts.prefixText):
            for s in genOpts.prefixText:
                write(s, file=self.outFile)
        # File Comment
        file_comment = '// *** THIS FILE IS GENERATED - DO NOT EDIT ***\n'
        file_comment += '// See icd_dispatch_table_generator.py for modifications\n'
        write(file_comment, file=self.outFile)
        # Copyright Notice
        copyright =  '/*\n'
        copyright += ' * Copyright (c) 2015-2017 The Khronos Group Inc.\n'
        copyright += ' * Copyright (c) 2015-2017 Valve Corporation\n'
        copyright += ' * Copyright (c) 2015-2017 LunarG, Inc.\n'
        copyright += ' *\n'
        copyright += ' * Licensed under the Apache License, Version 2.0 (the "License");\n'
        copyright += ' * you may not use this file except in compliance with the License.\n'
        copyright += ' * You may obtain a copy of the License at\n'
        copyright += ' *\n'
        copyright += ' *     http://www.apache.org/licenses/LICENSE-2.0\n'
        copyright += ' *\n'
        copyright += ' * Unless required by applicable law or agreed to in writing, software\n'
        copyright += ' * distributed under the License is distributed on an "AS IS" BASIS,\n'
        copyright += ' * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.\n'
        copyright += ' * See the License for the specific language governing permissions and\n'
        copyright += ' * limitations under the License.\n'
        copyright += ' *\n'
        copyright += ' * Author: Mark Young <marky@lunarg.com>\n'
        copyright += ' */\n'

        if self.genOpts.filename == 'vk_icd_dispatch_table.h':

            preamble += '#pragma once\n'

        else:

            preamble += '#define _GNU_SOURCE\n'
            preamble += '#include <stdio.h>\n'
            preamble += '#include <stdlib.h>\n'
            preamble += '#include <string.h>\n'
            preamble += '#include "vk_loader_platform.h"\n'
            preamble += '#include "loader.h"\n'
            preamble += '#include "vk_icd_dispatch_table.h"\n'
            preamble += '#include "vk_loader_dispatch_init.h"\n'
            preamble += '#include <vulkan/vk_icd.h>\n'
            preamble += '#include "wsi.h"\n'

        write(copyright, file=self.outFile)
        write(preamble, file=self.outFile)

    #
    # Write generate and write dispatch tables to output file
    def endFile(self):
        dispatch_table = ''

        if self.genOpts.filename == 'vk_icd_dispatch_table.h':
            union_def = ''
            icd_init_proto = ''

            # Write out the dispatch table
            dispatch_table += self.OutputIcdDispatchTable()
            write(dispatch_table, file=self.outFile);

            # Add loader instance extension enables union
            union_def += self.OutputIcdExtensionEnableUnion()
            write(union_def, file=self.outFile)

            # Write out the icd init prototype
            icd_init_proto += 'struct loader_icd_term;\n'
            icd_init_proto += 'VKAPI_ATTR bool VKAPI_CALL loader_icd_init_entries(struct loader_icd_term *icd_term, VkInstance inst,\n'
            icd_init_proto += '                                                   const PFN_vkGetInstanceProcAddr fp_gipa);\n'

            write(icd_init_proto, file=self.outFile)

        else:

            # Write out the dispatch table initialization
            dispatch_table += self.OutputIcdDispatchTableInit()
            write(dispatch_table, file=self.outFile);

        # Finish processing in superclass
        OutputGenerator.endFile(self)
    #
    # Process commands, adding to appropriate dispatch tables
    def genCmd(self, cmdinfo, name):
        OutputGenerator.genCmd(self, cmdinfo, name)

        avoid_entries = ['vkCreateInstance',
                         'vkGetInstanceProcAddr']
        # Get first param type
        params = cmdinfo.elem.findall('param')
        info = self.getTypeNameTuple(params[0])

        if name not in avoid_entries:
            self.AddCommandToDispatchList(name, info[0], self.featureExtraProtect)
            self.commands.append(name)

    #
    # Determine if this API should be ignored or added to the instance or device dispatch table
    def AddCommandToDispatchList(self, name, handle_type, protect):
        handle = self.registry.tree.find("types/type/[name='" + handle_type + "'][@category='handle']")
        if handle == None:
            return

        if ((handle_type == 'VkInstance' or handle_type == 'VkPhysicalDevice' or
             name in loader_constants.DEVICE_CMDS_NEED_TERM) and
            (name != 'vkGetInstanceProcAddr' and name != 'vkEnumerateDeviceLayerProperties')):
            self.dispatch_list.append((name, self.featureExtraProtect))
        return
    #
    # Retrieve the type and name for a parameter
    def getTypeNameTuple(self, param):
        type = ''
        name = ''
        for elem in param:
            if elem.tag == 'type':
                type = noneStr(elem.text)
            elif elem.tag == 'name':
                name = noneStr(elem.text)
        return (type, name)

    def beginFeature(self, interface, emit):
        # Start processing in superclass
        OutputGenerator.beginFeature(self, interface, emit)

        self.commands = []
        self.currentExtension = ''
        self.extensionOfInterest = 0

        if 'instance' == interface.get('type'):
            name = interface.get('name')

            if name not in loader_constants.WSI_EXT_NAMES and 'android' not in name:
                self.extensionOfInterest = 1
                self.currentExtension = name 

    def endFeature(self):

        if self.extensionOfInterest == 1 and self.commands:
            self.inst_ext_list.append(self.currentExtension)

        # Finish processing in superclass
        OutputGenerator.endFeature(self)

    #
    # Create a dispatch table from the appropriate list and return it as a string
    def OutputIcdDispatchTable(self):
        entries = []
        table = ''
        entries = self.dispatch_list
        table += '// Instance function pointer dispatch table\n'
        table += 'struct loader_icd_term_dispatch {\n'

        for item in entries:
            # Remove 'vk' from proto name
            base_name = item[0][2:]

            if item[1] is not None:
                table += '#ifdef %s\n' % item[1]
            table += '    PFN_%s %s;\n' % (item[0], base_name)
            if item[1] is not None:
                table += '#endif // %s\n' % item[1]
        table += '};\n'

        return table

    #
    # Init a dispatch table from the appropriate list and return it as a string
    def OutputIcdDispatchTableInit(self):
        entries = []
        table = ''
        entries = self.dispatch_list
        table += 'VKAPI_ATTR bool VKAPI_CALL loader_icd_init_entries(struct loader_icd_term *icd_term, VkInstance inst,\n'
        table += '                                                   const PFN_vkGetInstanceProcAddr fp_gipa) {\n'
        table += '\n'
        table += '#define LOOKUP_GIPA(func, required)                                                        \\\n'
        table += '    do {                                                                                   \\\n'
        table += '        icd_term->dispatch.func = (PFN_vk##func)fp_gipa(inst, "vk" #func);                 \\\n'
        table += '        if (!icd_term->dispatch.func && required) {                                        \\\n'
        table += '            loader_log((struct loader_instance *)inst, VK_DEBUG_REPORT_WARNING_BIT_EXT, 0, \\\n'
        table += '                       loader_platform_get_proc_address_error("vk" #func));                \\\n'
        table += '            return false;                                                                  \\\n'
        table += '        }                                                                                  \\\n'
        table += '    } while (0)\n'
        table += '\n'

        for item in entries:
            # Remove 'vk' from proto name
            base_name = item[0][2:]

            if item[1] is not None:
                table += '#ifdef %s\n' % item[1]
            if ('KHR' not in base_name and
                'KHX' not in base_name and
                'EXT' not in base_name and
                'AMD' not in base_name and
                'ARM' not in base_name and
                'GOOGLE' not in base_name and
                'LUNARG' not in base_name and
                'NN' not in base_name and
                'NV' not in base_name):
                table += '    LOOKUP_GIPA(%s, true);\n' % (base_name)
            else:
                table += '    LOOKUP_GIPA(%s, false);\n' % (base_name)
            if item[1] is not None:
                table += '#endif // %s\n' % item[1]

        table += '\n'
        table += '#undef LOOKUP_GIPA\n'
        table += '\n'
        table += '    return true;\n'
        table += '};\n'

        return table

    #
    # Create the extension enable union
    def OutputIcdExtensionEnableUnion(self):
        entries = []
        entries = self.inst_ext_list

        union = ''
        union += 'union loader_instance_extension_enables {\n'
        union += '    struct {\n'
        for item in entries:
            union += '        uint8_t %s : 1;\n' % item[3:].lower()
        union += '    };\n'
        union += '    uint64_t padding[4];\n'
        union += '};\n'
        return union

