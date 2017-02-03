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
# LoaderDispatchTableOutputGeneratorOptions - subclass of GeneratorOptions.
class LoaderDispatchTableOutputGeneratorOptions(GeneratorOptions):
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
                 alignFuncParam = 0):
        GeneratorOptions.__init__(self, filename, directory, apiname, profile,
                                  versions, emitversions, defaultExtensions,
                                  addExtensions, removeExtensions, sortProcedure)
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
# LoaderDispatchTableOutputGenerator - subclass of OutputGenerator.
# Generates dispatch table helper header files for LVL
class LoaderDispatchTableOutputGenerator(OutputGenerator):
    """Generate dispatch table helper header based on XML element attributes"""
    def __init__(self,
                 errFile = sys.stderr,
                 warnFile = sys.stderr,
                 diagFile = sys.stdout):
        OutputGenerator.__init__(self, errFile, warnFile, diagFile)

        # Internal state - accumulators for different inner block text
        self.core_instance_dispatch_list = [] # List of core entries for instance dispatch list
        self.ext_instance_dispatch_list = []  # List of extension entries for instance dispatch list
        self.instance_lookup_list = []        # List of lookup function entries for the instance dispatch list
        self.core_device_dispatch_list = []   # List of core entries for device dispatch list
        self.ext_device_dispatch_list = []    # List of extension entries for device dispatch list
        self.device_lookup_list = []          # List of lookup function entries for the device dispatch list
        self.commands = []                                # List of CommandData records for all Vulkan commands
        self.CommandData = namedtuple('CommandData', ['name', 'protect', 'cdecl'])

    #
    # Called once at the beginning of each run
    def beginFile(self, genOpts):
        OutputGenerator.beginFile(self, genOpts)
        # User-supplied prefix text, if any (list of strings)
        if (genOpts.prefixText):
            for s in genOpts.prefixText:
                write(s, file=self.outFile)
        # File Comment
        file_comment = '// *** THIS FILE IS GENERATED - DO NOT EDIT ***\n'
        file_comment += '// See loader_dispatch_init.py for modifications\n'
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
        copyright += ' * Author: Courtney Goeltzenleuchter <courtney@LunarG.com>\n'
        copyright += ' * Author: Jon Ashburn <jon@lunarg.com>\n'
        copyright += ' * Author: Mark Lobodzinski <mark@lunarg.com>\n'
        copyright += ' * Author: Mark Young <marky@lunarg.com>\n'
        copyright += ' */\n'

        preamble = ''

        if self.genOpts.filename == 'vk_loader_dispatch_init.h':
            preamble += '\n'
            preamble += '#include <vulkan/vulkan.h>\n'
            preamble += '#include <vulkan/vk_layer.h>\n'
            preamble += '#include <string.h>\n'
            preamble += '#include "loader.h"\n'
            preamble += '#include "vk_loader_platform.h"\n'
            preamble += '\n'
            preamble += '// Device extension error function\n'
            preamble += 'static VkResult VKAPI_CALL vkDevExtError(VkDevice dev) {\n'
            preamble += '    struct loader_device *found_dev;\n'
            preamble += '    // The device going in is a trampoline device\n'
            preamble += '    struct loader_icd_term *icd_term = loader_get_icd_and_device(dev, &found_dev, NULL);\n'
            preamble += '\n'
            preamble += '    if (icd_term)\n'
            preamble += '        loader_log(icd_term->this_instance, VK_DEBUG_REPORT_ERROR_BIT_EXT, 0,\n'
            preamble += '                   "Bad destination in loader trampoline dispatch,"\n'
            preamble += '                   "Are layers and extensions that you are calling enabled?");\n'
            preamble += '    return VK_ERROR_EXTENSION_NOT_PRESENT;\n'
            preamble += '}\n'
            preamble += '\n'

        else:
            preamble += '\n'
            preamble += '#pragma once\n'
            preamble += '\n'

        write(copyright, file=self.outFile)
        write(preamble, file=self.outFile)

    #
    # Write generate and write dispatch tables to output file
    def endFile(self):
        core_instance_table = ''
        extension_instance_table = ''
        instance_lookup_list = ''
        core_device_table = ''
        extension_device_table = ''
        device_lookup_list = ''
        loader_terms = ''
        dev_err_func = ''

        if self.genOpts.filename == 'vk_loader_dispatch_init.h':
            core_device_table += self.OutputLoaderCoreDispatchTable('device')
            extension_device_table += self.OutputLoaderExtensionDispatchTable('device')
            device_lookup_list += self.OutputLoaderLookupFunc('device')
            core_instance_table += self.OutputLoaderCoreDispatchTable('instance')
            extension_instance_table += self.OutputLoaderExtensionDispatchTable('instance')
            instance_lookup_list += self.OutputLoaderLookupFunc('instance')

            write(core_device_table, file=self.outFile);
            write(extension_device_table, file=self.outFile);
            write(device_lookup_list, file=self.outFile);
            write(core_instance_table, file=self.outFile);
            write(extension_instance_table, file=self.outFile);
            write(instance_lookup_list, file=self.outFile);

        else:
            loader_terms += self.OutputLoaderTerminators()
            write(loader_terms, file=self.outFile);

        # Finish processing in superclass
        OutputGenerator.endFile(self)

    #
    # Process commands, adding to appropriate dispatch tables
    def genCmd(self, cmdinfo, name):
        OutputGenerator.genCmd(self, cmdinfo, name)

        # Get first param type
        params = cmdinfo.elem.findall('param')
        info = self.getTypeNameTuple(params[0])

        if 'android' not in name.lower():
            self.AddCommandToDispatchList(name, cmdinfo, info[0])
    #
    # Check if the parameter passed in is a pointer
    def paramIsPointer(self, param):
        ispointer = 0
        paramtype = param.find('type')
        if (paramtype.tail is not None) and ('*' in paramtype.tail):
            ispointer = paramtype.tail.count('*')
        elif paramtype.text[:4] == 'PFN_':
            # Treat function pointer typedefs as a pointer to a single value
            ispointer = 1
        return ispointer
    #
    # Check if the parameter passed in is a static array
    def paramIsStaticArray(self, param):
        isstaticarray = 0
        paramname = param.find('name')
        if (paramname.tail is not None) and ('[' in paramname.tail):
            isstaticarray = paramname.tail.count('[')
        return isstaticarray
    #
    # Check if the parameter passed in is optional
    # Returns a list of Boolean values for comma separated len attributes (len='false,true')
    def paramIsOptional(self, param):
        # See if the handle is optional
        isoptional = False
        # Simple, if it's optional, return true
        optString = param.attrib.get('optional')
        if optString:
            if optString == 'true':
                isoptional = True
            elif ',' in optString:
                opts = []
                for opt in optString.split(','):
                    val = opt.strip()
                    if val == 'true':
                        opts.append(True)
                    elif val == 'false':
                        opts.append(False)
                    else:
                        print('Unrecognized len attribute value',val)
                isoptional = opts
        return isoptional
    #
    # Check if the handle passed in is optional
    # Uses the same logic as ValidityOutputGenerator.isHandleOptional
    def isHandleOptional(self, param, lenParam):
        # Simple, if it's optional, return true
        if param.isoptional:
            return True
        # If no validity is being generated, it usually means that validity is complex and not absolute, so let's say yes.
        if param.noautovalidity:
            return True
        # If the parameter is an array and we haven't already returned, find out if any of the len parameters are optional
        if lenParam and lenParam.isoptional:
            return True
        return False
    #
    # Generate a VkStructureType based on a structure typename
    def genVkStructureType(self, typename):
        # Add underscore between lowercase then uppercase
        value = re.sub('([a-z0-9])([A-Z])', r'\1_\2', typename)
        value = value.replace('D3_D12', 'D3D12')
        value = value.replace('Device_IDProp', 'Device_ID_Prop')
        # Change to uppercase
        value = value.upper()
        # Add STRUCTURE_TYPE_
        return re.sub('VK_', 'VK_STRUCTURE_TYPE_', value)
    #
    # Get the cached VkStructureType value for the specified struct typename, or generate a VkStructureType
    # value assuming the struct is defined by a different feature
    def getStructType(self, typename):
        value = None
        if typename in self.structTypes:
            value = self.structTypes[typename].value
        else:
            value = self.genVkStructureType(typename)
            self.logMsg('diag', 'ParameterValidation: Generating {} for {} structure type that was not defined by the current feature'.format(value, typename))
        return value

    # Retrieve the value of the len tag
    def getLen(self, param):
        result = None
        len = param.attrib.get('len')
        if len and len != 'null-terminated':
            # For string arrays, 'len' can look like 'count,null-terminated',
            # indicating that we have a null terminated array of strings.  We
            # strip the null-terminated from the 'len' field and only return
            # the parameter specifying the string count
            if 'null-terminated' in len:
                result = len.split(',')[0]
            else:
                result = len
            result = str(result).replace('::', '->')
        return result

    #
    # Determine if this API should be ignored or added to the instance or device dispatch table
    def AddCommandToDispatchList(self, name, cmdinfo, handle_type):
        handle = self.registry.tree.find("types/type/[name='" + handle_type + "'][@category='handle']")
        if handle != None and handle_type != 'VkInstance' and handle_type != 'VkPhysicalDevice':
            if ('KHR' not in name and
                'KHX' not in name and
                'EXT' not in name and
                'AMD' not in name and
                'ARM' not in name and
                'GOOGLE' not in name and
                'LUNARG' not in name and
                'NN' not in name and
                'NV' not in name):
                self.core_device_dispatch_list.append((name, self.featureExtraProtect))
                self.device_lookup_list.append((name, self.featureExtraProtect))
            else:
                self.ext_device_dispatch_list.append((name, self.featureExtraProtect))

                # Only device extensions requiring a trampoline/terminator should
                # be added to the lookup list here.
                if (name in loader_constants.DEVICE_CMDS_NEED_TERM):
                    self.device_lookup_list.append((name, self.featureExtraProtect))
        else:
            if ('KHR' not in name and
                'KHX' not in name and
                'EXT' not in name and
                'AMD' not in name and
                'ARM' not in name and
                'GOOGLE' not in name and
                'LUNARG' not in name and
                'NN' not in name and
                'NV' not in name):
                self.core_instance_dispatch_list.append((name, self.featureExtraProtect))

                # Generate a list of commands for use in printing the necessary
                # core instance terminator prototypes
                params = cmdinfo.elem.findall('param')
                lens = set()
                for param in params:
                    len = self.getLen(param)
                    if len:
                        lens.add(len)
                paramsInfo = []
                for param in params:
                    paramInfo = self.getTypeNameTuple(param)
                    cdecl = self.makeCParamDecl(param, 0)
                    iscount = False
                    if paramInfo[1] in lens:
                        iscount = True
                self.commands.append(self.CommandData(name=name, protect=self.featureExtraProtect,
                                                      cdecl=self.makeCDecls(cmdinfo.elem)[0]))

            else:
                self.ext_instance_dispatch_list.append((name, self.featureExtraProtect))

            self.instance_lookup_list.append((name, self.featureExtraProtect))

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

    #
    # Creates the prototypes for the loader's core instance command terminators
    def OutputLoaderTerminators(self):
        terminators = ''
        terminators += '// Loader core instance terminators\n'

        #terminators += 'VKAPI_ATTR VkResult VKAPI_CALL terminator_CreateInstance(const VkInstanceCreateInfo *pCreateInfo,\n'
        #terminators += '                                                         const VkAllocationCallbacks *pAllocator, VkInstance *pInstance);\n'

        for command in self.commands:
            mod_string = ''
            new_terminator = command.cdecl
            mod_string = new_terminator.replace("VKAPI_CALL vk", "VKAPI_CALL terminator_")

            if (command.protect != None):
                terminators += '#ifdef %s\n' % command.protect

            terminators += mod_string
            terminators += '\n'

            if (command.protect != None):
                terminators += '#endif // '
                terminators += command.protect
                terminators += '\n'

        #terminators += 'VKAPI_ATTR VkResult VKAPI_CALL terminator_CreateDevice(VkPhysicalDevice physicalDevice, const VkDeviceCreateInfo *pCreateInfo,\n'
        #terminators += '                                                       const VkAllocationCallbacks *pAllocator, VkDevice *pDevice);\n'

        return terminators

    #
    # Creates code to initialize a dispatch table from the appropriate list of
    # core entrypoints and return it as a string
    def OutputLoaderCoreDispatchTable(self, table_type):
        entries = []
        table = ''
        gpa_param = ''
        if table_type == 'device':
            gpa_param = 'dev'
            entries = self.core_device_dispatch_list
            table += '// Init Device function pointer dispatch table with core commands\n'
            table += 'static inline void loader_init_device_dispatch_table(struct loader_dev_dispatch_table *dev_table, PFN_vkGetDeviceProcAddr gpa,\n'
            table += '                                                     VkDevice dev) {\n'
            table += 'VkLayerDispatchTable *table = &dev_table->core_dispatch;\n'
            table += 'for (uint32_t i = 0; i < MAX_NUM_UNKNOWN_EXTS; i++) dev_table->ext_dispatch.dev_ext[i] = (PFN_vkDevExt)vkDevExtError;\n'
            table += '\n'
        else:
            entries = self.core_instance_dispatch_list
            gpa_param = 'inst'
            table += '// Init Instance function pointer dispatch table with core commands\n'
            table += 'static inline void loader_init_instance_core_dispatch_table(VkLayerInstanceDispatchTable *table, PFN_vkGetInstanceProcAddr gpa,\n'
            table += '                                                            VkInstance inst) {\n'

        for item in entries:
            # Remove 'vk' from proto name
            base_name = item[0][2:]

            if (base_name == 'CreateInstance' or base_name == 'CreateDevice' or
                base_name == 'EnumerateInstanceExtensionProperties' or
                base_name == 'EnumerateInstanceLayerProperties'):
                continue

            if item[1] is not None:
                table += '#ifdef %s\n' % item[1]

            table += '    table->%s = (PFN_%s)gpa(%s, "%s");\n' % (base_name, item[0], gpa_param, item[0])

            if item[1] is not None:
                table += '#endif // %s\n' % item[1]

        table += '}\n'

        return table

    #
    # Create code to initialize a dispatch table from the appropriate list of
    # extension entrypoints and return it as a string
    def OutputLoaderExtensionDispatchTable(self, table_type):
        entries = []
        table = ''
        gpa_param = ''
        if table_type == 'device':
            gpa_param = 'dev'
            entries = self.ext_device_dispatch_list
            table += '// Init Device function pointer dispatch table with extension commands\n'
            table += 'static inline void loader_init_device_extension_dispatch_table(struct loader_dev_dispatch_table *dev_table,\n'
            table += '                                                               PFN_vkGetDeviceProcAddr gpa, VkDevice dev) {\n'
            table += '    VkLayerDispatchTable *table = &dev_table->core_dispatch;\n'
            table += '\n'
        else:
            entries = self.ext_instance_dispatch_list
            gpa_param = 'inst'
            table += '// Init Instance function pointer dispatch table with core commands\n'
            table += 'static inline void loader_init_instance_extension_dispatch_table(VkLayerInstanceDispatchTable *table, PFN_vkGetInstanceProcAddr gpa,\n'
            table += '                                                                 VkInstance inst) {\n'

        for item in entries:
            # Remove 'vk' from proto name
            base_name = item[0][2:]

            if (base_name == 'CreateInstance' or base_name == 'CreateDevice' or
                base_name == 'EnumerateInstanceExtensionProperties' or
                base_name == 'EnumerateInstanceLayerProperties'):
                continue

            if item[1] is not None:
                table += '#ifdef %s\n' % item[1]
            table += '    table->%s = (PFN_%s)gpa(%s, "%s");\n' % (base_name, item[0], gpa_param, item[0])
            if item[1] is not None:
                table += '#endif // %s\n' % item[1]
        table += '}\n'

        return table

    #
    # Create a lookup table function from the appropriate list of entrypoints and
    # return it as a string
    def OutputLoaderLookupFunc(self, table_type):
        entries = []
        table = ''
        if table_type == 'device':
            entries = self.device_lookup_list
            table += '// Device command lookup function\n'
            table += 'static inline void *loader_lookup_device_dispatch_table(const VkLayerDispatchTable *table, const char *name) {\n'
            table += '    if (!name || name[0] != \'v\' || name[1] != \'k\') return NULL;\n'
            table += '\n'
            table += '    name += 2;\n'
        else:
            entries = self.instance_lookup_list
            table += '// Instance command lookup function\n'
            table += 'static inline void *loader_lookup_instance_dispatch_table(const VkLayerInstanceDispatchTable *table, const char *name,\n'
            table += '                                                          bool *found_name) {\n'
            table += '    if (!name || name[0] != \'v\' || name[1] != \'k\') {\n'
            table += '        *found_name = false;\n'
            table += '        return NULL;\n'
            table += '    }\n'
            table += '\n'
            table += '    *found_name = true;\n'
            table += '    name += 2;\n'

        for item in entries:
            # Remove 'vk' from proto name
            base_name = item[0][2:]

            if (base_name == 'CreateInstance' or base_name == 'CreateDevice' or
                base_name == 'EnumerateInstanceExtensionProperties' or
                base_name == 'EnumerateInstanceLayerProperties'):
                continue

            if item[1] is not None:
                table += '#ifdef %s\n' % item[1]

            table += '    if (!strcmp(name, "%s")) return (void *)table->%s;\n' % (base_name, base_name)

            if item[1] is not None:
                table += '#endif // %s\n' % item[1]

        table += '\n'
        if table_type == 'instance':
            table += '    *found_name = false;\n'
        table += '    return NULL;\n'
        table += '}\n'

        return table
