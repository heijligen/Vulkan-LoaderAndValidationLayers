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
# LoaderExtensionGeneratorOptions - subclass of GeneratorOptions.
class LoaderExtensionGeneratorOptions(GeneratorOptions):
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
                 alignFuncParam = 0,
                 currentExtension = '',
                 extensionOfInterest = 0):
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
# LoaderExtensionOutputGenerator - subclass of OutputGenerator.
# Generates dispatch table helper header files for LVL
class LoaderExtensionOutputGenerator(OutputGenerator):
    """Generate dispatch table helper header based on XML element attributes"""
    def __init__(self,
                 errFile = sys.stderr,
                 warnFile = sys.stderr,
                 diagFile = sys.stdout):
        OutputGenerator.__init__(self, errFile, warnFile, diagFile)

        # Internal state - accumulators for different inner block text
        self.core_instance_dispatch_list = [] # List of core entries for instance dispatch list
        self.ext_instance_dispatch_list = []  # List of extension entries for instance dispatch list
        self.core_device_dispatch_list = []   # List of core entries for device dispatch list
        self.ext_device_dispatch_list = []    # List of extension entries for device dispatch list
        self.core_commands = []               # List of CommandData records for core Vulkan commands
        self.ext_commands = []                # List of CommandData records for extension Vulkan commands
        self.CommandData = namedtuple('CommandData', ['name', 'protect', 'cdecl'])
        self.CommandParam = namedtuple('CommandParam', ['type', 'name', 'cdecl'])
        self.ExtCommandData = namedtuple('ExtCommandData', ['name', 'ext_name', 'ext_type', 'protect', 'return_type', 'handle_type', 'params', 'cdecl'])
        self.instanceExtensions = []
        self.ExtensionData = namedtuple('ExtensionData', ['name', 'protect', 'num_commands'])

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
        file_comment += '// See loader_extension_generator.py for modifications\n'
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
        copyright += ' * Author: Mark Lobodzinski <mark@lunarg.com>\n'
        copyright += ' * Author: Mark Young <marky@lunarg.com>\n'
        copyright += ' */\n'

        preamble = ''
        preamble += '\n'
        preamble += '#define _GNU_SOURCE\n'
        preamble += '#include <stdio.h>\n'
        preamble += '#include <stdlib.h>\n'
        preamble += '#include <string.h>\n'
        preamble += '#include "vk_loader_platform.h"\n'
        preamble += '#include "loader.h"\n'
        preamble += '#include "vk_loader_dispatch_init.h"\n'
        preamble += '#include <vulkan/vk_icd.h>\n'
        preamble += '#include "vk_loader_core_terminators.h"\n'
        preamble += '#include "wsi.h"\n'
        preamble += '#include "debug_report.h"\n'
        preamble += '\n'

        write(copyright, file=self.outFile)
        write(preamble, file=self.outFile)

    #
    # Write generate and write dispatch tables to output file
    def endFile(self):
        file_data = ''

        file_data += self.CreateTrampTermFuncs()
        file_data += self.InstExtensionGPA()
        file_data += self.InstantExtensionCreate()
        file_data += self.DeviceExtensionGetTerminator()
        file_data += self.InitInstLoaderExtensionDispatchTable()
        file_data += self.OutputInstantExtensionWhitelistArray()
        write(file_data, file=self.outFile);

        # Finish processing in superclass
        OutputGenerator.endFile(self)

    def beginFeature(self, interface, emit):
        # Start processing in superclass
        OutputGenerator.beginFeature(self, interface, emit)

        self.currentExtension = ''
        self.extensionOfInterest = 0
        self.type = interface.get('type')
        self.num_commands = 0

        name = interface.get('name')
        self.currentExtension = name 

        if 'android' not in name:
            self.extensionOfInterest = 1

    #
    # Process commands, adding to appropriate dispatch tables
    def genCmd(self, cmdinfo, name):
        OutputGenerator.genCmd(self, cmdinfo, name)

        # Get first param type
        params = cmdinfo.elem.findall('param')
        info = self.getTypeNameTuple(params[0])

        self.num_commands += 1

        if 'android' not in name:
            self.AddCommandToDispatchList(self.currentExtension, self.type, name, cmdinfo, info[0])

    def endFeature(self):

        if self.extensionOfInterest == 1 and self.type == 'instance':
            self.instanceExtensions.append(self.ExtensionData(name=self.currentExtension,
                                                              protect=self.featureExtraProtect,
                                                              num_commands=self.num_commands))

        # Finish processing in superclass
        OutputGenerator.endFeature(self)

    #
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
    def AddCommandToDispatchList(self, extension_name, extension_type, name, cmdinfo, handle_type):
        handle = self.registry.tree.find("types/type/[name='" + handle_type + "'][@category='handle']")

        return_type =  cmdinfo.elem.find('proto/type')
        if (return_type != None and return_type.text == 'void'):
           return_type = None

        cmd_params = []

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
            param_type = paramInfo[0]
            param_name = paramInfo[1]
            param_cdecl = self.makeCParamDecl(param, 0)
            cmd_params.append(self.CommandParam(type=param_type, name=param_name,
                                                cdecl=param_cdecl))

        if handle != None and handle_type != 'VkInstance' and handle_type != 'VkPhysicalDevice':
            if not loader_constants.IsCommandExtension(name):
                self.core_device_dispatch_list.append((name, self.featureExtraProtect))
            else:
                self.ext_device_dispatch_list.append((name, self.featureExtraProtect))
                self.ext_commands.append(
                    self.ExtCommandData(name=name, ext_name=extension_name,
                                        ext_type=extension_type,
                                        protect=self.featureExtraProtect,
                                        return_type = return_type,
                                        handle_type = handle_type,
                                        params = cmd_params,
                                        cdecl=self.makeCDecls(cmdinfo.elem)[0]))
        else:
            if not loader_constants.IsCommandExtension(name):
                self.core_instance_dispatch_list.append((name, self.featureExtraProtect))

                self.core_commands.append(
                    self.CommandData(name=name, protect=self.featureExtraProtect,
                                     cdecl=self.makeCDecls(cmdinfo.elem)[0]))

            else:
                self.ext_instance_dispatch_list.append((name, self.featureExtraProtect))
                self.ext_commands.append(
                    self.ExtCommandData(name=name, ext_name=extension_name,
                                        ext_type=extension_type,
                                        protect=self.featureExtraProtect,
                                        return_type = return_type,
                                        handle_type = handle_type,
                                        params = cmd_params,
                                        cdecl=self.makeCDecls(cmdinfo.elem)[0]))

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
    # Create the appropriate trampoline (and possibly terminator) functinos
    def CreateTrampTermFuncs(self):
        entries = []
        funcs = ''

        for ext_cmd in self.ext_commands:
            if (ext_cmd.ext_name in loader_constants.WSI_EXT_NAMES or
                ext_cmd.ext_name in loader_constants.AVOID_EXT_NAMES):
                continue

            if ext_cmd.protect is not None:
                funcs += '#ifdef %s\n' % ext_cmd.protect

            tramp_header = ext_cmd.cdecl.replace(";", " {\n")
            return_prefix = '    '
            base_name = ext_cmd.name[2:]
            has_surface = 0
            requires_terminator = 0

            for param in ext_cmd.params:
                if param.type == 'VkSurfaceKHR':
                    has_surface = 1

            if (ext_cmd.return_type != None):
                return_prefix += 'return '

            if (ext_cmd.ext_type == 'instance' or ext_cmd.handle_type == 'VkPhysicalDevice' or
                'DebugMarkerSetObject' in ext_cmd.name):
                requires_terminator = 1

            if requires_terminator == 1:
                term_header = tramp_header.replace("VKAPI_CALL vk", "VKAPI_CALL terminator_")

                funcs += tramp_header

                if ext_cmd.handle_type == 'VkPhysicalDevice':
                    funcs += '    const VkLayerInstanceDispatchTable *disp;\n'
                    funcs += '    VkPhysicalDevice unwrapped_phys_dev = loader_unwrap_physical_device(physicalDevice);\n'
                    funcs += '    disp = loader_get_instance_layer_dispatch(physicalDevice);\n'
                elif ext_cmd.handle_type == 'VkInstance':
                    funcs += '#error("Not implemented");\n'
                else:
                    funcs += '    const VkLayerDispatchTable *disp = loader_get_dispatch('
                    funcs += ext_cmd.params[0].name
                    funcs += ');\n'

                if 'DebugMarkerSetObject' in ext_cmd.name:
                    funcs += '    // If this is a physical device, we have to replace it with the proper one for the next call.\n'
                    funcs += '    if (%s->objectType == VK_DEBUG_REPORT_OBJECT_TYPE_PHYSICAL_DEVICE_EXT) {\n' % (ext_cmd.params[1].name)
                    funcs += '        struct loader_physical_device_tramp *phys_dev_tramp = (struct loader_physical_device_tramp *)(uintptr_t)%s->object;\n' % (ext_cmd.params[1].name)
                    funcs += '        %s->object = (uint64_t)(uintptr_t)phys_dev_tramp->phys_dev;\n' % (ext_cmd.params[1].name)
                    funcs += '    }\n'

                funcs += return_prefix
                funcs += 'disp->'
                funcs += base_name
                funcs += '('
                count = 0
                for param in ext_cmd.params:
                    if count != 0:
                        funcs += ', '

                    if param.type == 'VkPhysicalDevice':
                        funcs += 'unwrapped_phys_dev'
                    else:
                        funcs += param.name

                    count += 1
                funcs += ');\n'
                funcs += '}\n\n'

                funcs += term_header
                if ext_cmd.handle_type == 'VkPhysicalDevice':
                    funcs += '    struct loader_physical_device_term *phys_dev_term = (struct loader_physical_device_term *)physicalDevice;\n'
                    funcs += '    struct loader_icd_term *icd_term = phys_dev_term->this_icd_term;\n'
                    funcs += '    if (NULL == icd_term->dispatch.'
                    funcs += base_name
                    funcs += ') {\n'
                    if base_name == 'GetPhysicalDeviceExternalImageFormatPropertiesNV':
                        funcs += '        if (externalHandleType) {\n'
                        funcs += '            return VK_ERROR_FORMAT_NOT_SUPPORTED;\n'
                        funcs += '        }\n'
                        funcs += '        if (!icd_term->dispatch.GetPhysicalDeviceImageFormatProperties) {\n'
                        funcs += '            return VK_ERROR_INITIALIZATION_FAILED;\n'
                        funcs += '        }\n'
                        funcs += '        pExternalImageFormatProperties->externalMemoryFeatures = 0;\n'
                        funcs += '        pExternalImageFormatProperties->exportFromImportedHandleTypes = 0;\n'
                        funcs += '        pExternalImageFormatProperties->compatibleHandleTypes = 0;\n'
                        funcs += '\n'

                        funcs += '    '
                        funcs += return_prefix
                        funcs += 'icd_term->dispatch.GetPhysicalDeviceImageFormatProperties(\n'
                        funcs += '            phys_dev_term->phys_dev, format, type, tiling, usage, flags, &pExternalImageFormatProperties->imageFormatProperties);\n'

                    else:
                        funcs += '        loader_log(icd_term->this_instance, VK_DEBUG_REPORT_ERROR_BIT_EXT, 0,\n'
                        funcs += '                   "ICD associated with VkPhysicalDevice does not support '
                        funcs += base_name
                        funcs += '");\n'

                    if has_surface == 1:
                        funcs += '        VkIcdSurface *icd_surface = (VkIcdSurface *)(surface);\n'
                        funcs += '        uint8_t icd_index = phys_dev_term->icd_index;\n'
                        funcs += '        if (NULL != icd_surface->real_icd_surfaces) {\n'
                        funcs += '            if (NULL != (void *)icd_surface->real_icd_surfaces[icd_index]) {\n'
                        funcs += '                return icd_term->dispatch.'
                        funcs += base_name
                        funcs += '('
                        count = 0
                        for param in ext_cmd.params:
                            if count != 0:
                                funcs += ', '

                            if param.type == 'VkPhysicalDevice':
                                funcs += 'phys_dev_term->phys_dev'
                            elif param.type == 'VkSurfaceKHR':
                                funcs += 'icd_surface->real_icd_surfaces[icd_index]'
                            else:
                                funcs += param.name

                            count += 1
                        funcs += ');\n'
                        funcs += '            }\n'
                        funcs += '        }\n'

                    funcs += '    }\n'

                    funcs += return_prefix
                    funcs += 'icd_term->dispatch.'
                    funcs += base_name
                    funcs += '('
                    count = 0
                    for param in ext_cmd.params:
                        if count != 0:
                            funcs += ', '

                        if param.type == 'VkPhysicalDevice':
                            funcs += 'phys_dev_term->phys_dev'
                        else:
                            funcs += param.name

                        count += 1
                    funcs += ');\n'

                elif ext_cmd.handle_type == 'VkInstance':
                    funcs += '#error("Not implemented");\n'

                else:
                    funcs += '    uint32_t icd_index = 0;\n'
                    funcs += '    struct loader_device *dev;\n'
                    funcs += '    struct loader_icd_term *icd_term = loader_get_icd_and_device(%s, &dev, &icd_index);\n' % (ext_cmd.params[0].name)
                    funcs += '    if (NULL != icd_term && NULL != icd_term->dispatch.'
                    funcs += base_name
                    funcs += ') {\n'
                    funcs += '        // If this is a physical device, we have to replace it with the proper one for the next call.\n'
                    funcs += '        if (%s->objectType == VK_DEBUG_REPORT_OBJECT_TYPE_PHYSICAL_DEVICE_EXT) {\n' % (ext_cmd.params[1].name)
                    funcs += '            struct loader_physical_device_term *phys_dev_term = (struct loader_physical_device_term *)(uintptr_t)%s->object;\n' % (ext_cmd.params[1].name)
                    funcs += '            %s->object = (uint64_t)(uintptr_t)phys_dev_term->phys_dev;\n' % (ext_cmd.params[1].name)
                    funcs += '        // If this is a KHR_surface, and the ICD has created its own, we have to replace it with the proper one for the next call.\n'
                    funcs += '        } else if (%s->objectType == VK_DEBUG_REPORT_OBJECT_TYPE_SURFACE_KHR_EXT) {\n' % (ext_cmd.params[1].name)
                    funcs += '            if (NULL != icd_term && NULL != icd_term->dispatch.CreateSwapchainKHR) {\n'
                    funcs += '                VkIcdSurface *icd_surface = (VkIcdSurface *)(uintptr_t)%s->object;\n' % (ext_cmd.params[1].name)
                    funcs += '                if (NULL != icd_surface->real_icd_surfaces) {\n'
                    funcs += '                    %s->object = (uint64_t)icd_surface->real_icd_surfaces[icd_index];\n' % (ext_cmd.params[1].name)
                    funcs += '                }\n'
                    funcs += '            }\n'
                    funcs += '        }\n'
                    funcs += '        return icd_term->dispatch.'
                    funcs += base_name
                    funcs += '('
                    count = 0
                    for param in ext_cmd.params:
                        if count != 0:
                            funcs += ', '

                        if param.type == 'VkPhysicalDevice':
                            funcs += 'phys_dev_term->phys_dev'
                        elif param.type == 'VkSurfaceKHR':
                            funcs += 'icd_surface->real_icd_surfaces[icd_index]'
                        else:
                            funcs += param.name
                        count += 1

                    funcs += ');\n'
                    funcs += '    } else {\n'
                    funcs += '        return VK_SUCCESS;\n'
                    funcs += '    }\n'

                funcs += '}\n\n'
            else:
                funcs += tramp_header

                funcs += '    const VkLayerDispatchTable *disp = loader_get_dispatch('
                funcs += ext_cmd.params[0].name
                funcs += ');\n'

                funcs += return_prefix
                funcs += 'disp->'
                funcs += base_name
                funcs += '('
                count = 0
                for param in ext_cmd.params:
                    if count != 0:
                        funcs += ', '
                    funcs += param.name
                    count += 1
                funcs += ');\n'
                funcs += '}\n\n'

            if ext_cmd.protect is not None:
                funcs += '#endif // %s\n' % ext_cmd.protect

        return funcs


    #
    # Create a function for the extension GPA call
    def InstExtensionGPA(self):
        entries = []
        gpa_func = ''

        gpa_func += '// GPA helpers for extensions\n'
        gpa_func += 'bool extension_instance_gpa(struct loader_instance *ptr_instance, const char *name, void **addr) {\n'
        gpa_func += '    *addr = NULL;\n\n'

        for ext_cmd in self.ext_commands:
            if (ext_cmd.ext_name in loader_constants.WSI_EXT_NAMES or
                ext_cmd.ext_name in loader_constants.AVOID_EXT_NAMES):
                continue

            if ext_cmd.protect is not None:
                gpa_func += '#ifdef %s\n' % ext_cmd.protect

            if (ext_cmd.ext_type == 'instance'):
                gpa_func += '    if (!strcmp("%s", name)) {\n' % (ext_cmd.name)
                gpa_func += '        *addr = (ptr_instance->enabled_known_extensions.'
                gpa_func += ext_cmd.ext_name[3:].lower()
                gpa_func += ' == 1)\n'
                gpa_func += '                     ? (void *)%s\n' % (ext_cmd.name)
                gpa_func += '                     : NULL;\n'
                gpa_func += '        return true;\n'
                gpa_func += '    }\n'
            else:
                gpa_func += '    if (!strcmp("%s", name)) {\n' % (ext_cmd.name)
                gpa_func += '        *addr = (void *)%s;\n' % (ext_cmd.name)
                gpa_func += '        return true;\n'
                gpa_func += '    }\n'

            if ext_cmd.protect is not None:
                gpa_func += '#endif // %s\n' % ext_cmd.protect

        gpa_func += '    return false;\n'
        gpa_func += '}\n\n'

        return gpa_func

    #
    # Create the extension name init function
    def InstantExtensionCreate(self):
        entries = []
        entries = self.instanceExtensions
        count = 0

        create_func = ''
        create_func += '// A function that can be used to query enabled extensions during a vkCreateInstance call\n'
        create_func += 'void extensions_create_instance(struct loader_instance *ptr_instance, const VkInstanceCreateInfo *pCreateInfo) {\n'
        create_func += '    for (uint32_t i = 0; i < pCreateInfo->enabledExtensionCount; i++) {\n'
        for ext in entries:
            if (ext.name not in loader_constants.WSI_EXT_NAMES and
                ext.name not in loader_constants.AVOID_EXT_NAMES and
                'android' not in ext.name and ext.num_commands > 0):
                if ext.protect is not None:
                    create_func += '#ifdef %s\n' % ext.protect
                if count == 0:
                    create_func += '        if (0 == strcmp(pCreateInfo->ppEnabledExtensionNames[i], '
                else:
                    create_func += '        } else if (0 == strcmp(pCreateInfo->ppEnabledExtensionNames[i], '
                    
                if 'VK_KHR_GET_PHYSICAL_DEVICE_PROPERTIES2' == ext.name.upper():
                    create_func += 'VK_KHR_GET_PHYSICAL_DEVICE_PROPERTIES_2_EXTENSION_NAME)) {\n'
                else:
                    create_func += ext.name.upper()
                    create_func += '_EXTENSION_NAME)) {\n'

                create_func += '            ptr_instance->enabled_known_extensions.'
                create_func += ext.name[3:].lower()
                create_func += ' = 1;\n'

                if ext.protect is not None:
                    create_func += '#endif // %s\n' % ext.protect
                count += 1

        create_func += '        }\n'
        create_func += '    }\n'
        create_func += '}\n\n'
        return create_func

    #
    # Create code to initialize a dispatch table from the appropriate list of
    # extension entrypoints and return it as a string
    def DeviceExtensionGetTerminator(self):
        term_func = ''

        term_func += '// Some device commands still need a terminator because the loader needs to unwrap something about them.\n'
        term_func += '// In many cases, the item needing unwrapping is a VkPhysicalDevice or VkSurfaceKHR object.  But there may be other items\n'
        term_func += '// in the future.\n'
        term_func += 'PFN_vkVoidFunction get_extension_device_proc_terminator(const char *pName) {\n'
        term_func += '    PFN_vkVoidFunction addr = NULL;\n'

        count = 0
        for ext_cmd in self.ext_commands:
            if ext_cmd.name in loader_constants.DEVICE_CMDS_NEED_TERM:
                if ext_cmd.protect is not None:
                    term_func += '#ifdef %s\n' % ext_cmd.protect

                if count == 0:
                    term_func += '    if'
                else:
                    term_func += '    } else if'
                term_func += '(!strcmp(pName, "%s")) {\n' % (ext_cmd.name)
                term_func += '        addr = (PFN_vkVoidFunction)terminator_%s;\n' % (ext_cmd.name[2:])

                if ext_cmd.protect is not None:
                    term_func += '#endif // %s\n' % ext_cmd.protect

                count += 1

        if count > 0:
            term_func += '    }\n'

        term_func += '    return addr;\n'
        term_func += '}\n\n'

        return term_func

    #
    # Create code to initialize a dispatch table from the appropriate list of
    # core and extension entrypoints and return it as a string
    def InitInstLoaderExtensionDispatchTable(self):
        entries = []
        table = ''

        table += '// This table contains the loader\'s instance dispatch table, which contains\n'
        table += '// default functions if no instance layers are activated.  This contains\n'
        table += '// pointers to "terminator functions".\n'
        table += 'const VkLayerInstanceDispatchTable instance_disp = {\n'

        for x in range(0, 2):
            if x == 0:
                entries = self.core_instance_dispatch_list
            else:
                entries = self.ext_instance_dispatch_list

            for item in entries:
                # Remove 'vk' from proto name
                base_name = item[0][2:]

                if (base_name == 'CreateInstance' or base_name == 'CreateDevice' or
                    base_name == 'EnumerateInstanceExtensionProperties' or
                    base_name == 'EnumerateInstanceLayerProperties'):
                    continue

                if item[1] is not None:
                    table += '#ifdef %s\n' % item[1]

                if base_name == 'GetInstanceProcAddr':
                    table += '    .%s = %s,\n' % (base_name, item[0])
                else:
                    table += '    .%s = terminator_%s,\n' % (base_name, base_name)

                if item[1] is not None:
                    table += '#endif // %s\n' % item[1]
        table += '};\n\n'

        return table

    #
    # Create the extension name whitelist array
    def OutputInstantExtensionWhitelistArray(self):
        entries = []
        entries = self.instanceExtensions

        table = ''
        table += '// A null-terminated list of all of the instance extensions supported by the loader.\n'
        table += '// If an instance extension name is not in this list, but it is exported by one or more of the\n'
        table += '// ICDs detected by the loader, then the extension name not in the list will be filtered out\n'
        table += '// before passing the list of extensions to the application.\n'
        table += 'const char *const LOADER_INSTANCE_EXTENSIONS[] = {\n'
        for ext in entries:
            if ext.protect is not None:
                table += '#ifdef %s\n' % ext.protect
            table += '                                                  '

            if 'VK_KHR_GET_PHYSICAL_DEVICE_PROPERTIES2' == ext.name.upper():
                table += 'VK_KHR_GET_PHYSICAL_DEVICE_PROPERTIES_2_EXTENSION_NAME,\n'
            else:
                table += ext.name.upper()
                table += '_EXTENSION_NAME,\n'

            if ext.protect is not None:
                table += '#endif // %s\n' % ext.protect
        table += '                                                  NULL };\n'
        return table

